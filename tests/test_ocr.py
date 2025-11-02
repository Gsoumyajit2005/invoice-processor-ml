import sys
sys.path.append('src')

from preprocessing import load_image, convert_to_grayscale, remove_noise
from ocr import extract_text
import matplotlib.pyplot as plt
import numpy as np

print("=" * 60)
print("🎯 OPTIMIZING GRAYSCALE OCR")
print("=" * 60)

# Load and convert to grayscale
image = load_image('data/raw/receipt3.jpg')
gray = convert_to_grayscale(image)

# Test 1: Different PSM modes
print("\n📊 Testing different Tesseract PSM modes...\n")

psm_configs = [
    ('', 'Default'),
    ('--psm 3', 'Automatic page segmentation'),
    ('--psm 4', 'Single column of text'),
    ('--psm 6', 'Uniform block of text'),
    ('--psm 11', 'Sparse text, find as much as possible'),
    ('--psm 12', 'Sparse text with OSD (Orientation and Script Detection)'),
]

results = {}
for config, desc in psm_configs:
    text = extract_text(gray, config=config)
    results[desc] = text
    print(f"{desc:50s} → {len(text):4d} chars")

# Find best result
best_desc = max(results, key=lambda k: len(results[k]))
best_text = results[best_desc]

print(f"\n✅ WINNER: {best_desc} ({len(best_text)} chars)")

# Test 2: With slight denoising
print("\n📊 Testing with light denoising...\n")

denoised = remove_noise(gray, kernel_size=3)
text_denoised = extract_text(denoised, config='--psm 6')
print(f"Grayscale + Denoise (psm 6): {len(text_denoised)} chars")


# Display best result
print("\n" + "=" * 60)
print("📄 BEST EXTRACTED TEXT:")
print("=" * 60)
print(best_text)
print("=" * 60)

# Visualize
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

axes[0].imshow(image)
axes[0].set_title("Original")
axes[0].axis('off')

axes[1].imshow(gray, cmap='gray')
axes[1].set_title(f"Grayscale\n({len(best_text)} chars - {best_desc})")
axes[1].axis('off')

axes[2].imshow(denoised, cmap='gray')
axes[2].set_title(f"Denoised\n({len(text_denoised)} chars)")
axes[2].axis('off')

plt.tight_layout()
plt.show()

print(f"\n💡 Recommended pipeline: Grayscale + {best_desc}")

# Test the combination we missed!
print("\n📊 Testing BEST combination...\n")

denoised = remove_noise(gray, kernel_size=3)

# Test PSM 11 on denoised
text_denoised_psm11 = extract_text(denoised, config='--psm 11')
text_denoised_psm6 = extract_text(denoised, config='--psm 6')

print(f"Denoised + PSM 6:  {len(text_denoised_psm6)} chars")
print(f"Denoised + PSM 11: {len(text_denoised_psm11)} chars")

if len(text_denoised_psm11) > len(text_denoised_psm6):
    print(f"\n✅ PSM 11 wins! ({len(text_denoised_psm11)} chars)")
    best_config = '--psm 11'
    best_text_final = text_denoised_psm11
else:
    print(f"\n✅ PSM 6 wins! ({len(text_denoised_psm6)} chars)")
    best_config = '--psm 6'
    best_text_final = text_denoised_psm6

print(f"\n🏆 FINAL WINNER: Denoised + {best_config}")
print("\nFull text:")
print("=" * 60)
print(best_text_final)
print("=" * 60)