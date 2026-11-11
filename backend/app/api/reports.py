"""Bulk export endpoints (JSON, CSV, and XSS-safe HTML)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, verify_backend_secret
from app.core.schemas import BulkReportRequest
from app.db.repository import InvoiceRepository
from app.services.reporting import (
    generate_csv_report,
    generate_html_report,
    generate_json_report,
)

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(verify_backend_secret)],
)


@router.post("/bulk")
async def export_bulk_report(
    payload: BulkReportRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    """Generate a bulk report over filtered or selected invoices."""
    records = await InvoiceRepository.list_for_report(
        session,
        invoice_ids=payload.invoice_ids,
        status=payload.status,
    )

    if payload.format == "csv":
        return Response(
            content=generate_csv_report(records),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="invoices_report.csv"'},
        )
    if payload.format == "html":
        return Response(
            content=generate_html_report(records),
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="invoices_report.html"'},
        )
    return Response(
        content=generate_json_report(records),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="invoices_report.json"'},
    )
