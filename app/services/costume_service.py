from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.setup_logging import get_logger
from app.models import Costume, CostumeAvailability
from app.schemas import CostumeInput

logger = get_logger(__name__)


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
		logger.info(
			'Costumes retrieved',
			extra={'count': len(costumes), 'availability': availability},
		)
		return costumes

	async def get_by_id(self, session: AsyncSession, costume_id: int) -> Costume:
		costume = await session.scalar(select(Costume).where(Costume.id == costume_id))
		if not costume:
			logger.error('Costume not found', extra={'costume_id': costume_id})
			raise HTTPException(404, detail='Costume not registered.')
		logger.info('Costume retrieved', extra={'costume_id': costume_id})
		return costume

	async def create(
		self, session: AsyncSession, costume_data: CostumeInput
	) -> Costume:
		existing = await session.scalar(
			select(Costume).where(Costume.name == costume_data.name)
		)
		if existing:
			logger.error(
				'Costume already exists',
				extra={'costume_id': existing.id, 'costume_name': costume_data.name},
			)
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
		logger.info(
			'Costume created',
			extra={
				'costume_id': db_costume.id,
				'costume_name': db_costume.name,
				'availability': db_costume.availability,
			},
		)
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
		logger.info(
			'Costume updated',
			extra={
				'costume_id': db_costume.id,
				'costume_name': db_costume.name,
				'availability': db_costume.availability,
			},
		)
		return db_costume

	async def delete(self, session: AsyncSession, costume_id: int) -> None:
		db_costume = await self.get_by_id(session, costume_id)
		await session.delete(db_costume)
		await session.commit()
		logger.info('Costume deleted', extra={'costume_id': costume_id})
