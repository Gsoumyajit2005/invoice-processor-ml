"""Database-backed object storage for serverless environments (Supabase / PostgreSQL)."""

from __future__ import annotations

import logging
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

logger = logging.getLogger(__name__)


class PostgresStorage:
    """Stores documents and rendered page images in PostgreSQL `storage_objects` table."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        clean_key = key.lstrip("/")
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO storage_objects (key, content_type, data, created_at)
                        VALUES (:key, :content_type, :data, NOW())
                        ON CONFLICT (key) DO UPDATE
                        SET content_type = EXCLUDED.content_type,
                            data = EXCLUDED.data,
                            created_at = NOW()
                        """
                    ),
                    {"key": clean_key, "content_type": content_type, "data": data},
                )
        return clean_key

    async def get_bytes(self, key: str) -> bytes:
        clean_key = key.lstrip("/")
        async with self._session_factory() as session:
            res = await session.execute(
                text("SELECT data FROM storage_objects WHERE key = :key"),
                {"key": clean_key},
            )
            row = res.fetchone()
            if row is None:
                raise FileNotFoundError(clean_key)
            return bytes(row[0])

    async def delete_prefix(self, prefix: str) -> int:
        clean = prefix.lstrip("/")
        like_pattern = f"{clean}%"
        async with self._session_factory() as session:
            async with session.begin():
                res = await session.execute(
                    text("DELETE FROM storage_objects WHERE key LIKE :pattern"),
                    {"pattern": like_pattern},
                )
                return res.rowcount or 0

    async def exists(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        async with self._session_factory() as session:
            res = await session.execute(
                text("SELECT 1 FROM storage_objects WHERE key = :key"),
                {"key": clean_key},
            )
            return res.scalar() is not None
