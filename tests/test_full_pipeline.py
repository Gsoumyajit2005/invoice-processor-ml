import sys
sys.path.append('src')

from preprocessing import load_image, convert_to_grayscale, remove_noise
from ocr import extract_text
from extraction import structure_output
import json

print("=" * 60)
print("🎯 FULL INVOICE PROCESSING PIPELINE TEST")
print("=" * 60)

# Step 1: Load and preprocess image
print("\n1️⃣ Loading and preprocessing image...")
image = load_image('data/raw/receipt3.jpg')
gray = convert_to_grayscale(image)
denoised = remove_noise(gray, kernel_size=3)
print("✅ Image preprocessed")

# Step 2: Extract text with OCR
print("\n2️⃣ Extracting text with OCR...")
text = extract_text(denoised, config='--psm 6')
print(f"✅ Extracted {len(text)} characters")

# Step 3: Extract structured information
print("\n3️⃣ Extracting structured information...")
result = structure_output(text)
print("✅ Information extracted")

# Step 4: Display results
print("\n" + "=" * 60)
print("📊 EXTRACTED INVOICE DATA (JSON)")
print("=" * 60)
print(json.dumps(result, indent=2, ensure_ascii=False))
print("=" * 60)

print("\n🎉 PIPELINE COMPLETE!")
print("\n📋 Summary:")
print(f"   Vendor: {result['vendor']}")
print(f"   Invoice #: {result['invoice_number']}")
print(f"   Date: {result['date']}")
print(f"   Total: ${result['total']}")