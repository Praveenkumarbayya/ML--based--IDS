"""Async SQLAlchemy setup."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.settings import get_settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _ensure_engine():
    global _engine, _sessionmaker
    if _engine is None:
        settings = get_settings()
        # SQLite: make sure the parent directory exists.
        if settings.database_url.startswith("sqlite"):
            db_path = settings.database_url.split("///", 1)[-1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
        _sessionmaker = async_sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False,
        )
    return _engine, _sessionmaker


async def init_db() -> None:
    """Create tables on startup. Alembic handles migrations in production,
    but this keeps dev ergonomic."""
    # Import so the models register on Base.metadata.
    from src import db_models  # noqa: F401

    engine, _ = _ensure_engine()
    async with engine.begin() as conn:
        # Enable WAL for SQLite — better concurrency without ceremony.
        settings = get_settings()
        if settings.database_url.startswith("sqlite"):
            await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            await conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
        await conn.run_sync(Base.metadata.create_all)


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a session scoped to one request."""
    _, sm = _ensure_engine()
    async with sm() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
