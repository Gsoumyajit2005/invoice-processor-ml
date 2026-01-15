# scripts/prepare_doctr_data.py

"""
Prepare training data using DocTR OCR output.

This script:
1. Iterates through SROIE training/test images
2. Runs DocTR OCR to get words and boxes
3. Aligns DocTR output with ground truth labels using fuzzy matching
4. Saves the aligned dataset to a pickle file for training

This ensures the model learns from DocTR's actual output (with its specific errors)
rather than from perfect ground truth which it will never see in production.
"""

import torch
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import pickle
from pathlib import Path
from PIL import Image
from tqdm import tqdm
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple, Optional

from doctr.io import DocumentFile
from doctr.models import ocr_predictor

# --- CONFIGURATION ---
SROIE_DATA_PATH = "data/sroie"
OUTPUT_CACHE_PATH = "data/doctr_trained_cache.pkl"

# Ground truth field names and their corresponding BIO labels
GT_FIELD_MAPPING = {
    "company": "COMPANY",
    "date": "DATE", 
    "address": "ADDRESS",
    "total": "TOTAL",
}


def load_doctr_predictor():
    """Initialize DocTR predictor with lightweight backbone and move to GPU."""
    print("Loading DocTR OCR predictor...")
    
    # 1. Initialize the model
    predictor = ocr_predictor(
        det_arch='db_resnet50',
        reco_arch='crnn_vgg16_bn',
        pretrained=True
    )
    
    # 2. Force it to GPU if available
    if torch.cuda.is_available():
        print("🚀 Moving DocTR to GPU (CUDA)...")
        predictor.cuda()
    else:
        print("⚠️ GPU not found. Running on CPU (this will be slow).")
        
    print("DocTR OCR predictor ready.")
    return predictor


def parse_doctr_output(doctr_result, img_width: int, img_height: int) -> Tuple[List[str], List[List[int]]]:
    """
    Parse DocTR output into words and normalized boxes (0-1000 scale).
    
    Returns:
        words: List of word strings
        normalized_boxes: List of [x0, y0, x1, y1] in 0-1000 scale
    """
    words = []
    normalized_boxes = []
    
    for page in doctr_result.pages:
        for block in page.blocks:
            for line in block.lines:
                for word in line.words:
                    if not word.value.strip():
                        continue
                    
                    words.append(word.value)
                    
                    # DocTR bbox format: ((x_min, y_min), (x_max, y_max)) in 0-1 scale
                    (x_min, y_min), (x_max, y_max) = word.geometry
                    
                    # Normalize to 0-1000 scale with clamping
                    normalized_boxes.append([
                        max(0, min(1000, int(x_min * 1000))),
                        max(0, min(1000, int(y_min * 1000))),
                        max(0, min(1000, int(x_max * 1000))),
                        max(0, min(1000, int(y_max * 1000))),
                    ])
    
    return words, normalized_boxes


def fuzzy_match_score(s1: str, s2: str) -> float:
    """Calculate fuzzy match score between two strings."""
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def find_entity_in_words(
    entity_text: str,
    words: List[str],
    start_idx: int = 0,
    threshold: float = 0.7
) -> Optional[Tuple[int, int]]:
    """
    Find a ground truth entity in the DocTR words using fuzzy matching.
    Includes expansion search to handle OCR word splitting.
    """
    entity_words = entity_text.split()
    n_target = len(entity_words)
    
    # 1. Single word match
    if n_target == 1:
        best_score = 0
        best_idx = -1
        for i in range(start_idx, len(words)):
            score = fuzzy_match_score(entity_text, words[i])
            if score > best_score and score >= threshold:
                best_score = score
                best_idx = i
        if best_idx >= 0:
            return (best_idx, best_idx)

    # 2. Multi-word entity: Flexible Window Search
    # We search windows of size N, N+1, N+2... up to N+5 (to catch OCR splits)
    # AND N-1, N-2... (to catch OCR merges)
    
    best_match_score = 0.0
    best_match_indices = None
    
    # Define search range: from (Length - 3) to (Length + 5)
    min_len = max(1, n_target - 3)
    max_len = min(len(words) - start_idx, n_target + 5)
    
    combined_entity_text = " ".join(entity_words)

    # Iterate through window sizes
    for window_size in range(min_len, max_len + 1):
        for i in range(start_idx, len(words) - window_size + 1):
            
            # Construct window text
            window_tokens = words[i : i + window_size]
            window_text = " ".join(window_tokens)
            
            score = fuzzy_match_score(combined_entity_text, window_text)
            
            # Optimization: If perfect match, return immediately
            if score > 0.95:
                return (i, i + window_size - 1)
            
            if score > best_match_score and score >= threshold:
                best_match_score = score
                best_match_indices = (i, i + window_size - 1)

    return best_match_indices


