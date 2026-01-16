# src/ml_extraction.py

import os
import torch
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
from huggingface_hub import snapshot_download
from PIL import Image
from typing import List, Dict, Any, Tuple
import re
import numpy as np
from extraction import extract_invoice_number, extract_total, extract_address
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

# --- CONFIGURATION ---
LOCAL_MODEL_PATH = "./models/layoutlmv3-doctr-trained"
HUB_MODEL_ID = "GSoumyajit2005/layoutlmv3-doctr-invoice-processor" 

# --- Load LayoutLMv3 Model ---
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

# --- Load DocTR OCR Predictor ---
def load_doctr_predictor():
    """Initialize DocTR predictor and move to GPU for speed."""
    print("Loading DocTR OCR predictor...")
    predictor = ocr_predictor(
        det_arch='db_resnet50',
        reco_arch='crnn_vgg16_bn',
        pretrained=True
    )
    if torch.cuda.is_available():
        print("🚀 Moving DocTR to GPU (CUDA)...")
        predictor.cuda()
    else:
        print("⚠️ GPU not found. Running on CPU (slow).")
        
    print("DocTR OCR predictor is ready.")
    return predictor

MODEL, PROCESSOR = load_model_and_processor(LOCAL_MODEL_PATH, HUB_MODEL_ID)
DOCTR_PREDICTOR = load_doctr_predictor()

if MODEL and PROCESSOR:
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    MODEL.to(DEVICE)
    MODEL.eval()
    print(f"ML Model is ready on device: {DEVICE}")
else:
    DEVICE = None
    print("❌ Could not load ML model.")


