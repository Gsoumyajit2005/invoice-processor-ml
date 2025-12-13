import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor, DataCollatorForTokenClassification
from src.sroie_loader import load_sroie
from PIL import Image
from tqdm import tqdm
from seqeval.metrics import f1_score, precision_score, recall_score
from pathlib import Path
import os

# --- 1. Global Configuration & Label Mapping ---
print("Setting up configuration...")
label_list = ['O', 'B-COMPANY', 'I-COMPANY', 'B-DATE', 'I-DATE', 
              'B-ADDRESS', 'I-ADDRESS', 'B-TOTAL', 'I-TOTAL']
label2id = {label: idx for idx, label in enumerate(label_list)}
id2label = {idx: label for idx, label in enumerate(label_list)}

MODEL_CHECKPOINT = "microsoft/layoutlmv3-base"
SROIE_DATA_PATH = os.getenv("SROIE_DATA_PATH", os.path.join("data", "sroie"))

# --- 2. PyTorch Dataset Class ---
class SROIEDataset(Dataset):
    """PyTorch Dataset for SROIE data."""
    def __init__(self, data, processor, label2id):
        self.data = data
        self.processor = processor
        self.label2id = label2id
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        example = self.data[idx]
        
        # Load image and get its dimensions
        image = Image.open(example['image_path']).convert("RGB")
        width, height = image.size
        
        # Normalize bounding boxes
        boxes = []
        for box in example['bboxes']:
            x, y, w, h = box
            x0, y0, x1, y1 = x, y, x + w, y + h
            
            x0_norm = int((x0 / width) * 1000)
            y0_norm = int((y0 / height) * 1000)
            x1_norm = int((x1 / width) * 1000)
            y1_norm = int((y1 / height) * 1000)
            
            # Clip to ensure all values are within the 0-1000 range
            x0_norm = max(0, min(x0_norm, 1000))
            y0_norm = max(0, min(y0_norm, 1000))
            x1_norm = max(0, min(x1_norm, 1000))
            y1_norm = max(0, min(y1_norm, 1000))
            
            boxes.append([x0_norm, y0_norm, x1_norm, y1_norm])
        
        # Convert NER tags to IDs
        word_labels = [self.label2id[label] for label in example['ner_tags']]
        
        # Use processor to encode everything, with truncation
        encoding = self.processor(
            image, 
            text=example['words'], 
            boxes=boxes, 
            word_labels=word_labels, 
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        
        # Squeeze the batch dimension to get 1D tensors
        item = {key: val.squeeze(0) for key, val in encoding.items()}
        return item

# --- 3. Main Training Script ---
def train():
    """Main function to run the training process."""
    # --- Load Data ---
    print("Loading SROIE dataset...")
    raw_dataset = load_sroie(SROIE_DATA_PATH)
    
    # --- Load Processor ---
    print("Creating processor...")
    processor = LayoutLMv3Processor.from_pretrained(MODEL_CHECKPOINT, apply_ocr=False)

    # --- Create PyTorch Datasets and DataLoaders ---
    print("Creating PyTorch datasets and dataloaders...")
    train_dataset = SROIEDataset(raw_dataset['train'], processor, label2id)
    test_dataset = SROIEDataset(raw_dataset['test'], processor, label2id)

    data_collator = DataCollatorForTokenClassification(
        tokenizer=processor.tokenizer,
        padding=True,
        return_tensors="pt"
    )

    train_dataloader = DataLoader(train_dataset, batch_size=2, shuffle=True, collate_fn=data_collator)
    test_dataloader = DataLoader(test_dataset, batch_size=2, shuffle=False, collate_fn=data_collator)

    # --- Load Model ---
    print("Loading LayoutLMv3 model for fine-tuning...")
    model = LayoutLMv3ForTokenClassification.from_pretrained(
        MODEL_CHECKPOINT,
        num_labels=len(label_list),
        id2label=id2label,
        label2id=label2id
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"Training on: {device}")

    # --- Setup Optimizer ---
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5)

    # --- Training Loop ---
    best_f1 = 0
    NUM_EPOCHS = 10

    for epoch in range(NUM_EPOCHS):
        print(f"\n{'='*60}\nEpoch {epoch + 1}/{NUM_EPOCHS}\n{'='*60}")
        
        # --- Training Step ---
        model.train()
        total_train_loss = 0
        train_progress_bar = tqdm(train_dataloader, desc=f"Training Epoch {epoch+1}")
        for batch in train_progress_bar:
            batch = {k: v.to(device) for k, v in batch.items()}
            
            outputs = model(**batch)
            loss = outputs.loss
            
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            
            total_train_loss += loss.item()
            train_progress_bar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        avg_train_loss = total_train_loss / len(train_dataloader)

        # --- Validation Step ---
        model.eval()
        all_predictions = []
        all_labels = []
        with torch.no_grad():
            for batch in tqdm(test_dataloader, desc="Validation"):
                batch = {k: v.to(device) for k, v in batch.items()}
                outputs = model(**batch)
                
                predictions = outputs.logits.argmax(dim=-1)
                labels = batch['labels']

                for i in range(labels.shape[0]):
                    true_labels_i = [id2label[l.item()] for l in labels[i] if l.item() != -100]
                    pred_labels_i = [id2label[p.item()] for p, l in zip(predictions[i], labels[i]) if l.item() != -100]
                    all_labels.append(true_labels_i)
                    all_predictions.append(pred_labels_i)
        
        # --- Calculate Metrics ---
        f1 = f1_score(all_labels, all_predictions)
        precision = precision_score(all_labels, all_predictions)
        recall = recall_score(all_labels, all_predictions)
        
        print(f"\n📊 Epoch {epoch + 1} Results:")
        print(f"  Train Loss: {avg_train_loss:.4f}")
        print(f"  F1 Score:   {f1:.4f}")
        print(f"  Precision:  {precision:.4f}")
        print(f"  Recall:     {recall:.4f}")
        
        # --- Save Best Model ---
        if f1 > best_f1:
            best_f1 = f1
            print(f"  🌟 New best F1! Saving model...")
            save_path = Path("./models/layoutlmv3-sroie-best")
            save_path.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(save_path)
            processor.save_pretrained(save_path)

    print(f"\n🎉 TRAINING COMPLETE! Best F1 Score: {best_f1:.4f}")
    print(f"Model saved to: ./models/layoutlmv3-sroie-best")


if __name__ == '__main__':
    train()