def load_ground_truth(json_path: Path) -> Dict[str, str]:
    """
    Load ground truth entities from the tagged JSON.
    
    The SROIE tagged JSON has: {"words": [...], "bbox": [...], "labels": [...]}
    We need to reconstruct the entity values from words + labels.
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    
    words = data.get("words", [])
    labels = data.get("labels", [])
    
    # Reconstruct entities from BIO tags
    entities = {}
    current_entity = None
    current_text = []
    
    for word, label in zip(words, labels):
        if label.startswith("B-"):
            # Save previous entity if exists
            if current_entity and current_text:
                entities[current_entity.lower()] = " ".join(current_text)
            
            # Start new entity
            current_entity = label[2:]  # Remove "B-" prefix
            current_text = [word]
            
        elif label.startswith("I-") and current_entity:
            entity_type = label[2:]
            if entity_type == current_entity:
                current_text.append(word)
            else:
                # Entity type changed, save current
                if current_text:
                    entities[current_entity.lower()] = " ".join(current_text)
                current_entity = None
                current_text = []
        else:
            # "O" label - save current entity if exists
            if current_entity and current_text:
                entities[current_entity.lower()] = " ".join(current_text)
            current_entity = None
            current_text = []
    
    # Don't forget the last entity
    if current_entity and current_text:
        entities[current_entity.lower()] = " ".join(current_text)
    
    return entities


def align_labels(
    doctr_words: List[str],
    ground_truth: Dict[str, str]
) -> List[str]:
    labels = ["O"] * len(doctr_words)
    used_indices = set()
    
    for gt_field, bio_label in GT_FIELD_MAPPING.items():
        if gt_field not in ground_truth:
            continue
            
        entity_text = ground_truth[gt_field]
        if not entity_text or not entity_text.strip():
            continue
        
        # DYNAMIC THRESHOLD: Be lenient with Addresses, strict with Dates/Totals
        current_threshold = 0.6
        if bio_label == "ADDRESS":
            current_threshold = 0.45  # Lower threshold for messy addresses
        elif bio_label in ["DATE", "TOTAL"]:
            current_threshold = 0.7   # Keep strict for precision fields
        
        match = find_entity_in_words(entity_text, doctr_words, start_idx=0, threshold=current_threshold)
        
        if match:
            start_idx, end_idx = match
            
            # Overlap check
            if any(i in used_indices for i in range(start_idx, end_idx + 1)):
                continue
            
            labels[start_idx] = f"B-{bio_label}"
            for i in range(start_idx + 1, end_idx + 1):
                labels[i] = f"I-{bio_label}"
            
            used_indices.update(range(start_idx, end_idx + 1))
    
    return labels


def process_split(
    split_path: Path,
    predictor,
    split_name: str
) -> List[Dict[str, Any]]:
    """Process all images in a split directory."""
    
    # Find image and annotation directories
    if (split_path / "images").exists():
        img_dir = split_path / "images"
    elif (split_path / "img").exists():
        img_dir = split_path / "img"
    else:
        print(f"   ⚠️ No image directory found in {split_path}")
        return []
    
    if (split_path / "tagged").exists():
        ann_dir = split_path / "tagged"
    elif (split_path / "box").exists():
        ann_dir = split_path / "box"
    else:
        print(f"   ⚠️ No annotation directory found in {split_path}")
        return []
    
    examples = []
    image_files = sorted([f for f in img_dir.iterdir() if f.suffix.lower() in [".jpg", ".png"]])
    
    print(f"   Processing {len(image_files)} images in {split_name}...")
    
    for img_file in tqdm(image_files, desc=f"   {split_name}"):
        try:
            # Check for corresponding annotation
            json_path = ann_dir / f"{img_file.stem}.json"
            if not json_path.exists():
                continue
            
            # Load image dimensions
            with Image.open(img_file) as img:
                width, height = img.size
            
            # Run DocTR OCR
            doc = DocumentFile.from_images(str(img_file))
            doctr_result = predictor(doc)
            
            # Parse DocTR output
            words, boxes = parse_doctr_output(doctr_result, width, height)
            
            if not words:
                continue
            
            # Load ground truth and align labels
            ground_truth = load_ground_truth(json_path)
            aligned_labels = align_labels(words, ground_truth)
            
            # Create example
            examples.append({
                "image_path": str(img_file),
                "words": words,
                "bboxes": boxes,
                "ner_tags": aligned_labels,
                "ground_truth": ground_truth  # Keep for debugging
            })
            
        except Exception as e:
            print(f"\n   ❌ Error processing {img_file.name}: {e}")
            continue
    
    return examples


def main():
    print("=" * 60)
    print("📦 DocTR Training Data Preparation")
    print("=" * 60)
    
    sroie_path = Path(SROIE_DATA_PATH)
    
    if not sroie_path.exists():
        print(f"❌ SROIE path not found: {sroie_path}")
        return
    
    # Load DocTR predictor
    predictor = load_doctr_predictor()
    
    dataset = {"train": [], "test": []}
    
    # Process each split
    for split in ["train", "test"]:
        split_path = sroie_path / split
        if not split_path.exists():
            print(f"   ⚠️ Split not found: {split}")
            continue
        
        print(f"\n📂 Processing {split} split...")
        examples = process_split(split_path, predictor, split)
        dataset[split] = examples
        
        # Stats
        total_entities = sum(
            sum(1 for label in ex["ner_tags"] if label.startswith("B-"))
            for ex in examples
        )
        print(f"   ✅ {len(examples)} images processed")
        print(f"   📊 {total_entities} entities aligned")
    
    # Save cache
    print(f"\n💾 Saving cache to {OUTPUT_CACHE_PATH}...")
    output_path = Path(OUTPUT_CACHE_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "wb") as f:
        pickle.dump(dataset, f)
    
    print(f"✅ Cache saved!")
    print(f"   - Train examples: {len(dataset['train'])}")
    print(f"   - Test examples: {len(dataset['test'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
