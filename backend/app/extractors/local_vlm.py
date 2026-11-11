"""Local Qwen/Qwen3.5-0.8B VLM extractor with serialized GPU access for 6GB VRAM."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.paths import QWEN35_08B_DIR, configure_local_caches
from app.core.schemas import InvoiceExtraction, parse_vlm_extraction
from app.extractors.base import (
    CloudConfig,
    OcrDocumentResult,
    build_v2_extraction_prompt,
)
from app.pdf.processor import ProcessedDocument


class LocalVlmUnavailableError(RuntimeError):
    """Raised when local Qwen3.5 weights or torch dependencies are unavailable."""


class LocalVlmExtractor:
    """Lazy thread-safe singleton running Qwen3.5-0.8B FP16/BF16 + optional LoRA adapter."""

    name = "local:Qwen3.5-0.8B"

    def __init__(
        self,
        settings: Settings,
        *,
        model_dir: Path | None = None,
        max_prompt_images: int = 3,
    ) -> None:
        self._settings = settings
        self._model_dir = model_dir or QWEN35_08B_DIR
        self._max_prompt_images = max_prompt_images
        self._init_lock = threading.Lock()
        self._infer_lock: asyncio.Lock | None = None
        self._processor: Any | None = None
        self._model: Any | None = None

    def is_available(self) -> bool:
        """Return True if local VLM inference is enabled and weights exist on disk."""
        return self._settings.local_vlm_enabled and self._model_dir.exists()

    def _get_async_lock(self) -> asyncio.Lock:
        if self._infer_lock is None:
            self._infer_lock = asyncio.Lock()
        return self._infer_lock

    def _ensure_loaded(self) -> tuple[Any, Any]:
        if self._model is not None and self._processor is not None:
            return self._processor, self._model

        with self._init_lock:
            if self._model is not None and self._processor is not None:
                return self._processor, self._model

            if not self.is_available():
                raise LocalVlmUnavailableError(
                    f"Local VLM disabled or weights not found at {self._model_dir}"
                )

            configure_local_caches(offline=self._settings.local_vlm_offline)
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor

            processor = AutoProcessor.from_pretrained(
                str(self._model_dir),
                local_files_only=self._settings.local_vlm_offline,
            )
            if hasattr(processor, "image_processor") and hasattr(
                processor.image_processor, "size"
            ):
                processor.image_processor.size = {
                    "shortest_edge": 65536,
                    "longest_edge": 1024 * 1280,
                }

            dtype = (
                torch.bfloat16 if self._settings.local_vlm_dtype == "bfloat16" else torch.float16
            )
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            if device.type == "cpu":
                dtype = torch.float32

            model: Any = AutoModelForImageTextToText.from_pretrained(
                str(self._model_dir),
                dtype=dtype,
                local_files_only=self._settings.local_vlm_offline,
            )

            adapter_dir = self._settings.resolved_adapter_dir
            if adapter_dir and adapter_dir.exists():
                from peft import PeftModel

                model = PeftModel.from_pretrained(model, str(adapter_dir))
                self.name = f"local:Qwen3.5-0.8B+lora({adapter_dir.name})"

            model.to(device)
            model.eval()
            self._processor = processor
            self._model = model
            return self._processor, self._model

    def _infer_sync(
        self, doc: ProcessedDocument, ocr: OcrDocumentResult
    ) -> tuple[InvoiceExtraction, str]:
        import torch

        processor, model = self._ensure_loaded()
        prompt = build_v2_extraction_prompt(ocr.markdown or ocr.plain_text)

        prompt_images = [p.image for p in doc.pages[: self._max_prompt_images]]
        content: list[dict[str, Any]] = [{"type": "image", "image": im} for im in prompt_images]
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]

        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            enable_thinking=False,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device)

        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=self._settings.local_vlm_max_new_tokens,
                do_sample=False,
            )

        if torch.cuda.is_available():
            torch.cuda.synchronize()

        gen_tokens = output_ids[:, inputs["input_ids"].shape[1] :]
        raw_text = processor.batch_decode(gen_tokens, skip_special_tokens=True)[0].strip()
        parsed, ok, err = parse_vlm_extraction(raw_text)
        if not ok or parsed is None:
            warn = f"local_vlm_parse_failed: {err}"
            return InvoiceExtraction(validation_warnings=[warn]), raw_text
        return parsed, raw_text

    async def extract(
        self,
        doc: ProcessedDocument,
        ocr: OcrDocumentResult,
        *,
        cloud_config: CloudConfig | None = None,
    ) -> tuple[InvoiceExtraction, str]:
        """Serialize GPU inference so concurrent uploads never OOM a 6GB card."""
        _ = cloud_config
        async with self._get_async_lock():
            return await asyncio.to_thread(self._infer_sync, doc, ocr)

    def warmup_status(self) -> dict[str, Any]:
        """Inspect readiness without allocating VRAM on /health checks."""
        return {
            "enabled": self._settings.local_vlm_enabled,
            "weights_present": self._model_dir.exists(),
            "loaded": self._model is not None,
            "adapter_configured": bool(self._settings.resolved_adapter_dir),
            "model_dir": str(self._model_dir),
            "started_at": time.monotonic(),
        }
