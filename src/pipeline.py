# src/pipeline.py

"""
Main invoice processing pipeline
Orchestrates preprocessing, OCR, and extraction
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json
from pydantic import ValidationError
import cv2 

# --- IMPORTS ---
from preprocessing import load_image, convert_to_grayscale, remove_noise
from ocr import extract_text
from extraction import structure_output
from ml_extraction import extract_ml_based
from schema import InvoiceData
from pdf_utils import extract_text_from_pdf, convert_pdf_to_images
from utils import generate_semantic_hash

def process_invoice(image_path: str, 
                   method: str = 'ml',
                   save_results: bool = False, 
                   output_dir: str = 'outputs') -> Dict[str, Any]:
    """
    Process an invoice image using either rule-based or ML-based extraction.
    
    Args:
        image_path: Path to the invoice image.
        method: The extraction method to use ('ml' or 'rules'). Default is 'ml'.
        save_results: Whether to save JSON results to a file.
        output_dir: Directory to save results.
    
    Returns:
        A dictionary with the extracted invoice data.
    """
    
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image/PDF not found at path: {image_path}")
    
    print(f"Processing: {image_path}")
    
    raw_result = {}
    is_digital_pdf = False

    # --- 1. SMART PDF HANDLING ---
    if image_path.lower().endswith('.pdf'):
        print("📄 PDF detected. Checking type...")
        try:
            # Attempt to extract text directly (Fast Path)
            digital_text = extract_text_from_pdf(image_path)
            
            # Heuristic: If we found >50 chars, it's likely a native Digital PDF
            if len(digital_text.strip()) > 50:
                print("   ✅ Digital Text found. Using Rule-Based Engine (Fast Mode).")
                # We bypass the ML model because we have perfect text
                raw_result = structure_output(digital_text)
                is_digital_pdf = True
                method = 'rules (digital)' # Override method for logging
            else:
                print("   ⚠️  Sparse text detected. Treating as Scanned PDF.")
                # Convert first page to image for the ML pipeline
                print("   🔄 Converting Page 1 to Image...")
                images = convert_pdf_to_images(image_path)
                
                # Save as temp jpg so our existing pipeline can read it
                # (In production, you might pass the array directly, but this is safer for now)
                temp_jpg = image_path.replace('.pdf', '.jpg')
                cv2.imwrite(temp_jpg, images[0])
                
                # SWAP THE PATH: The rest of the pipeline will now see a JPG!
                image_path = temp_jpg 
                print(f"   ➡️  Continuing with converted image: {image_path}")
                
        except Exception as e:
            print(f"   ❌ PDF Error: {e}. Falling back to standard processing.")

    # --- 2. STANDARD EXTRACTION (ML / RULES) ---
    # Only run this if we didn't already extract from Digital PDF
    if not is_digital_pdf:
        print(f"⚙️  Using '{method}' method on image...")
        
        if method == 'ml':
            try:
                raw_result = extract_ml_based(image_path)
            except Exception as e:
                raise ValueError(f"Error during ML-based extraction: {e}")
                
        elif method == 'rules':
            try:
                image = load_image(image_path)
                gray_image = convert_to_grayscale(image)
                preprocessed_image = remove_noise(gray_image, kernel_size=3)
                text = extract_text(preprocessed_image, config='--psm 6')
                raw_result = structure_output(text)
            except Exception as e:
                raise ValueError(f"Error during rule-based extraction: {e}")
                
        # Clean up temp file if we created one
        if image_path.endswith('.jpg') and 'sample_pdf' in image_path: # Safety check
             # Optional: os.remove(image_path)
             pass
    
    # --- VALIDATION STEP ---
    final_data = raw_result # Default to raw if validation crashes hard

    if method == 'ml':
        try:
            invoice = InvoiceData(**raw_result)
            final_data = invoice.model_dump(mode='json')
            final_data['validation_status'] = 'passed'
            print("✅ Data Validation Passed")
        except ValidationError as e:
            print(f"❌ Data Validation Failed: {len(e.errors())} errors")

            # We keep the 'raw_result' data so the user isn't left with nothing,
            # but we attach the error report so they know what to fix.
            final_data = raw_result.copy()
            final_data['validation_status'] = 'failed'
            
            # Format errors nicely
            error_list = []
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err['loc'])
                msg = err['msg']
                print(f"   - {field}: {msg}")
                error_list.append(f"{field}: {msg}")

            final_data['validation_errors'] = error_list
        
        # Preserve raw_predictions and raw_text for UI visualization (not in schema)
        if 'raw_predictions' in raw_result:
            final_data['raw_predictions'] = raw_result['raw_predictions']
        if 'raw_text' in raw_result:
            final_data['raw_text'] = raw_result['raw_text']

    # --- DUPLICATE DETECTION ---
    # We calculate the hash based on the final (or raw) data.
    # This gives us a unique fingerprint for this specific business transaction.
    final_data['semantic_hash'] = generate_semantic_hash(final_data)
    
    # --- SAVING STEP ---
    if save_results:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Helper to serialize Decimals/Dates for JSON (standard json.dump fails on them)
        # You can use 'default=str' in json.dump or convert before saving
        json_path = output_path / (Path(image_path).stem + f"_{method}.json")
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                # Use default=str to handle Decimal and Date objects automatically
                json.dump(final_data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            raise IOError(f"Error saving results to {json_path}: {e}")

    return final_data


def process_batch(image_folder: str, output_dir: str = 'outputs') -> list:
    """Process multiple invoices in a folder""" # Corrected indentation
    results = []
    
    supported_extensions = ['*.jpg', '*.png', '*.jpeg']
    
    for ext in supported_extensions:
        for img_file in Path(image_folder).glob(ext):
            print(f"🔄 Processing: {img_file}")
            try:
                result = process_invoice(str(img_file), save_results=True, output_dir=output_dir)
                results.append(result)
            except Exception as e:
                print(f"❌ Error processing {img_file}: {e}")
    
    print(f"\n🎉 Batch processing complete! {len(results)} invoices processed.")
    return results


def main():
    """Command-line interface for invoice processing"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Process invoice images or folders and extract structured data.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single invoice
  python src/pipeline.py data/raw/receipt1.jpg

  # Process and save a single invoice
  python src/pipeline.py data/raw/receipt1.jpg --save

  # Process an entire folder of invoices
  python src/pipeline.py data/raw --save --output results/
        """
    )
    
    # Corrected: Single 'path' argument
    parser.add_argument('path', help='Path to an invoice image or a folder of images')
    parser.add_argument('--save', action='store_true', help='Save results to JSON files')
    parser.add_argument('--output', default='outputs', help='Output directory for JSON files')
    parser.add_argument('--method', default='ml', choices=['ml', 'rules'], help="Extraction method: 'ml' or 'rules'")
    
    args = parser.parse_args()
    
    try:
        # Check if path is a directory or a file
        if Path(args.path).is_dir():
            process_batch(args.path, output_dir=args.output)
        elif Path(args.path).is_file():
            # Corrected: Use args.path
            print(f"🔄 Processing: {args.path}")
            result = process_invoice(args.path, method=args.method, save_results=args.save, output_dir=args.output)
            
            print("\n📊 Extracted Data:")
            print("=" * 60)
            print(f"Vendor:         {result.get('vendor', 'N/A')}")
            print(f"Invoice Number: {result.get('invoice_number', 'N/A')}")
            print(f"Date:           {result.get('date', 'N/A')}")
            print(f"Total:          ${result.get('total_amount', 0.0)}")
            print("=" * 60)
            
            if args.save:
                print(f"\n💾 JSON saved to: {args.output}/{Path(args.path).stem}.json")
        else:
            raise FileNotFoundError(f"Path does not exist: {args.path}")
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())