"""Shared single & batch document ingestion, storage, extraction, and DB persistence."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.hashing import compute_file_hash, compute_semantic_hash
from app.core.schemas import ExtractionResponse
from app.db.repository import InvoiceRepository, page_urls_for_invoice
from app.extractors.base import CloudConfig
from app.extractors.router import ExtractionRouter
from app.pdf.processor import process_document
from app.storage.base import StorageBackend

_MIME_TO_EXT = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class PayloadTooLargeError(ValueError):
    """Raised when an uploaded file exceeds MAX_UPLOAD_MB."""


def sanitize_filename(raw_name: str | None) -> str:
    """Strip directory components so caller paths never enter DB metadata."""
    cleaned = Path(raw_name or "document").name.strip()
    return cleaned or "document"


async def extract_and_persist(
    *,
    content: bytes,
    filename: str | None,
    mode: Literal["auto", "local", "cloud"] | None,
    cloud_config: CloudConfig | None,
    settings: Settings,
    router: ExtractionRouter,
    storage: StorageBackend,
    session: AsyncSession,
) -> ExtractionResponse:
    """Validate document bytes, extract fields, store artifacts, and save DB row."""
    if len(content) > settings.max_upload_bytes:
        raise PayloadTooLargeError(
            f"Uploaded file ({len(content)} bytes) exceeds {settings.max_upload_mb} MB limit."
        )

    safe_name = sanitize_filename(filename)
    doc = process_document(
        content,
        filename=safe_name,
        max_pages=settings.max_pdf_pages,
        dpi=settings.ocr_dpi,
    )
    file_hash = compute_file_hash(content)

    run_result = await router.run(doc, mode=mode, cloud_config=cloud_config)
    semantic_hash = compute_semantic_hash(run_result.extraction)

    existing_dup = await InvoiceRepository.find_duplicate(
        session,
        file_hash=file_hash,
        semantic_hash=semantic_hash,
    )
    duplicate_of_id = existing_dup.id if existing_dup is not None else None

    invoice_id = uuid.uuid4()
    ext = _MIME_TO_EXT.get(doc.mime_type, Path(safe_name).suffix or ".bin")
    original_key = f"invoices/{invoice_id}/original{ext}"
    await storage.put_bytes(original_key, content, content_type=doc.mime_type)

    for page in doc.pages:
        page_key = f"invoices/{invoice_id}/pages/{page.page_number}.png"
        await storage.put_bytes(page_key, page.png_bytes, content_type="image/png")

    record = await InvoiceRepository.create_from_extraction(
        session,
        invoice_id=invoice_id,
        filename=safe_name,
        mime_type=doc.mime_type,
        file_key=original_key,
        file_hash=file_hash,
        semantic_hash=semantic_hash,
        duplicate_of_id=duplicate_of_id,
        page_count=doc.page_count,
        run_result=run_result,
    )

    page_urls = page_urls_for_invoice(record.id, doc.page_count)
    created_at = record.created_at
    assert created_at is not None

    status: Literal["extracted", "needs_review", "verified", "failed"] = (
        "needs_review" if record.status == "needs_review" else "extracted"
    )
    return ExtractionResponse(
        invoice_id=record.id,
        filename=record.filename,
        file_hash=record.file_hash,
        semantic_hash=record.semantic_hash,
        duplicate_of_id=record.duplicate_of_id,
        status=status,
        extractor_used=run_result.extractor_used,
        latency_ms=run_result.latency_ms,
        page_count=doc.page_count,
        items_match_subtotal=run_result.reconciliation.items_match_subtotal,
        totals_reconcile=run_result.reconciliation.totals_reconcile,
        needs_escalation=run_result.reconciliation.needs_escalation,
        extraction=run_result.extraction,
        page_image_urls=page_urls,
        created_at=created_at,
    )
