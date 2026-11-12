"""Tests for visual grounding, PDF/image processor validation, and local disk storage."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.core.schemas import InvoiceExtraction, LineItemSchema
from app.extractors.base import OcrLine
from app.extractors.grounding import ground_extraction
from app.pdf.processor import (
    DocumentValidationError,
    UnsupportedMediaTypeError,
    detect_mime_type,
    process_document,
)
from app.storage.local import LocalDiskStorage

from tests.conftest import make_multipage_pdf_bytes, make_png_bytes


def test_ground_extraction_links_scalars_localized_amounts_and_line_rows() -> None:
    ocr_lines = [
        OcrLine(page=1, text="MedEquip GmbH", x1=50, y1=30, x2=300, y2=60, confidence=0.99),
        OcrLine(
            page=1,
            text="Rechnungsdatum: 28.05.2025",
            x1=600,
            y1=80,
            x2=910,
            y2=110,
            confidence=0.95,
        ),
        OcrLine(page=1, text="Bohrmaschine", x1=60, y1=340, x2=280, y2=370, confidence=0.94),
        OcrLine(page=1, text="1.285,20", x1=790, y1=340, x2=910, y2=370, confidence=0.96),
        OcrLine(
            page=1,
            text="Subtotal: 1.080,00",
            x1=600,
            y1=700,
            x2=910,
            y2=730,
            confidence=0.93,
        ),
        OcrLine(
            page=1,
            text="Gesamtbetrag: 1.285,20",
            x1=600,
            y1=820,
            x2=920,
            y2=855,
            confidence=0.98,
        ),
    ]
    ext = InvoiceExtraction(
        vendor="MedEquip GmbH",
        date="2025-05-28",
        subtotal=1080.0,
        total_amount=1285.20,
        line_items=[LineItemSchema(description="Bohrmaschine", total_price=1285.20)],
    )

    grounded = ground_extraction(ext, ocr_lines)
    assert grounded.provenance["vendor"].source == "ocr_matched"
    assert grounded.provenance["vendor"].bbox is not None
    assert grounded.provenance["vendor"].bbox.y1 == 30

    # Bottom-biased tie-breaker puts total_amount on Gesamtbetrag row (y1=820) vs row item (y1=340)
    assert grounded.provenance["total_amount"].bbox is not None
    assert grounded.provenance["total_amount"].bbox.y1 == 820

    assert grounded.provenance["date"].bbox is not None
    assert grounded.provenance["date"].bbox.page == 1

    # Line item bbox expands horizontally from description (x1=60) through same-row price (x2=910)
    item_bbox = grounded.line_items[0].bbox
    assert item_bbox is not None
    assert item_bbox.x1 == 60
    assert item_bbox.x2 == 910


def test_detect_mime_type_and_process_multipage_pdf() -> None:
    png_bytes = make_png_bytes()
    assert detect_mime_type(png_bytes) == "image/png"

    pdf_bytes = make_multipage_pdf_bytes(num_pages=2)
    doc = process_document(pdf_bytes, filename="two_pages.pdf", max_pages=5)
    assert doc.is_pdf is True
    assert doc.page_count == 2
    assert len(doc.pages) == 2
    assert doc.pages[0].page_number == 1
    assert doc.pages[1].page_number == 2

    with pytest.raises(UnsupportedMediaTypeError):
        detect_mime_type(b"MZ_FAKE_EXECUTABLE")

    with pytest.raises(DocumentValidationError, match="exceeding"):
        process_document(pdf_bytes, filename="two_pages.pdf", max_pages=1)


async def test_local_disk_storage_crud_and_traversal_guard(tmp_path: Path) -> None:
    storage = LocalDiskStorage(tmp_path / "store")
    key = await storage.put_bytes("invoices/abc/pages/1.png", b"png-data", content_type="image/png")
    assert key == "invoices/abc/pages/1.png"
    assert await storage.exists(key) is True
    assert await storage.get_bytes(key) == b"png-data"

    deleted = await storage.delete_prefix("invoices/abc/")
    assert deleted == 1
    assert await storage.exists(key) is False

    with pytest.raises(ValueError, match="Unsafe storage key"):
        await storage.get_bytes("../../etc/passwd")

    with pytest.raises(FileNotFoundError):
        await storage.get_bytes("invoices/missing/1.png")


def test_ground_extraction_tight_substring_interpolation_and_ocr_fallback() -> None:
    ocr_lines = [
        OcrLine(
            page=1,
            text="Bestellung AUFNR234953 vom 02.05.2022",
            x1=100.0,
            y1=200.0,
            x2=900.0,
            y2=230.0,
            confidence=0.98,
        ),
        OcrLine(
            page=1,
            text="Total Amount: EUR 3,988.40",
            x1=500.0,
            y1=800.0,
            x2=900.0,
            y2=830.0,
            confidence=0.99,
        ),
    ]

    # Test 1: Fallback recovery from OCR line when receipt_number is None
    ext_missing_num = InvoiceExtraction(
        vendor="AutoVendor",
        date="2022-05-02",
        total_amount=3988.40,
    )
    grounded = ground_extraction(ext_missing_num, ocr_lines)
    assert grounded.receipt_number is not None
    assert "234953" in grounded.receipt_number

    # Test 2: Substring bounding box interpolation tightness
    num_prov = grounded.provenance.get("receipt_number")
    assert num_prov is not None
    assert num_prov.bbox is not None
    # Instead of spanning the entire line (100 to 900), the box is tightly interpolated around the number
    assert num_prov.bbox.x1 > 100.0
    assert num_prov.bbox.x2 < 800.0

    # Date bounding box is interpolated to the end of the line
    date_prov = grounded.provenance.get("date")
    assert date_prov is not None
    assert date_prov.bbox is not None
    assert date_prov.bbox.x1 > 500.0

    # Total amount bounding box is interpolated to the price portion
    tot_prov = grounded.provenance.get("total_amount")
    assert tot_prov is not None
    assert tot_prov.bbox is not None
    assert tot_prov.bbox.x1 > 600.0
