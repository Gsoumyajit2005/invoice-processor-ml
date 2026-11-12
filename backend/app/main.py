"""FastAPI application entrypoint and lifespan wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler

from app.api import extract, health, invoices, reports
from app.api.deps import limiter
from app.core.config import Settings, get_settings
from app.core.paths import configure_local_caches
from app.db.session import create_engine_and_sessionmaker, init_db
from app.extractors.router import ExtractionRouter
from app.storage.base import build_storage_backend


def create_app(
    settings_override: Settings | None = None,
    *,
    router_override: ExtractionRouter | None = None,
) -> FastAPI:
    """Build and configure the FastAPI application cleanly for prod and tests."""
    active_settings = settings_override or get_settings()

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
        configure_local_caches(offline=active_settings.local_vlm_offline)
        engine, session_factory = create_engine_and_sessionmaker(active_settings)
        storage = build_storage_backend(active_settings, session_factory=session_factory)
        extraction_router = router_override or ExtractionRouter(active_settings)

        app_instance.state.settings = active_settings
        app_instance.state.engine = engine
        app_instance.state.session_factory = session_factory
        app_instance.state.storage = storage
        app_instance.state.router = extraction_router

        if active_settings.database_url.startswith("sqlite"):
            await init_db(engine)

        try:
            yield
        finally:
            await engine.dispose()

    app_instance = FastAPI(
        title="Hybrid Document AI Invoice Processor",
        version="2.0.0",
        lifespan=lifespan,
    )
    app_instance.state.limiter = limiter
    app_instance.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,  # type: ignore[arg-type]
    )

    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app_instance.include_router(health.router, prefix="/api/v1")
    app_instance.include_router(extract.router, prefix="/api/v1")
    app_instance.include_router(invoices.router, prefix="/api/v1")
    app_instance.include_router(reports.router, prefix="/api/v1")

    return app_instance


app = create_app()
