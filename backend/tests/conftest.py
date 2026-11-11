"""Shared fixtures and deterministic extraction stubs for FastAPI tests."""

from __future__ import annotations

import io
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.core.config import Settings
from app.core.schemas import InvoiceExtraction, LineItemSchema
from app.extractors.base import CloudConfig, OcrDocumentResult, OcrLine
from app.extractors.router import ExtractionRouter
from app.main import create_app
from app.pdf.processor import ProcessedDocument
from PIL import Image


def make_png_bytes(
    width: int = 400, height: int = 600, color: tuple[int, int, int] = (245, 245, 245)
) -> bytes:
    """Create valid PNG image bytes in memory."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_multipage_pdf_bytes(num_pages: int = 2) -> bytes:
    """Create valid multi-page PDF bytes via Pillow without external files."""
    pages = [
        Image.new("RGB", (500, 700), color=(250 - i * 10, 250, 250)) for i in range(num_pages)
    ]
    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
    return buf.getvalue()


class FakeOcrService:
    """Fast deterministic OCR stand-in returning synthetic normalized bounding boxes."""

    def __init__(self, lines: list[OcrLine] | None = None, markdown: str | None = None) -> None:
        self._lines = lines
        self._markdown = markdown

    async def run(self, doc: ProcessedDocument) -> OcrDocumentResult:
        lines = self._lines or [
            OcrLine(page=1, text="MedEquip GmbH", x1=50, y1=40, x2=320, y2=75, confidence=0.98),
            OcrLine(
                page=1, text="Invoice # AUFNR123", x1=50, y1=110, x2=300, y2=140, confidence=0.97
            ),
            OcrLine(page=1, text="28.05.2025", x1=700, y1=110, x2=880, y2=140, confidence=0.96),
            OcrLine(
                page=1, text="Surgical Gloves Pack", x1=60, y1=320, x2=420, y2=350, confidence=0.95
            ),
            OcrLine(page=1, text="100.00", x1=780, y1=320, x2=900, y2=350, confidence=0.97),
            OcrLine(page=1, text="Tax 19%", x1=620, y1=760, x2=740, y2=790, confidence=0.95),
            OcrLine(page=1, text="19.00", x1=780, y1=760, x2=900, y2=790, confidence=0.96),
            OcrLine(
                page=1, text="Total EUR 119.00", x1=620, y1=820, x2=910, y2=860, confidence=0.99
            ),
        ]
        md = self._markdown or "\n".join(line.text for line in lines)
        return OcrDocumentResult(
            markdown=f"--- Page 1 / {doc.page_count} ---\n{md}",
            plain_text=md,
            lines=lines,
            latency_ms=12,
        )


class StubExtractor:
    """Configurable local or cloud VLM stub recording invocations."""

    def __init__(self, name: str, payload: InvoiceExtraction) -> None:
        self.name = name
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return True

    async def extract(
        self,
        doc: ProcessedDocument,
        ocr: OcrDocumentResult,
        *,
        cloud_config: CloudConfig | None = None,
    ) -> tuple[InvoiceExtraction, str]:
        self.calls.append(
            {
                "filename": doc.filename,
                "pages": doc.page_count,
                "ocr_chars": len(ocr.markdown),
                "has_cloud_key": bool(cloud_config and cloud_config.api_key),
            }
        )
        return self.payload.model_copy(deep=True), self.payload.model_dump_json()


@pytest.fixture
def sample_extraction() -> InvoiceExtraction:
    return InvoiceExtraction(
        document_type="invoice",
        vendor="MedEquip GmbH",
        receipt_number="AUFNR123",
        date="2025-05-28",
        currency="EUR",
        subtotal=100.0,
        tax_amount=19.0,
        total_amount=119.0,
        line_items=[
            LineItemSchema(
                description="Surgical Gloves Pack",
                quantity=2.0,
                unit_price=50.0,
                total_price=100.0,
            )
        ],
    )


@pytest.fixture
async def test_client(
    tmp_path: Path, sample_extraction: InvoiceExtraction
) -> AsyncIterator[httpx.AsyncClient]:
    """Spin up isolated FastAPI app backed by temp SQLite DB and LocalDiskStorage."""
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"

    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{db_path}",
        storage_backend="local",
        local_upload_dir=str(upload_dir),
        max_upload_mb=1,
        max_pdf_pages=5,
        local_vlm_enabled=True,
        local_vlm_offline=True,
        rate_limit_extract="100/minute",
    )
    local_stub = StubExtractor("local:Qwen3.5-0.8B", sample_extraction)
    cloud_stub = StubExtractor("cloud:gemini-2.5-flash", sample_extraction)
    router = ExtractionRouter(
        settings,
        ocr_service=FakeOcrService(),  # type: ignore[arg-type]
        local_extractor=local_stub,
        cloud_extractor=cloud_stub,
    )
    app = create_app(settings_override=settings, router_override=router)
    app.state.local_stub = local_stub
    app.state.cloud_stub = cloud_stub

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield client
