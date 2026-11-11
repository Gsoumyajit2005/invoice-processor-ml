"""Application settings via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import REPO_ROOT


class Settings(BaseSettings):
    """Typed runtime configuration loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5433/invoices_db"
    )

    # Storage
    storage_backend: Literal["local", "s3"] = "local"
    local_upload_dir: str = "backend/uploads"
    s3_bucket: str | None = None
    s3_region: str = "auto"
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None

    # Security & API limits
    backend_shared_secret: str | None = None
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )
    max_upload_mb: int = Field(default=20, ge=1, le=100)
    max_pdf_pages: int = Field(default=20, ge=1, le=100)
    rate_limit_extract: str = "20/minute"

    # Extraction & VLM settings
    extractor_default_mode: Literal["auto", "local", "cloud"] = "auto"
    local_vlm_enabled: bool = True
    local_vlm_dtype: Literal["float16", "bfloat16"] = "float16"
    local_vlm_max_new_tokens: int = Field(default=1536, ge=256, le=4096)
    local_vlm_adapter_dir: str | None = "models/qwen35-0.8b-invoice-lora"
    local_vlm_offline: bool = True
    ocr_dpi: float = Field(default=150.0, ge=72.0, le=300.0)
    ocr_threads: int = Field(default=4, ge=1, le=16)

    # Optional server-side Cloud VLM fallback defaults (per-request headers override)
    default_cloud_provider: str | None = "gemini"
    default_cloud_model: str | None = "gemini/gemini-2.5-flash"
    default_cloud_api_key: str | None = None

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def resolved_upload_dir(self) -> Path:
        path = Path(self.local_upload_dir)
        return path if path.is_absolute() else (REPO_ROOT / path)

    @property
    def resolved_adapter_dir(self) -> Path | None:
        if not self.local_vlm_adapter_dir:
            return None
        path = Path(self.local_vlm_adapter_dir)
        return path if path.is_absolute() else (REPO_ROOT / path)

    @property
    def sync_database_url(self) -> str:
        """Convert async DB URL to sync driver URL for Alembic migrations."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        if url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()
