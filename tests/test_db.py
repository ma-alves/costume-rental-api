import pytest
from factories import CostumeFactory, RentalFactory, UserFactory
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
		or costume.availability == CostumeAvailability.UNRETURNED
	)


@pytest.mark.asyncio
async def test_create_user(test_session: AsyncSession):
	new_user = UserFactory()

	test_session.add(new_user)
	await test_session.commit()

	user = await test_session.scalar(select(User).where(User.id == new_user.id))

	assert user.name == new_user.name
	assert user.email == new_user.email
	assert user.passwordHash == new_user.passwordHash
	assert user.phone == new_user.phone


@pytest.mark.asyncio
async def test_create_customer(test_session: AsyncSession):
	new_customer = UserFactory(role=Role.CUSTOMER)

	test_session.add(new_customer)
	await test_session.commit()

	customer = await test_session.scalar(select(User).where(User.id == new_customer.id))

	assert customer.cpf == new_customer.cpf
	assert customer.name == new_customer.name
	assert customer.email == new_customer.email
	assert customer.phone == new_customer.phone
	assert customer.address == new_customer.address
	assert customer.role == Role.CUSTOMER


@pytest.mark.asyncio
async def test_create_rental(test_session: AsyncSession):
	new_rental = RentalFactory()
	test_session.add(new_rental)
	await test_session.commit()

	rental = await test_session.scalar(select(Rental).where(Rental.id == new_rental.id))

	assert rental.rental_date == new_rental.rental_date
	assert rental.return_date == new_rental.return_date
	assert rental.costume_id == new_rental.costume_id
	assert rental.user_id == new_rental.user_id
