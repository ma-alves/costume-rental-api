import pytest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
	Costume,
	CostumeAvailability,
	Customer,
	Employee,
)
from factories import CostumeFactory, CustomerFactory, EmployeeFactory


@pytest.mark.asyncio
async def test_create_costume(test_session: AsyncSession):
	new_costume = CostumeFactory()

	test_session.add(new_costume)
	await test_session.commit()

	costume = await test_session.scalar(
		select(Costume).where(Costume.id == new_costume.id)
	)

	assert costume.name == costume.name
	assert costume.description == costume.description
	assert costume.fee == costume.fee
	assert (
		costume.availability == CostumeAvailability.AVAILABLE
		or costume.availability == CostumeAvailability.UNAVAILABLE
	)


@pytest.mark.asyncio
async def test_create_employee(test_session: AsyncSession):
	new_employee = EmployeeFactory()

	test_session.add(new_employee)
	await test_session.commit()

	employee = await test_session.scalar(
		select(Employee).where(Employee.id == new_employee.id)
	)

	assert employee.name == new_employee.name
	assert employee.email == new_employee.email
	assert employee.password == new_employee.password
	assert employee.phone_number == new_employee.phone_number


@pytest.mark.asyncio
async def test_create_customer(test_session: AsyncSession):
	new_customer = CustomerFactory()

	test_session.add(new_customer)
	await test_session.commit()

	customer = await test_session.scalar(
		select(Customer).where(Customer.id == new_customer.id)
	)

	assert customer.cpf == new_customer.cpf
	assert customer.name == new_customer.name
	assert customer.email == new_customer.email
	assert customer.phone_number == new_customer.phone_number
	assert customer.address == new_customer.address
