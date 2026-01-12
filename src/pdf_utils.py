# src/pdf_utils.py

import pdfplumber
from pdf2image import convert_from_path
from pathlib import Path
from typing import List, Union
import numpy as np
import cv2

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts raw text from a digital PDF"""

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"
            return full_text.strip()
            
    except Exception as e:
        raise ValueError(f"Failed to read PDF {pdf_path}: {str(e)}")


def convert_pdf_to_images(pdf_path: str) -> List[np.ndarray]:
    """
    Converts a PDF into a list of OpenCV images (numpy arrays).
    Required for the ML pipeline (LayoutLM) or Scanned PDFs.
    
    Logic:
    1. Use 'convert_from_path' to get PIL images.
    2. Convert PIL images to numpy arrays (OpenCV format).
    3. Return list of arrays.
    """
    # 1. Convert to PIL images
    try:
        pil_images = convert_from_path(pdf_path)
    except Exception as e:
        raise ValueError(f"Error converting PDF to image: {e}")

    cv_images = []
    for pil_img in pil_images:
        
        array = np.array(pil_img)
        cv_images.append(cv2.cvtColor(array, cv2.COLOR_RGB2BGR))
        
    return cv_images