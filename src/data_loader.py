# src/data_loader.py

import json
import ast
import numpy as np
from datasets import load_dataset
from difflib import SequenceMatcher

# --- CONFIGURATION ---
LABEL_MAPPING = {
    # Vendor/Company
    "seller": "COMPANY",
    "store_name": "COMPANY",
    
    # Address
    "store_addr": "ADDRESS",
    
    # Date
    "date": "DATE",
    "invoice_date": "DATE",
    
    # Total
    "total": "TOTAL",
    "total_gross_worth": "TOTAL",

    # Receipt Number / Invoice No
    "invoice_no": "INVOICE_NO",

    # Bill To / Client
    "client": "BILL_TO"
}

def safe_parse(content):
    """Robustly parses input that might be a list, a JSON string, or a Python string literal."""
    if isinstance(content, list):
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        try:
            return ast.literal_eval(content)
        except (ValueError, SyntaxError):
            pass
    return []

def normalize_box(box, width, height):
    """Converts 8-point polygons to 4-point normalized [0-1000] bbox."""
    try:
        # Handle nested format variations
        if isinstance(box, list) and len(box) == 2 and isinstance(box[0], list):
            polygon = box[0]
        elif isinstance(box, list) and len(box) == 4 and isinstance(box[0], list):
            polygon = box
        else:
            return None 

        xs = [point[0] for point in polygon]
        ys = [point[1] for point in polygon]
        
        return [
            int(max(0, min(1000 * (min(xs) / width), 1000))),
            int(max(0, min(1000 * (min(ys) / height), 1000))),
            int(max(0, min(1000 * (max(xs) / width), 1000))),
            int(max(0, min(1000 * (max(ys) / height), 1000)))
        ]
    except Exception:
        return None

def tokenize_and_spread_boxes(words, boxes):
    """
    Splits phrases into individual words and duplicates the bounding box.
    Input: ['Invoice #123'], [BOX_A]
    Output: ['Invoice', '#123'], [BOX_A, BOX_A]
    """
    tokenized_words = []
    tokenized_boxes = []
    
    for word, box in zip(words, boxes):
        # Split by whitespace
        sub_words = str(word).split()
        for sw in sub_words:
            tokenized_words.append(sw)
            tokenized_boxes.append(box)
            
    return tokenized_words, tokenized_boxes

def align_labels(ocr_words, label_map):
    """Matches OCR words to Ground Truth values using Sub-sequence Matching."""
    tags = ["O"] * len(ocr_words)
    
    for target_text, label_class in label_map.items():
        if not target_text: continue
        
        target_tokens = str(target_text).split()
        if not target_tokens: continue
        
        n_target = len(target_tokens)
        
        # Sliding window search
        for i in range(len(ocr_words) - n_target + 1):
            window = ocr_words[i : i + n_target]
            
            # Check match
            match = True
            for j in range(n_target):
                # Clean punctuation for comparison
                w_clean = window[j].strip(".,-:")
                t_clean = target_tokens[j].strip(".,-:")
                if w_clean not in t_clean and t_clean not in w_clean:
                    match = False
                    break
            
            if match:
                tags[i] = f"B-{label_class}"
                for k in range(1, n_target):
                    tags[i + k] = f"I-{label_class}"
                
    return tags

def load_unified_dataset(split="train", sample_size=None):
    print(f"🔄 Loading dataset 'mychen76/invoices-and-receipts_ocr_v1' ({split})...")
    dataset = load_dataset("mychen76/invoices-and-receipts_ocr_v1", split=split)
    
    if sample_size:
        dataset = dataset.select(range(sample_size))
        
    processed_data = []
    
    print("⚙️ Processing, Tokenizing, and Aligning...")
    for example in dataset:
        try:
            image = example['image']
            if image.mode != "RGB":
                image = image.convert("RGB")
            width, height = image.size
            
            # 1. Parse Raw OCR
            raw_words = safe_parse(json.loads(example['raw_data']).get('ocr_words'))
            raw_boxes = safe_parse(json.loads(example['raw_data']).get('ocr_boxes'))
            
            if not raw_words or not raw_boxes or len(raw_words) != len(raw_boxes):
                continue

            # 2. Normalize Boxes first
            norm_boxes = []
            valid_words = []
            for i, box in enumerate(raw_boxes):
                nb = normalize_box(box, width, height)
                if nb:
                    norm_boxes.append(nb)
                    valid_words.append(raw_words[i])

            # 3. TOKENIZE (The Fix)
            final_words, final_boxes = tokenize_and_spread_boxes(valid_words, norm_boxes)

            # 4. Map Labels
            parsed_json = json.loads(example['parsed_data'])
            fields = safe_parse(parsed_json.get('json', {}))
            label_value_map = {}
            if isinstance(fields, dict):
                for k, v in fields.items():
                    if k in LABEL_MAPPING and v:
                        label_value_map[v] = LABEL_MAPPING[k]

            # 5. Align Labels
            final_tags = align_labels(final_words, label_value_map)

            # Only keep if we found at least one entity (cleaner training data)
            unique_tags = set(final_tags)
            if len(unique_tags) > 1: 
                processed_data.append({
                    "image": image,
                    "words": final_words,
                    "bboxes": final_boxes,
                    "ner_tags": final_tags
                })
            
        except Exception:
            continue

    print(f"✅ Successfully processed {len(processed_data)} examples.")
    return processed_data

if __name__ == "__main__":
    # Test run
    data = load_unified_dataset(sample_size=20)
    if len(data) > 0:
        print(f"\nSample 0 Words: {data[0]['words'][:10]}...")
        print(f"Sample 0 Tags:  {data[0]['ner_tags'][:10]}...")
        
        all_tags = [t for item in data for t in item['ner_tags']]
        unique_tags = set(all_tags)
        print(f"\nUnique Tags Found in Sample: {unique_tags}")
    else:
        print("No valid examples found in sample.")