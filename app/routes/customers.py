from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Customer, Employee
from app.schemas import CustomerSchema, CustomerList, Message
from app.security import get_current_employee


router = APIRouter(prefix='/customers', tags=['customers'])

CurrentEmployee = Annotated[Employee, Depends(get_current_employee)]
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get('/', response_model=CustomerList)
async def get_customers(
	session: Session,
	current_employee: CurrentEmployee,
	skip: int = 0,
	limit: int = 0,
):
	customers_scalar = await session.scalars(
		select(Customer).offset(skip).limit(limit)
	)
	customers = customers_scalar.all()

	return {'customers': customers}


@router.get('/{customer_cpf}', response_model=CustomerSchema)
async def get_customer(
	session: Session, current_employee: CurrentEmployee, customer_cpf: str
):
	db_customer = await session.scalar(
		select(Customer).where(Customer.cpf == customer_cpf)
	)

	if not db_customer:
		raise HTTPException(404, detail='Customer not registered.')

	return db_customer


@router.post('/', response_model=CustomerSchema, status_code=201)
async def create_customer(
	session: Session,
	current_employee: CurrentEmployee,
	customer: CustomerSchema,
):
	db_customer = await session.scalar(
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
	await session.commit()
	await session.refresh(db_customer)

	return db_customer


@router.put('/{customer_cpf}', response_model=CustomerSchema)
async def update_customer(
	session: Session,
	current_employee: CurrentEmployee,
	customer: CustomerSchema,
	customer_cpf: int,
):
	db_customer = await session.scalar(
		select(Customer).where(Customer.cpf == customer_cpf)
	)

	if not db_customer:
		raise HTTPException(404, detail='Customer not registered.')

	db_customer.cpf = customer.cpf
	db_customer.name = customer.name
	db_customer.email = customer.email
	db_customer.phone_number = customer.phone_number
	db_customer.address = customer.address

	await session.commit()
	await session.refresh(db_customer)

	return db_customer


@router.delete('/{customer_cpf}', response_model=Message)
async def delete_customer(
	session: Session, current_employee: CurrentEmployee, customer_cpf: int
):
	db_customer = await session.scalar(
		select(Customer).where(Customer.cpf == customer_cpf)
	)

	if not db_customer:
		raise HTTPException(404, detail='Customer not registered.')

	await session.delete(db_customer)
	await session.commit()

	return {'message': 'Customer deleted.'}
