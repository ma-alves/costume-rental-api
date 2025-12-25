from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator

from .settings import Settings


DATABASE_URL = Settings().DATABASE_URL

async_engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    expire_on_commit=False, 
    class_=AsyncSession,
    autoflush=False
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit() # Commit changes if the request is successful
        except Exception:
            await session.rollback() # Rollback on exception
            raise
        finally:
            await session.close() # Ensure the session is closed
