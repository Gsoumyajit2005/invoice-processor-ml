"""Database repository helpers for invoice CRUD, duplicate checks, and HITL edits."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col

from app.core.hashing import compute_semantic_hash
from app.core.reconciliation import reconcile_invoice
from app.core.schemas import (
    BoundingBox,
    FieldProvenance,
    InvoiceDetailResponse,
    InvoiceExtraction,
    InvoicePatchRequest,
    InvoiceSummary,
    LineItemDTO,
    LineItemSchema,
)
from app.db.models import InvoiceRecord, LineItemRecord
from app.extractors.base import ExtractionRunResult


def to_decimal(val: float | None) -> Decimal | None:
    """Convert optional float into fixed 4-decimal Decimal for SQL Numeric columns."""
    if val is None:
        return None
    return Decimal(f"{val:.4f}")


def to_float(val: Decimal | float | None) -> float | None:
    """Convert optional Decimal/numeric DB field into JSON-serializable float."""
    if val is None:
        return None
    return float(val)


def _parse_iso_date(val: str | None) -> date | None:
    if not val:
        return None
    return date.fromisoformat(val)


def _build_line_item_records(
    invoice_id: uuid.UUID, items: list[LineItemSchema]
) -> list[LineItemRecord]:
    return [
        LineItemRecord(
            invoice_id=invoice_id,
            position=idx,
            description=item.description,
            quantity=to_decimal(item.quantity),
            unit_price=to_decimal(item.unit_price),
            total_price=to_decimal(item.total_price),
            bbox_json=item.bbox.model_dump(mode="json") if item.bbox else None,
        )
        for idx, item in enumerate(items)
    ]


def record_to_extraction(record: InvoiceRecord) -> InvoiceExtraction:
    """Reconstruct a canonical InvoiceExtraction schema from persisted ORM rows."""
    provenance: dict[str, FieldProvenance] = {}
    for key, raw_val in (record.provenance_json or {}).items():
        if isinstance(raw_val, dict):
            provenance[key] = FieldProvenance.model_validate(raw_val)

    items: list[LineItemSchema] = []
    for li in sorted(record.line_items, key=lambda x: x.position):
        bbox = BoundingBox.model_validate(li.bbox_json) if li.bbox_json else None
        items.append(
            LineItemSchema(
                description=li.description,
                quantity=to_float(li.quantity),
                unit_price=to_float(li.unit_price),
                total_price=to_float(li.total_price),
                bbox=bbox,
            )
        )

    doc_type = (
        record.document_type
        if record.document_type in {"invoice", "receipt", "credit_note", "unknown"}
        else "invoice"
    )
    return InvoiceExtraction(
        document_type=doc_type,  # type: ignore[arg-type]
        vendor=record.vendor,
        vendor_address=record.vendor_address,
        receipt_number=record.receipt_number,
        date=record.invoice_date.isoformat() if record.invoice_date else None,
        due_date=record.due_date.isoformat() if record.due_date else None,
        currency=record.currency,
        subtotal=to_float(record.subtotal),
        tax_amount=to_float(record.tax_amount),
        discount_amount=to_float(record.discount_amount),
        total_amount=to_float(record.total_amount),
        bill_to=record.bill_to,
        line_items=items,
        provenance=provenance,
        validation_warnings=list(record.warnings_json or []),
    )


def page_urls_for_invoice(invoice_id: uuid.UUID, page_count: int) -> list[str]:
    """Build relative API URLs for rendered page PNG endpoints."""
    return [f"/api/v1/invoices/{invoice_id}/pages/{page}" for page in range(1, page_count + 1)]


def record_to_summary(record: InvoiceRecord) -> InvoiceSummary:
    """Map InvoiceRecord to list-view summary DTO."""
    now = record.created_at or datetime.now().astimezone()
    updated = record.updated_at or now
    return InvoiceSummary(
        id=record.id,
        filename=record.filename,
        document_type=record.document_type,
        vendor=record.vendor,
        receipt_number=record.receipt_number,
        date=record.invoice_date.isoformat() if record.invoice_date else None,
        currency=record.currency,
        total_amount=to_float(record.total_amount),
        status=record.status,
        extractor_used=record.extractor_used,
        items_match_subtotal=record.items_match_subtotal,
        totals_reconcile=record.totals_reconcile,
        duplicate_of_id=record.duplicate_of_id,
        page_count=record.page_count,
        created_at=now,
        updated_at=updated,
    )


def record_to_detail(record: InvoiceRecord) -> InvoiceDetailResponse:
    """Map InvoiceRecord + eager line items into full detail response DTO."""
    now = record.created_at or datetime.now().astimezone()
    updated = record.updated_at or now
    provenance = {
        key: FieldProvenance.model_validate(val)
        for key, val in (record.provenance_json or {}).items()
        if isinstance(val, dict)
    }
    line_items = [
        LineItemDTO(
            id=li.id,
            position=li.position,
            description=li.description,
            quantity=to_float(li.quantity),
            unit_price=to_float(li.unit_price),
            total_price=to_float(li.total_price),
            bbox=BoundingBox.model_validate(li.bbox_json) if li.bbox_json else None,
        )
        for li in sorted(record.line_items, key=lambda x: x.position)
    ]
    return InvoiceDetailResponse(
        id=record.id,
        filename=record.filename,
        file_hash=record.file_hash,
        semantic_hash=record.semantic_hash,
        duplicate_of_id=record.duplicate_of_id,
        status=record.status,
        document_type=record.document_type,
        vendor=record.vendor,
        vendor_address=record.vendor_address,
        receipt_number=record.receipt_number,
        date=record.invoice_date.isoformat() if record.invoice_date else None,
        due_date=record.due_date.isoformat() if record.due_date else None,
        currency=record.currency,
        subtotal=to_float(record.subtotal),
        tax_amount=to_float(record.tax_amount),
        discount_amount=to_float(record.discount_amount),
        total_amount=to_float(record.total_amount),
        bill_to=record.bill_to,
        extractor_used=record.extractor_used,
        extraction_latency_ms=record.extraction_latency_ms,
        items_match_subtotal=record.items_match_subtotal,
        totals_reconcile=record.totals_reconcile,
        page_count=record.page_count,
        raw_ocr_markdown=record.raw_ocr_markdown,
        provenance=provenance,
        validation_warnings=list(record.warnings_json or []),
        line_items=line_items,
        page_image_urls=page_urls_for_invoice(record.id, record.page_count),
        created_at=now,
        updated_at=updated,
    )


class InvoiceRepository:
    """Async repository encapsulating invoice queries, dedup lookup, and updates."""

    @staticmethod
    async def find_duplicate(
        session: AsyncSession,
        *,
        file_hash: str,
        semantic_hash: str | None,
    ) -> InvoiceRecord | None:
        """Return earliest matching invoice sharing exact file_hash or semantic_hash."""
        conditions = [col(InvoiceRecord.file_hash) == file_hash]
        if semantic_hash:
            conditions.append(col(InvoiceRecord.semantic_hash) == semantic_hash)

        stmt = (
            select(InvoiceRecord)
            .where(or_(*conditions))
            .order_by(col(InvoiceRecord.created_at).asc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_from_extraction(
        session: AsyncSession,
        *,
        invoice_id: uuid.UUID,
        filename: str,
        mime_type: str,
        file_key: str,
        file_hash: str,
        semantic_hash: str | None,
        duplicate_of_id: uuid.UUID | None,
        page_count: int,
        run_result: ExtractionRunResult,
    ) -> InvoiceRecord:
        """Persist extracted invoice, line items, OCR text, and reconciliation state."""
        ext = run_result.extraction
        rec = run_result.reconciliation
        status = "needs_review" if rec.needs_escalation else "extracted"

        record = InvoiceRecord(
            id=invoice_id,
            file_hash=file_hash,
            semantic_hash=semantic_hash,
            duplicate_of_id=duplicate_of_id,
            filename=filename,
            mime_type=mime_type,
            file_key=file_key,
            page_count=page_count,
            status=status,
            document_type=ext.document_type,
            vendor=ext.vendor,
            vendor_address=ext.vendor_address,
            receipt_number=ext.receipt_number,
            invoice_date=_parse_iso_date(ext.date),
            due_date=_parse_iso_date(ext.due_date),
            currency=ext.currency,
            subtotal=to_decimal(ext.subtotal),
            tax_amount=to_decimal(ext.tax_amount),
            discount_amount=to_decimal(ext.discount_amount),
            total_amount=to_decimal(ext.total_amount),
            bill_to=ext.bill_to,
            extractor_used=run_result.extractor_used,
            extraction_latency_ms=run_result.latency_ms,
            items_match_subtotal=rec.items_match_subtotal,
            totals_reconcile=rec.totals_reconcile,
            raw_ocr_markdown=run_result.ocr.markdown,
            provenance_json={
                k: v.model_dump(mode="json") for k, v in ext.provenance.items()
            },
            warnings_json=list(ext.validation_warnings),
            line_items=_build_line_item_records(invoice_id, ext.line_items),
        )
        session.add(record)
        await session.commit()
        await session.refresh(record, attribute_names=["created_at", "updated_at", "line_items"])
        return record

    @staticmethod
    async def get_by_id(
        session: AsyncSession, invoice_id: uuid.UUID
    ) -> InvoiceRecord | None:
        """Fetch a single invoice with eager-loaded ordered line items."""
        stmt = (
            select(InvoiceRecord)
            .where(col(InvoiceRecord.id) == invoice_id)
            .options(selectinload(cast(Any, InvoiceRecord.line_items)))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_invoices(
        session: AsyncSession,
        *,
        search: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[InvoiceRecord], int]:
        """Search and paginate invoices sorted newest-first."""
        filters: list[Any] = []
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    col(InvoiceRecord.vendor).ilike(term),
                    col(InvoiceRecord.receipt_number).ilike(term),
                    col(InvoiceRecord.filename).ilike(term),
                )
            )
        if status and status.strip():
            filters.append(col(InvoiceRecord.status) == status.strip())
        if date_from is not None:
            filters.append(col(InvoiceRecord.invoice_date) >= date_from)
        if date_to is not None:
            filters.append(col(InvoiceRecord.invoice_date) <= date_to)

        count_stmt = select(func.count()).select_from(InvoiceRecord)
        list_stmt = select(InvoiceRecord)
        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)

        total_res = await session.execute(count_stmt)
        total = int(total_res.scalar_one() or 0)

        rows_res = await session.execute(
            list_stmt.order_by(col(InvoiceRecord.created_at).desc()).limit(limit).offset(offset)
        )
        items = list(rows_res.scalars().all())
        return items, total

    @staticmethod
    async def apply_patch(
        session: AsyncSession,
        record: InvoiceRecord,
        patch: InvoicePatchRequest,
    ) -> InvoiceRecord:
        """Apply partial HITL edits, recalculate math & semantic hash, and save."""
        provided = patch.model_fields_set
        provenance = dict(record.provenance_json or {})

        scalar_map = {
            "document_type": ("document_type", lambda v: v or "invoice"),
            "vendor": ("vendor", lambda v: v),
            "vendor_address": ("vendor_address", lambda v: v),
            "receipt_number": ("receipt_number", lambda v: v),
            "date": ("invoice_date", _parse_iso_date),
            "due_date": ("due_date", _parse_iso_date),
            "currency": ("currency", lambda v: v),
            "subtotal": ("subtotal", to_decimal),
            "tax_amount": ("tax_amount", to_decimal),
            "discount_amount": ("discount_amount", to_decimal),
            "total_amount": ("total_amount", to_decimal),
            "bill_to": ("bill_to", lambda v: v),
        }

        for req_field, (attr_name, transform) in scalar_map.items():
            if req_field not in provided:
                continue
            raw_val = getattr(patch, req_field)
            setattr(record, attr_name, transform(raw_val))
            if req_field != "document_type":
                existing_entry = provenance.get(req_field)
                existing_bbox = (
                    existing_entry.get("bbox") if isinstance(existing_entry, dict) else None
                )
                provenance[req_field] = FieldProvenance(
                    value=raw_val,
                    bbox=BoundingBox.model_validate(existing_bbox) if existing_bbox else None,
                    source="user_edited",
                ).model_dump(mode="json")

        if "line_items" in provided and patch.line_items is not None:
            record.line_items.clear()
            await session.flush()
            record.line_items.extend(_build_line_item_records(record.id, patch.line_items))

        record.provenance_json = provenance

        # Re-evaluate reconciliation and semantic hash against updated fields
        updated_ext = record_to_extraction(record)
        rec = reconcile_invoice(updated_ext, ocr_text=record.raw_ocr_markdown)
        record.items_match_subtotal = rec.items_match_subtotal
        record.totals_reconcile = rec.totals_reconcile
        record.warnings_json = list(rec.warnings)
        record.semantic_hash = compute_semantic_hash(updated_ext)

        if patch.mark_verified:
            record.status = "verified"
        elif "status" in provided and patch.status is not None:
            record.status = patch.status

        await session.commit()
        await session.refresh(record, attribute_names=["updated_at", "line_items"])
        return record

    @staticmethod
    async def delete_invoice(session: AsyncSession, record: InvoiceRecord) -> None:
        """Delete invoice record while nullifying any downstream duplicate references."""
        await session.execute(
            update(InvoiceRecord)
            .where(col(InvoiceRecord.duplicate_of_id) == record.id)
            .values(duplicate_of_id=None)
        )
        await session.delete(record)
        await session.commit()

    @staticmethod
    async def list_for_report(
        session: AsyncSession,
        *,
        invoice_ids: list[uuid.UUID] | None = None,
        status: str | None = None,
    ) -> list[InvoiceRecord]:
        """Fetch matching invoices with line items ordered newest-first for reports."""
        stmt = select(InvoiceRecord).options(
            selectinload(cast(Any, InvoiceRecord.line_items))
        )
        if invoice_ids:
            stmt = stmt.where(col(InvoiceRecord.id).in_(invoice_ids))
        if status and status.strip():
            stmt = stmt.where(col(InvoiceRecord.status) == status.strip())
        stmt = stmt.order_by(col(InvoiceRecord.created_at).desc())
        res = await session.execute(stmt)
        return list(res.scalars().all())
