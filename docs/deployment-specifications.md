# 🌐 Hybrid Document AI Invoice Processor v2 — Production Deployment Specifications

> **System Status**: 100% Operational, Verified & Live  
> **Infrastructure Cost**: \$0.00 / month (100% Free Tiers, Zero Credit Cards Required)  
> **Model Sovereignty**: 100% Custom Models (`Indra OCR 1.1` + `Qwen3.5-0.8B` + `Phase 3 LoRA`), Zero Commercial Cloud APIs  

---

## 1. System Topology & Architecture

```mermaid
flowchart TD
    subgraph Users ["Client Layer"]
        Browser["Desktop / Mobile Browser\n(Google Chrome, Safari, Firefox)"]
    end

    subgraph Vercel ["Edge Frontend (Vercel Serverless)"]
        UI["Next.js 16 App Router (React 19, TypeScript)\n• Landing Page, Upload, HITL Review Studio\n• Real-Time [0..1000] SVG Bounding Box Overlays\n• Math Reconciliation Balance Badges"]
        BFF["BFF API Proxy (/api/v1/*)\n• Injects X-Backend-Secret\n• maxDuration = 60s\n• HMAC Cookie Auth"]
    end

    subgraph Modal ["Backend Compute (Modal Serverless)"]
        FastAPI["FastAPI ASGI App (Python 3.12, Debian Slim CPU)\n• URL: gsoumyajit2005--invoice-processor-fastapi-app.us-east.modal.run\n• Rate Limiter (SlowAPI)\n• Multi-page Rasterization (pypdfium2)\n• Indra OCR 1.1 ONNX Engine (300ms/page)"]
        Volume[("modal.Volume: invoice-processor-weights\n(/weights/indra-ocr - det.onnx, rec.onnx)")]
    end

    subgraph ZeroGPU ["Vision-Language Model Microservice (Hugging Face Spaces)"]
        GradioApp["ZeroGPU Gradio App (Python 3.12)\n• Space: GSoumyajit2005/invoice-vlm-zerogpu\n• Dynamic NVIDIA A10G / RTX 6000 48GB GPU\n• Base Model: Qwen/Qwen3.5-0.8B FP16\n• Math LoRA Merge: 132 Transformer Projection Layers\n• Decorator: @spaces.GPU(duration=30)\n• API Endpoint: /extract_invoice"]
    end

    subgraph Supabase ["Data & Storage Layer (Supabase PostgreSQL 16)"]
        DB[("PostgreSQL 16 (AWS Sydney / ap-southeast-2)\n• Connection Pooler on Port 5432\n• Relational Tables: invoices, line_items\n• Binary Storage Table: storage_objects (BYTEA)")]
    end

    Browser -->|HTTPS| UI
    UI -->|Internal Fetch| BFF
    BFF -->|HTTPS / HTTP2| FastAPI
    FastAPI <-->|Cached ONNX| Volume
    FastAPI -->|Gradio Client HTTPS| GradioApp
    FastAPI -->|Async SQLAlchemy / asyncpg| DB
```

---

## 2. Infrastructure Inventory & Component Matrix

| Component | Host / Provider | Hardware / Plan | Cost / Limits | Production URL / Hostname |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend UI** | Vercel | Serverless Edge (Node.js 20) | Free Hobby Tier (100 GB-hrs/mo) | `https://invoflow-ai.vercel.app` |
| **Backend API** | Modal | Shared Multi-core CPU Tier | Free Tier (\$30/mo credits included, 0 card hold) | `https://gsoumyajit2005--invoice-processor-fastapi-app.us-east.modal.run` |
| **VLM LoRA Engine** | Hugging Face Spaces | **ZeroGPU (NVIDIA A10G / RTX 6000 48GB)** | 100% Free (Zero card, dynamic GPU allocation) | `https://huggingface.co/spaces/GSoumyajit2005/invoice-vlm-zerogpu` |
| **Database** | Supabase | PostgreSQL 16 (AWS ap-southeast-2) | Free Tier (500 MB DB, 2 projects) | `aws-1-ap-southeast-2.pooler.supabase.com:5432` |
| **Binary Artifact Storage** | Supabase | Database `storage_objects` (`BYTEA`) | Shared DB Storage (100% persistent) | Direct via `PostgresStorage` backend |
| **OCR Models Cache** | Modal | Persistent `modal.Volume` | Free (Up to 50 GB storage) | Volume `invoice-processor-weights` |

---

## 3. Component Deep Dive & Specifications

### 3.1 Frontend: Next.js 16 on Vercel

- **Framework**: Next.js 16.4 App Router, React 19, TypeScript 5.8, Tailwind CSS v4.
- **Repository Location**: `frontend/`
- **Deployment Strategy**: Automated Vercel GitHub integration triggered on push to `main`.
- **Key Files**:
  - `frontend/src/app/api/v1/[...path]/route.ts`: Reverse proxy forwarding browser requests to Modal backend.
  - `frontend/src/app/api/auth/route.ts`: HMAC signed cookie session management.
  - `frontend/src/components/DocumentOverlayViewer.tsx`: Interactive SVG polygon overlay rendering normalized [0..1000] bounding boxes over document page images.
  - `frontend/src/components/InvoiceReviewForm.tsx`: Field verification form with automatic total amount, tax, and line item arithmetic reconciliation.
