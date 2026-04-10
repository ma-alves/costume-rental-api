from http import HTTPStatus

from fastapi.testclient import TestClient


def test_root_returns_ok_and_localhost_doc(client: TestClient):
	response = client.get('/api/v1/')

	assert response.status_code == HTTPStatus.OK
	assert response.json() == {'message': 'API Swagger: http://127.0.0.1:8000/docs.'}


def test_rate_limiter_middleware(client: TestClient):
	for req in range(50):  # bate na 49
		response = client.get('/api/v1/')
		if response.status_code != HTTPStatus.OK:
			break
	assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
