from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
	Costume,
	CostumeAvailability,
	Payment,
	PaymentStatus,
	Rental,
	Role,
	StripeCustomer,
	User,
)
from app.security import get_password_hash


@pytest.fixture
async def customer_user(test_session: AsyncSession):
	"""Create a test customer user."""
	customer = User(
		name='Test Customer',
		email='customer@example.com',
		passwordHash=get_password_hash('test1234'),
		phone='12345678901',
		cpf='12345678901',
		address='Test Address',
		role=Role.CUSTOMER,
	)
	test_session.add(customer)
	await test_session.commit()
	await test_session.refresh(customer)
	customer.clean_password = 'test1234'
	return customer


@pytest.fixture
async def test_costume(test_session: AsyncSession):
	"""Create a test costume."""
	costume = Costume(
		name='Test Costume',
		description='A test costume',
		fee=100.0,
		availability=CostumeAvailability.AVAILABLE,
	)
	test_session.add(costume)
	await test_session.commit()
	await test_session.refresh(costume)
	return costume


@pytest.fixture
async def test_rental(test_session: AsyncSession, customer_user, test_costume):
	"""Create a test rental."""
	rental = Rental(
		user_id=customer_user.id,
		costume_id=test_costume.id,
		rental_date=datetime.now(),
		return_date=datetime.now() + timedelta(days=7),
	)
	test_session.add(rental)
	await test_session.commit()
	await test_session.refresh(rental)
	return rental


@pytest.fixture
def customer_token(client: TestClient, customer_user):
	"""Get customer authentication token."""
	response = client.post(
		'/api/v1/auth/token',
		data={'username': customer_user.email, 'password': customer_user.clean_password},
	)
	return response.json()['access_token']


