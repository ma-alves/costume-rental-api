from http import HTTPStatus

from fastapi.testclient import TestClient

from app.models import User


def test_read_users(client: TestClient, user: User, token: str):
	response = client.get('/api/v1/users', headers={'Authorization': f'Bearer {token}'})
	assert response.status_code == HTTPStatus.OK
	response_json = response.json()
	assert 'users' in response_json
	assert len(response_json['users']) >= 1


def test_create_user(client: TestClient):
	response = client.post(
		'/api/v1/users',
		json={
			'name': 'matheus',
			'email': 'matheus@email.com',
			'password': 'matheus1234',
			'phone': '12345678910',
			'cpf': '12345678910',
			'address': 'Test Address',
			'role': 'customer',
		},
	)
	assert response.status_code == HTTPStatus.CREATED
	assert response.json() == {
		'id': 1,
		'name': 'matheus',
		'email': 'matheus@email.com',
		'phone': '12345678910',
		'role': 'customer',
	}


def test_create_user_already_exists(client: TestClient):
	first_response = client.post(
		'/api/v1/users',
		json={
			'name': 'matheus',
			'email': 'matheus@email.com',
			'password': 'matheus1234',
			'phone': '12345678910',
			'cpf': '12345678910',
			'address': 'Test Address',
			'role': 'customer',
		},
	)
	second_response = client.post(
		'/api/v1/users',
		json={
			'name': 'matheus',
			'email': 'matheus@email.com',
			'password': 'matheus1234',
			'phone': '12345678910',
			'cpf': '12345678910',
			'address': 'Test Address',
			'role': 'customer',
		},
	)
	assert first_response.status_code == HTTPStatus.CREATED
	assert second_response.status_code == HTTPStatus.BAD_REQUEST
	assert second_response.json() == {'detail': 'User already registered.'}


def test_read_user(client: TestClient, user: User, token: str):
	response = client.get(
		f'/api/v1/users/{user.id}', headers={'Authorization': f'Bearer {token}'}
	)
	assert response.status_code == HTTPStatus.OK
	response_json = response.json()
	assert response_json['id'] == user.id
	assert response_json['name'] == user.name
	assert response_json['email'] == user.email
	assert response_json['phone'] == user.phone
	if hasattr(user.role, 'value'):
		assert response_json['role'] == user.role.value
	else:
		assert response_json['role'] == user.role


def test_read_user_not_registered(client: TestClient, token: str):
	response = client.get(
		'/api/v1/users/404', headers={'Authorization': f'Bearer {token}'}
	)
	assert response.status_code == HTTPStatus.NOT_FOUND
	assert response.json() == {'detail': 'User not registered.'}


def test_update_user(client: TestClient, user: User, token: str):
	response = client.put(
		f'/api/v1/users/{user.id}',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'name': 'yasmim',
			'email': 'yasmim@email.com',
			'password': 'novasenha1234',
			'phone': '99999999999',
			'cpf': '12345678901',
			'address': 'New Address',
			'role': 'admin',
		},
	)
	assert response.status_code == HTTPStatus.OK
	assert response.json() == {
		'id': user.id,
		'name': 'yasmim',
		'email': 'yasmim@email.com',
		'phone': '99999999999',
		'role': 'admin',
	}


def test_update_user_no_permission(
	client: TestClient, other_user: User, other_token: str
):
	response = client.put(
		f'/api/v1/users/{other_user.id + 100}',
		headers={'Authorization': f'Bearer {other_token}'},
		json={
			'name': 'yasmim',
			'email': 'yasmim@email.com',
			'password': 'novasenha1234',
			'phone': '99999999999',
			'cpf': '12345678901',
			'address': 'New Address',
			'role': 'admin',
		},
	)
	assert response.status_code == HTTPStatus.FORBIDDEN
	assert response.json() == {'detail': 'Not enough permissions'}


def test_delete_user(client: TestClient, user: User, token: str):
	response = client.delete(
		f'/api/v1/users/{user.id}',
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
		f'/api/v1/users/{user.id}',
		headers={'Authorization': f'Bearer {other_token}'},
	)
	assert response_delete.status_code == HTTPStatus.FORBIDDEN
	assert response_delete.json() == {'detail': 'Not enough permissions'}
