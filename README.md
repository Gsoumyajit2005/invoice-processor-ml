---
title: Invoice Processor Ml
emoji: ⚡
colorFrom: indigo
colorTo: pink
sdk: docker
pinned: false
license: mit
short_description: Hybrid invoice extraction using LayoutLMv3 and Regex
---

# 📄 Smart Invoice Processor

A production-grade Hybrid Invoice Extraction System that combines the semantic understanding of LayoutLMv3 with the precision of Regex Heuristics. Designed for robustness, it features a Dual-Engine Architecture with automatic fallback logic to ensure 100% extraction coverage for business-critical fields (Invoice #, Date, Total) even when the AI model is uncertain.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.51+-red.svg)
![Tesseract](https://img.shields.io/badge/Tesseract-5.0+-green.svg)
![Transformers](https://img.shields.io/badge/Transformers-4.x-purple.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.x-orange.svg)

[![🤗 Live Demo](https://img.shields.io/badge/🤗%20Live%20Demo-Hugging%20Face%20Spaces-yellow.svg)](https://huggingface.co/spaces/GSoumyajit2005/invoice-processor-ml)

---

## 🚀 Try it Live!

> **No installation required!** Try the full application instantly on Hugging Face Spaces:
>
> ### 👉 [**Launch Live Demo**](https://huggingface.co/spaces/GSoumyajit2005/invoice-processor-ml) 👈
>
> Upload any invoice image and watch the hybrid ML+Regex engine extract structured data in real-time.

---

## 🎯 Features

### 🧠 Core Intelligence

- **Hybrid Inference Engine:** Automatically triggers a Regex Fallback Engine if the ML model (LayoutLMv3) returns low confidence or missing critical fields (Invoice #, Date).
- **ML-Based Extraction:** Fine-tuned `LayoutLMv3` Transformer for semantic understanding of complex layouts (SROIE dataset).
- **Rule-Based Fallback:** Deterministic regex patterns ensure 100% coverage for standard fields when ML is uncertain.

### 🛡️ Robustness & Engineering

- **Defensive Data Handling:** Implemented coordinate clamping to prevent model crashes from negative OCR bounding boxes.
- **Cross-Platform OCR:** Dynamic Tesseract path discovery that works out-of-the-box on Windows (Local) and Linux (Docker/Production).
- **Clean JSON Output:** Normalized schema handling nested entities, line items, and validation flags.

### 💻 Usability

- **Streamlit Web UI:** Interactive dashboard for real-time inference, visualization, and side-by-side comparison (ML vs. Regex).
- **CLI & Batch Processing:** Process single files or entire directories via command line with JSON export.
- **Auto-Validation:** Heuristic checks to validate that the extracted "Total Amount" matches the sum of line items.

> Note on Invoice Numbers: The SROIE dataset used for training does not include "Invoice Number" labels. To solve this, the system uses a Hybrid Fallback Mechanism: if the ML model (LayoutLMv3) returns null for the Invoice Number, the system automatically triggers a targeted Regex extraction to ensure this critical field is captured.

---

## 🛠️ Technical Deep Dive (Why this architecture?)

### 1. The "Safety Net" Fallback Logic

Standard ML models often fail on specific fields like "Invoice Number" if the layout is unseen. This system implements a **priority-based extraction**:

1.  **Primary:** LayoutLMv3 predicts entity labels (context-aware).
2.  **Fallback:** If `Invoice_No` or `Total` is null, the system executes a targeted Regex scan on the raw text.
    _Result:_ Combines the generalization of AI with the determinism of Rules.

### 2. Robustness & Error Handling

- **OCR Noise:** Handles common Tesseract errors (e.g., reading "1nvoice" as "Invoice").
- **Coordinate Normalization:** A custom `clamp()` function ensures all bounding boxes stay strictly within [0, 1000] to prevent Transformer index errors.

### 3. Dual-Engine Architecture

The system implements a **Dual-Engine Architecture** with automatic fallback logic:

1. **Primary Engine:** LayoutLMv3 predicts entity labels (context-aware).
2. **Fallback Engine:** If `Invoice_No` or `Total` is null, the system executes a targeted Regex scan on the raw text.

### 4. Clean JSON Output

The system outputs a clean JSON with the following fields:

- `receipt_number`: The invoice number (extracted by LayoutLMv3 or Regex).
- `date`: The invoice date (extracted by LayoutLMv3 or Regex).
- `bill_to`: The bill-to information (extracted by LayoutLMv3 or Regex).
- `items`: The list of items (extracted by LayoutLMv3 or Regex).
- `total_amount`: The total amount (extracted by LayoutLMv3 or Regex).
- `extraction_confidence`: The confidence of the extraction (0-100).
- `validation_passed`: Whether the validation passed (true/false).

---

## 📊 Demo

### Web Interface

![Homepage](docs/screenshots/homepage.png)
_Clean upload → extract flow with method selector (ML vs Regex)._

### Successful Extraction (ML-based)

![Success Result](docs/screenshots/success_result.png)
_Fields extracted with LayoutLMv3._

### Format Detection (simulated)

![Format Detection](docs/screenshots/format_detection.png)
_UI shows simple format hints and confidence._

### Example JSON (Rule-based)

```json
{
  "receipt_number": "PEGIV-1030765",
  "date": "15/01/2019",
  "bill_to": {
    "name": "THE PEAK QUARRY WORKS",
    "email": null
  },
  "items": [],
  "total_amount": 193.0,
  "extraction_confidence": 100,
  "validation_passed": true,
  "vendor": "OJC MARKETING SDN BHD",
  "address": "NO JALAN BAYU 4, BANDAR SERI ALAM, 81750 MASAI, JOHOR"
}
```

### Example JSON (ML-based)

```json
{
  "receipt_number": null,
  "date": "15/01/2019",
  "bill_to": null,
  "items": [],
  "total_amount": 193.0,
  "vendor": "OJC MARKETING SDN BHD",
  "address": "NO JALAN BAYU 4, BANDAR SERI ALAM, 81750 MASAI, JOHOR",
  "raw_text": "…",
  "raw_ocr_words": ["…"],
  "raw_predictions": {
    "DATE": {"text": "15/01/2019", "bbox": [[…]]},
    "TOTAL": {"text": "193.00", "bbox": [[…]]},
    "COMPANY": {"text": "OJC MARKETING SDN BHD", "bbox": [[…]]},
    "ADDRESS": {"text": "…", "bbox": [[…]]}
  }
}
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Tesseract OCR
- (Optional) CUDA-capable GPU for training/inference speed

### Installation

1. Clone the repository

```bash
git clone https://github.com/GSoumyajit2005/invoice-processor-ml
cd invoice-processor-ml
```

2. Create and Activate Virtual Environment (Recommended) Ensures the correct Python version and isolates dependencies.

- **Linux / macOS**:

```bash
python3 -m venv venv
source venv/bin/activate
```

- **Windows**:

```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Install Tesseract OCR

- **Windows**: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
- **Mac**: `brew install tesseract`
- **Linux**: `sudo apt install tesseract-ocr`

5. Tesseract Configuration (Auto-Detected) The system automatically detects Tesseract on both Windows (Registry/Standard Paths) and Linux (`/usr/bin/tesseract`). No manual configuration is required in `src/ocr.py`.

6. Run the web app

```bash
streamlit run app.py
```

### Training the Model (Optional)

To retrain the model from scratch using the provided scripts:

```bash
python scripts/train_combined.py
```

(Note: Requires SROIE dataset in data/sroie)

## 💻 Usage

### Web Interface (Recommended)

The easiest way to use the processor is via the web interface.

```bash
streamlit run app.py
```

- Upload an invoice image (PNG/JPG).
- Choose extraction method in sidebar:
  - ML-Based (LayoutLMv3)
  - Rule-Based (Regex)
- View JSON, download results.

### Command-Line Interface (CLI)

You can also process invoices directly from the command line.

#### 1. Processing a Single Invoice

This command processes the provided sample invoice and prints the results to the console.

```bash
python src/pipeline.py data/samples/sample_invoice.jpg --save --method ml
# or
python src/pipeline.py data/samples/sample_invoice.jpg --save --method rules
```

#### 2. Batch Processing a Folder

The CLI can process an entire folder of images at once.

First, place your own invoice images (e.g., `my_invoice1.jpg`, `my_invoice2.png`) into the `data/raw/` folder.

Then, run the following command. It will process all images in `data/raw/`. Saved files are written to `outputs/{stem}_{method}.json`.

```bash
python src/pipeline.py data/raw --save --method ml
```

### Python API

You can integrate the pipeline directly into your own Python scripts.

```python
from src.pipeline import process_invoice
import json

result = process_invoice('data/samples/sample_invoice.jpg', method='ml')
print(json.dumps(result, indent=2))
```

## 🏗️ Architecture

```
                           ┌────────────────┐
                           │  Upload Image  │
                           └───────┬────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │   Preprocessing    │  (OpenCV grayscale/denoise)
                         └────────┬───────────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │     OCR       │  (Tesseract)
                          └───────┬───────┘
                                  │
                   ┌──────────────┴──────────────┐
                   │                             │
                   ▼                             ▼
         ┌──────────────────┐           ┌────────────────────────┐
         │  Rule-based IE   │           │   ML-based IE (NER)    │
         │  (regex, heur.)  │           │ LayoutLMv3 token-class │
         └────────┬─────────┘           └───────────┬────────────┘
                  │                                 │
                  └──────────────┬──────────────────┘
                                 ▼
                         ┌──────────────────┐
                         │   Post-process   │
                         │ validate, scores │
                         └────────┬─────────┘
                                  ▼
                         ┌──────────────────┐
                         │    JSON Output   │
                         └──────────────────┘
```

## 📁 Project Structure

```
invoice-processor-ml/
│
├── data/
│   ├── raw/                    # Input invoice images for processing
│   └── processed/              # (Reserved for future use)
│
├── data/samples/
│   └── sample_invoice.jpg      # Public sample for quick testing
│
├── docs/
│   └── screenshots/            # UI Screenshots for the README demo
│
├── models/
│   └── layoutlmv3-sroie-generalized/  # Fine-tuned model (created after training)
│
├── outputs/                    # Default folder for saved JSON results
│
├── scripts/                    # Training and analysis scripts
│   ├── train_combined.py       # Main training loop (SROIE + Custom Data)
│   ├── eval_new_dataset.py     # Evaluation scripts
│   └── explore_new_dataset.py  # Dataset exploration tools
│
├── src/
│   ├── sroie_loader.py         # SROIE dataset loading logic
│   ├── data_loader.py          # Unified data loader for training
│   ├── preprocessing.py        # Image preprocessing functions (grayscale, denoise)
│   ├── ocr.py                  # Tesseract OCR integration
│   ├── extraction.py           # Regex-based information extraction logic
│   ├── ml_extraction.py        # ML-based extraction (LayoutLMv3)
│   ├── pipeline.py             # Main orchestrator for the pipeline and CLI
│   ├── database.py             # PostgreSQL connection (scaffolded)
│   ├── models.py               # SQLModel tables for persistence (scaffolded)
│   └── repository.py           # CRUD operations for invoices (scaffolded)
│
├── tests/
│   ├── test_preprocessing.py   # Tests for the preprocessing module
│   ├── test_ocr.py             # Tests for the OCR module
│   └── test_pipeline.py        # End-to-end pipeline tests
│
├── app.py                      # Streamlit web interface
├── requirements.txt            # Python dependencies
└── README.md                   # You are Here!
```

## 🧠 Model & Training

- **Model**: `microsoft/layoutlmv3-base` (125M params)
- **Task**: Token Classification (NER) with 9 labels: `O, B/I-COMPANY, B/I-ADDRESS, B/I-DATE, B/I-TOTAL`
- **Dataset**: SROIE (ICDAR 2019, English retail receipts), mychen76/invoices-and-receipts_ocr_v1 (English)
- **Training**: RTX 3050 6GB, PyTorch 2.x, Transformers 4.x
- **Result**: Best F1 ≈ 0.922 on validation (epoch 5 saved)

- Training scripts (local):
- `scripts/train_combined.py` (data prep, training loop with validation + model save)
- Model saved to: `models/layoutlmv3-sroie-generalized/`

## 📈 Performance

- **OCR accuracy (clear images)**: High with Tesseract
- **Rule-based extraction**: Strong on simple retail receipts
- **ML-based extraction (SROIE-style)**:
  - COMPANY / ADDRESS / DATE / TOTAL: High F1 on simple receipts
  - Complex business invoices: Partial extraction unless further fine-tuned

## ⚠️ Known Limitations

1. **Layout Sensitivity**: The ML model was fine‑tuned on SROIE (retail receipts) and mychen76/invoices-and-receipts_ocr_v1 (English). Professional multi-column invoices may underperform until you fine‑tune on more diverse datasets.
2. **Invoice Number**: SROIE dataset lacks invoice number labels. The system solves this by using the Hybrid Fallback Engine, which successfully extracts invoice numbers using Regex whenever the ML model output is empty.
3. **Line Items/Tables**: Not trained for table extraction yet. Rule-based supports simple totals; table extraction comes later.
4. **OCR Variability**: Tesseract outputs can vary; preprocessing and thresholds can impact ML results.

## 🔮 Future Enhancements

- [x] Add and fine‑tune on mychen76/invoices-and-receipts_ocr_v1 (English) for broader invoice formats
- [ ] (Optional) Add FATURA (table-focused) for line-item extraction
- [ ] Sliding-window chunking for >512 token documents (to avoid truncation)
- [ ] Table detection (Camelot/Tabula/DeepDeSRT) for line items
- [ ] PDF support (pdf2image) for multipage invoices
- [x] FastAPI backend + Docker
- [x] CI/CD pipeline (GitHub Actions → HuggingFace Spaces auto-deploy)
- [ ] Multilingual OCR (PaddleOCR) and multilingual fine‑tuning
- [ ] Confidence calibration and better validation rules
- [ ] Database persistence layer (PostgreSQL - scaffolded, ready for implementation)

## 🛠️ Tech Stack

| Component        | Technology                          |
| ---------------- | ----------------------------------- |
| OCR              | Tesseract 5.0+                      |
| Image Processing | OpenCV, Pillow                      |
| ML/NLP           | PyTorch 2.x, Transformers           |
| Model            | LayoutLMv3 (token class.)           |
| Web Interface    | Streamlit                           |
| Data Format      | JSON                                |
| CI/CD            | GitHub Actions → HuggingFace Spaces |
| Containerization | Docker                              |

## 📚 What I Learned

- OCR challenges (confusable characters, confidence-based filtering)
- Layout-aware NER with LayoutLMv3 (text + bbox + pixels)
- Data normalization (bbox to 0–1000 scale)
- End-to-end pipelines (UI + CLI + JSON output)
- When regex is enough vs when ML is needed
- Evaluation (seqeval F1 for NER)

## 🤝 Contributing

Contributions welcome! Areas needing improvement:

- New patterns for regex extractor
- Better preprocessing for OCR
- New datasets and training configs
- Tests and CI

## 📝 License

MIT License - See LICENSE file for details

## 👨‍💻 Author

**Soumyajit Ghosh** - 3rd Year BTech Student

- Exploring AI/ML and practical applications
- [LinkedIn](https://www.linkedin.com/in/soumyajit-ghosh-tech) | [GitHub](https://github.com/GSoumyajit2005) | [Portfolio](https://soumyajitghosh.vercel.app)

---

**Note**: "This is a learning project demonstrating an end-to-end ML pipeline. Not recommended for production use without further validation, retraining on diverse datasets, and security hardening."
