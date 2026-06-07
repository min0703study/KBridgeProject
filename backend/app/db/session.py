from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.config import get_settings


def _get_database_url() -> str:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for the PostgreSQL backend")
    return settings.database_url


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(_get_database_url(), pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async_session_maker = get_sessionmaker()
    async with async_session_maker() as session:
        yield session
