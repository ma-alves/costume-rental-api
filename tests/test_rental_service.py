from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Costume, CostumeAvailability, Rental, Role, User
from app.auth_schema import RentalInput
from app.services.rental_service import RentalService


@pytest.fixture
def rental_service():
	return RentalService()


@pytest.fixture
def mock_session():
	return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_costume():
	costume = Costume(
		name='Test Costume',
		description='A test costume',
		fee=100.0,
		availability=CostumeAvailability.AVAILABLE,
	)
	costume.id = 1
	return costume


@pytest.fixture
def mock_customer():
	customer = User(
		name='Test Customer',
		email='customer@test.com',
		passwordHash='hashed',
		phone='12345678901',
		cpf='12345678901',
		address='Test Address',
		role=Role.CUSTOMER,
	)
	customer.id = 2
	return customer


@pytest.fixture
def mock_admin_user():
	user = User(
		name='Admin',
		email='admin@test.com',
		passwordHash='hashed',
		phone='12345678901',
		cpf='12345678901',
		address='Test Address',
		role=Role.ADMIN,
	)
	user.id = 1
	return user


@pytest.fixture
def mock_rental(mock_costume, mock_customer, mock_admin_user):
	rental = Rental(
		user_id=mock_admin_user.id,
		costume_id=mock_costume.id,
	)
	rental.id = 1
	rental.rental_date = datetime.now()
	rental.return_date = datetime.now() + timedelta(days=7)
	rental.costumes = mock_costume
	rental.users = mock_admin_user
	return rental


@pytest.mark.asyncio
async def test_get_all_returns_rentals(rental_service, mock_session, mock_rental):
	mock_scalars = MagicMock()
	mock_scalars.all.return_value = [mock_rental]
	mock_session.scalars.return_value = mock_scalars

	result = await rental_service.get_all(mock_session)

	assert result == [mock_rental]


@pytest.mark.asyncio
async def test_get_all_returns_empty_list_when_empty(rental_service, mock_session):
	mock_scalars = MagicMock()
	mock_scalars.all.return_value = []
	mock_session.scalars.return_value = mock_scalars

	result = await rental_service.get_all(mock_session)

	assert result == []


@pytest.mark.asyncio
async def test_get_by_id_returns_rental(rental_service, mock_session, mock_rental):
	mock_session.scalar.return_value = mock_rental

	result = await rental_service.get_by_id(mock_session, 1)

	assert result == mock_rental


@pytest.mark.asyncio
async def test_get_by_id_raises_404_when_not_found(rental_service, mock_session):
	mock_session.scalar.return_value = None

	with pytest.raises(HTTPException) as exc_info:
		await rental_service.get_by_id(mock_session, 999)

	assert exc_info.value.status_code == 404
	assert exc_info.value.detail == 'Rental not registered.'


@pytest.mark.asyncio
async def test_create_rental_success(
	rental_service, mock_session, mock_costume, mock_customer, mock_admin_user
):
	rental_data = RentalInput(
		costume_id=mock_costume.id,
		customer_id=mock_customer.id,
	)

	mock_session.scalar.side_effect = [mock_costume, mock_customer]
	mock_session.add = MagicMock()
	mock_session.commit = AsyncMock()
	mock_session.refresh = AsyncMock()

	with patch.object(rental_service, '_set_rental_attr', return_value=None):
		result = await rental_service.create(mock_session, rental_data, mock_admin_user)

		assert result.costume_id == mock_costume.id
		assert result.user_id == mock_admin_user.id
		mock_session.add.assert_called_once()
		mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_rental_costume_not_registered(
	rental_service, mock_session, mock_customer, mock_admin_user
):
	rental_data = RentalInput(
		costume_id=999,
		customer_id=mock_customer.id,
	)

	mock_session.scalar.return_value = None

	with pytest.raises(HTTPException) as exc_info:
		await rental_service.create(mock_session, rental_data, mock_admin_user)

	assert exc_info.value.status_code == 400
	assert exc_info.value.detail == 'Costume not registered.'


@pytest.mark.asyncio
async def test_create_rental_costume_unavailable(
	rental_service, mock_session, mock_customer, mock_admin_user
):
	unavailable_costume = Costume(
		name='Test Costume',
		description='A test costume',
		fee=100.0,
		availability=CostumeAvailability.UNAVAILABLE,
	)
	unavailable_costume.id = 1

	rental_data = RentalInput(
		costume_id=unavailable_costume.id,
		customer_id=mock_customer.id,
	)

	mock_session.scalar.return_value = unavailable_costume

	with pytest.raises(HTTPException) as exc_info:
		await rental_service.create(mock_session, rental_data, mock_admin_user)

	assert exc_info.value.status_code == 400
	assert exc_info.value.detail == 'Costume unavailable.'


@pytest.mark.asyncio
async def test_create_rental_customer_not_registered(
	rental_service, mock_session, mock_costume, mock_admin_user
):
	rental_data = RentalInput(
		costume_id=mock_costume.id,
		customer_id=999,
	)

	mock_session.scalar.side_effect = [mock_costume, None]

	with pytest.raises(HTTPException) as exc_info:
		await rental_service.create(mock_session, rental_data, mock_admin_user)

	assert exc_info.value.status_code == 400
	assert exc_info.value.detail == 'Customer not registered.'


@pytest.mark.asyncio
async def test_delete_rental_success(
	rental_service, mock_session, mock_rental, mock_costume
):
	mock_session.scalar.side_effect = [mock_rental, mock_costume]
	mock_session.delete = AsyncMock()
	mock_session.commit = AsyncMock()

	await rental_service.delete(mock_session, 1)

	mock_session.delete.assert_called_once()
	mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_rental_not_registered(rental_service, mock_session):
	mock_session.scalar.return_value = None

	with pytest.raises(HTTPException) as exc_info:
		await rental_service.delete(mock_session, 999)

	assert exc_info.value.status_code == 404
	assert exc_info.value.detail == 'Rental not registered.'


@pytest.mark.asyncio
async def test_set_rental_attr(rental_service, mock_rental):
	result = rental_service._set_rental_attr(mock_rental)

	assert hasattr(result, 'costume')
	assert hasattr(result, 'user')
	assert result.costume == mock_rental.costumes.__dict__
