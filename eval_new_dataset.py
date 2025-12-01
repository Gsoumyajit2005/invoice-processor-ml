import torch
from src.data_loader import load_unified_dataset
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor, DataCollatorForTokenClassification
from torch.utils.data import DataLoader
from seqeval.metrics import classification_report
from tqdm import tqdm
from train_combined import UnifiedDataset, label2id, id2label, LABEL_LIST

# Load Model
model_path = "./models/layoutlmv3-generalized"
model = LayoutLMv3ForTokenClassification.from_pretrained(model_path)
processor = LayoutLMv3Processor.from_pretrained(model_path, apply_ocr=False)
device = torch.device("cuda")
model.to(device)

# Load ONLY the new dataset (validation split)
# We want to see how well it learned THIS specific dataset
print("Loading new dataset validation split...")
val_data = load_unified_dataset(split="valid", sample_size=None)
dataset = UnifiedDataset(val_data, processor, label2id)
loader = DataLoader(dataset, batch_size=4, collate_fn=DataCollatorForTokenClassification(processor.tokenizer, padding=True, return_tensors="pt"))

print("Running evaluation...")
model.eval()
preds, labs = [], []

for batch in tqdm(loader):
    batch = {k: v.to(device) for k, v in batch.items()}
    with torch.no_grad():
        outputs = model(**batch)
    
    predictions = outputs.logits.argmax(dim=-1)
    labels = batch['labels']
    
    for i in range(len(labels)):
        p = [id2label[p.item()] for p, l in zip(predictions[i], labels[i]) if l.item() != -100]
        l = [id2label[l.item()] for l in labels[i] if l.item() != -100]
        preds.append(p)
        labs.append(l)

print("\nClassification Report:")
print(classification_report(labs, preds))