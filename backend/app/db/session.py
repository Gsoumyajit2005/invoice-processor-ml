"""Async SQLAlchemy engine and session management."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

from app.core.config import Settings


def create_engine_and_sessionmaker(
    settings: Settings,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Build async SQLAlchemy engine and session factory for Postgres or SQLite."""
    is_sqlite = settings.database_url.startswith("sqlite")
    kwargs = {"echo": False, "future": True}
    if not is_sqlite:
        kwargs["pool_pre_ping"] = True
    engine = create_async_engine(settings.database_url, **kwargs)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine, session_factory


async def init_db(engine: AsyncEngine) -> None:
    """Ensure tables exist when bootstrapping lightweight dev/test SQLite databases."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession and guarantee close on request exit."""
    async with session_factory() as session:
        yield session
