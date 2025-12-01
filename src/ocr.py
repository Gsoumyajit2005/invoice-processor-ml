# src/ocr.py

import pytesseract
import numpy as np
import os
import shutil
import sys

# --- Dynamic Tesseract Configuration ---
# This block ensures the code runs on both Windows (Local) and Linux (Production)
if os.name == 'nt': # Windows
    # Common default installation paths for Windows
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getlogin())
    ]
    
    # Search for the executable
    found = False
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            found = True
            print(f"✅ Found Tesseract at: {path}")
            break
            
    if not found:
        print("⚠️ Warning: Tesseract exe not found in standard paths. Assuming it's in system PATH.")
else:
    # Linux/Mac (Docker/Production)
    if not shutil.which('tesseract'):
        print("⚠️ Warning: 'tesseract' binary not found in PATH. Please install tesseract-ocr.")

def extract_text(image: np.ndarray, lang: str='eng', config: str='--psm 11') -> str:
    if image is None:
        raise ValueError("Input image is None")
    # Pytesseract will now use the path found above (or default to PATH)
    return pytesseract.image_to_string(image, lang=lang, config=config).strip()

def extract_text_with_boxes(image):
    pass