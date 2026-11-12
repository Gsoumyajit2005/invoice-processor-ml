"""Modal 1.6+ serverless split architecture for Hybrid Invoice Processor v2.

Splits workload into:
1. Low-idle, cheap CPU container serving the FastAPI ASGI application (CRUD, verification,
   reports, page streaming, S3/DB access).
2. Dedicated GPU container (NVIDIA T4, 120s auto-scaledown) running Indra OCR + Qwen3.5-0.8B
   with merged Phase 3 LoRA adapter cached in a persistent modal.Volume.
"""

from __future__ import annotations

import io
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
]

GPU_DEPS = CPU_DEPS + [
    "torch>=2.6.0",
    "torchvision>=0.21.0",
    "transformers>=5.8.1",
    "accelerate>=1.3.0",
    "peft>=0.14.0",
    "bitsandbytes>=0.45.0",
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

gpu_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install(*GPU_DEPS)
    .env(
        {
            "PYTHONPATH": "/root",
            "INVOICE_MODELS_DIR": "/weights",
            "LOCAL_VLM_OFFLINE": "0",
        }
    )
    .add_local_dir("backend/app", remote_path="/root/app", copy=True)
)


@app.cls(
    cpu=4.0,
    memory=8192,
    timeout=300,
    scaledown_window=120,
    volumes={"/weights": weights_vol},
    image=gpu_image,
)
class GPUExtractor:
    """Serverless worker hosting Indra OCR & Qwen3.5-0.8B LoRA on multi-core CPU."""

    model_label: str = "Qwen3.5-0.8B"
    processor: Any = None
    model: Any = None
    ocr_service: Any = None

    @modal.enter()
    def load_models(self) -> None:
        """Initialize models once per warm container lifecycle."""
        import torch
        from app.core.config import Settings
        from app.core.paths import configure_local_caches
        from app.extractors.indra_service import IndraOcrService
        from peft import PeftModel
        from transformers import AutoModelForImageTextToText, AutoProcessor

        configure_local_caches(offline=False)

        model_path = Path("/weights/Qwen3.5-0.8B")
        lora_path = Path("/weights/qwen35-0.8b-invoice-lora")

        if not model_path.exists():
            print(
                f"[GPUExtractor] Warning: {model_path} does not exist yet. Run seed_weights first."
            )
            return

        print(f"[GPUExtractor] Loading base model from {model_path}...")
        processor = AutoProcessor.from_pretrained(str(model_path), local_files_only=True)
        if hasattr(processor, "image_processor") and hasattr(processor.image_processor, "size"):
            processor.image_processor.size = {
                "shortest_edge": 65536,
                "longest_edge": 1024 * 1280,
            }

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32

        model = AutoModelForImageTextToText.from_pretrained(
            str(model_path),
            torch_dtype=dtype,
            device_map=device,
            local_files_only=True,
        )

        if lora_path.exists() and (lora_path / "adapter_config.json").exists():
            print(f"[GPUExtractor] Merging LoRA adapter from {lora_path}...")
            model = PeftModel.from_pretrained(model, str(lora_path)).merge_and_unload()
            self.model_label = "Qwen3.5-0.8B+lora"
        else:
            self.model_label = "Qwen3.5-0.8B-base"

        model.eval()
        self.processor = processor
        self.model = model

        ocr_settings = Settings(local_vlm_offline=False)
        self.ocr_service = IndraOcrService(ocr_settings)
        print(f"[GPUExtractor] Warmup complete with {self.model_label} on {device.upper()}.")

    def _infer_vlm_impl(
        self, pages_bytes: list[bytes], ocr_text: str
    ) -> tuple[dict[str, Any], str]:
        """Run multimodal VLM extraction over rasterized page images + OCR text."""
        import torch
        from app.core.schemas import parse_vlm_extraction
        from app.extractors.base import build_v2_extraction_prompt
        from PIL import Image

        if self.model is None or self.processor is None:
            raise RuntimeError(
                "GPUExtractor model is not loaded. Ensure volume weights are seeded."
            )

        images = [Image.open(io.BytesIO(b)).convert("RGB") for b in pages_bytes]
        prompt = build_v2_extraction_prompt(ocr_text)

        content: list[dict[str, Any]] = [{"type": "image", "image": img} for img in images]
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]

        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            enable_thinking=False,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=1536,
                do_sample=False,
            )

        gen_tokens = output_ids[:, inputs["input_ids"].shape[1] :]
        raw_text = self.processor.batch_decode(gen_tokens, skip_special_tokens=True)[0].strip()
        parsed, ok, err = parse_vlm_extraction(raw_text)
        if not ok or parsed is None:
            return {"validation_warnings": [f"modal_vlm_parse_failed: {err}"]}, raw_text
        return parsed.model_dump(), raw_text

    @modal.method()
    def infer_vlm(self, pages_bytes: list[bytes], ocr_text: str) -> tuple[dict[str, Any], str]:
        """Expose VLM inference over Modal RPC."""
        return self._infer_vlm_impl(pages_bytes, ocr_text)

    @modal.method()
    def extract_document(
        self,
        file_bytes: bytes,
        filename: str,
        mode: str = "auto",
        cloud_config_dict: dict[str, str | None] | None = None,
    ) -> dict[str, Any]:
        """Full end-to-end extraction callable remotely for testing or background jobs."""
        import asyncio

        from app.core.reconciliation import reconcile_invoice
        from app.core.schemas import InvoiceExtraction
        from app.extractors.grounding import ground_extraction
        from app.pdf.processor import process_document

        _ = mode
        _ = cloud_config_dict

        doc = process_document(file_bytes, filename=filename, max_pages=20)
        assert self.ocr_service is not None
        ocr = asyncio.run(self.ocr_service.run(doc))

        pages_bytes = [p.png_bytes for p in doc.pages[:3]]
        parsed_dict, raw_text = self._infer_vlm_impl(pages_bytes, ocr.markdown or ocr.plain_text)
        extraction = InvoiceExtraction.model_validate(parsed_dict)
        reconciliation = reconcile_invoice(extraction, ocr_text=ocr.plain_text)
        grounded = ground_extraction(extraction, ocr.lines)

        return {
            "filename": filename,
            "model_label": self.model_label,
            "extraction": grounded.model_dump(),
            "reconciliation": {
                "items_match_subtotal": reconciliation.items_match_subtotal,
                "totals_reconcile": reconciliation.totals_reconcile,
                "needs_escalation": reconciliation.needs_escalation,
                "warnings": reconciliation.warnings,
            },
            "ocr_plain_text": ocr.plain_text,
            "raw_model_output": raw_text,
        }


