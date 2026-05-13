import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
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
from app.auth_schema import (
	PaymentCaptureRequest,
	IntentCreateRequest,
	PaymentRefundRequest,
)
from app.security import get_password_hash
from app.services.payment_service import PaymentService


@pytest_asyncio.fixture
async def test_user(test_session: AsyncSession):
	"""Create a test user."""
	user = User(
		name='Test User',
		email='test@example.com',
		passwordHash=get_password_hash('test1234'),
		phone='12345678901',
		cpf='12345678901',
		address='Test Address',
		role=Role.CUSTOMER,
	)
	test_session.add(user)
	await test_session.commit()
	await test_session.refresh(user)
	return user


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
async def test_rental(test_session: AsyncSession, test_user, test_costume):
	"""Create a test rental."""
	rental = Rental(
		user_id=test_user.id,
		costume_id=test_costume.id,
		rental_date=datetime.now(),
		return_date=datetime.now() + timedelta(days=7),
	)
	test_session.add(rental)
	await test_session.commit()
	await test_session.refresh(rental)
	return rental


@pytest_asyncio.fixture
async def test_payment(test_session: AsyncSession, test_rental):
	"""Create a test payment."""
	payment = Payment(
		rental_id=test_rental.id,
		stripe_payment_intent_id='pi_123456789',
		amount=10000,
		status=PaymentStatus.PENDING,
		currency='brl',
	)
	test_session.add(payment)
	await test_session.commit()
	await test_session.refresh(payment)
	return payment


class TestPaymentServicePrivateHelpers:
	"""Tests for PaymentService private helper methods."""

	def test_generate_idempotency_key_format(self):
		"""Test idempotency key generation format."""
		service = PaymentService()
		key = service._generate_idempotency_key('payment_intent', '123')

		parts = key.split(':')
		assert len(parts) == 3
		assert parts[0] == 'payment_intent'
		assert parts[1] == '123'
		# parts[2] should be a UUID
		try:
			uuid.UUID(parts[2])
		except ValueError:
			pytest.fail('Third part is not a valid UUID')

	def test_generate_idempotency_key_uniqueness(self):
		"""Test that idempotency keys are unique."""
		service = PaymentService()
		key1 = service._generate_idempotency_key('refund', '456')
		key2 = service._generate_idempotency_key('refund', '456')

		assert key1 != key2  # Should be unique due to UUID


class TestPaymentServiceCreateCustomer:
	"""Tests for _create_stripe_customer private method."""

	@patch('stripe.Customer.create')
	def test_create_stripe_customer_success(self, mock_create):
		"""Test successful Stripe customer creation."""
		mock_customer = MagicMock()
		mock_customer.id = 'cus_123456789'
		mock_create.return_value = mock_customer

		service = PaymentService()
		customer_id = service._create_stripe_customer(
			email='test@example.com', name='Test User'
		)

		assert customer_id == 'cus_123456789'
		mock_create.assert_called_once_with(
			email='test@example.com', name='Test User'
		)

	@patch('stripe.Customer.create')
	def test_create_stripe_customer_stripe_error(self, mock_create):
		"""Test Stripe customer creation with Stripe error."""
		import stripe

		mock_create.side_effect = stripe.StripeError('Customer creation failed')

		service = PaymentService()
		with pytest.raises(HTTPException) as exc_info:
			service._create_stripe_customer(
				email='test@example.com', name='Test User'
			)

		assert exc_info.value.status_code == 500


