"""Unit tests for PostgresStorage backend."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from app.db.session import create_engine_and_sessionmaker
from app.storage.postgres import PostgresStorage


@pytest.mark.asyncio
async def test_postgres_storage_crud_lifecycle():
    settings = Settings()
    engine, session_factory = create_engine_and_sessionmaker(settings)
    storage = PostgresStorage(session_factory)

    test_key = "tests/mock_invoice/pages/1.png"
    sample_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"

    # Put
    stored_key = await storage.put_bytes(test_key, sample_data, content_type="image/png")
    assert stored_key == test_key

    # Exists
    exists = await storage.exists(test_key)
    assert exists is True

    # Get
    data = await storage.get_bytes(test_key)
    assert data == sample_data

    # Delete prefix
    deleted_count = await storage.delete_prefix("tests/mock_invoice/")
    assert deleted_count >= 1

    # Verify deleted
    assert await storage.exists(test_key) is False
    with pytest.raises(FileNotFoundError):
        await storage.get_bytes(test_key)

    await engine.dispose()
