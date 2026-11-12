"""Pluggable document/page storage backends."""

from app.storage.base import StorageBackend, build_storage_backend
from app.storage.local import LocalDiskStorage
from app.storage.postgres import PostgresStorage
from app.storage.s3 import S3Storage

__all__ = [
    "LocalDiskStorage",
    "PostgresStorage",
    "S3Storage",
    "StorageBackend",
    "build_storage_backend",
]
