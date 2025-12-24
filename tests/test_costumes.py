from http import HTTPStatus
from fastapi.testclient import TestClient


def test_get_costumes(client: TestClient):
	response = client.get('/costumes')
	assert response.status_code == 200
	assert response.json() == {'costumes': []}


def test_get_costume(client: TestClient, costume):
	response = client.get(f'/costumes/{costume.id}')
	assert response.status_code == 200
	assert response.json() == {
		'id': costume.id,
		'name': f'{costume.name}',
		'description': f'{costume.description}',
		'fee': costume.fee,
		'availability': costume.availability,
	}


def test_get_costume_not_registered(client: TestClient):
	response = client.get(f'/costumes/404')
	assert response.status_code == 404
	assert response.json() == {'detail': 'Costume not registered.'}


def test_create_costume(client: TestClient, user, token):
	response = client.post(
		'/costumes',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'name': 'Dinossauro',
			'description': 'Um Tiranossauro Rex cabuloso!',
			'fee': 59.90,
			'availability': 'available',
		},
	)
	assert response.status_code == 201
	assert response.json() == {
		'id': 1,
		'name': 'Dinossauro',
		'description': 'Um Tiranossauro Rex cabuloso!',
		'fee': 59.90,
		'availability': 'available',
	}


def test_create_costume_already_exists(client: TestClient, user, token):
	first_response = client.post(
		'/costumes',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'name': 'Dinossauro',
			'description': 'Um Tiranossauro Rex cabuloso!',
			'fee': 59.90,
			'availability': 'available',
		},
	)
	second_response = client.post(
		'/costumes',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'name': 'Dinossauro',
			'description': 'Um Tiranossauro Rex cabuloso!',
			'fee': 59.90,
			'availability': 'available',
		},
	)
	assert first_response.status_code == 201
	assert second_response.status_code == HTTPStatus.CONFLICT
	assert second_response.json() == {'detail': 'Costume already registered.'}


def test_update_costume(client: TestClient, costume, user, token):
	response = client.put(
		f'/costumes/{costume.id}',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'name': 'Updated name',
			'description': 'Updated description',
			'fee': 76.90,
			'availability': 'unavailable',
		},
	)
	assert response.status_code == 200
	assert response.json() == {
		'id': costume.id,
		'name': 'Updated name',
		'description': 'Updated description',
		'fee': 76.90,
		'availability': 'unavailable',
	}


def test_update_costume_not_registered(client: TestClient, user, token):
	response = client.put(
		f'/costumes/404',
		headers={'Authorization': f'Bearer {token}'},
		json={
			'name': 'Updated name',
			'description': 'Updated description',
			'fee': 76.90,
			'availability': 'unavailable',
		},
	)
	assert response.status_code == 404
	assert response.json() == {'detail': 'Costume not registered.'}


def test_delete_costume(client: TestClient, costume, user, token):
	response = client.delete(
		f'/costumes/{costume.id}',
		headers={'Authorization': f'Bearer {token}'},
	)
	assert response.status_code == 200
	assert response.json() == {'message': 'Costume deleted.'}


def test_delete_costume_not_registered(client: TestClient, user, token):
	response = client.delete(
		f'/costumes/404',
		headers={'Authorization': f'Bearer {token}'},
	)
	assert response.status_code == 404
	assert response.json() == {'detail': 'Costume not registered.'}