- **Critical Configuration**:
  - `export const maxDuration = 60;` declared in both `route.ts` files to prevent Vercel's default 10-second serverless execution timeout.
  - Client-side document canvas streams images directly from `/api/v1/invoices/[id]/pages/[page]` with private caching headers (`Cache-Control: private, max-age=3600`).

### 3.2 Backend: FastAPI on Modal CPU

- **Framework**: FastAPI 0.115+, Uvicorn 0.32+, SQLModel 0.0.22, SQLAlchemy 2.0 Async, Pydantic v2.
- **Repository Location**: `backend/` and `modal_app.py`
- **Deployment Command**: `uv run modal deploy modal_app.py`
- **Image Definition**: `modal.Image.debian_slim(python_version="3.12")` with `libgl1`, `libglib2.0-0` and `CPU_DEPS`.
- **Hardware Profile**: Multi-core CPU, 4 GB RAM, 120-second timeout.
- **Execution Flow**:
  1. Receives multi-part file upload (`.pdf`, `.png`, `.jpg`, `.webp`).
  2. Computes SHA-256 binary hash (`file_hash`) for deduplication.
  3. Uses `pypdfium2` (at 150 DPI) to rasterize PDF pages into high-resolution PNG bytes.
  4. Runs `IndraOcrService` (Indra OCR 1.1 ONNX) on CPU in ~300ms per page, generating full layout markdown and token bounding boxes.
  5. Instantiates `HfZerogpuExtractor` using `gradio_client.Client` and calls Hugging Face ZeroGPU endpoint `/extract_invoice`.
  6. Passes raw VLM JSON output through `parse_vlm_extraction` and `reconcile_invoice`.
  7. Executes `ground_extraction` to snap extracted text values to spatial OCR token bounding boxes.
  8. Commits original file and rendered page images into `storage_objects` via `PostgresStorage`.
  9. Commits invoice metadata and line item records into PostgreSQL `invoices` and `line_items` tables.

### 3.3 Multimodal VLM: Hugging Face ZeroGPU Microservice

- **Repository Location**: Hugging Face Space `GSoumyajit2005/invoice-vlm-zerogpu` (local template in `hf_space/`).
- **Base Model**: `Qwen/Qwen3.5-0.8B` (`transformers.AutoModelForImageTextToText` in FP16).
- **Fine-Tuned Adapter**: Phase 3 LoRA adapter (`adapter_model.safetensors`, 37.4 MB; `adapter_config.json`, rank $r=16$, $\alpha=32$).
- **Mathematical LoRA Merge on CPU**:
  To prevent ZeroGPU CUDA dispatcher interception crashes (`RuntimeError: No CUDA GPUs are available`), the LoRA weights are merged mathematically directly on CPU tensors before moving weights to the ZeroGPU CUDA device:
  $$\Delta W = \left(B \times A\right) \times \frac{\alpha}{r} = (B \times A) \times 2.0$$
  $$W_{\text{merged}} = W_{\text{base}} + \Delta W$$
  Merged across all 132 linear projection layers (`in_proj_qkv`, `out_proj`, `gate_proj`, `up_proj`, `down_proj`).
- **GPU Decorator**: `@spaces.GPU(duration=30)` dynamically attaches an NVIDIA A10G/RTX 6000 48GB GPU slice only during token generation and releases it immediately after, guaranteeing 100% free operation with zero idle GPU billing.

### 3.4 Database & Artifact Storage: Supabase PostgreSQL 16

- **Database Engine**: PostgreSQL 16 on AWS Sydney (`ap-southeast-2`).
- **Connection Method**: Connection Pooler via `aws-1-ap-southeast-2.pooler.supabase.com:5432` (supports both IPv4 and IPv6 networks).
- **Alembic Version**: `0001_initial_schema (head)`.
- **Tables**:
  - `invoices`: Core document records, vendor information, financial fields, raw OCR markdown, JSON provenance, duplicate detection links.
  - `line_items`: Individual invoice items, quantities, unit prices, total prices, positional ordering, and bounding box coordinates.
  - `storage_objects`: Binary large object storage (`BYTEA`) storing raw PDFs (`invoices/[id]/original.pdf`) and page preview images (`invoices/[id]/pages/[page].png`).

---

## 4. Environment Variables Reference

### 4.1 Frontend Environment Variables (`frontend/.env.local` / Vercel Dashboard)

