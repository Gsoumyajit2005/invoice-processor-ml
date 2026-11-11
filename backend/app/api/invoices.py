"""Invoice CRUD, HITL edit/verify, search pagination, and rendered page streaming."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_storage, verify_backend_secret
from app.core.schemas import (
    InvoiceDetailResponse,
    InvoiceListResponse,
    InvoicePatchRequest,
)
from app.db.repository import InvoiceRepository, record_to_detail, record_to_summary
from app.storage.base import StorageBackend

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"],
    dependencies=[Depends(verify_backend_secret)],
)


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> InvoiceListResponse:
    """List invoices with optional search, status/date filters, and pagination."""
    rows, total = await InvoiceRepository.list_invoices(
        session,
        search=search,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return InvoiceListResponse(
        items=[record_to_summary(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
async def get_invoice_detail(
    invoice_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvoiceDetailResponse:
    """Fetch full invoice details, line items, provenance boxes, and page image URLs."""
    record = await InvoiceRepository.get_by_id(session, invoice_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found.",
        )
    return record_to_detail(record)


@router.patch("/{invoice_id}", response_model=InvoiceDetailResponse)
async def patch_invoice(
    invoice_id: uuid.UUID,
    patch: InvoicePatchRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvoiceDetailResponse:
    """Apply HITL corrections to fields/line items and optionally mark verified."""
    record = await InvoiceRepository.get_by_id(session, invoice_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found.",
        )
    updated = await InvoiceRepository.apply_patch(session, record, patch)
    return record_to_detail(updated)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> Response:
    """Delete an invoice record and its stored original & page PNG artifacts."""
    record = await InvoiceRepository.get_by_id(session, invoice_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found.",
        )
    await InvoiceRepository.delete_invoice(session, record)
    await storage.delete_prefix(f"invoices/{invoice_id}/")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{invoice_id}/pages/{page}")
async def get_invoice_page_image(
    invoice_id: uuid.UUID,
    page: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> Response:
    """Stream rendered page PNG image for side-by-side Workbench bounding-box overlay."""
    if page < 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid page number.")

    record = await InvoiceRepository.get_by_id(session, invoice_id)
    if record is None or page > record.page_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page} for invoice {invoice_id} not found.",
        )

    page_key = f"invoices/{invoice_id}/pages/{page}.png"
    try:
        png_bytes = await storage.get_bytes(page_key)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stored image missing for page {page}.",
        ) from exc

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=3600"},
    )
