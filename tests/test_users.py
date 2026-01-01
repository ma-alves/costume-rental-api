from http import HTTPStatus

from fastapi.testclient import TestClient

from app.models import User


def test_read_users(client: TestClient):
	response = client.get('/users')
	assert response.status_code == HTTPStatus.OK
	assert response.json() == {'users': []}


def test_create_user(client: TestClient):
	response = client.post(
		'/users',
		json={
			'name': 'matheus',
			'email': 'matheus@email.com',
			'password': 'matheus1234',
			'phone_number': '12345678910',
			'is_admin': False,
		},
	)
	assert response.status_code == HTTPStatus.CREATED
	assert response.json() == {
		'id': 1,
		'name': 'matheus',
		'email': 'matheus@email.com',
		'phone_number': '12345678910',
		'is_admin': False,
	}


def test_create_user_already_exists(client: TestClient):
	first_response = client.post(
		'/users',
		json={
			'name': 'matheus',
			'email': 'matheus@email.com',
			'password': 'matheus1234',
			'phone_number': '12345678910',
			'is_admin': False,
		},
	)
	second_response = client.post(
		'/users',
		json={
			'name': 'matheus',
			'email': 'matheus@email.com',
			'password': 'matheus1234',
			'phone_number': '12345678910',
			'is_admin': False,
		},
	)
	assert first_response.status_code == HTTPStatus.CREATED
	assert second_response.status_code == HTTPStatus.BAD_REQUEST
	assert second_response.json() == {'detail': 'User already registered.'}


def test_read_user(client: TestClient, user):
	response = client.get(f'/users/{user.id}')
	assert response.status_code == HTTPStatus.OK
	assert response.json() == {
		'id': user.id,
		'name': f'{user.name}',
		'email': f'{user.email}',
		'phone_number': f'{user.phone_number}',
		'is_admin': True,
	}


def test_read_user_not_registered(client: TestClient):
	response = client.get('/users/404')
	assert response.status_code == HTTPStatus.NOT_FOUND
	assert response.json() == {'detail': 'User not registered.'}


def test_update_user(client: TestClient, user: User, token: str):
	response = client.put(
		f'/users/{user.id}',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'name': 'yasmim',
			'email': 'yasmim@email.com',
			'password': 'novasenha1234',
			'phone_number': '12345678910',
			'is_admin': True,
		},
	)
	assert response.status_code == HTTPStatus.OK
	assert response.json() == {
		'id': user.id,
		'name': f'{user.name}',
		'email': f'{user.email}',
		'phone_number': f'{user.phone_number}',
		'is_admin': user.is_admin,
	}


def test_update_user_no_permission(
	client: TestClient, other_user: User, other_token: str
):
	response = client.put(
		'/users/400',
		headers={'Authorization': f'Bearer {other_token}'},
		json={
			'name': 'yasmim',
			'email': 'yasmim@email.com',
			'password': 'novasenha1234',
			'phone_number': '12345678910',
			'is_admin': True,
		},
	)
	assert response.status_code == HTTPStatus.BAD_REQUEST
	assert response.json() == {'detail': 'Not enough permissions'}


def test_delete_user(client: TestClient, user: User, token: str):
	response = client.delete(
		f'/users/{user.id}',
		headers={'Authorization': f'Bearer {token}'},
	)
	assert response.status_code == HTTPStatus.OK
	assert response.json() == {'message': 'User deleted.'}


def test_delete_user_no_permission(
	client: TestClient,
	user: User,
	other_user: User,
	other_token: str,
):
	response_delete = client.delete(
		f'/users/{user.id}',
		headers={'Authorization': f'Bearer {other_token}'},
	)
	assert response_delete.status_code == HTTPStatus.BAD_REQUEST
	assert response_delete.json() == {'detail': 'Not enough permissions'}
