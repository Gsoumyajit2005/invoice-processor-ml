# src/ml_extraction.py

import os
import torch
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from huggingface_hub import snapshot_download
from PIL import Image
import pytesseract
from typing import List, Dict, Any
import re
import numpy as np
from extraction import extract_invoice_number, extract_total

# --- CONFIGURATION ---
LOCAL_MODEL_PATH = "./models/layoutlmv3-generalized"
HUB_MODEL_ID = "GSoumyajit2005/layoutlmv3-sroie-invoice-extraction" 

# --- Load Model ---
def load_model_and_processor(model_path, hub_id):
    print("Loading processor from microsoft/layoutlmv3-base...")
    processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base", apply_ocr=False)

    if not os.path.exists(model_path) or not os.listdir(model_path):
        print(f"Downloading model from Hub: {hub_id}...")
        snapshot_download(repo_id=hub_id, local_dir=model_path, local_dir_use_symlinks=False)

    try:
        model = LayoutLMv3ForTokenClassification.from_pretrained(model_path)
    except Exception:
        print(f"Fallback: Loading directly from Hub {hub_id}...")
        model = LayoutLMv3ForTokenClassification.from_pretrained(hub_id)

    return model, processor

MODEL, PROCESSOR = load_model_and_processor(LOCAL_MODEL_PATH, HUB_MODEL_ID)

if MODEL and PROCESSOR:
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    MODEL.to(DEVICE)
    MODEL.eval()
    print(f"ML Model is ready on device: {DEVICE}")
else:
    DEVICE = None
    print("❌ Could not load ML model.")

def _process_predictions(words, unnormalized_boxes, encoding, predictions, id2label):
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
            entities[entity_type]['text'] += " " + word
            entities[entity_type]['bbox'].append(unnormalized_boxes[word_idx])
    
    for entity in entities.values():
        entity['text'] = entity['text'].strip()

    return entities

def extract_ml_based(image_path: str) -> Dict[str, Any]:
    if not MODEL or not PROCESSOR:
        raise RuntimeError("ML model is not loaded.")

    # 1. Load Image
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    
    words = []
    unnormalized_boxes = []
    for i in range(len(ocr_data['level'])):
        if int(ocr_data['conf'][i]) > 30 and ocr_data['text'][i].strip() != '':
            words.append(ocr_data['text'][i])
            unnormalized_boxes.append([
                ocr_data['left'][i], ocr_data['top'][i], 
                ocr_data['width'][i], ocr_data['height'][i]
            ])
            
    raw_text = " ".join(words)

    # 2. Normalize Boxes (WITH SAFETY CLAMP)
    normalized_boxes = []
    for box in unnormalized_boxes:
        x, y, w, h = box
        x0, y0, x1, y1 = x, y, x + w, y + h
        
        # ⚠️ The Fix: Ensure values never exceed 1000 or drop below 0
        normalized_boxes.append([
            max(0, min(1000, int(1000 * (x0 / width)))),
            max(0, min(1000, int(1000 * (y0 / height)))),
            max(0, min(1000, int(1000 * (x1 / width)))),
            max(0, min(1000, int(1000 * (y1 / height)))),
        ])

    # 3. Inference
    encoding = PROCESSOR(
        image, text=words, boxes=normalized_boxes, 
        truncation=True, max_length=512, return_tensors="pt"
    ).to(DEVICE)

    with torch.no_grad():
        outputs = MODEL(**encoding)

    predictions = outputs.logits.argmax(-1).squeeze().tolist()
    extracted_entities = _process_predictions(words, unnormalized_boxes, encoding, predictions, MODEL.config.id2label)

    # 4. Construct Output
    final_output = {
        "vendor": extracted_entities.get("COMPANY", {}).get("text"),
        "date": extracted_entities.get("DATE", {}).get("text"),
        "address": extracted_entities.get("ADDRESS", {}).get("text"),
        "receipt_number": extracted_entities.get("INVOICE_NO", {}).get("text"),
        "bill_to": extracted_entities.get("BILL_TO", {}).get("text"),
        "total_amount": None, 
        "items": [],
        "raw_text": raw_text
    }

    # Fallbacks
    ml_total = extracted_entities.get("TOTAL", {}).get("text")
    if ml_total:
        try:
            cleaned = re.sub(r'[^\d.,]', '', ml_total).replace(',', '.')
            final_output["total_amount"] = float(cleaned)
        except (ValueError, TypeError):
            pass
            
    if final_output["total_amount"] is None:
        final_output["total_amount"] = extract_total(raw_text)

    if not final_output["receipt_number"]:
        final_output["receipt_number"] = extract_invoice_number(raw_text)
    
    return final_output