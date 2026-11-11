"""Health check endpoint reporting database, storage, and local VLM readiness."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_app_settings, get_db_session, get_extraction_router
from app.core.config import Settings
from app.extractors.local_vlm import LocalVlmExtractor
from app.extractors.router import ExtractionRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    settings: Annotated[Settings, Depends(get_app_settings)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    extraction_router: Annotated[ExtractionRouter, Depends(get_extraction_router)],
) -> dict[str, object]:
    """Return service health, database connectivity, and VLM readiness."""
    db_ok = False
    db_error: str | None = None
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        db_error = str(exc)

    local_status = (
        extraction_router.local_extractor.warmup_status()
        if isinstance(extraction_router.local_extractor, LocalVlmExtractor)
        else {"enabled": True, "loaded": True}
    )

    return {
        "status": "ok" if db_ok else "degraded",
        "database": {"connected": db_ok, "error": db_error},
        "storage_backend": settings.storage_backend,
        "local_vlm": local_status,
        "cloud_default_configured": bool(settings.default_cloud_api_key),
        "limits": {
            "max_upload_mb": settings.max_upload_mb,
            "max_pdf_pages": settings.max_pdf_pages,
            "rate_limit_extract": settings.rate_limit_extract,
        },
    }
