from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Costume, CostumeAvailability
from app.schemas import CostumeInput
from app.services.costume_service import CostumeService


@pytest.fixture
def costume_service():
	return CostumeService()


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


@pytest.mark.asyncio
async def test_get_all_returns_costumes(costume_service, mock_session, mock_costume):
	mock_scalars = MagicMock()
	mock_scalars.all.return_value = [mock_costume]
	mock_session.scalars.return_value = mock_scalars

	result = await costume_service.get_all(mock_session, None)

	assert result == [mock_costume]


@pytest.mark.asyncio
async def test_get_all_returns_empty_list_when_empty(costume_service, mock_session):
	mock_scalars = MagicMock()
	mock_scalars.all.return_value = []
	mock_session.scalars.return_value = mock_scalars

	result = await costume_service.get_all(mock_session, None)

	assert result == []


@pytest.mark.asyncio
async def test_get_all_filters_by_availability(
	costume_service, mock_session, mock_costume
):
	mock_scalars = MagicMock()
	mock_scalars.all.return_value = [mock_costume]
	mock_session.scalars.return_value = mock_scalars

	result = await costume_service.get_all(
		mock_session, CostumeAvailability.AVAILABLE, skip=0, limit=100
	)

	assert result == [mock_costume]


@pytest.mark.asyncio
async def test_get_by_id_returns_costume(costume_service, mock_session, mock_costume):
	mock_session.scalar.return_value = mock_costume

	result = await costume_service.get_by_id(mock_session, 1)

	assert result == mock_costume


@pytest.mark.asyncio
async def test_get_by_id_raises_404_when_not_found(costume_service, mock_session):
	mock_session.scalar.return_value = None

	with pytest.raises(HTTPException) as exc_info:
		await costume_service.get_by_id(mock_session, 999)

	assert exc_info.value.status_code == 404
	assert exc_info.value.detail == 'Costume not registered.'


@pytest.mark.asyncio
async def test_create_costume_success(costume_service, mock_session):
	costume_data = CostumeInput(
		name='New Costume',
		description='A new costume',
		fee=99.0,
		availability=CostumeAvailability.AVAILABLE,
	)

	mock_session.scalar.return_value = None
	mock_session.add = MagicMock()
	mock_session.commit = AsyncMock()
	mock_session.refresh = AsyncMock()

	result = await costume_service.create(mock_session, costume_data)

	assert result.name == costume_data.name
	assert result.description == costume_data.description
	mock_session.add.assert_called_once()
	mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_costume_already_exists(
	costume_service, mock_session, mock_costume
):
	costume_data = CostumeInput(
		name='Test Costume',
		description='A test costume',
		fee=100.0,
		availability=CostumeAvailability.AVAILABLE,
	)

	mock_session.scalar.return_value = mock_costume

	with pytest.raises(HTTPException) as exc_info:
		await costume_service.create(mock_session, costume_data)

	assert exc_info.value.status_code == 409
	assert exc_info.value.detail == 'Costume already registered.'


@pytest.mark.asyncio
async def test_update_costume_success(costume_service, mock_session, mock_costume):
	costume_data = CostumeInput(
		name='Updated Costume',
		description='Updated description',
		fee=150.0,
		availability=CostumeAvailability.UNAVAILABLE,
	)

	mock_session.commit = AsyncMock()
	mock_session.refresh = AsyncMock()
	mock_session.scalar.return_value = mock_costume

	result = await costume_service.update(mock_session, 1, costume_data)

	assert result.name == 'Updated Costume'
	mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_costume_success(costume_service, mock_session, mock_costume):
	mock_session.delete = AsyncMock()
	mock_session.commit = AsyncMock()
	mock_session.scalar.return_value = mock_costume

	await costume_service.delete(mock_session, 1)

	mock_session.delete.assert_called_once()
	mock_session.commit.assert_called_once()
