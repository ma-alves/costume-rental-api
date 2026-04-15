from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Costume, CostumeAvailability
from app.schemas import CostumeInput


class CostumeService:
	async def get_all(
		self,
		session: AsyncSession,
		availability: CostumeAvailability,
		skip: int = 0,
		limit: int = 100,
	):
		query = select(Costume)
		if availability:
			query = query.filter(Costume.availability == availability)
		costumes_scalar = await session.scalars(query.offset(skip).limit(limit))
		costumes = costumes_scalar.all()

		return costumes

	async def get_by_id(self, session: AsyncSession, costume_id: int) -> Costume:
		costume = await session.scalar(select(Costume).where(Costume.id == costume_id))
		if not costume:
			raise HTTPException(404, detail='Costume not registered.')

		return costume

	async def create(
		self, session: AsyncSession, costume_data: CostumeInput
	) -> Costume:
		existing = await session.scalar(
			select(Costume).where(Costume.name == costume_data.name)
		)
		if existing:
			raise HTTPException(409, detail='Costume already registered.')
		db_costume = Costume(
			name=costume_data.name,
			description=costume_data.description,
			fee=costume_data.fee,
			availability=costume_data.availability,
		)
		session.add(db_costume)
		await session.commit()
		await session.refresh(db_costume)

		return db_costume

	async def update(
		self, session: AsyncSession, costume_id: int, costume_data: CostumeInput
	) -> Costume:
		db_costume = await self.get_by_id(session, costume_id)
		db_costume.name = costume_data.name
		db_costume.description = costume_data.description
		db_costume.fee = costume_data.fee
		db_costume.availability = costume_data.availability
		await session.commit()
		await session.refresh(db_costume)

		return db_costume

	async def delete(self, session: AsyncSession, costume_id: int) -> None:
		db_costume = await self.get_by_id(session, costume_id)
		await session.delete(db_costume)
		await session.commit()
