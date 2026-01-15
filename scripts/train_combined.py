import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor, DataCollatorForTokenClassification
from PIL import Image
from tqdm import tqdm
from seqeval.metrics import f1_score
from pathlib import Path
import numpy as np
import random
import os
import pickle

# --- IMPORTS ---
from src.sroie_loader import load_sroie
from src.data_loader import load_unified_dataset

# --- CONFIGURATION ---
# Points to your local SROIE copy
SROIE_DATA_PATH = "data/sroie" 
DOCTR_CACHE_PATH = "data/doctr_trained_cache.pkl"  # DocTR pre-processed cache
MODEL_CHECKPOINT = "microsoft/layoutlmv3-base"
OUTPUT_DIR = "models/layoutlmv3-doctr-trained"

# Standard Label Set
LABEL_LIST = ['O', 'B-COMPANY', 'I-COMPANY', 'B-DATE', 'I-DATE', 
              'B-ADDRESS', 'I-ADDRESS', 'B-TOTAL', 'I-TOTAL', 
              'B-INVOICE_NO', 'I-INVOICE_NO','B-BILL_TO', 'I-BILL_TO']
label2id = {label: idx for idx, label in enumerate(LABEL_LIST)}
id2label = {idx: label for idx, label in enumerate(LABEL_LIST)}

class UnifiedDataset(Dataset):
    def __init__(self, data, processor, label2id):
        self.data = data
        self.processor = processor
        self.label2id = label2id
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        example = self.data[idx]
        
        # 1. Image Loading
        try:
            if 'image' in example and isinstance(example['image'], Image.Image):
                image = example['image']
            elif 'image_path' in example:
                image = Image.open(example['image_path']).convert("RGB")
            else:
                image = Image.new('RGB', (224, 224), color='white')
        except Exception:
             image = Image.new('RGB', (224, 224), color='white')

        # 2. Boxes are ALREADY normalized!
        # Just need to ensure they are integers and valid
        boxes = []
        for box in example['bboxes']:
             # Extra safety clamp, just in case
             safe_box = [
                 max(0, min(int(box[0]), 1000)),
                 max(0, min(int(box[1]), 1000)),
                 max(0, min(int(box[2]), 1000)),
                 max(0, min(int(box[3]), 1000))
             ]
             boxes.append(safe_box)
        
        # 3. Label Encoding
        word_labels = []
        for label in example['ner_tags']:
            word_labels.append(self.label2id.get(label, 0))
        
        # 4. Processor Encoding
        encoding = self.processor(
            image, 
            text=example['words'], 
            boxes=boxes, 
            word_labels=word_labels, 
            truncation=True, 
            padding="max_length", 
            max_length=512, 
            return_tensors="pt"
        )
        
        return {k: v.squeeze(0) for k, v in encoding.items()}


def load_doctr_cache(cache_path: str) -> dict:
    """Load pre-processed DocTR training data from cache."""
    print(f"📦 Loading DocTR cache from {cache_path}...")
    with open(cache_path, "rb") as f:
        data = pickle.load(f)
    print(f"   ✅ Loaded {len(data.get('train', []))} train, {len(data.get('test', []))} test examples")
    return data


def train():
    print(f"{'='*40}\n🚀 STARTING HYBRID TRAINING\n{'='*40}")
    
    # 1. Load SROIE data (prefer DocTR cache if available)
    if os.path.exists(DOCTR_CACHE_PATH):
        print("🔄 Using DocTR-aligned training data (recommended)")
        sroie_data = load_doctr_cache(DOCTR_CACHE_PATH)
    else:
        print("⚠️  DocTR cache not found. Using original SROIE loader.")
        print("   Run 'python scripts/prepare_doctr_data.py' to generate the cache.")
        
        if not os.path.exists(SROIE_DATA_PATH):
            print(f"❌ Error: SROIE path not found at {SROIE_DATA_PATH}")
            print("Please make sure you copied the 'sroie' folder into 'data/'.")
            return
        
        sroie_data = load_sroie(SROIE_DATA_PATH)
    
    print(f"   - SROIE Train: {len(sroie_data['train'])}")
    print(f"   - SROIE Test:  {len(sroie_data['test'])}")

    # 2. Load New Dataset
    print("📦 Loading General Invoice dataset...")
    # Reduced sample size slightly to stay safe on RAM
    new_data = load_unified_dataset(split='train', sample_size=600) 
    
    random.shuffle(new_data)
    split_idx = int(len(new_data) * 0.9)
    new_train = new_data[:split_idx]
    new_test = new_data[split_idx:]
    
    print(f"   - General Train: {len(new_train)}")
    print(f"   - General Test:  {len(new_test)}")

    # 3. Merge
    full_train_data = sroie_data['train'] + new_train
    full_test_data = sroie_data['test'] + new_test
    print(f"\n🔗 COMBINED DATASET SIZE: {len(full_train_data)} Training Images")

    # 4. Setup Model
    processor = LayoutLMv3Processor.from_pretrained(MODEL_CHECKPOINT, apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained(
        MODEL_CHECKPOINT, num_labels=len(LABEL_LIST),
        id2label=id2label, label2id=label2id
    )
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"   - Device: {device}")
    
    # 5. Dataloaders
    train_ds = UnifiedDataset(full_train_data, processor, label2id)
    test_ds = UnifiedDataset(full_test_data, processor, label2id)
    
    collator = DataCollatorForTokenClassification(processor.tokenizer, padding=True, return_tensors="pt")
    train_loader = DataLoader(train_ds, batch_size=2, shuffle=True, collate_fn=collator)
    test_loader = DataLoader(test_ds, batch_size=2, collate_fn=collator)

    # 6. Optimize & Train
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-5)
    best_f1 = 0.0
    NUM_EPOCHS = 10
    
    print("\n🔥 Beginning Fine-Tuning...")
    for epoch in range(NUM_EPOCHS):
        model.train()
        total_loss = 0
        
        progress = tqdm(train_loader, desc=f"Epoch {epoch+1}/{NUM_EPOCHS}")
        for batch in progress:
            batch = {k: v.to(device) for k, v in batch.items()}
            
            optimizer.zero_grad()
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            progress.set_postfix({"loss": f"{loss.item():.4f}"})
            
        # --- Evaluation ---
        model.eval()
        all_preds, all_labels = [], []
        print("   Running Validation...")
        with torch.no_grad():
            for batch in test_loader:
                batch = {k: v.to(device) for k, v in batch.items()}
                outputs = model(**batch)
                predictions = outputs.logits.argmax(dim=-1)
                labels = batch['labels']
                
                for i in range(len(labels)):
                    true_labels = [id2label[l.item()] for l in labels[i] if l.item() != -100]
                    pred_labels = [id2label[p.item()] for p, l in zip(predictions[i], labels[i]) if l.item() != -100]
                    all_labels.append(true_labels)
                    all_preds.append(pred_labels)

        f1 = f1_score(all_labels, all_preds)
        print(f"   📊 Epoch {epoch+1} F1 Score: {f1:.4f}")
        
        if f1 > best_f1:
            best_f1 = f1
            print(f"   💾 Saving Improved Model to {OUTPUT_DIR}")
            Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
            model.save_pretrained(OUTPUT_DIR)
            processor.save_pretrained(OUTPUT_DIR)

if __name__ == "__main__":
    train()