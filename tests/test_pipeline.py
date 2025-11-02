import sys
import json
from pathlib import Path

# Add the 'src' directory to the Python path
sys.path.append('src')

from pipeline import process_invoice

def test_full_pipeline():
    """
    Tests the full invoice processing pipeline on a sample receipt
    and prints the advanced JSON structure.
    """
    print("=" * 60)
    print("🎯 ADVANCED INVOICE PROCESSING PIPELINE TEST")
    print("=" * 60)

    # --- Configuration ---
    image_path = 'data/raw/receipt1.jpg'
    save_output = True
    output_dir = 'outputs'

    # Check if the image exists
    if not Path(image_path).exists():
        print(f"❌ ERROR: Test image not found at '{image_path}'")
        return

    # --- Processing ---
    print(f"\n🔄 Processing invoice: {image_path}...")
    try:
        # Call the main processing function
        result = process_invoice(image_path, save_results=save_output, output_dir=output_dir)
        print("✅ Invoice processed successfully!")
    except Exception as e:
        print(f"❌ An error occurred during processing: {e}")
        # Print traceback for detailed debugging
        import traceback
        traceback.print_exc()
        return

    # --- Display Results ---
    print("\n" + "=" * 60)
    print("📊 EXTRACTED INVOICE DATA (Advanced JSON)")
    print("=" * 60)

    # Pretty-print the JSON to the console
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("📋 SUMMARY OF KEY EXTRACTED FIELDS")
    print("=" * 60)

    # --- Print a clean summary ---
    print(f"📄 Receipt Number: {result.get('receipt_number', 'N/A')}")
    print(f"📅 Date: {result.get('date', 'N/A')}")
    
    # Print Bill To info safely
    bill_to = result.get('bill_to')
    if bill_to and isinstance(bill_to, dict):
        print(f"👤 Bill To: {bill_to.get('name', 'N/A')}")
    else:
        print("👤 Bill To: N/A")

    # Print line items
    print("\n🛒 Line Items:")
    items = result.get('items', [])
    if items:
        for i, item in enumerate(items, 1):
            desc = item.get('description', 'No Description')
            qty = item.get('quantity', 1)
            total = item.get('total', 0.0)
            print(f"  - Item {i}: {desc[:40]:<40} | Qty: {qty} | Total: {total:.2f}")
    else:
        print("  - No line items extracted.")

    # Print total and validation status
    print(f"\n💵 Total Amount: ${result.get('total_amount', 0.0):.2f}")
    
    confidence = result.get('extraction_confidence', 0)
    print(f"📈 Confidence: {confidence}%")

    validation = "✅ Passed" if result.get('validation_passed', False) else "❌ Failed"
    print(f"✔️ Validation: {validation}")
    
    print("\n" + "=" * 60)
    
    if save_output:
        json_path = Path(output_dir) / (Path(image_path).stem + '.json')
        print(f"\n💾 Full JSON output saved to: {json_path}")

    print("\n🎉 PIPELINE TEST COMPLETE!")


if __name__ == '__main__':
    test_full_pipeline()