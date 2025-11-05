"""
Main invoice processing pipeline
Orchestrates preprocessing, OCR, and extraction
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json

# Make sure all your modules are imported
from preprocessing import load_image, convert_to_grayscale, remove_noise
from ocr import extract_text
from extraction import structure_output
from ml_extraction import extract_ml_based

def process_invoice(image_path: str, 
                   method: str = 'ml', # <-- New parameter: 'ml' or 'rules'
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
        raise FileNotFoundError(f"Image not found at path: {image_path}")
    
    print(f"Processing with '{method}' method...")

    if method == 'ml':
        # --- ML-Based Extraction ---
        try:
            # The ml_extraction function handles everything internally
            structured_data = extract_ml_based(image_path)
        except Exception as e:
            raise ValueError(f"Error during ML-based extraction: {e}")
            
    elif method == 'rules':
        # --- Rule-Based Extraction (Your original logic) ---
        try:
            image = load_image(image_path)
            gray_image = convert_to_grayscale(image)
            preprocessed_image = remove_noise(gray_image, kernel_size=3)
            text = extract_text(preprocessed_image, config='--psm 6')
            structured_data = structure_output(text) # Calls your old extraction.py
        except Exception as e:
            raise ValueError(f"Error during rule-based extraction: {e}")
            
    else:
        raise ValueError(f"Unknown extraction method: '{method}'. Choose 'ml' or 'rules'.")

    # --- Saving Logic (remains the same) ---
    if save_results:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        json_path = output_path / (Path(image_path).stem + f"_{method}.json") # Add method to filename
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Error saving results to {json_path}: {e}")

    return structured_data


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
            print(f"Total:          ${result.get('total', 0.0)}")
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