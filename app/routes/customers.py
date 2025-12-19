from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Customer, Employee
from app.schemas import CustomerSchema, CustomerList, Message
from app.security import get_current_employee


router = APIRouter(prefix='/customers', tags=['customers'])

CurrentEmployee = Annotated[Employee, Depends(get_current_employee)]
SessionDep = Annotated[Session, Depends(get_session)]


@router.get('/', response_model=CustomerList)
def get_customers(
	session: SessionDep,
	current_employee: CurrentEmployee,
	skip: int = 0,
	limit: int = 0,
):
	customers = session.scalars(
		select(Customer).offset(skip).limit(limit)
	).all()

	return {'customers': customers}


@router.get('/{customer_cpf}', response_model=CustomerSchema)
def get_customer(
	session: SessionDep, current_employee: CurrentEmployee, customer_cpf: str
):
	db_customer = session.scalar(
		select(Customer).where(Customer.cpf == customer_cpf)
	)

	if not db_customer:
		raise HTTPException(404, detail='Customer not registered.')

	return db_customer


@router.post('/', response_model=CustomerSchema, status_code=201)
def create_customer(
	session: SessionDep,
	current_employee: CurrentEmployee,
	customer: CustomerSchema,
):
	db_customer = session.scalar(
		select(Customer).where(Customer.cpf == customer.cpf)
	)
	if db_customer:
		raise HTTPException(400, detail='Customer already registered.')

	db_customer = Customer(
		cpf=customer.cpf,
		name=customer.name,
		email=customer.email,
		phone_number=customer.phone_number,
		address=customer.address,
	)

	session.add(db_customer)
	session.commit()
	session.refresh(db_customer)

	return db_customer


@router.put('/{customer_cpf}', response_model=CustomerSchema)
def update_customer(
	session: SessionDep,
	current_employee: CurrentEmployee,
	customer: CustomerSchema,
	customer_cpf: int,
):
	db_customer = session.scalar(
		select(Customer).where(Customer.cpf == customer_cpf)
	)

	if not db_customer:
		raise HTTPException(404, detail='Customer not registered.')

	db_customer.cpf = customer.cpf
	db_customer.name = customer.name
	db_customer.email = customer.email
	db_customer.phone_number = customer.phone_number
	db_customer.address = customer.address
	session.commit()
	session.refresh(db_customer)

	return db_customer


@router.delete('/{customer_cpf}', response_model=Message)
def delete_customer(
	session: SessionDep, current_employee: CurrentEmployee, customer_cpf: int
):
	db_customer = session.scalar(
		select(Customer).where(Customer.cpf == customer_cpf)
	)

	if not db_customer:
		raise HTTPException(404, detail='Customer not registered.')

	session.delete(db_customer)
	session.commit()

	return {'message': 'Customer deleted.'}
