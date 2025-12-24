from freezegun import freeze_time


def test_get_token(client, user):
	response = client.post(
		'/auth/token',
		data={'username': user.email, 'password': user.clean_password},
	)
	token = response.json()

	assert response.status_code == 200
	assert 'access_token' in token
	assert 'token_type' in token


def test_token_expired_after_time(client, user):
	with freeze_time('2023-07-14 12:00:00'):
		response = client.post(
			'/auth/token',
			data={
				'username': user.email,
				'password': user.clean_password,
			},
		)
		assert response.status_code == 200
		token = response.json()['access_token']

	with freeze_time('2023-07-22 12:00:00'):
		response = client.put(
			f'/users/{user.id}',
			headers={'Authorization': f'Bearer {token}'},
			json={
				'name': 'yasmim',
				'email': 'yasmim@email.com',
				'password': 'novasenha1234',
				'phone_number': '12345678910',
			},
		)
		assert response.status_code == 401
		assert response.json() == {'detail': 'Could not validate credentials'}


def test_token_inexistent_user(client):
	response = client.post(
		'/auth/token',
		data={'username': 'no_user@no_domain.com', 'password': 'testtest'},
	)
	assert response.status_code == 404
	assert response.json() == {'detail': 'User not registered.'}


def test_token_incorrect_password(client, user):
	response = client.post(
		'/auth/token',
		data={'username': user.email, 'password': 'wrong_password'},
	)
	assert response.status_code == 400
	assert response.json() == {'detail': 'Incorrect email or password.'}


def test_refresh_token(client, token, user):
	response = client.post(
		'/auth/refresh_token', headers={'Authorization': f'Bearer {token}'}
	)

	data = response.json()

	assert response.status_code == 200
	assert 'access_token' in data
	assert 'token_type' in data
	assert data['token_type'] == 'bearer'


def test_token_expired_dont_refresh(client, user):
	with freeze_time('2023-07-14 12:00:00'):
		response = client.post(
			'/auth/token',
			data={
				'username': user.email,
				'password': user.clean_password,
			},
		)
		assert response.status_code == 200
		token = response.json()['access_token']

	with freeze_time('2023-07-22 12:00:00'):
		response = client.post(
			'/auth/refresh_token',
			headers={'Authorization': f'Bearer {token}'},
		)
		assert response.status_code == 401
		assert response.json() == {'detail': 'Could not validate credentials'}