def get_app_secrets() -> list[modal.Secret]:
    """Load deployment secrets from modal secret 'invoice-secrets' or local .env file."""
    if Path(".env").exists():
        return [modal.Secret.from_dotenv(path=Path(".env"))]
    return [modal.Secret.from_name("invoice-secrets")]


@app.function(
    image=cpu_image,
    volumes={"/weights": weights_vol},
    secrets=get_app_secrets(),
    timeout=300,
)
@modal.asgi_app()
def fastapi_app() -> Any:
    """FastAPI ASGI app running on Modal CPU tier, delegating inference to GPUExtractor."""
    from app.core.config import Settings
    from app.core.schemas import InvoiceExtraction
    from app.extractors.base import CloudConfig, ExtractorBackend, OcrDocumentResult
    from app.extractors.router import ExtractionRouter
    from app.main import create_app
    from app.pdf.processor import ProcessedDocument

    class ModalRemoteVlmExtractor(ExtractorBackend):
        name = "modal:GPUExtractor(T4)"

        def is_available(self) -> bool:
            return True

        async def extract(
            self,
            doc: ProcessedDocument,
            ocr: OcrDocumentResult,
            *,
            cloud_config: CloudConfig | None = None,
        ) -> tuple[InvoiceExtraction, str]:
            _ = cloud_config
            worker = GPUExtractor()
            pages_bytes = [p.png_bytes for p in doc.pages[:3]]
            ocr_text = ocr.markdown or ocr.plain_text
            parsed_dict, raw_text = await worker.infer_vlm.remote.aio(pages_bytes, ocr_text)
            return InvoiceExtraction.model_validate(parsed_dict), raw_text

    settings = Settings()
    router = ExtractionRouter(settings, local_extractor=ModalRemoteVlmExtractor())
    return create_app(settings_override=settings, router_override=router)


