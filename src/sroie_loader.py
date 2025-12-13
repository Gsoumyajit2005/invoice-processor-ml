import json
from pathlib import Path
from PIL import Image

def load_sroie(path):
    print(f"🔄 Loading SROIE from local path: {path}")
    path = Path(path)
    dataset = {'train': [], 'test': []}
    
    for split in ["train", "test"]:
        split_path = path / split
        
        if (split_path / "images").exists(): img_dir = split_path / "images"
        elif (split_path / "img").exists(): img_dir = split_path / "img"
        else: continue

        if (split_path / "tagged").exists(): ann_dir = split_path / "tagged"
        elif (split_path / "box").exists(): ann_dir = split_path / "box"
        else: continue

        examples = []
        for img_file in sorted(img_dir.iterdir()):
            if img_file.suffix.lower() not in [".jpg", ".png"]: continue
            
            name = img_file.stem
            json_path = ann_dir / f"{name}.json"
            if not json_path.exists(): continue
                
            with open(json_path, encoding="utf8") as f:
                data = json.load(f)
            
            if "words" in data and "bbox" in data and "labels" in data:
                # --- NORMALIZATION HAPPENS HERE (YOUR FIX) ---
                try:
                    with Image.open(img_file) as img:
                        width, height = img.size
                    
                    norm_boxes = []
                    for box in data["bbox"]:
                        # SROIE is raw [x0, y0, x1, y1]
                        x0, y0, x1, y1 = box
                        
                        # Normalize and Clamp
                        norm_box = [
                            int(max(0, min(1000 * (x0 / width), 1000))),
                            int(max(0, min(1000 * (y0 / height), 1000))),
                            int(max(0, min(1000 * (x1 / width), 1000))),
                            int(max(0, min(1000 * (y1 / height), 1000)))
                        ]
                        norm_boxes.append(norm_box)

                    examples.append({
                        "image_path": str(img_file),
                        "words": data["words"],
                        "bboxes": norm_boxes, # Storing normalized boxes
                        "ner_tags": data["labels"]
                    })
                except Exception as e:
                    print(f"Skipping {name}: {e}")
                    continue
        
        dataset[split] = examples
        print(f"   Mapped {len(examples)} paths for {split}")
    
    return dataset