"""Hugging Face ZeroGPU VLM extractor microservice integration."""

from __future__ import annotations

import asyncio
import logging
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.schemas import InvoiceExtraction, parse_vlm_extraction
from app.extractors.base import (
    CloudConfig,
    OcrDocumentResult,
    build_v2_extraction_prompt,
)
from app.pdf.processor import ProcessedDocument

logger = logging.getLogger(__name__)


class HfZerogpuExtractor:
    """Extractor calling remote Qwen3.5-0.8B LoRA hosted on Hugging Face ZeroGPU."""

    name = "zerogpu:Qwen3.5-0.8B+lora"

    def __init__(
        self,
        settings: Settings,
        *,
        space_id: str | None = None,
        hf_token: str | None = None,
    ) -> None:
        self._settings = settings
        self.space_id = space_id or getattr(settings, "hf_zerogpu_space", "GSoumyajit2005/invoice-vlm-zerogpu")
        self.hf_token = hf_token or getattr(settings, "hf_token", None)
        self._client: Any | None = None
        self._init_lock = threading.Lock()

    def is_available(self) -> bool:
        """Return True if space_id is configured."""
        return bool(self.space_id)

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        with self._init_lock:
            if self._client is not None:
                return self._client
            import os
            from gradio_client import Client

            # Ensure offline env flags do not block gradio_client from connecting to HF Space
            os.environ.pop("HF_HUB_OFFLINE", None)
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
            try:
                import huggingface_hub.constants
                huggingface_hub.constants.HF_HUB_OFFLINE = False
            except Exception:
                pass

            logger.info("Initializing Gradio client for ZeroGPU Space: %s", self.space_id)
            self._client = Client(self.space_id, token=self.hf_token)
            return self._client

    def _infer_sync(self, image_path: str, prompt: str) -> str:
        from gradio_client import handle_file

        client = self._get_client()
        result = client.predict(
            image=handle_file(image_path),
            prompt=prompt,
            api_name="/extract_invoice",
        )
        return str(result)

    async def extract(
        self,
        doc: ProcessedDocument,
        ocr: OcrDocumentResult,
        *,
        cloud_config: CloudConfig | None = None,
    ) -> tuple[InvoiceExtraction, str]:
        """Extract invoice data via Hugging Face ZeroGPU NVIDIA GPU microservice."""
        _ = cloud_config
        if not doc.pages:
            return (
                InvoiceExtraction(validation_warnings=["zerogpu_failed: document has no pages"]),
                "",
            )

        prompt = build_v2_extraction_prompt(ocr.markdown or ocr.plain_text)
        primary_image = doc.pages[0].image

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

        try:
            primary_image.save(tmp_path, format="PNG")
            t0 = time.perf_counter()
            raw_text = await asyncio.to_thread(self._infer_sync, str(tmp_path), prompt)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            logger.info("ZeroGPU inference succeeded in %d ms", latency_ms)
        except Exception as exc:
            logger.error("ZeroGPU extraction error: %s", exc, exc_info=True)
            return (
                InvoiceExtraction(validation_warnings=[f"zerogpu_failed: {exc}"]),
                "",
            )
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

        parsed, ok, err = parse_vlm_extraction(raw_text)
        if not ok or parsed is None:
            warn = f"zerogpu_parse_failed: {err}"
            return InvoiceExtraction(validation_warnings=[warn]), raw_text

        return parsed, raw_text

    def warmup_status(self) -> dict[str, Any]:
        """Inspect readiness."""
        return {
            "enabled": self.is_available(),
            "space_id": self.space_id,
            "connected": self._client is not None,
        }
