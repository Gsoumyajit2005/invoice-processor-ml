"""Single and batch invoice extraction endpoints."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_app_settings,
    get_cloud_config,
    get_db_session,
    get_extraction_router,
    get_storage,
    limiter,
    rate_limit_extract_rule,
    verify_backend_secret,
)
from app.core.config import Settings
from app.core.schemas import ExtractionResponse
from app.extractors.base import CloudConfig
from app.extractors.cloud_vlm import CloudConfigError
from app.extractors.local_vlm import LocalVlmUnavailableError
from app.extractors.router import ExtractionRouter
from app.pdf.processor import DocumentValidationError, UnsupportedMediaTypeError
from app.services.ingestion import PayloadTooLargeError, extract_and_persist
from app.storage.base import StorageBackend

router = APIRouter(
    tags=["extract"],
    dependencies=[Depends(verify_backend_secret)],
)

_MAX_BATCH_FILES = 20


class BatchItemResult(BaseModel):
    """Per-file outcome in a batch upload."""

    filename: str
    ok: bool
    result: ExtractionResponse | None = None
    error: str | None = None


class BatchExtractionResponse(BaseModel):
    """Batch upload summary and per-file extraction payloads."""

    total: int
    succeeded: int
    failed: int
    items: list[BatchItemResult]


async def _read_bounded_upload(upload: UploadFile, max_bytes: int) -> bytes:
    content = await upload.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise PayloadTooLargeError(
            f"Uploaded file exceeds maximum allowed size ({max_bytes // (1024 * 1024)} MB)."
        )
    return content


def _to_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, PayloadTooLargeError):
        return HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc))
    if isinstance(exc, UnsupportedMediaTypeError):
        return HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        )
    if isinstance(exc, (DocumentValidationError, CloudConfigError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, LocalVlmUnavailableError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Extraction failed: {exc}",
    )


@router.post("/extract", response_model=ExtractionResponse)
@limiter.limit(rate_limit_extract_rule)
async def extract_single_invoice(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
    extraction_router: Annotated[ExtractionRouter, Depends(get_extraction_router)],
    cloud_config: Annotated[CloudConfig | None, Depends(get_cloud_config)],
    file: UploadFile = File(...),
    mode: Literal["auto", "local", "cloud"] | None = Query(default=None),
) -> ExtractionResponse:
    """Upload a single image or multi-page PDF, extract structured fields, and persist."""
    _ = request
    try:
        content = await _read_bounded_upload(file, settings.max_upload_bytes)
        return await extract_and_persist(
            content=content,
            filename=file.filename,
            mode=mode,
            cloud_config=cloud_config,
            settings=settings,
            router=extraction_router,
            storage=storage,
            session=session,
        )
    except Exception as exc:
        await session.rollback()
        raise _to_http_exception(exc) from exc


@router.post("/extract/batch", response_model=BatchExtractionResponse)
@limiter.limit(rate_limit_extract_rule)
async def extract_batch_invoices(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
    extraction_router: Annotated[ExtractionRouter, Depends(get_extraction_router)],
    cloud_config: Annotated[CloudConfig | None, Depends(get_cloud_config)],
    files: list[UploadFile] = File(...),
    mode: Literal["auto", "local", "cloud"] | None = Query(default=None),
) -> BatchExtractionResponse:
    """Sequentially process a batch of uploaded invoices with per-file fault isolation."""
    _ = request
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file must be uploaded.",
        )
    if len(files) > _MAX_BATCH_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch upload supports at most {_MAX_BATCH_FILES} files per request.",
        )

    results: list[BatchItemResult] = []
    succeeded = 0
    for upload in files:
        fname = upload.filename or "document"
        try:
            content = await _read_bounded_upload(upload, settings.max_upload_bytes)
            extracted = await extract_and_persist(
                content=content,
                filename=fname,
                mode=mode,
                cloud_config=cloud_config,
                settings=settings,
                router=extraction_router,
                storage=storage,
                session=session,
            )
            results.append(BatchItemResult(filename=fname, ok=True, result=extracted))
            succeeded += 1
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            results.append(BatchItemResult(filename=fname, ok=False, error=str(exc)))

    return BatchExtractionResponse(
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        items=results,
    )
