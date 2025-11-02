import pytesseract
import numpy as np
from typing import Optional

pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

def extract_text(image: np.ndarray, lang: str='eng', config: str='--psm 11') -> str:
    if image is None:
        raise ValueError("Input image is None")
    text = pytesseract.image_to_string(image, lang=lang, config=config)
    return text.strip()

def extract_text_with_boxes(image):
    pass

