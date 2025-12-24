from fastapi.testclient import TestClient


def test_get_customers(client: TestClient, employee, token):
	response = client.get('/customers', headers={'Authorization': f'Bearer {token}'})
	assert response.status_code == 200
	assert response.json() == {'customers': []}


def test_get_customer(client: TestClient, customer, employee, token):
	response = client.get(
		f'/customers/{customer.id}',
		headers={'Authorization': f'Bearer {token}'},
	)
	assert response.status_code == 200
	assert response.json() == {
		'cpf': customer.cpf,
		'name': customer.name,
		'email': customer.email,
		'phone_number': customer.phone_number,
		'address': customer.address,
	}


def test_get_customer_not_registered(client: TestClient, employee, token):
	response = client.get(
		'/customers/404', headers={'Authorization': f'Bearer {token}'}
	)
	assert response.status_code == 404
	assert response.json() == {'detail': 'Customer not registered.'}


def test_create_customer(client: TestClient, employee, token):
	response = client.post(
		'/customers',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'cpf': '00900900911',
			'name': 'Cachorro Doido',
			'email': 'calordamulinga@gmail.com',
			'phone_number': '61912345678',
			'address': 'Rua 12 Lote 12 Casa 12',
		},
	)

	assert response.status_code == 201
	assert response.json() == {
		'cpf': '00900900911',
		'name': 'Cachorro Doido',
		'email': 'calordamulinga@gmail.com',
		'phone_number': '61912345678',
		'address': 'Rua 12 Lote 12 Casa 12',
	}


def test_create_customer_already_registered(client: TestClient, employee, token):
	first_response = client.post(
		'/customers',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'cpf': '00900900911',
			'name': 'Cachorro Doido',
			'email': 'calordamulinga@gmail.com',
			'phone_number': '61912345678',
			'address': 'Rua 12 Lote 12 Casa 12',
		},
	)

	second_response = client.post(
		'/customers',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'cpf': '00900900911',
			'name': 'Cachorro Doido',
			'email': 'calordamulinga@gmail.com',
			'phone_number': '61912345678',
			'address': 'Rua 12 Lote 12 Casa 12',
		},
	)
	assert second_response.status_code == 400
	assert second_response.json() == {'detail': 'Customer already registered.'}


def test_update_customer(client: TestClient, customer, employee, token):
	response = client.put(
		f'/customers/{customer.id}',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'cpf': '00900900911',
			'name': 'Cachorro Doido',
			'email': 'calordamulinga@gmail.com',
			'phone_number': '61912345678',
			'address': 'Rua 12 Lote 12 Casa 12',
		},
	)
	assert response.status_code == 200
	assert response.json() == {
		'cpf': '00900900911',
		'name': 'Cachorro Doido',
		'email': 'calordamulinga@gmail.com',
		'phone_number': '61912345678',
		'address': 'Rua 12 Lote 12 Casa 12',
	}


def test_update_customer_not_registered(client: TestClient, employee, token):
	response = client.put(
		'/customers/404',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'cpf': '00900900911',
			'name': 'Cachorro Doido',
			'email': 'calordamulinga@gmail.com',
			'phone_number': '61912345678',
			'address': 'Rua 12 Lote 12 Casa 12',
		},
	)
	assert response.status_code == 404
	assert response.json() == {'detail': 'Customer not registered.'}


def test_delete_customer(client: TestClient, customer, employee, token):
	response = client.delete(
		f'/customers/{customer.id}',
		headers={'Authorization': f'Bearer {token}'},
	)
	assert response.status_code == 200
	assert response.json() == {'message': 'Customer deleted.'}


def test_delete_customer_not_registered(client: TestClient, employee, token):
	response = client.delete(
		'/customers/404',
		headers={'Authorization': f'Bearer {token}'},
	)
	assert response.status_code == 404
	assert response.json() == {'detail': 'Customer not registered.'}
