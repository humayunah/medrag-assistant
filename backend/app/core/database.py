from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Deferred initialization — engine is created at app startup, not at import time.
# This prevents import errors when DATABASE_URL is not yet configured.
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None:
    """Initialize the database engine. Call this during FastAPI lifespan startup."""
    global engine, async_session_factory

    from app.core.config import settings

    db_url = settings.DATABASE_POOL_URL or settings.DATABASE_URL
    if not db_url:
        raise RuntimeError("DATABASE_URL or DATABASE_POOL_URL must be set")

    engine = create_async_engine(
        db_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"statement_cache_size": 0},
    )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_engine() first.")
    return async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_tenant_db(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a tenant-scoped database session.

    Sets the PostgreSQL session variable `app.current_tenant` so that
    Row Level Security policies can filter by tenant automatically.
    """
    factory = _get_session_factory()
    async with factory() as session:
        try:
            await session.execute(
                text("SET app.current_tenant = :tenant_id"),
                {"tenant_id": tenant_id},
            )
            yield session
        finally:
            await session.close()
