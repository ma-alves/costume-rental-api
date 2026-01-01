from http import HTTPStatus

from fastapi.testclient import TestClient


def test_root_returns_ok_and_localhost_doc(client: TestClient):
	response = client.get('/')

	assert response.status_code == HTTPStatus.OK
	assert response.json() == {
		'message': 'Go to http://127.0.0.1:8000/docs to access the endpoints.'
	}
