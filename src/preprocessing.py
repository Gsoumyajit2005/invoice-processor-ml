import cv2
import numpy as np
from pathlib import Path



def load_image(image_path: str) -> np.ndarray:
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found : {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image
        

def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    if image is None:
        raise ValueError(f"Image is None, cannot convert to grayscale")
    if len(image.shape) ==2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)


def remove_noise(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    if image is None:
        raise ValueError(f"Image is None, cannot remove noise")
    if kernel_size <= 0:
        raise ValueError("Kernel size must be positive")
    if kernel_size % 2 == 0:
        raise ValueError("Kernel size must be odd")
    denoised_image = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    return denoised_image


def binarize(image: np.ndarray, method: str = 'adaptive', block_size: int=11, C: int=2) -> np.ndarray:
    if image is None:
        raise ValueError(f"Image is None, cannot binarize")
    if image.ndim != 2:
        raise ValueError("Input image must be grayscale for binarization")
    if method == 'simple':
        _, binary_image = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
    elif method == 'adaptive':
        binary_image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY, block_size, C)
    else:
        raise ValueError(f"Unknown binarization method: {method}")
    return binary_image


def deskew(image):
    pass


def preprocess_pipeline(image: np.ndarray, 
                       steps: list = ['grayscale', 'denoise', 'binarize'],
                       denoise_kernel: int = 3,
                       binarize_method: str = 'adaptive',
                       binarize_block_size: int = 11,
                       binarize_C: int = 2) -> np.ndarray:
    if image is None:
        raise ValueError("Input image is None")
    
    processed = image
    
    for step in steps:
        if step == 'grayscale':
            processed = convert_to_grayscale(processed)
        elif step == 'denoise':
            processed = remove_noise(processed, kernel_size=denoise_kernel)
        elif step == 'binarize':
            processed = binarize(processed, 
                               method=binarize_method,
                               block_size=binarize_block_size, 
                               C=binarize_C)
        else:
            raise ValueError(f"Unknown preprocessing step: {step}")
    
    return processed