class TestPaymentServicePaymentIntent:
	"""Tests for PaymentIntent operations."""

	@patch('stripe.PaymentIntent.create')
	def test_create_stripe_payment_intent_success(self, mock_create):
		"""Test successful Stripe PaymentIntent creation."""
		mock_pi = MagicMock()
		mock_pi.client_secret = 'pi_secret_123'
		mock_pi.id = 'pi_123456789'
		mock_create.return_value = mock_pi

		service = PaymentService()
		client_secret, payment_intent_id = service._create_stripe_payment_intent(
			amount=10000, currency='brl', customer_id='cus_123456789'
		)

		assert client_secret == 'pi_secret_123'
		assert payment_intent_id == 'pi_123456789'
		mock_create.assert_called_once()

	@patch('stripe.PaymentIntent.retrieve')
	def test_retrieve_stripe_payment_intent_success(self, mock_retrieve):
		"""Test successful PaymentIntent retrieval."""
		mock_pi = MagicMock()
		mock_pi.id = 'pi_123456789'
		mock_pi.status = 'succeeded'
		mock_pi.amount = 10000
		mock_pi.currency = 'brl'
		mock_pi.client_secret = 'pi_secret_123'
		mock_pi.charges.data = []
		mock_retrieve.return_value = mock_pi

		service = PaymentService()
		result = service._retrieve_stripe_payment_intent('pi_123456789')

		assert result['id'] == 'pi_123456789'
		assert result['status'] == 'succeeded'
		assert result['amount'] == 10000

	@patch('stripe.PaymentIntent.modify')
	def test_capture_stripe_payment_intent_success(self, mock_modify):
		"""Test successful PaymentIntent capture."""
		mock_pi = MagicMock()
		mock_pi.id = 'pi_123456789'
		mock_pi.status = 'succeeded'
		mock_pi.charges.data = []
		mock_modify.return_value = mock_pi

		service = PaymentService()
		pi_id, status = service._capture_stripe_payment_intent('pi_123456789')

		assert pi_id == 'pi_123456789'
		assert status == 'succeeded'


class TestPaymentServiceRefund:
	"""Tests for refund operations."""

	@patch('stripe.Refund.create')
	def test_refund_stripe_payment_full_success(self, mock_refund):
		"""Test successful full refund."""
		mock_ref = MagicMock()
		mock_ref.id = 're_123456789'
		mock_ref.status = 'succeeded'
		mock_ref.amount = 10000
		mock_refund.return_value = mock_ref

		service = PaymentService()
		refund_id, status, amount = service._refund_stripe_payment('pi_123456789')

		assert refund_id == 're_123456789'
		assert status == 'succeeded'
		assert amount == 10000

	@patch('stripe.Refund.create')
	def test_refund_stripe_payment_partial_success(self, mock_refund):
		"""Test successful partial refund."""
		mock_ref = MagicMock()
		mock_ref.id = 're_123456789'
		mock_ref.status = 'succeeded'
		mock_ref.amount = 5000
		mock_refund.return_value = mock_ref

		service = PaymentService()
		refund_id, status, amount = service._refund_stripe_payment(
			'pi_123456789', amount=5000
		)

		assert amount == 5000


class TestPaymentServiceStatusMapping:
	"""Tests for Stripe status to enum mapping."""

	def test_get_payment_status_enum_pending_statuses(self):
		"""Test mapping of pending Stripe statuses."""
		service = PaymentService()

		assert (
			service._get_payment_status_enum('requires_payment_method')
			== PaymentStatus.PENDING
		)
		assert (
			service._get_payment_status_enum('requires_confirmation')
			== PaymentStatus.PENDING
		)
		assert (
			service._get_payment_status_enum('processing') == PaymentStatus.PENDING
		)

	def test_get_payment_status_enum_succeeded(self):
		"""Test mapping of succeeded status."""
		service = PaymentService()

		assert (
			service._get_payment_status_enum('succeeded') == PaymentStatus.CAPTURED
		)

	def test_get_payment_status_enum_requires_capture(self):
		"""Test mapping of requires_capture status."""
		service = PaymentService()

		assert (
			service._get_payment_status_enum('requires_capture')
			== PaymentStatus.SUCCEEDED
		)

	def test_get_payment_status_enum_failed(self):
		"""Test mapping of failed status."""
		service = PaymentService()

		assert service._get_payment_status_enum('canceled') == PaymentStatus.FAILED

	def test_get_payment_status_enum_unknown(self):
		"""Test mapping of unknown status defaults to pending."""
		service = PaymentService()

		assert (
			service._get_payment_status_enum('unknown_status')
			== PaymentStatus.PENDING
		)


