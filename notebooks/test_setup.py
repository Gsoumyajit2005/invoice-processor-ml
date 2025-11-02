# This is just a verification script - you can copy this
import pytesseract
from PIL import Image
import cv2
import numpy as np

# If Windows, you might need to set this path:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

print("✅ All imports successful!")
print(f"Tesseract version: {pytesseract.get_tesseract_version()}")