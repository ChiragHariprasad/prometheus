from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
)
from app.core.config import settings


engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=settings.POSTGRES_POOL_SIZE,
    max_overflow=settings.POSTGRES_MAX_OVERFLOW,
    pool_timeout=settings.POSTGRES_POOL_TIMEOUT,
    pool_recycle=settings.POSTGRES_POOL_RECYCLE,
    echo=settings.POSTGRES_ECHO,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
