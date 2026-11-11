"""LiteLLM cloud VLM extractor supporting BYO-key Gemini, OpenAI, and OpenRouter."""

from __future__ import annotations

import base64
from typing import Any

import litellm

from app.core.config import Settings
from app.core.schemas import InvoiceExtraction, parse_vlm_extraction
from app.extractors.base import (
    CloudConfig,
    OcrDocumentResult,
    build_v2_extraction_prompt,
)
from app.pdf.processor import ProcessedDocument

_PROVIDER_DEFAULT_MODELS = {
    "gemini": "gemini/gemini-2.5-flash",
    "openai": "openai/gpt-4o-mini",
    "openrouter": "openrouter/google/gemini-2.5-flash",
}


class CloudConfigError(RuntimeError):
    """Raised when Cloud VLM extraction is requested without a model or API key."""


class CloudVlmExtractor:
    """Ephemeral BYO-key LiteLLM adapter for multimodal cloud escalation."""

    name = "cloud:litellm"

    def __init__(self, settings: Settings, *, max_prompt_images: int = 4) -> None:
        self._settings = settings
        self._max_prompt_images = max_prompt_images

    def resolve_credentials(self, cloud_config: CloudConfig | None) -> tuple[str, str]:
        """Resolve effective (litellm_model, api_key) without storing or logging keys."""
        provider = (
            (cloud_config.provider if cloud_config else None)
            or self._settings.default_cloud_provider
            or "gemini"
        ).lower()
        model = (
            (cloud_config.model if cloud_config else None)
            or self._settings.default_cloud_model
            or _PROVIDER_DEFAULT_MODELS.get(provider, "gemini/gemini-2.5-flash")
        )
        if "/" not in model and provider in _PROVIDER_DEFAULT_MODELS:
            model = f"{provider}/{model}"

        api_key = (
            (cloud_config.api_key if cloud_config else None)
            or self._settings.default_cloud_api_key
        )
        if not api_key:
            raise CloudConfigError(
                "Cloud VLM requested or required for escalation, but no API key was provided."
            )
        return model, api_key

    def has_credentials(self, cloud_config: CloudConfig | None) -> bool:
        """Check cleanly whether either request-scoped or default server key exists."""
        return bool(
            (cloud_config and cloud_config.api_key) or self._settings.default_cloud_api_key
        )

    async def extract(
        self,
        doc: ProcessedDocument,
        ocr: OcrDocumentResult,
        *,
        cloud_config: CloudConfig | None = None,
    ) -> tuple[InvoiceExtraction, str]:
        """Call LiteLLM async completion over page images + Indra OCR transcript."""
        model, api_key = self.resolve_credentials(cloud_config)
        prompt = build_v2_extraction_prompt(ocr.markdown or ocr.plain_text)

        content: list[dict[str, Any]] = []
        for page in doc.pages[: self._max_prompt_images]:
            b64 = base64.b64encode(page.png_bytes).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )
        content.append({"type": "text", "text": prompt})

        response: Any = await litellm.acompletion(
            model=model,
            api_key=api_key,
            messages=[{"role": "user", "content": content}],
            temperature=0.0,
            max_tokens=2048,
        )
        raw_text = ""
        if getattr(response, "choices", None):
            msg = response.choices[0].message
            raw_text = (getattr(msg, "content", None) or "").strip()

        parsed, ok, err = parse_vlm_extraction(raw_text)
        if not ok or parsed is None:
            return (
                InvoiceExtraction(
                    validation_warnings=[f"cloud_vlm_parse_failed ({model}): {err}"]
                ),
                raw_text,
            )
        return parsed, raw_text