def parse_doctr_output(doctr_result, img_width: int, img_height: int) -> Tuple[List[str], List[List[int]], List[List[int]]]:
    """
    Parse DocTR's hierarchical output (Page -> Block -> Line -> Word) 
    into flat lists of words and bounding boxes for LayoutLMv3.
    
    DocTR returns coordinates in 0-1.0 scale (relative to image).
    We convert to:
    - unnormalized_boxes: pixel coordinates [x, y, width, height] for visualization
    - normalized_boxes: 0-1000 scale [x0, y0, x1, y1] for LayoutLMv3
    
    Args:
        doctr_result: Output from DocTR predictor
        img_width: Original image width in pixels
        img_height: Original image height in pixels
        
    Returns:
        words: List of word strings
        unnormalized_boxes: List of [x, y, width, height] in pixel coordinates
        normalized_boxes: List of [x0, y0, x1, y1] in 0-1000 scale
    """
    words = []
    unnormalized_boxes = []
    normalized_boxes = []
    
    # DocTR hierarchy: Document -> Page -> Block -> Line -> Word
    for page in doctr_result.pages:
        for block in page.blocks:
            for line in block.lines:
                for word in line.words:
                    # Skip empty words
                    if not word.value.strip():
                        continue
                    
                    words.append(word.value)
                    
                    # DocTR bbox format: ((x_min, y_min), (x_max, y_max)) in 0-1 scale
                    (x_min, y_min), (x_max, y_max) = word.geometry
                    
                    # Convert to pixel coordinates for visualization
                    px_x0 = int(x_min * img_width)
                    px_y0 = int(y_min * img_height)
                    px_x1 = int(x_max * img_width)
                    px_y1 = int(y_max * img_height)
                    
                    # Unnormalized box: [x, y, width, height] for visualization overlay
                    unnormalized_boxes.append([
                        px_x0, 
                        px_y0, 
                        px_x1 - px_x0,  # width
                        px_y1 - px_y0   # height
                    ])
                    
                    # Normalized box: [x0, y0, x1, y1] in 0-1000 scale for LayoutLMv3
                    # Clamp values to ensure they stay within [0, 1000]
                    normalized_boxes.append([
                        max(0, min(1000, int(x_min * 1000))),
                        max(0, min(1000, int(y_min * 1000))),
                        max(0, min(1000, int(x_max * 1000))),
                        max(0, min(1000, int(y_max * 1000))),
                    ])
    
    return words, unnormalized_boxes, normalized_boxes


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
    
    # 2. Run DocTR OCR
    doc = DocumentFile.from_images(image_path)
    doctr_result = DOCTR_PREDICTOR(doc)
    
    # 3. Parse DocTR output to get words and boxes
    words, unnormalized_boxes, normalized_boxes = parse_doctr_output(
        doctr_result, width, height
    )
    
    # Reconstructs lines so regex can work line-by-line
    lines = []
    current_line = []
    
    if len(unnormalized_boxes) > 0:
        # Initialize with first word's Y and Height
        current_y = unnormalized_boxes[0][1]
        current_h = unnormalized_boxes[0][3]
        
        for i, word in enumerate(words):
            y = unnormalized_boxes[i][1]
            h = unnormalized_boxes[i][3]
            
            # If vertical gap > 50% of line height, it's a new line
            if abs(y - current_y) > max(current_h, h) / 2:
                lines.append(" ".join(current_line))
                current_line = []
                current_y = y
                current_h = h
            
            current_line.append(word)
            
        # Append the last line
        if current_line:
            lines.append(" ".join(current_line))
            
    raw_text = "\n".join(lines)
    
    # Handle empty OCR result
    if not words:
        return {
            "vendor": None,
            "date": None,
            "address": None,
            "receipt_number": None,
            "bill_to": None,
            "total_amount": None,
            "items": [],
            "raw_text": "",
            "raw_predictions": {}
        }

    # 4. Inference with LayoutLMv3
    encoding = PROCESSOR(
        image, text=words, boxes=normalized_boxes, 
        truncation=True, max_length=512, return_tensors="pt"
    ).to(DEVICE)

    with torch.no_grad():
        outputs = MODEL(**encoding)

    predictions = outputs.logits.argmax(-1).squeeze().tolist()
    extracted_entities = _process_predictions(words, unnormalized_boxes, encoding, predictions, MODEL.config.id2label)

    # 5. Construct Output
    final_output = {
        "vendor": extracted_entities.get("COMPANY", {}).get("text"),
        "date": extracted_entities.get("DATE", {}).get("text"),
        "address": extracted_entities.get("ADDRESS", {}).get("text"),
        "receipt_number": extracted_entities.get("INVOICE_NO", {}).get("text"),
        "bill_to": extracted_entities.get("BILL_TO", {}).get("text"),
        "total_amount": None, 
        "items": [],
        "raw_text": raw_text,
        "raw_predictions": extracted_entities  # Contains text and bbox data for each entity
    }

    # 6. Vendor Fallback (Spatial Heuristic)
    # If ML failed to find a vendor, assume the largest text at the top is the vendor
    if not final_output["vendor"] and unnormalized_boxes:
        # Filter for words in the top 20% of the image
        top_words_indices = [
            i for i, box in enumerate(unnormalized_boxes) 
            if box[1] < height * 0.2
        ]
        
        if top_words_indices:
            # Find the word with the largest height (font size)
            largest_idx = max(top_words_indices, key=lambda i: unnormalized_boxes[i][3])
            final_output["vendor"] = words[largest_idx]
    
    # --- ADDRESS FALLBACK ---
    if not final_output["address"]:
        # We pass the extracted (or fallback) Vendor Name to help anchor the search
        # Use the raw text and the known vendor to find the address spatially
        fallback_address = extract_address(raw_text, vendor_name=final_output["vendor"])
        
        if fallback_address:
            final_output["address"] = fallback_address
    
    # Backfill Bounding Boxes for Address Fallback
    # If Regex found the address but ML didn't, find its boxes in the OCR data
    if final_output["address"] and "ADDRESS" not in final_output["raw_predictions"]:
        address_text = final_output["address"]
        address_boxes = []
        
        # The address may span multiple words, so we search for each word
        # Split by comma first (since extract_address joins lines with ", ")
        address_parts = [part.strip() for part in address_text.split(",")]
        
        for part in address_parts:
            part_words = part.split()
            for target_word in part_words:                    
                for i, word in enumerate(words):
                    # Case-insensitive match
                    if target_word.lower() == word.lower() or target_word.lower() in word.lower():
                        address_boxes.append(unnormalized_boxes[i])
                        break  # Only match once per target word
        
        # If we found any boxes, inject into raw_predictions
        if address_boxes:
            final_output["raw_predictions"]["ADDRESS"] = {
                "text": address_text,
                "bbox": address_boxes
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

    # Backfill Bounding Boxes for Regex Results
    # If Regex found the number but ML didn't, we must find its box 
    # in the OCR data so the UI can draw it.

    if final_output["receipt_number"] and "INVOICE_NO" not in final_output["raw_predictions"]:
        target_val = final_output["receipt_number"].strip()
        found_box = None
        
        # 1. Try finding the exact word in the OCR list
        # 'words' and 'unnormalized_boxes' are available from step 3
        for i, word in enumerate(words):
            # Check for exact match or if the word contains the target (e.g. "Inv#123")
            if target_val == word or (len(target_val) > 3 and target_val in word):
                found_box = unnormalized_boxes[i]
                break
        
        # 2. If found, inject it into raw_predictions
        if found_box:
            # The UI expects a list of boxes
            final_output["raw_predictions"]["INVOICE_NO"] = {
                "text": target_val,
                "bbox": [found_box] 
            }
    
    return final_output