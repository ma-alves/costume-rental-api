from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Role, User
from app.auth_schema import UserInput
from app.services.user_service import UserService


@pytest.fixture
def user_service():
	return UserService()


@pytest.fixture
def mock_session():
	return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user():
	user = User(
		name='testuser',
		email='test@example.com',
		passwordHash='hashedpassword',
		phone='12345678901',
		cpf='12345678901',
		address='Test Address',
		role=Role.CUSTOMER,
	)
	user.id = 1
	return user


@pytest.fixture
def mock_admin_user():
	user = User(
		name='admin',
		email='admin@example.com',
		passwordHash='hashedpassword',
		phone='12345678901',
		cpf='12345678901',
		address='Test Address',
		role=Role.ADMIN,
	)
	user.id = 1
	return user


@pytest.mark.asyncio
async def test_get_all_returns_users(user_service, mock_session, mock_user):
	mock_scalars = MagicMock()
	mock_scalars.all.return_value = [mock_user]
	mock_session.scalars.return_value = mock_scalars

	result = await user_service.get_all(mock_session)

	assert result == [mock_user]


@pytest.mark.asyncio
async def test_get_all_returns_none_when_empty(user_service, mock_session):
	mock_scalars = MagicMock()
	mock_scalars.all.return_value = []
	mock_session.scalars.return_value = mock_scalars

	result = await user_service.get_all(mock_session)

	assert result is None


@pytest.mark.asyncio
async def test_get_by_id_returns_user(user_service, mock_session, mock_user):
	mock_session.scalar.return_value = mock_user

	result = await user_service.get_by_id(mock_session, 1)

	assert result == mock_user


@pytest.mark.asyncio
async def test_get_by_id_raises_404_when_not_found(user_service, mock_session):
	mock_session.scalar.return_value = None

	with pytest.raises(HTTPException) as exc_info:
		await user_service.get_by_id(mock_session, 999)

	assert exc_info.value.status_code == 404
	assert exc_info.value.detail == 'User not registered.'


@pytest.mark.asyncio
async def test_get_by_email_returns_user(user_service, mock_session, mock_user):
	mock_session.scalar.return_value = mock_user

	result = await user_service.get_by_email(mock_session, 'test@example.com')

	assert result == mock_user


@pytest.mark.asyncio
async def test_get_by_email_returns_none(user_service, mock_session):
	mock_session.scalar.return_value = None

	result = await user_service.get_by_email(mock_session, 'notfound@example.com')

	assert result is None


@pytest.mark.asyncio
async def test_create_user_success(user_service, mock_session):
	user_data = UserInput(
		name='newuser',
		email='new@example.com',
		password='password123',
		phone='12345678901',
		cpf='12345678901',
		address='Test Address',
		role=Role.CUSTOMER,
	)

	mock_session.scalar.return_value = None
	mock_session.add = MagicMock()
	mock_session.commit = AsyncMock()
	mock_session.refresh = AsyncMock()

	with (
		patch.object(user_service, 'get_by_email', return_value=None),
		patch(
			'app.services.user_service.get_password_hash', return_value='hashedpassword'
		),
	):
		result = await user_service.create(mock_session, user_data)

		assert result.name == user_data.name
		assert result.email == user_data.email
		mock_session.add.assert_called_once()
		mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_already_exists(user_service, mock_session, mock_user):
	user_data = UserInput(
		name='existinguser',
		email='test@example.com',
		password='password123',
		phone='12345678901',
		cpf='12345678901',
		address='Test Address',
		role=Role.CUSTOMER,
	)

	with patch.object(user_service, 'get_by_email', return_value=mock_user):
		with pytest.raises(HTTPException) as exc_info:
			await user_service.create(mock_session, user_data)

		assert exc_info.value.status_code == 400
		assert exc_info.value.detail == 'User already registered.'


@pytest.mark.asyncio
async def test_update_user_success(user_service, mock_session, mock_admin_user):
	user_data = UserInput(
		name='updated',
		email='updated@example.com',
		password='newpassword',
		phone='99999999999',
		cpf='12345678901',
		address='New Address',
		role=Role.CUSTOMER,
	)

	mock_session.commit = AsyncMock()
	mock_session.refresh = AsyncMock()

	with (
		patch.object(user_service, 'get_by_id', return_value=mock_admin_user),
		patch('app.services.user_service.get_password_hash', return_value='newhashed'),
	):
		result = await user_service.update(mock_session, 1, user_data, mock_admin_user)

		assert result.name == 'updated'
		mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_permission_denied_non_admin(
	user_service, mock_session, mock_user
):
	other_user = User(
		name='other',
		email='other@example.com',
		passwordHash='hashed',
		phone='12345678901',
		cpf='12345678901',
		address='Address',
		role=Role.CUSTOMER,
	)
	other_user.id = 2

	user_data = UserInput(
		name='updated',
		email='updated@example.com',
		password='newpassword',
		phone='99999999999',
		cpf='12345678901',
		address='New Address',
		role=Role.CUSTOMER,
	)

	with pytest.raises(HTTPException) as exc_info:
		await user_service.update(mock_session, 2, user_data, mock_user)

	assert exc_info.value.status_code == 403
	assert exc_info.value.detail == 'Not enough permissions'


@pytest.mark.asyncio
async def test_delete_user_success(user_service, mock_session, mock_admin_user):
	mock_session.delete = AsyncMock()
	mock_session.commit = AsyncMock()

	with patch.object(user_service, 'get_by_id', return_value=mock_admin_user):
		await user_service.delete(mock_session, 1, mock_admin_user)

		mock_session.delete.assert_called_once()
		mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_user_permission_denied(user_service, mock_session, mock_user):
	other_user = User(
		name='other',
		email='other@example.com',
		passwordHash='hashed',
		phone='12345678901',
		cpf='12345678901',
		address='Address',
		role=Role.CUSTOMER,
	)
	other_user.id = 2

	with pytest.raises(HTTPException) as exc_info:
		await user_service.delete(mock_session, 2, mock_user)

	assert exc_info.value.status_code == 403
	assert exc_info.value.detail == 'Not enough permissions'