| Variable | Required | Description | Example / Production Value |
| :--- | :---: | :--- | :--- |
| `BACKEND_API_URL` | **Yes** | HTTPS URL of the deployed Modal FastAPI application | `https://gsoumyajit2005--invoice-processor-fastapi-app.us-east.modal.run` |
| `BACKEND_SHARED_SECRET` | No | Shared secret header (`X-Backend-Secret`) | (Optional secret string) |
| `DEMO_PASSWORD` | **Yes** | Password required to unlock the demo web UI | `invoflow2026` |
| `AUTH_SECRET` | **Yes** | 32+ character HMAC secret for signing auth session cookies | (Random 32-byte hex string) |

### 4.2 Backend Environment Variables (`.env` / Modal Secret `invoice-secrets`)

| Variable | Required | Description | Example / Production Value |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | **Yes** | Async PostgreSQL connection string with session pooler | `postgresql+asyncpg://postgres.qrpzfubpjjjtolgjjmpy:PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres` |
| `STORAGE_BACKEND` | **Yes** | Storage provider for PDFs and page PNGs | `database` (or `local` / `s3`) |
| `EXTRACTOR_DEFAULT_MODE`| **Yes** | Primary extraction routing strategy | `hf_zerogpu` |
| `HF_ZEROGPU_SPACE` | **Yes** | Space ID of the hosted ZeroGPU microservice | `GSoumyajit2005/invoice-vlm-zerogpu` |
| `HF_TOKEN` | No | Hugging Face user access token for private Spaces | `hf_...` |
| `LOCAL_VLM_OFFLINE` | No | Prevents outbound downloads if local weights present | `0` |
| `OCR_DPI` | No | Page rasterization resolution | `150.0` |
| `MAX_UPLOAD_MB` | No | Maximum single file upload size | `20` |
| `MAX_PDF_PAGES` | No | Maximum pages processed per document | `20` |

---

## 5. Deployment & Maintenance Runbooks

### 5.1 Redeploying the Modal Backend

When changes are made to `backend/app/` or `modal_app.py`:

```bash
# 1. Ensure dependencies are synced
uv sync

# 2. Deploy updated ASGI app to Modal
uv run modal deploy modal_app.py
```

### 5.2 Updating the Hugging Face ZeroGPU Model Space

If you update the LoRA weights or prompt template:

```bash
# 1. Clone Space repo to temporary directory
git clone https://huggingface.co/spaces/GSoumyajit2005/invoice-vlm-zerogpu /tmp/space_update

# 2. Copy updated app.py and adapter weights
cp hf_space/app.py /tmp/space_update/app.py
cp hf_space/requirements.txt /tmp/space_update/requirements.txt
cp -r models/qwen35-0.8b-invoice-lora/* /tmp/space_update/lora_adapter/

# 3. Track files >10MB via Git LFS
cd /tmp/space_update
git lfs track "lora_adapter/*.safetensors"
git lfs track "lora_adapter/*.json"
git add .gitattributes app.py requirements.txt lora_adapter/

# 4. Commit and push
git commit -m "feat: update extraction model weights"
git push origin main

# 5. Clean up
rm -rf /tmp/space_update
```

### 5.3 Running Database Migrations

When altering the database schema in `backend/app/db/models.py`:

```bash
# 1. Generate new migration
uv run --package invoice-backend alembic revision --autogenerate -m "describe_changes"

# 2. Apply migration to Supabase PostgreSQL
uv run --package invoice-backend alembic upgrade head
```

---

## 6. Incident Response & Troubleshooting Matrix

| Symptom / Error | Root Cause | Exact Resolution |
| :--- | :--- | :--- |
| `FUNCTION_INVOCATION_TIMEOUT` on Vercel | Vercel Serverless Function timed out at 10s default. | Add `export const maxDuration = 60;` in `frontend/src/app/api/v1/[...path]/route.ts`. |
| `Cross-site POST form submissions are forbidden` | `BACKEND_API_URL` lacked region prefix (`.us-east`), resolving to Modal marketing page. | Ensure `BACKEND_API_URL` is `https://gsoumyajit2005--invoice-processor-fastapi-app.us-east.modal.run`. |
| `psycopg.OperationalError: Network is unreachable` | Direct host `db.<ref>.supabase.co` resolves to IPv6 only; client network lacks IPv6 route. | Use Supabase Session Pooler host: `aws-1-ap-southeast-2.pooler.supabase.com:5432` with username `postgres.<ref>`. |
| `RuntimeError: No CUDA GPUs are available` on ZeroGPU Space | PEFT adapter loading attempted to touch CUDA device outside `@spaces.GPU` context. | Use mathematical LoRA tensor merge on CPU (`safe_open(..., device='cpu')`) before `model.to("cuda")`. |
| `git push rejected: files larger than 10 MiB` on Hugging Face | Large model safetensors or tokenizers committed as raw Git objects. | Run `git lfs track "*.safetensors"` and `git lfs track "lora_adapter/tokenizer.json"`. |
| `Unable to load document page image` (404) | Document images were written to ephemeral container disk instead of persistent storage. | Use `STORAGE_BACKEND="database"` (`PostgresStorage`) to persist all PNG bytes in PostgreSQL `storage_objects`. |
