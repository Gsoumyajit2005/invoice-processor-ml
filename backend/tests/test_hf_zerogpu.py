"""Unit tests for Hugging Face ZeroGPU extractor integration."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from app.extractors.hf_zerogpu import HfZerogpuExtractor


def test_hf_zerogpu_extractor_initialization():
    settings = Settings(
        hf_zerogpu_space="GSoumyajit2005/invoice-vlm-zerogpu",
    )
    extractor = HfZerogpuExtractor(settings)
    assert extractor.name == "zerogpu:Qwen3.5-0.8B+lora"
    assert extractor.space_id == "GSoumyajit2005/invoice-vlm-zerogpu"
    assert extractor.is_available() is True
    status = extractor.warmup_status()
    assert status["enabled"] is True
    assert status["connected"] is False


@pytest.mark.asyncio
async def test_hf_zerogpu_extract_empty_document():
    from app.extractors.base import OcrDocumentResult
    from app.pdf.processor import ProcessedDocument

    settings = Settings()
    extractor = HfZerogpuExtractor(settings)
    doc = ProcessedDocument(
        filename="empty.pdf",
        mime_type="application/pdf",
        page_count=0,
        is_pdf=True,
        has_native_text=False,
        pages=[],
    )
    ocr = OcrDocumentResult(markdown="", plain_text="")
    extraction, raw = await extractor.extract(doc, ocr)
    assert "zerogpu_failed: document has no pages" in extraction.validation_warnings[0]
    assert raw == ""