@app.function(
    image=gpu_image,
    volumes={"/weights": weights_vol},
    timeout=1800,
)
def seed_weights(
    force: bool = False,
    lora_files: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    """Seed /weights Modal volume with Qwen3.5-0.8B, Indra OCR, and LoRA adapter."""
    from app.core.config import Settings
    from app.extractors.indra_service import IndraOcrService
    from huggingface_hub import snapshot_download

    weights_path = Path("/weights")
    qwen_dir = weights_path / "Qwen3.5-0.8B"
    lora_dir = weights_path / "qwen35-0.8b-invoice-lora"
    ocr_dir = weights_path / "indra-ocr"

    status: dict[str, Any] = {}

    # 1. Base Model
    if not (qwen_dir / "config.json").exists() or force:
        print("[seed_weights] Downloading Qwen/Qwen3.5-0.8B from HuggingFace...")
        snapshot_download(
            repo_id="Qwen/Qwen3.5-0.8B",
            local_dir=str(qwen_dir),
        )
        status["base_model"] = "downloaded"
    else:
        print("[seed_weights] Qwen3.5-0.8B already present in volume.")
        status["base_model"] = "cached"

    # 2. LoRA weights
    lora_dir.mkdir(parents=True, exist_ok=True)
    if lora_files:
        print(f"[seed_weights] Writing {len(lora_files)} uploaded LoRA files...")
        for fname, data in lora_files.items():
            target = lora_dir / fname
            target.write_bytes(data)
            print(f"  - Wrote {fname} ({len(data)} bytes)")
        status["lora"] = f"uploaded_{len(lora_files)}_files"
    elif (lora_dir / "adapter_config.json").exists():
        status["lora"] = "cached"
    else:
        status["lora"] = "missing (using base model)"

    # 3. Indra OCR
    ocr_dir.mkdir(parents=True, exist_ok=True)
    print("[seed_weights] Priming Indra OCR cache...")
    _ = IndraOcrService(Settings(local_vlm_offline=False))
    status["indra_ocr"] = "cached"

    weights_vol.commit()
    print("[seed_weights] Volume successfully committed!")
    return status


@app.local_entrypoint()
def main(action: str = "help", file: str = "data/samples/sample_pdf_2.pdf") -> None:
    """CLI entrypoint for managing and testing Modal serverless deployment."""
    if action == "seed":
        print("Packaging local LoRA weights if present...")
        local_lora_dir = Path("models/qwen35-0.8b-invoice-lora")
        lora_payload: dict[str, bytes] = {}
        if local_lora_dir.exists():
            for p in local_lora_dir.iterdir():
                if p.is_file():
                    lora_payload[p.name] = p.read_bytes()
            print(f"Found {len(lora_payload)} local LoRA files to upload.")
        else:
            print("No local models/qwen35-0.8b-invoice-lora found; seeding base model only.")

        res = seed_weights.remote(force=False, lora_files=lora_payload)
        print("Seed result:", res)

    elif action == "test":
        target = Path(file)
        if not target.exists():
            print(f"File not found: {target}")
            return
        print(f"Invoking GPUExtractor.extract_document.remote on {target}...")
        file_bytes = target.read_bytes()
        worker = GPUExtractor()
        result = worker.extract_document.remote(file_bytes=file_bytes, filename=target.name)
        ext = result["extraction"]
        print("\n--- Extraction Result ---")
        print(f"Model Used: {result['model_label']}")
        print(f"Vendor:     {ext.get('vendor')}")
        print(f"Date:       {ext.get('date')}")
        print(f"Total:      {ext.get('total_amount')} {ext.get('currency')}")
        print(f"Line Items: {len(ext.get('line_items', []))}")
        print(f"Reconciled: {result['reconciliation']}")

    else:
        print("Usage:")
        print("  modal run modal_app.py --action seed    # Download base model & upload LoRA")
        print("  modal run modal_app.py --action test    # Test inference on sample document")
        print("  modal deploy modal_app.py               # Deploy ASGI FastAPI & GPU worker")
