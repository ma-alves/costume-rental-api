from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from .settings import Settings


engine = create_async_engine(Settings().DATABASE_URL)
# Base.metadata.create_all(bind=engine)


async def get_session():
	with AsyncSession(engine, expire_on_commit=False) as session:
		yield session
