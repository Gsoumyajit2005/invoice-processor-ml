from datasets import load_dataset
import json
import ast  # <--- Added for robust parsing

# --- 1. Load the dataset ---
print("📥 Loading 'mychen76/invoices-and-receipts_ocr_v1' from Hugging Face...")
try:
    dataset = load_dataset("mychen76/invoices-and-receipts_ocr_v1", split='train')
    print("✅ Dataset loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load dataset. Error: {e}")
    exit()

# --- 2. Print Dataset Information ---
print("\n" + "="*60)
print("📊 DATASET INFORMATION & FEATURES")
print("="*60)
print(f"Number of examples: {len(dataset)}")
print(f"\nFeatures (Columns): {dataset.features}")


# --- 3. Explore a Single Example ---
print("\n" + "="*60)
print("📄 EXPLORING THE FIRST SAMPLE")
print("="*60)
if len(dataset) > 0:
    sample = dataset[0]
    
    # Parse the main wrapper JSONs
    try:
        raw_data = json.loads(sample['raw_data'])
        parsed_data = json.loads(sample['parsed_data'])
    except json.JSONDecodeError as e:
        print(f"❌ Error decoding main JSON wrappers: {e}")
        exit()

    print(f"\nImage object: {sample['image']}")
    
    # --- ROBUST PARSING LOGIC ---
    def safe_parse(content):
        """Try JSON, fallback to AST (for single quotes)"""
        if isinstance(content, list):
            return content # Already a list
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                try:
                    return ast.literal_eval(content)
                except:
                    return None
        return None

    ocr_words = safe_parse(raw_data.get('ocr_words'))
    ocr_boxes = safe_parse(raw_data.get('ocr_boxes'))
    
    if ocr_words and ocr_boxes:
        print(f"\nFound {len(ocr_words)} OCR words.")
        print("Sample Word & Box Format:")
        # Print first 3 to check coordinate format (4 numbers or 8 numbers?)
        for i in range(min(3, len(ocr_words))):
            print(f"  Word: '{ocr_words[i]}' | Box: {ocr_boxes[i]}")
    else:
        print("❌ OCR fields missing or could not be parsed.")


else:
    print("Dataset is empty.")


# --- 4. Discover All Unique NER Tags ---
print("\n" + "="*60)
print("📋 ALL UNIQUE ENTITY LABELS IN THIS DATASET")
print("="*60)
if len(dataset) > 0:
    all_entity_labels = set()
    
    print("Scanning dataset for labels...")
    for i, example in enumerate(dataset):
        try:
            # Parse parsed_data
            parsed_example = json.loads(example['parsed_data'])
            
            # The 'json' field inside might be a string or a dict
            fields_data = parsed_example.get('json', {})
            
            if isinstance(fields_data, str):
                try:
                    fields = json.loads(fields_data)
                except:
                    fields = ast.literal_eval(fields_data)
            else:
                fields = fields_data
                
            if fields:
                all_entity_labels.update(fields.keys())
                
        except Exception:
            continue # Skip corrupted examples silently
    
    if all_entity_labels:
        print(f"\nFound {len(all_entity_labels)} unique entity labels:")
        print(sorted(list(all_entity_labels)))
    else:
        print("Could not find any entity labels.")
else:
    print("Cannot analyze tags of an empty dataset.")


# Add this to explore_new_dataset.py
sample = dataset[0]
sample['image'].save("data/samples/test_invoice_no.jpg")
print("Saved sample image to data/samples/test_invoice_no.jpg")