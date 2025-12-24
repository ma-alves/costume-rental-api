from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
	Costume,
	CostumeAvailability,
	Customer,
	Employee,
	Rental,
)
from app.schemas import (
	Message,
	RentalInput,
	RentalList,
	RentalSchema,
	RentalPatch,
)
from app.security import get_current_employee


router = APIRouter(prefix='/rental', tags=['rental'])

CurrentEmployee = Annotated[Employee, Depends(get_current_employee)]
Session = Annotated[AsyncSession, Depends(get_session)]


def set_rental_attr(rental):
	"""Set the models dictionaries in the json response. É uma gambiarra absurda desenvolvida através do desespero, em algum momento encontrarei uma solução melhor."""
	setattr(rental, 'costume', rental.costumes.__dict__)
	setattr(rental, 'customer', rental.customers.__dict__)
	setattr(rental, 'employee', rental.employees.__dict__)

	return rental


@router.get('/', response_model=RentalList)
async def read_rental_list(
	session: Session,
	current_employee: CurrentEmployee,
	skip: int = 0,
	limit: int = 100,
):
	db_rental_list_scalar = await session.scalars(
		select(Rental).offset(skip).limit(limit)
	)
	db_rental_list = db_rental_list_scalar.all()

	rental_list = [set_rental_attr(rental_obj) for rental_obj in db_rental_list]

	return {'rental_list': rental_list}


@router.get('/{rental_id}', response_model=RentalSchema)
async def read_rental(
	session: Session, current_employee: CurrentEmployee, rental_id: int
):
	db_rental = await session.scalar(select(Rental).where(Rental.id == rental_id))

	if not db_rental:
		raise HTTPException(404, detail='Rental not registered.')

	set_rental_attr(db_rental)

	return db_rental


@router.post('/', response_model=RentalSchema, status_code=201)
async def create_rental(
	session: Session, current_employee: CurrentEmployee, rental: RentalInput
):
	# Costume code
	db_costume = await session.scalar(
		select(Costume).where(Costume.id == rental.costume_id)
	)
	if not db_costume:
		raise HTTPException(400, detail='Costume not registered.')

	if db_costume.availability == CostumeAvailability.UNAVAILABLE:
		raise HTTPException(400, detail='Costume unavailable.')

	db_costume.availability = CostumeAvailability.UNAVAILABLE

	# Customer code
	db_customer = await session.scalar(
		select(Customer).where(Customer.id == rental.customer_id)
	)
	if not db_customer:
		raise HTTPException(400, detail='Customer not registered.')

	# Rental code
	db_rental = Rental(
		employee_id=current_employee.id,
		customer_id=db_customer.id,
		costume_id=rental.costume_id,
	)

	session.add(db_rental)
	await session.commit()
	await session.refresh(db_rental)

	set_rental_attr(db_rental)

	return db_rental


@router.patch('/{rental_id}', response_model=RentalSchema)
async def patch_rental(
	session: Session,
	current_employee: CurrentEmployee,
	rental_id: int,
	rental: RentalPatch,
):
	db_rental = await session.scalar(select(Rental).where(Rental.id == rental_id))

	if not db_rental:
		raise HTTPException(404, detail='Rental not registered.')

	for key, value in rental.model_dump(exclude_unset=True).items():
		setattr(db_rental, key, value)

	if db_rental.return_date < db_rental.rental_date:
		raise HTTPException(400, detail="Rental date can't be later than return date.")

	session.add(db_rental)
	await session.commit()
	await session.refresh(db_rental)

	set_rental_attr(db_rental)

	return db_rental


@router.delete('/{rental_id}', response_model=Message)
async def delete_rental(
	session: Session, current_employee: CurrentEmployee, rental_id: int
):
	db_rental = await session.scalar(select(Rental).where(Rental.id == rental_id))

	if not db_rental:
		raise HTTPException(404, detail='Rental not registered.')

	# Updating unavailable costume to available
	db_costume = await session.scalar(
		select(Costume).where(Costume.id == db_rental.costume_id)
	)
	db_costume.availability = CostumeAvailability.AVAILABLE

	await session.delete(db_rental)
	await session.commit()

	return {'message': 'Rental register has been deleted successfully.'}
