from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.config import get_settings


settings = get_settings()

engine = None
AsyncSessionLocal = None


def get_engine():
    global engine

    if engine is None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required for database-backed APIs.")
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global AsyncSessionLocal

    if AsyncSessionLocal is None:
        AsyncSessionLocal = async_sessionmaker(get_engine(), expire_on_commit=False)
    return AsyncSessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_sessionmaker()() as session:
        yield session
