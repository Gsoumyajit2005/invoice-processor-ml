"""Local filesystem object storage for development and single-node deployments."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path


class LocalDiskStorage:
    """Stores documents and rendered page images under a sandboxed root directory."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, key: str) -> Path:
        clean_key = key.lstrip("/")
        target = (self.root_dir / clean_key).resolve()
        if not target.is_relative_to(self.root_dir):
            raise ValueError(f"Unsafe storage key outside root: {key!r}")
        return target

    def _put_sync(self, key: str, data: bytes) -> str:
        target = self._safe_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return key.lstrip("/")

    def _get_sync(self, key: str) -> bytes:
        target = self._safe_path(key)
        if not target.is_file():
            raise FileNotFoundError(key)
        return target.read_bytes()

    def _delete_prefix_sync(self, prefix: str) -> int:
        clean = prefix.strip("/")
        target = self._safe_path(clean)
        if target.is_dir():
            count = sum(1 for p in target.rglob("*") if p.is_file())
            shutil.rmtree(target)
            return count
        if target.is_file():
            target.unlink()
            return 1
        return 0

    async def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        _ = content_type
        return await asyncio.to_thread(self._put_sync, key, data)

    async def get_bytes(self, key: str) -> bytes:
        return await asyncio.to_thread(self._get_sync, key)

    async def delete_prefix(self, prefix: str) -> int:
        return await asyncio.to_thread(self._delete_prefix_sync, prefix)

    async def exists(self, key: str) -> bool:
        target = self._safe_path(key)
        return await asyncio.to_thread(target.is_file)