class TestPaymentRouteCreatePaymentIntent:
	"""Tests for create payment intent endpoint."""

	@patch('stripe.Customer.create')
	@patch('stripe.PaymentIntent.create')
	async def test_create_payment_intent_success(
		self,
		mock_create_intent,
		mock_create_customer,
		client: TestClient,
		test_session: AsyncSession,
		customer_token,
		test_rental,
	):
		"""Test successful payment intent creation."""
		mock_create_customer.return_value = MagicMock(id='cus_123456789')
		mock_intent = MagicMock(
			id='pi_123456789',
			client_secret='pi_123456789_secret',
		)
		mock_create_intent.return_value = mock_intent

		response = client.post(
			'/api/v1/payments/create-payment-intent',
			json={'rental_id': test_rental.id, 'save_card': True},
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 200
		data = response.json()
		assert data['payment_intent_id'] == 'pi_123456789'
		assert data['client_secret'] == 'pi_123456789_secret'
		assert data['amount'] == 10000  # 100.0 * 100 (cents)
		assert data['currency'] == 'brl'

	@patch('stripe.Customer.create')
	@patch('stripe.PaymentIntent.create')
	async def test_create_payment_intent_rental_not_found(
		self,
		mock_create_intent,
		mock_create_customer,
		client: TestClient,
		customer_token,
	):
		"""Test payment intent creation with non-existent rental."""
		response = client.post(
			'/api/v1/payments/create-payment-intent',
			json={'rental_id': 9999, 'save_card': True},
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 404
		assert 'not found' in response.json()['detail'].lower()

	@patch('stripe.Customer.create')
	@patch('stripe.PaymentIntent.create')
	async def test_create_payment_intent_not_owner(
		self,
		mock_create_intent,
		mock_create_customer,
		client: TestClient,
		test_session: AsyncSession,
		customer_token,
		test_rental,
	):
		"""Test payment intent creation when user is not rental owner."""
		# Create another user
		other_user = User(
			name='Other User',
			email='other@example.com',
			passwordHash=get_password_hash('test1234'),
			phone='12345678901',
			cpf='11111111111',
			address='Other Address',
			role=Role.CUSTOMER,
		)
		test_session.add(other_user)
		await test_session.commit()

		# Create token for other user
		response = client.post(
			'/api/v1/auth/token',
			data={'username': 'other@example.com', 'password': 'test1234'},
		)
		other_token = response.json()['access_token']

		# Try to create payment for rental owned by different user
		response = client.post(
			'/api/v1/payments/create-payment-intent',
			json={'rental_id': test_rental.id, 'save_card': True},
			headers={'Authorization': f'Bearer {other_token}'},
		)

		assert response.status_code == 403


class TestPaymentRouteRetrievePayment:
	"""Tests for retrieve payment endpoint."""

	@patch('stripe.PaymentIntent.retrieve')
	async def test_retrieve_payment_intent_success(
		self,
		mock_retrieve,
		client: TestClient,
		test_session: AsyncSession,
		customer_user,
		customer_token,
		test_rental,
	):
		"""Test successful payment intent retrieval."""
		# Create a payment record
		payment = Payment(
			rental_id=test_rental.id,
			stripe_payment_intent_id='pi_123456789',
			amount=10000,
			status=PaymentStatus.PENDING,
			currency='brl',
		)
		test_session.add(payment)
		await test_session.commit()

		mock_retrieve.return_value = MagicMock(
			id='pi_123456789',
			status='requires_payment_method',
			amount=10000,
			currency='brl',
			client_secret='pi_123456789_secret',
			charges=MagicMock(data=[]),
		)

		response = client.get(
			'/api/v1/payments/payment-intent/pi_123456789',
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 200
		data = response.json()
		assert data['id'] == 'pi_123456789'
		assert data['amount'] == 10000


class TestPaymentRouteCapture:
	"""Tests for capture payment endpoint."""

	@patch('stripe.PaymentIntent.modify')
	async def test_capture_payment_success(
		self,
		mock_modify,
		client: TestClient,
		test_session: AsyncSession,
		customer_user,
		customer_token,
		test_rental,
	):
		"""Test successful payment capture."""
		# Create a payment record
		payment = Payment(
			rental_id=test_rental.id,
			stripe_payment_intent_id='pi_123456789',
			amount=10000,
			status=PaymentStatus.PENDING,
			currency='brl',
		)
		test_session.add(payment)
		await test_session.commit()

		mock_modify.return_value = MagicMock(
			id='pi_123456789',
			status='succeeded',
		)

		response = client.post(
			'/api/v1/payments/capture',
			json={'payment_intent_id': 'pi_123456789'},
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 200
		data = response.json()
		assert data['payment_intent_id'] == 'pi_123456789'
		assert data['status'] == 'succeeded'


class TestPaymentRouteRefund:
	"""Tests for refund endpoint."""

	@patch('stripe.Refund.create')
	async def test_refund_full_success(
		self,
		mock_refund_create,
		client: TestClient,
		test_session: AsyncSession,
		customer_user,
		customer_token,
		test_rental,
	):
		"""Test successful full refund."""
		# Create a payment record
		payment = Payment(
			rental_id=test_rental.id,
			stripe_payment_intent_id='pi_123456789',
			amount=10000,
			status=PaymentStatus.CAPTURED,
			currency='brl',
		)
		test_session.add(payment)
		await test_session.commit()

		mock_refund_create.return_value = MagicMock(
			id='re_123456789',
			status='succeeded',
			amount=10000,
		)

		response = client.post(
			'/api/v1/payments/refund',
			json={'payment_intent_id': 'pi_123456789'},
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 200
		data = response.json()
		assert data['refund_id'] == 're_123456789'
		assert data['amount'] == 10000

	@patch('stripe.Refund.create')
	async def test_refund_partial_success(
		self,
		mock_refund_create,
		client: TestClient,
		test_session: AsyncSession,
		customer_user,
		customer_token,
		test_rental,
	):
		"""Test successful partial refund."""
		# Create a payment record
		payment = Payment(
			rental_id=test_rental.id,
			stripe_payment_intent_id='pi_123456789',
			amount=10000,
			status=PaymentStatus.CAPTURED,
			currency='brl',
		)
		test_session.add(payment)
		await test_session.commit()

		mock_refund_create.return_value = MagicMock(
			id='re_123456789',
			status='succeeded',
			amount=5000,
		)

		response = client.post(
			'/api/v1/payments/refund',
			json={'payment_intent_id': 'pi_123456789', 'amount': 5000},
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 200
		data = response.json()
		assert data['amount'] == 5000

	async def test_refund_amount_exceeds_payment(
		self,
		client: TestClient,
		test_session: AsyncSession,
		customer_user,
		customer_token,
		test_rental,
	):
		"""Test refund with amount exceeding payment."""
		# Create a payment record
		payment = Payment(
			rental_id=test_rental.id,
			stripe_payment_intent_id='pi_123456789',
			amount=10000,
			status=PaymentStatus.CAPTURED,
			currency='brl',
		)
		test_session.add(payment)
		await test_session.commit()

		response = client.post(
			'/api/v1/payments/refund',
			json={'payment_intent_id': 'pi_123456789', 'amount': 15000},
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 400
		assert 'cannot exceed' in response.json()['detail'].lower()


class TestPaymentRouteCustomer:
	"""Tests for customer management endpoints."""

	@patch('stripe.Customer.create')
	async def test_create_customer_success(
		self,
		mock_create,
		client: TestClient,
		customer_user,
		customer_token,
		test_session: AsyncSession,
	):
		"""Test successful customer creation."""
		mock_create.return_value = MagicMock(id='cus_123456789')

		response = client.post(
			'/api/v1/payments/create-customer',
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 200
		data = response.json()
		assert data['stripe_customer_id'] == 'cus_123456789'
		assert data['user_id'] == customer_user.id

	async def test_create_customer_already_exists(
		self,
		client: TestClient,
		customer_user,
		customer_token,
		test_session: AsyncSession,
	):
		"""Test customer creation when customer already exists."""
		# Create stripe customer first
		stripe_customer = StripeCustomer(
			user_id=customer_user.id,
			stripe_customer_id='cus_existing',
		)
		test_session.add(stripe_customer)
		await test_session.commit()

		response = client.post(
			'/api/v1/payments/create-customer',
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 200
		data = response.json()
		assert data['stripe_customer_id'] == 'cus_existing'


class TestPaymentRouteSavedCards:
	"""Tests for saved cards endpoints."""

	@patch('stripe.PaymentMethod.list')
	async def test_list_saved_cards_success(
		self,
		mock_list,
		client: TestClient,
		customer_user,
		customer_token,
		test_session: AsyncSession,
	):
		"""Test successful saved cards listing."""
		# Create stripe customer
		stripe_customer = StripeCustomer(
			user_id=customer_user.id,
			stripe_customer_id='cus_123456789',
		)
		test_session.add(stripe_customer)
		await test_session.commit()

		mock_method = MagicMock(
			id='pm_123456789',
			type='card',
			billing_details={'name': 'Test User'},
		)
		mock_list.return_value = MagicMock(data=[mock_method])

		response = client.get(
			'/api/v1/payments/saved-cards',
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 200
		data = response.json()
		assert len(data['payment_methods']) == 1
		assert data['payment_methods'][0]['id'] == 'pm_123456789'

	async def test_list_saved_cards_no_customer(
		self,
		client: TestClient,
		customer_token,
	):
		"""Test saved cards listing when customer doesn't exist."""
		response = client.get(
			'/api/v1/payments/saved-cards',
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 200
		data = response.json()
		assert len(data['payment_methods']) == 0

	@patch('stripe.PaymentMethod.detach')
	async def test_delete_saved_card_success(
		self,
		mock_detach,
		client: TestClient,
		customer_user,
		customer_token,
		test_session: AsyncSession,
	):
		"""Test successful saved card deletion."""
		# Create stripe customer
		stripe_customer = StripeCustomer(
			user_id=customer_user.id,
			stripe_customer_id='cus_123456789',
		)
		test_session.add(stripe_customer)
		await test_session.commit()

		mock_detach.return_value = MagicMock(id='pm_123456789', status='detached')

		response = client.delete(
			'/api/v1/payments/saved-cards/pm_123456789',
			headers={'Authorization': f'Bearer {customer_token}'},
		)

		assert response.status_code == 200
		assert 'deleted' in response.json()['message'].lower()
