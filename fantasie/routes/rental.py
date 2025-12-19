from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from fantasie.database import get_session
from fantasie.models import (
	Costume,
	CostumeAvailability,
	Customer,
	Employee,
	Rental,
)
from fantasie.schemas import (
	Message,
	RentalInput,
	RentalList,
	RentalSchema,
	RentalPatch,
)
from fantasie.security import get_current_employee


router = APIRouter(prefix='/rental', tags=['rental'])

CurrentEmployee = Annotated[Employee, Depends(get_current_employee)]
SessionDep = Annotated[Session, Depends(get_session)]


def set_rental_attr(rental):
	"""Sets the models' dictionaries to the json response."""
	setattr(rental, 'costume', rental.costumes.__dict__)
	setattr(rental, 'customer', rental.customers.__dict__)
	setattr(rental, 'employee', rental.employees.__dict__)

	return rental


@router.get('/', response_model=RentalList)
def read_rental_list(
	session: SessionDep,
	current_employee: CurrentEmployee,
	skip: int = 0,
	limit: int = 100,
):
	db_rental_list = session.scalars(
		select(Rental).offset(skip).limit(limit)
	).all()

	rental_list = [
		set_rental_attr(rental_obj) for rental_obj in db_rental_list
	]

	return {'rental_list': rental_list}


@router.get('/{rental_id}', response_model=RentalSchema)
def read_rental(
	session: SessionDep, current_employee: CurrentEmployee, rental_id: int
):
	db_rental = session.scalar(select(Rental).where(Rental.id == rental_id))

	if not db_rental:
		raise HTTPException(404, detail='Rental not registered.')

	set_rental_attr(db_rental)

	return db_rental


@router.post('/', response_model=RentalSchema, status_code=201)
def create_rental(
	session: SessionDep, current_employee: CurrentEmployee, rental: RentalInput
):
	# Costume code
	db_costume = session.scalar(
		select(Costume).where(Costume.id == rental.costume_id)
	)
	if not db_costume:
		raise HTTPException(400, detail='Costume not registered.')
	
	if db_costume.availability == CostumeAvailability.UNAVAILABLE:
		raise HTTPException(400, detail='Costume unavailable.')
	
	db_costume.availability = CostumeAvailability.UNAVAILABLE

	# Customer code
	db_customer = session.scalar(
		select(Customer).where(Customer.cpf == rental.customer_cpf)
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
	session.commit()
	session.refresh(db_rental)

	set_rental_attr(db_rental)

	return db_rental


@router.patch('/{rental_id}', response_model=RentalSchema)
def patch_rental(
	session: SessionDep,
	current_employee: CurrentEmployee,
	rental_id: int,
	rental: RentalPatch,
):
	db_rental = session.scalar(select(Rental).where(Rental.id == rental_id))
	
	if not db_rental:
		raise HTTPException(404, detail='Rental not registered.')

	for key, value in rental.model_dump(exclude_unset=True).items():
		setattr(db_rental, key, value)

	if db_rental.return_date < db_rental.rental_date:
		raise HTTPException(
			400, detail="Rental date can't be later than return date."
		)

	session.add(db_rental)
	session.commit()
	session.refresh(db_rental)

	set_rental_attr(db_rental)

	return db_rental


@router.delete('/{rental_id}', response_model=Message)
def delete_rental(
	session: SessionDep, current_employee: CurrentEmployee, rental_id: int
):
	db_rental = session.scalar(select(Rental).where(Rental.id == rental_id))

	if not db_rental:
		raise HTTPException(404, detail='Rental not registered.')

	# Updating unavailable costume to available
	db_costume = session.scalar(
		select(Costume).where(Costume.id == db_rental.costume_id)
	)
	db_costume.availability = CostumeAvailability.AVAILABLE

	session.delete(db_rental)
	session.commit()

	return {'message': 'Rental register has been deleted successfully.'}
