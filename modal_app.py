"""Modal serverless deployment for Modern Hybrid Invoice Processor v2.

Runs the lightweight FastAPI ASGI backend on Modal CPU tier with Supabase PostgreSQL,
Indra OCR 1.1 ONNX rasterization, and delegates Qwen3.5-0.8B LoRA multimodal inference
to Hugging Face ZeroGPU (NVIDIA A10G/RTX 6000 48GB GPU, 100% free with no credit card).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import modal

APP_NAME = "invoice-processor"
app = modal.App(APP_NAME)
weights_vol = modal.Volume.from_name("invoice-processor-weights", create_if_missing=True)

CPU_DEPS = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "python-multipart>=0.0.17",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "sqlmodel>=0.0.22",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "psycopg[binary]>=3.2.0",
    "alembic>=1.14.0",
    "slowapi>=0.1.9",
    "boto3>=1.35.0",
    "httpx>=0.28.0",
    "litellm>=1.55.0",
    "indra-ocr>=1.1.2",
    "pypdfium2>=4.30.0",
    "pdfplumber>=0.11.4",
    "pillow>=11.0.0",
    "rapidfuzz>=3.10.0",
    "python-dateutil>=2.9.0",
    "huggingface-hub>=0.27.0",
    "gradio-client>=2.7.2",
]

cpu_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install(*CPU_DEPS)
    .env(
        {
            "PYTHONPATH": "/root",
            "INVOICE_MODELS_DIR": "/weights",
            "LOCAL_VLM_OFFLINE": "0",
        }
    )
    .add_local_dir("backend/app", remote_path="/root/app", copy=True)
)


def get_app_secrets() -> list[modal.Secret]:
    """Load deployment secrets from modal secret 'invoice-secrets' or local .env file."""
    if Path(".env").exists():
        return [modal.Secret.from_dotenv(path=Path(".env"))]
    return [modal.Secret.from_name("invoice-secrets")]


@app.function(
    image=cpu_image,
    volumes={"/weights": weights_vol},
    secrets=get_app_secrets(),
    timeout=120,
)
@modal.asgi_app()
def fastapi_app() -> Any:
    """FastAPI ASGI app running on Modal CPU tier, delegating Qwen LoRA inference to HF ZeroGPU."""
    from app.core.config import Settings
    from app.extractors.hf_zerogpu import HfZerogpuExtractor
    from app.extractors.indra_service import IndraOcrService
    from app.extractors.router import ExtractionRouter
    from app.main import create_app

    ocr_dir = Path("/weights/indra-ocr")
    if not (ocr_dir / "det.onnx").exists():
        print("[fastapi_app] Downloading missing Indra OCR weights into /weights/indra-ocr...")
        from huggingface_hub import snapshot_download

        ocr_dir.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id="datalab-to/indra-ocr",
            revision="v1.1.0",
            local_dir=str(ocr_dir),
        )
        weights_vol.commit()
        print("[fastapi_app] Indra OCR weights committed to persistent volume.")

    settings = Settings(
        local_vlm_offline=False,
        extractor_default_mode="hf_zerogpu",
    )
    ocr_service = IndraOcrService(settings)
    hf_extractor = HfZerogpuExtractor(
        settings,
        space_id="GSoumyajit2005/invoice-vlm-zerogpu",
    )
    router = ExtractionRouter(
        settings,
        ocr_service=ocr_service,
        local_extractor=hf_extractor,
    )
    return create_app(settings_override=settings, router_override=router)


@app.local_entrypoint()
def main(action: str = "help", file: str = "data/samples/sample_pdf_2.pdf") -> None:
    """CLI entrypoint for managing and testing Modal serverless deployment."""
    import httpx

    if action == "test":
        target = Path(file)
        if not target.exists():
            print(f"File not found: {target}")
            return
        url = "https://gsoumyajit2005--invoice-processor-fastapi-app.us-east.modal.run/api/v1/extract"
        print(f"Sending extraction request for {target.name} to {url}...")
        with open(target, "rb") as f:
            files = {"file": (target.name, f, "application/pdf")}
            resp = httpx.post(url, files=files, timeout=60.0)
        print("Status:", resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            print("Extracted Data:", data)
        else:
            print("Response:", resp.text)
    else:
        print("Usage:")
        print("  modal deploy modal_app.py               # Deploy ASGI FastAPI CPU microservice")
        print("  modal run modal_app.py --action test    # Test extraction endpoint")
