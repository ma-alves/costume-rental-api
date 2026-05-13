from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Costume, CostumeAvailability, Rental, Role, User
from app.schemas.rental_schema import RentalInput


class RentalService:
	async def get_all(self, session: AsyncSession, skip: int = 0, limit: int = 100):
		rentals_scalar = await session.scalars(select(Rental).offset(skip).limit(limit))
		rentals = rentals_scalar.all()
		for rental in rentals:
			self._set_rental_attr(rental)

		return rentals

	async def get_by_id(self, session: AsyncSession, rental_id: int) -> Rental:
		rental = await session.scalar(select(Rental).where(Rental.id == rental_id))
		if not rental:
			raise HTTPException(404, detail='Rental not registered.')
		self._set_rental_attr(rental)

		return rental

	async def create(
		self, session: AsyncSession, rental_data: RentalInput, current_user: User
	) -> Rental:
		db_costume = await session.scalar(
			select(Costume).where(Costume.id == rental_data.costume_id)
		)
		if not db_costume:
			raise HTTPException(400, detail='Costume not registered.')
		if db_costume.availability == CostumeAvailability.UNAVAILABLE:
			raise HTTPException(400, detail='Costume unavailable.')
		db_costume.availability = CostumeAvailability.UNAVAILABLE

		db_customer = await session.scalar(
			select(User).where(
				User.id == rental_data.customer_id, User.role == Role.CUSTOMER
			)
		)
		if not db_customer:
			raise HTTPException(400, detail='Customer not registered.')

		db_rental = Rental(
			user_id=current_user.id,
			costume_id=rental_data.costume_id,
		)
		session.add(db_rental)
		await session.commit()
		await session.refresh(db_rental)
		self._set_rental_attr(db_rental)

		return db_rental

	async def delete(self, session: AsyncSession, rental_id: int) -> None:
		db_rental = await session.scalar(select(Rental).where(Rental.id == rental_id))
		if not db_rental:
			raise HTTPException(404, detail='Rental not registered.')

		db_costume = await session.scalar(
			select(Costume).where(Costume.id == db_rental.costume_id)
		)
		db_costume.availability = CostumeAvailability.AVAILABLE
		await session.delete(db_rental)
		await session.commit()

    # Método interno para adequação ao Pydantic em outputs aninhados, futuramente revisar
	def _set_rental_attr(self, rental: Rental) -> Rental:
		"""Sets costume and rental attributes on rental.__dict__"""
		setattr(rental, 'costume', rental.costumes.__dict__)
		setattr(rental, 'user', rental.users.__dict__)
		return rental
