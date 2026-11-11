"""Shared FastAPI dependencies, authentication secret verification, and rate limiter."""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.extractors.base import CloudConfig
from app.extractors.router import ExtractionRouter
from app.storage.base import StorageBackend

limiter = Limiter(key_func=get_remote_address)


def rate_limit_extract_rule() -> str:
    """Resolve configurable rate limit string dynamically for slowapi."""
    return get_settings().rate_limit_extract


def get_app_settings(request: Request) -> Settings:
    """Return active Settings bound to FastAPI app state."""
    return request.app.state.settings


def get_storage(request: Request) -> StorageBackend:
    """Return StorageBackend bound to FastAPI app state."""
    return request.app.state.storage


def get_extraction_router(request: Request) -> ExtractionRouter:
    """Return ExtractionRouter bound to FastAPI app state."""
    return request.app.state.router


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession per HTTP request."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


async def verify_backend_secret(
    settings: Annotated[Settings, Depends(get_app_settings)],
    x_backend_secret: str | None = Header(default=None),
) -> None:
    """Validate optional X-Backend-Secret header when BACKEND_SHARED_SECRET is set."""
    expected = settings.backend_shared_secret
    if not expected:
        return
    if not x_backend_secret or not secrets.compare_digest(x_backend_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Backend-Secret header.",
        )


def get_cloud_config(
    x_llm_provider: str | None = Header(default=None),
    x_llm_model: str | None = Header(default=None),
    x_llm_api_key: str | None = Header(default=None),
) -> CloudConfig | None:
    """Extract ephemeral BYO-key headers into an unlogged CloudConfig."""
    if not any((x_llm_provider, x_llm_model, x_llm_api_key)):
        return None
    return CloudConfig(
        provider=x_llm_provider,
        model=x_llm_model,
        api_key=x_llm_api_key,
    )
