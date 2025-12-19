from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Employee
from app.schemas import (
	EmployeeInput,
	EmployeeList,
	EmployeeOutput,
	Message,
)
from app.security import get_password_hash, get_current_employee


router = APIRouter(prefix='/employees', tags=['employees'])

CurrentEmployee = Annotated[Employee, Depends(get_current_employee)]
SessionDep = Annotated[Session, Depends(get_session)]


@router.get('/', response_model=EmployeeList)
def read_employees(session: SessionDep, skip: int = 0, limit: int = 100):
	employees = session.scalars(
		select(Employee).offset(skip).limit(limit)
	).all()

	return {'employees': employees}


@router.get('/{employee_id}', response_model=EmployeeOutput, status_code=200)
def read_employee(session: SessionDep, employee_id: int):
	employee = session.scalar(
		select(Employee).where(Employee.id == employee_id)
	)

	if not employee:
		raise HTTPException(404, detail='Employee not registered.')

	return employee


# adicionar 'is_admin' em current_employee
@router.post('/', response_model=EmployeeOutput, status_code=201)
def create_employee(employee: EmployeeInput, session: SessionDep):
	"""
	Open endpoint so anyone can test the API's permissions.
	"""
	db_employee = session.scalar(
		select(Employee).where(Employee.email == employee.email)
	)
	if db_employee:
		raise HTTPException(400, detail='Employee already registered.')

	hashed_password = get_password_hash(employee.password)

	db_employee = Employee(
		name=employee.name,
		email=employee.email,
		password=hashed_password,
		phone_number=employee.phone_number,
		is_admin=employee.is_admin,
	)

	session.add(db_employee)
	session.commit()
	session.refresh(db_employee)

	return db_employee


@router.put('/{employee_id}', response_model=EmployeeOutput)
def update_employee(
	current_employee: CurrentEmployee,
	session: SessionDep,
	employee: EmployeeInput,
	employee_id: int,
):
	if (
		current_employee.id != employee_id
		and current_employee.is_admin is False
	):
		raise HTTPException(status_code=400, detail='Not enough permissions')

	db_employee = session.scalar(
		select(Employee).where(Employee.id == employee_id)
	)

	if not db_employee:
		raise HTTPException(404, detail='Employee not registered.')

	db_employee.name = employee.name
	db_employee.password = get_password_hash(employee.password)
	db_employee.email = employee.email
	db_employee.phone_number = employee.phone_number
	db_employee.is_admin = employee.is_admin
	session.commit()
	session.refresh(db_employee)

	return db_employee


@router.delete('/{employee_id}', response_model=Message)
def delete_employee(
	current_employee: CurrentEmployee,
	session: SessionDep,
	employee_id: int,
):
	if (
		current_employee.id != employee_id
		and current_employee.is_admin is False
	):
		raise HTTPException(status_code=400, detail='Not enough permissions')

	db_employee = session.scalar(
		select(Employee).where(Employee.id == employee_id)
	)

	if not db_employee:
		raise HTTPException(404, detail='Employee not registered.')

	session.delete(db_employee)
	session.commit()

	return {'message': 'Employee deleted.'}
