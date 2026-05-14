import pytest
from factories import create_costume, create_rental, create_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
	Costume,
	CostumeAvailability,
	Rental,
	Role,
	User,
)


@pytest.mark.asyncio
async def test_create_costume(test_session: AsyncSession):
	new_costume = await create_costume(test_session)

	costume = await test_session.scalar(
		select(Costume).where(Costume.id == new_costume.id)
	)

	assert costume.name == new_costume.name
	assert costume.description == new_costume.description
	assert costume.fee == new_costume.fee
	assert (
		costume.availability == CostumeAvailability.AVAILABLE
		or costume.availability == CostumeAvailability.UNAVAILABLE
		or costume.availability == CostumeAvailability.UNRETURNED
	)


@pytest.mark.asyncio
async def test_create_user(test_session: AsyncSession):
	new_user = await create_user(test_session, role=Role.ADMIN)

	user = await test_session.scalar(select(User).where(User.id == new_user.id))

	assert user.name == new_user.name
	assert user.email == new_user.email
	assert user.passwordHash == new_user.passwordHash
	assert user.phone == new_user.phone


@pytest.mark.asyncio
async def test_create_customer(test_session: AsyncSession):
	new_customer = await create_user(test_session, role=Role.CUSTOMER)

	customer = await test_session.scalar(select(User).where(User.id == new_customer.id))

	assert customer.cpf == new_customer.cpf
	assert customer.name == new_customer.name
	assert customer.email == new_customer.email
	assert customer.phone == new_customer.phone
	assert customer.address == new_customer.address
	assert customer.role == Role.CUSTOMER


@pytest.mark.asyncio
async def test_create_rental(test_session: AsyncSession):
	costume = await create_costume(test_session)
	customer = await create_user(test_session, role=Role.CUSTOMER)
	new_rental = await create_rental(
		test_session, user_id=customer.id, costume_id=costume.id
	)

	rental = await test_session.scalar(select(Rental).where(Rental.id == new_rental.id))

	assert rental.rental_date == new_rental.rental_date
	assert rental.return_date == new_rental.return_date
	assert rental.costume_id == new_rental.costume_id
	assert rental.user_id == new_rental.user_id
