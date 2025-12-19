from http import HTTPStatus

from fastapi.testclient import TestClient
from app.models import Employee


def test_read_employees(client: TestClient):
	response = client.get('/employees')
	assert response.status_code == HTTPStatus.OK
	assert response.json() == {'employees': []}


def test_create_employee(client: TestClient):
	response = client.post(
		'/employees',
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


def test_create_employee_already_exists(client: TestClient):
	first_response = client.post(
		'/employees',
		json={
			'name': 'matheus',
			'email': 'matheus@email.com',
			'password': 'matheus1234',
			'phone_number': '12345678910',
			'is_admin': False,
		},
	)
	second_response = client.post(
		'/employees',
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
	assert second_response.json() == {'detail': 'Employee already registered.'}


def test_read_employee(client: TestClient, employee):
	response = client.get(f'/employees/{employee.id}')
	assert response.status_code == HTTPStatus.OK
	assert response.json() == {
		'id': employee.id,
		'name': f'{employee.name}',
		'email': f'{employee.email}',
		'phone_number': f'{employee.phone_number}',
		'is_admin': True,
	}


def test_read_employee_not_registered(client: TestClient):
	response = client.get('/employees/404')
	assert response.status_code == HTTPStatus.NOT_FOUND
	assert response.json() == {'detail': 'Employee not registered.'}


def test_update_employee(client: TestClient, employee: Employee, token: str):
	response = client.put(
		f'/employees/{employee.id}',
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
		'id': employee.id,
		'name': f'{employee.name}',
		'email': f'{employee.email}',
		'phone_number': f'{employee.phone_number}',
		'is_admin': employee.is_admin,
	}


def test_update_employee_no_permission(
	client: TestClient, other_employee: Employee, other_token: str
):
	response = client.put(
		'/employees/400',
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


def test_delete_employee(client: TestClient, employee: Employee, token: str):
	response = client.delete(
		f'/employees/{employee.id}',
		headers={'Authorization': f'Bearer {token}'},
	)
	assert response.status_code == HTTPStatus.OK
	assert response.json() == {'message': 'Employee deleted.'}


def test_delete_employee_no_permission(
	client: TestClient,
	employee: Employee,
	other_employee: Employee,
	other_token: str,
):
	response_delete = client.delete(
		f'/employees/{employee.id}',
		headers={'Authorization': f'Bearer {other_token}'},
	)
	assert response_delete.status_code == HTTPStatus.BAD_REQUEST
	assert response_delete.json() == {'detail': 'Not enough permissions'}
