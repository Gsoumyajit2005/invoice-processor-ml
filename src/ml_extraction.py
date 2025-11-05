# src/ml_extraction.py

import torch
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from PIL import Image
import pytesseract
from typing import List, Dict, Any
import re

# --- CONFIGURATION ---
# The local path where we expect to find/save the model
LOCAL_MODEL_PATH = "./models/layoutlmv3-sroie-best"
# The Hugging Face Hub ID for the model to download if not found locally
HUB_MODEL_ID = "GSoumyajit2005/layoutlmv3-sroie-invoice-extraction" 

# --- Function to load the model ---
def load_model_and_processor(model_path, hub_id):
    """
    Tries to load the model from a local path. If it fails,
    it downloads it from the Hugging Face Hub.
    """
    try:
        # Try loading from local path first
        print(f"Attempting to load model from local path: {model_path}...")
        processor = LayoutLMv3Processor.from_pretrained(model_path)
        model = LayoutLMv3ForTokenClassification.from_pretrained(model_path)
        print("✅ Model loaded successfully from local path.")
    except OSError:
        # If it fails, download from the Hub
        print(f"Model not found locally. Downloading from Hugging Face Hub: {hub_id}...")
        from huggingface_hub import snapshot_download
        # Download the model files and save them to the local path
        snapshot_download(repo_id=hub_id, local_dir=model_path, local_dir_use_symlinks=False)
        # Now load from the local path again
        processor = LayoutLMv3Processor.from_pretrained(model_path)
        model = LayoutLMv3ForTokenClassification.from_pretrained(model_path)
        print("✅ Model downloaded and loaded successfully from the Hub.")
        
    return model, processor

# --- Load the model and processor only ONCE when the module is imported ---
MODEL, PROCESSOR = load_model_and_processor(LOCAL_MODEL_PATH, HUB_MODEL_ID)

if MODEL and PROCESSOR:
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    MODEL.to(DEVICE)
    MODEL.eval()
    print(f"ML Model is ready on device: {DEVICE}")
else:
    DEVICE = None
    print("❌ Could not load ML model.")

# --- Helper Function to group entities ---
def _process_predictions(words: List[str], unnormalized_boxes: List[List[int]], encoding, predictions: List[int], id2label: Dict[int, str]) -> Dict[str, Any]:
    word_ids = encoding.word_ids(batch_index=0)
    
    word_level_preds = {} 
    for idx, word_id in enumerate(word_ids):
        if word_id is not None:
            label_id = predictions[idx]
            if label_id != -100:
                if word_id not in word_level_preds:
                    word_level_preds[word_id] = id2label[label_id]

    entities = {}
    for word_idx, label in word_level_preds.items():
        if label == 'O': continue
        
        entity_type = label[2:] 
        word = words[word_idx]
        
        if label.startswith('B-'):
            entities[entity_type] = {"text": word, "bbox": [unnormalized_boxes[word_idx]]}
        elif label.startswith('I-') and entity_type in entities:
            if word_idx > 0 and word_level_preds.get(word_idx - 1) in (f'B-{entity_type}', f'I-{entity_type}'):
                entities[entity_type]['text'] += " " + word
                entities[entity_type]['bbox'].append(unnormalized_boxes[word_idx])
            else:
                 entities[entity_type] = {"text": word, "bbox": [unnormalized_boxes[word_idx]]}
    
    # Clean up the final text field
    for entity in entities.values():
        entity['text'] = entity['text'].strip()

    return entities

# --- Main Function to be called from the pipeline ---
def extract_ml_based(image_path: str) -> Dict[str, Any]:
    """
    Performs end-to-end ML-based extraction on a single image.
    
    Args:
        image_path: The path to the invoice image.
        
    Returns:
        A dictionary containing the extracted entities.
    """
    if not MODEL or not PROCESSOR:
        raise RuntimeError("ML model is not loaded. Cannot perform extraction.")

    # 1. Load Image
    image = Image.open(image_path).convert("RGB")
    width, height = image.size

    # 2. Perform OCR
    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    n_boxes = len(ocr_data['level'])
    words = []
    unnormalized_boxes = []
    for i in range(n_boxes):
        if int(ocr_data['conf'][i]) > 60 and ocr_data['text'][i].strip() != '':
            word = ocr_data['text'][i]
            (x, y, w, h) = (ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i])
            words.append(word)
            unnormalized_boxes.append([x, y, x + w, y + h])

    # 3. Normalize Boxes and Prepare Inputs
    normalized_boxes = []
    for box in unnormalized_boxes:
        normalized_boxes.append([
            int(1000 * (box[0] / width)),
            int(1000 * (box[1] / height)),
            int(1000 * (box[2] / width)),
            int(1000 * (box[3] / height)),
        ])

    # 4. Process with LayoutLMv3 Processor
    encoding = PROCESSOR(
        image, 
        text=words, 
        boxes=normalized_boxes, 
        truncation=True, 
        max_length=512, 
        return_tensors="pt"
    ).to(DEVICE)

    # 5. Run Inference
    with torch.no_grad():
        outputs = MODEL(**encoding)

    predictions = outputs.logits.argmax(-1).squeeze().tolist()
    
    # 6. Post-process to get final entities
    extracted_entities = _process_predictions(words, unnormalized_boxes, encoding, predictions, MODEL.config.id2label)

    # 7. Format the output to be consistent with your rule-based output
        # Format the output to be consistent with the desired UI structure
        # Format the output to be a superset of all possible fields
    final_output = {
        # --- Standard UI Fields ---
        "receipt_number": None,  # SROIE doesn't train for this. Your regex model will provide it.
        "date": extracted_entities.get("DATE", {}).get("text"),
        "bill_to": None,         # SROIE doesn't train for this. Your regex model will provide it.
        "items": [],             # SROIE doesn't train for line items.
        "total_amount": None,
        
        # --- Additional Fields from ML Model ---
        "vendor": extracted_entities.get("COMPANY", {}).get("text"), # The ML model finds 'COMPANY'
        "address": extracted_entities.get("ADDRESS", {}).get("text"),
        
        # --- Debugging Info ---
        "raw_text": " ".join(words),
        "raw_ocr_words": words,
        "raw_predictions": extracted_entities
    }

    # Safely extract and convert total
    total_text = extracted_entities.get("TOTAL", {}).get("text")
    if total_text:
        try:
            cleaned_total = re.sub(r'[^\d.]', '', total_text)
            final_output["total_amount"] = float(cleaned_total)
        except (ValueError, TypeError):
            final_output["total_amount"] = None

    return final_output