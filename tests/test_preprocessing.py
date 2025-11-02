import sys
sys.path.append('src')  # So Python can find our modules

from preprocessing import load_image, convert_to_grayscale, remove_noise, binarize, preprocess_pipeline
import numpy as np
import matplotlib.pyplot as plt

# Test 1: Load a valid image
print("Test 1: Loading receipt1.jpg...")
image = load_image('data/raw/receipt1.jpg')
print(f"✅ Success! Image shape: {image.shape}")
print(f"   Data type: {image.dtype}")
print(f"   Value range: {image.min()} to {image.max()}")

# Test 2: Visualize it
print("\nTest 2: Displaying image...")
plt.imshow(image)
plt.title("Loaded Receipt")
plt.axis('off')
plt.show()
print("✅ If you see the receipt image, it worked!")

# Test 3: Try loading non-existent file
print("\nTest 3: Testing error handling...")
try:
    load_image('data/raw/fake_image.jpg')
    print("❌ Should have raised FileNotFoundError!")
except FileNotFoundError as e:
    print(f"✅ Correctly raised error: {e}")

# Test 4: Grayscale conversion
print("\nTest 4: Converting to grayscale...")
gray = convert_to_grayscale(image)
print(f"✅ Success! Grayscale shape: {gray.shape}")
print(f"   Original had 3 channels, now has: {len(gray.shape)} dimensions")

# Visualize side-by-side
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
ax1.imshow(image)
ax1.set_title("Original (RGB)")
ax1.axis('off')

ax2.imshow(gray, cmap='gray')  # cmap='gray' tells matplotlib to display in grayscale
ax2.set_title("Grayscale")
ax2.axis('off')

plt.tight_layout()
plt.show()

# Test 5: Already grayscale (should return as-is)
print("\nTest 5: Converting already-grayscale image...")
gray_again = convert_to_grayscale(gray)
print(f"✅ Returned without error: {gray_again.shape}")
assert gray_again is gray, "Should return same object if already grayscale"
print("✅ Correctly returned the same image!")

print("\n🎉 Grayscale tests passed!")

# Test 6: Binarization - Simple method
print("\nTest 6: Simple binarization...")
binary_simple = binarize(gray, method='simple')
print(f"✅ Success! Binary shape: {binary_simple.shape}")
print(f"   Unique values: {np.unique(binary_simple)}")  # Should be [0, 255]

# Test 7: Binarization - Adaptive method
print("\nTest 7: Adaptive binarization...")
binary_adaptive = binarize(gray, method='adaptive', block_size=11, C=2)
print(f"✅ Success! Binary shape: {binary_adaptive.shape}")
print(f"   Unique values: {np.unique(binary_adaptive)}")

# Visualize comparison
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

axes[0, 0].imshow(image)
axes[0, 0].set_title("1. Original (RGB)")
axes[0, 0].axis('off')

axes[0, 1].imshow(gray, cmap='gray')
axes[0, 1].set_title("2. Grayscale")
axes[0, 1].axis('off')

axes[1, 0].imshow(binary_simple, cmap='gray')
axes[1, 0].set_title("3. Simple Threshold")
axes[1, 0].axis('off')

axes[1, 1].imshow(binary_adaptive, cmap='gray')
axes[1, 1].set_title("4. Adaptive Threshold")
axes[1, 1].axis('off')

plt.tight_layout()
plt.show()

# Test 8: Error handling
print("\nTest 8: Testing error handling...")
try:
    binarize(image, method='adaptive')  # RGB image (3D) should fail
    print("❌ Should have raised ValueError!")
except ValueError as e:
    print(f"✅ Correctly raised error: {e}")

print("\n🎉 Binarization tests passed!")

# Test 9: Noise removal
print("\nTest 9: Noise removal...")
denoised = remove_noise(gray, kernel_size=3)
print(f"✅ Success! Denoised shape: {denoised.shape}")

# Test different kernel sizes
denoised_light = remove_noise(gray, kernel_size=3)
denoised_heavy = remove_noise(gray, kernel_size=7)

# Visualize comparison
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

axes[0].imshow(gray, cmap='gray')
axes[0].set_title("Original Grayscale")
axes[0].axis('off')

axes[1].imshow(denoised_light, cmap='gray')
axes[1].set_title("Denoised (kernel=3)")
axes[1].axis('off')

axes[2].imshow(denoised_heavy, cmap='gray')
axes[2].set_title("Denoised (kernel=7)")
axes[2].axis('off')

plt.tight_layout()
plt.show()
print("   Notice: kernel=7 is blurrier but removes more noise")

# Test 10: Error handling
print("\nTest 10: Noise removal error handling...")
try:
    remove_noise(gray, kernel_size=4)  # Even number
    print("❌ Should have raised ValueError!")
except ValueError as e:
    print(f"✅ Correctly raised error: {e}")

print("\n🎉 Noise removal tests passed!")

# Test 11: Full pipeline
print("\nTest 11: Full preprocessing pipeline...")

# Test with all steps
full_processed = preprocess_pipeline(image, 
                                     steps=['grayscale', 'denoise', 'binarize'],
                                     denoise_kernel=3,
                                     binarize_method='adaptive')
print(f"✅ Full pipeline success! Shape: {full_processed.shape}")

# Test with selective steps (your clean images)
clean_processed = preprocess_pipeline(image, 
                                      steps=['grayscale', 'binarize'],
                                      binarize_method='adaptive')
print(f"✅ Clean pipeline success! Shape: {clean_processed.shape}")

# Visualize comparison
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

axes[0].imshow(image)
axes[0].set_title("Original")
axes[0].axis('off')

axes[1].imshow(full_processed, cmap='gray')
axes[1].set_title("Full Pipeline\n(grayscale → denoise → binarize)")
axes[1].axis('off')

axes[2].imshow(clean_processed, cmap='gray')
axes[2].set_title("Clean Pipeline\n(grayscale → binarize)")
axes[2].axis('off')

plt.tight_layout()
plt.show()

print("\n🎉 Pipeline tests passed!")

print("\n🎉 All tests passed!")
