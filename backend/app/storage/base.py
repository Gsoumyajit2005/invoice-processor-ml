"""Storage backend protocol and configuration factory (local disk or S3/Supabase/R2)."""

from __future__ import annotations

from typing import Protocol

from app.core.config import Settings


class StorageBackend(Protocol):
    """Abstract async object storage for uploaded documents and rendered page PNGs."""

    async def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Persist bytes at key and return the canonical storage key."""
        ...

    async def get_bytes(self, key: str) -> bytes:
        """Read bytes for key; raise FileNotFoundError if absent."""
        ...

    async def delete_prefix(self, prefix: str) -> int:
        """Delete all objects sharing prefix and return count deleted."""
        ...

    async def exists(self, key: str) -> bool:
        """Return True if object exists at key."""
        ...


def build_storage_backend(
    settings: Settings,
    *,
    session_factory: Any | None = None,
) -> StorageBackend:
    """Instantiate configured StorageBackend (PostgreSQL, local disk, or S3-compatible)."""
    if settings.storage_backend == "s3":
        from app.storage.s3 import S3Storage

        if not settings.s3_bucket:
            raise ValueError("S3_BUCKET must be configured when STORAGE_BACKEND=s3.")
        return S3Storage(
            bucket=settings.s3_bucket,
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )

    if session_factory is not None and (
        settings.storage_backend == "database" or "sqlite" not in settings.database_url
    ):
        from app.storage.postgres import PostgresStorage

        return PostgresStorage(session_factory)

    from app.storage.local import LocalDiskStorage

    return LocalDiskStorage(settings.resolved_upload_dir)