class TestPaymentServicePaymentMethods:
	"""Tests for payment method operations."""

	@patch('stripe.PaymentMethod.list')
	def test_list_stripe_payment_methods_success(self, mock_list):
		"""Test successful listing of payment methods."""
		mock_method1 = MagicMock()
		mock_method1.id = 'pm_123'
		mock_method1.type = 'card'
		mock_list.return_value.data = [mock_method1]

		service = PaymentService()
		methods = service._list_stripe_payment_methods('cus_123456789')

		assert len(methods) == 1
		assert methods[0].id == 'pm_123'

	@patch('stripe.PaymentMethod.detach')
	def test_delete_stripe_payment_method_success(self, mock_detach):
		"""Test successful payment method deletion."""
		mock_pm = MagicMock()
		mock_pm.id = 'pm_123'
		mock_pm.status = 'disconnected'
		mock_detach.return_value = mock_pm

		service = PaymentService()
		result = service._delete_stripe_payment_method('pm_123')

		assert result['id'] == 'pm_123'
		assert result['status'] == 'disconnected'


class TestPaymentServicePublicMethods:
	"""Tests for public async methods."""

	@patch.object(PaymentService, '_create_stripe_customer')
	@patch.object(PaymentService, '_create_stripe_payment_intent')
	@pytest.mark.asyncio
	async def test_create_payment_intent_success(
		self,
		mock_create_pi,
		mock_create_customer,
		test_session: AsyncSession,
		test_user,
		test_rental,
	):
		"""Test successful payment intent creation."""
		mock_create_customer.return_value = 'cus_123456789'
		mock_create_pi.return_value = ('pi_secret_123', 'pi_123456789')

		service = PaymentService()
		request = IntentCreateRequest(rental_id=test_rental.id)

		response = await service.create_payment_intent(
			test_session, test_user, request
		)

		assert response.client_secret == 'pi_secret_123'
		assert response.payment_intent_id == 'pi_123456789'
		assert response.amount == 10000  # 100.0 * 100

	@patch.object(PaymentService, '_create_stripe_customer')
	@patch.object(PaymentService, '_create_stripe_payment_intent')
	@pytest.mark.asyncio
	async def test_create_payment_intent_authorization_check(
		self,
		mock_create_pi,
		mock_create_customer,
		test_session: AsyncSession,
		test_user,
		test_rental,
	):
		"""Test that payment creation checks authorization."""
		# Create a different user
		other_user = User(
			name='Other User',
			email='other@example.com',
			passwordHash=get_password_hash('test1234'),
			phone='12345678901',
			cpf='12345678901',
			address='Test Address',
			role=Role.CUSTOMER,
		)
		test_session.add(other_user)
		await test_session.commit()

		service = PaymentService()
		request = IntentCreateRequest(rental_id=test_rental.id)

		with pytest.raises(HTTPException) as exc_info:
			await service.create_payment_intent(test_session, other_user, request)

		assert exc_info.value.status_code == 403

	@patch.object(PaymentService, '_retrieve_stripe_payment_intent')
	@pytest.mark.asyncio
	async def test_retrieve_payment_intent_success(
		self,
		mock_retrieve_pi,
		test_session: AsyncSession,
		test_user,
		test_payment,
	):
		"""Test successful payment intent retrieval."""
		mock_retrieve_pi.return_value = {
			'id': 'pi_123456789',
			'status': 'succeeded',
			'amount': 10000,
			'currency': 'brl',
			'client_secret': 'pi_secret_123',
		}

		service = PaymentService()
		response = await service.retrieve_payment_intent(
			test_session, test_user, 'pi_123456789'
		)

		assert response.id == 'pi_123456789'
		assert response.status == 'succeeded'

	@patch.object(PaymentService, '_capture_stripe_payment_intent')
	@pytest.mark.asyncio
	async def test_capture_payment_success(
		self,
		mock_capture_pi,
		test_session: AsyncSession,
		test_user,
		test_payment,
	):
		"""Test successful payment capture."""
		mock_capture_pi.return_value = ('pi_123456789', 'succeeded')

		service = PaymentService()
		request = PaymentCaptureRequest(payment_intent_id='pi_123456789')

		response = await service.capture_payment(test_session, test_user, request)

		assert response.payment_intent_id == 'pi_123456789'
		assert response.status == 'succeeded'

	@patch.object(PaymentService, '_refund_stripe_payment')
	@pytest.mark.asyncio
	async def test_refund_payment_success(
		self,
		mock_refund_pi,
		test_session: AsyncSession,
		test_user,
		test_payment,
	):
		"""Test successful payment refund."""
		mock_refund_pi.return_value = ('re_123456789', 'succeeded', 10000)

		service = PaymentService()
		request = PaymentRefundRequest(payment_intent_id='pi_123456789')

		response = await service.refund_payment(test_session, test_user, request)

		assert response.refund_id == 're_123456789'
		assert response.status == 'succeeded'

	@patch.object(PaymentService, '_refund_stripe_payment')
	@pytest.mark.asyncio
	async def test_refund_payment_partial_success(
		self,
		mock_refund_pi,
		test_session: AsyncSession,
		test_user,
		test_payment,
	):
		"""Test successful partial payment refund."""
		mock_refund_pi.return_value = ('re_123456789', 'succeeded', 5000)

		service = PaymentService()
		request = PaymentRefundRequest(payment_intent_id='pi_123456789', amount=5000)

		response = await service.refund_payment(test_session, test_user, request)

		assert response.amount == 5000

	@pytest.mark.asyncio
	async def test_refund_payment_amount_exceeds_payment(
		self,
		test_session: AsyncSession,
		test_user,
		test_payment,
	):
		"""Test refund amount validation."""
		service = PaymentService()
		request = PaymentRefundRequest(
			payment_intent_id='pi_123456789', amount=20000  # More than payment amount
		)

		with pytest.raises(HTTPException) as exc_info:
			await service.refund_payment(test_session, test_user, request)

		assert exc_info.value.status_code == 400

	@patch.object(PaymentService, '_create_stripe_customer')
	@pytest.mark.asyncio
	async def test_create_customer_success(
		self,
		mock_create_customer,
		test_session: AsyncSession,
		test_user,
	):
		"""Test successful customer creation."""
		mock_create_customer.return_value = 'cus_123456789'

		service = PaymentService()
		response = await service.create_customer(test_session, test_user)

		assert response.stripe_customer_id == 'cus_123456789'
		assert response.user_id == test_user.id

	@patch.object(PaymentService, '_list_stripe_payment_methods')
	@pytest.mark.asyncio
	async def test_list_saved_cards_success(
		self,
		mock_list_methods,
		test_session: AsyncSession,
		test_user,
	):
		"""Test successful card listing."""
		# Create a Stripe customer record
		stripe_customer = StripeCustomer(
			user_id=test_user.id, stripe_customer_id='cus_123456789'
		)
		test_session.add(stripe_customer)
		await test_session.commit()

		mock_method = MagicMock()
		mock_method.id = 'pm_123'
		mock_method.type = 'card'
		mock_method.billing_details = {'name': 'Test Card'}
		mock_list_methods.return_value = [mock_method]

		service = PaymentService()
		response = await service.list_saved_cards(test_session, test_user)

		assert len(response.payment_methods) == 1
		assert response.payment_methods[0].id == 'pm_123'

	@patch.object(PaymentService, '_delete_stripe_payment_method')
	@pytest.mark.asyncio
	async def test_delete_saved_card_success(
		self,
		mock_delete_method,
		test_session: AsyncSession,
		test_user,
	):
		"""Test successful card deletion."""
		# Create a Stripe customer record
		stripe_customer = StripeCustomer(
			user_id=test_user.id, stripe_customer_id='cus_123456789'
		)
		test_session.add(stripe_customer)
		await test_session.commit()

		mock_delete_method.return_value = {'id': 'pm_123', 'status': 'disconnected'}

		service = PaymentService()
		result = await service.delete_saved_card(test_session, test_user, 'pm_123')

		assert 'message' in result
		assert result['result']['id'] == 'pm_123'
