import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
	Costume,
	CostumeAvailability,
	Payment,
	PaymentStatus,
	Rental,
	Role,
	User,
)
from app.security import get_password_hash


@pytest_asyncio.fixture
async def webhook_user(test_session: AsyncSession):
	"""Create a test user for webhook tests."""
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
async def webhook_costume(test_session: AsyncSession):
	"""Create a test costume for webhook tests."""
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
async def webhook_rental(test_session: AsyncSession, webhook_user, webhook_costume):
	"""Create a test rental for webhook tests."""
	rental = Rental(
		user_id=webhook_user.id,
		costume_id=webhook_costume.id,
		rental_date=datetime.now(),
		return_date=datetime.now() + timedelta(days=7),
	)
	test_session.add(rental)
	await test_session.commit()
	await test_session.refresh(rental)
	return rental


@pytest_asyncio.fixture
async def webhook_payment(test_session: AsyncSession, webhook_rental):
	"""Create a test payment for webhook tests."""
	payment = Payment(
		rental_id=webhook_rental.id,
		stripe_payment_intent_id='pi_123456789',
		amount=10000,
		status=PaymentStatus.PENDING,
		currency='brl',
	)
	test_session.add(payment)
	await test_session.commit()
	await test_session.refresh(payment)
	return payment


class TestWebhookSignatureVerification:
	"""Tests for webhook signature verification."""

	def test_webhook_missing_signature(self, client: TestClient):
		"""Test webhook request without signature header."""
		payload = json.dumps({'type': 'payment_intent.succeeded'})

		response = client.post(
			'/api/v1/webhooks/stripe',
			content=payload,
			headers={'Content-Type': 'application/json'},
		)

		assert response.status_code == 400
		assert 'stripe-signature' in response.json()['detail'].lower()

	@patch('stripe.Webhook.construct_event')
	def test_webhook_invalid_signature(self, mock_construct, client: TestClient):
		"""Test webhook request with invalid signature."""
		import stripe

		mock_construct.side_effect = stripe.error.SignatureVerificationError(
			'Invalid signature', 'sig_header'
		)

		payload = json.dumps({'type': 'payment_intent.succeeded'})

		response = client.post(
			'/api/v1/webhooks/stripe',
			content=payload,
			headers={
				'Content-Type': 'application/json',
				'stripe-signature': 'invalid_signature',
			},
		)

		assert response.status_code == 400


class TestWebhookPaymentIntentSucceeded:
	"""Tests for payment_intent.succeeded webhook event."""

	@patch('stripe.Webhook.construct_event')
	@pytest.mark.asyncio
	async def test_webhook_payment_intent_succeeded(
		self,
		mock_construct,
		client: TestClient,
		test_session: AsyncSession,
		webhook_payment,
	):
		"""Test payment_intent.succeeded webhook handling."""
		event = {
			'type': 'payment_intent.succeeded',
			'data': {
				'object': {
					'id': 'pi_123456789',
					'status': 'succeeded',
					'metadata': {'rental_id': str(webhook_payment.rental_id)},
				}
			},
		}
		mock_construct.return_value = event

		payload = json.dumps(event)

		response = client.post(
			'/api/v1/webhooks/stripe',
			content=payload,
			headers={
				'Content-Type': 'application/json',
				'stripe-signature': 'sig_header',
			},
		)

		assert response.status_code == 200
		assert response.json()['success'] is True
		assert response.json()['event_type'] == 'payment_intent.succeeded'

		# Verify payment was updated
		await test_session.refresh(webhook_payment)
		assert webhook_payment.status == PaymentStatus.SUCCEEDED

	@patch('stripe.Webhook.construct_event')
	def test_webhook_payment_intent_succeeded_not_found(
		self,
		mock_construct,
		client: TestClient,
	):
		"""Test payment_intent.succeeded webhook with non-existent payment."""
		event = {
			'type': 'payment_intent.succeeded',
			'data': {
				'object': {
					'id': 'pi_nonexistent',
					'status': 'succeeded',
				}
			},
		}
		mock_construct.return_value = event

		payload = json.dumps(event)

		response = client.post(
			'/api/v1/webhooks/stripe',
			content=payload,
			headers={
				'Content-Type': 'application/json',
				'stripe-signature': 'sig_header',
			},
		)

		# Should still return 200 but log warning
		assert response.status_code == 200


class TestWebhookPaymentIntentFailed:
	"""Tests for payment_intent.payment_failed webhook event."""

	@patch('stripe.Webhook.construct_event')
	@pytest.mark.asyncio
	async def test_webhook_payment_intent_failed(
		self,
		mock_construct,
		client: TestClient,
		test_session: AsyncSession,
		webhook_payment,
	):
		"""Test payment_intent.payment_failed webhook handling."""
		event = {
			'type': 'payment_intent.payment_failed',
			'data': {
				'object': {
					'id': 'pi_123456789',
					'status': 'canceled',
					'metadata': {'rental_id': str(webhook_payment.rental_id)},
				}
			},
		}
		mock_construct.return_value = event

		payload = json.dumps(event)

		response = client.post(
			'/api/v1/webhooks/stripe',
			content=payload,
			headers={
				'Content-Type': 'application/json',
				'stripe-signature': 'sig_header',
			},
		)

		assert response.status_code == 200
		assert response.json()['event_type'] == 'payment_intent.payment_failed'

		# Verify payment was updated
		await test_session.refresh(webhook_payment)
		assert webhook_payment.status == PaymentStatus.FAILED


class TestWebhookChargeRefunded:
	"""Tests for charge.refunded webhook event."""

	@patch('stripe.Webhook.construct_event')
	@pytest.mark.asyncio
	async def test_webhook_charge_refunded(
		self,
		mock_construct,
		client: TestClient,
		test_session: AsyncSession,
		webhook_payment,
	):
		"""Test charge.refunded webhook handling."""
		event = {
			'type': 'charge.refunded',
			'data': {
				'object': {
					'payment_intent': 'pi_123456789',
					'amount_refunded': 5000,
				}
			},
		}
		mock_construct.return_value = event

		payload = json.dumps(event)

		response = client.post(
			'/api/v1/webhooks/stripe',
			content=payload,
			headers={
				'Content-Type': 'application/json',
				'stripe-signature': 'sig_header',
			},
		)

		assert response.status_code == 200
		assert response.json()['event_type'] == 'charge.refunded'

		# Verify payment was updated
		await test_session.refresh(webhook_payment)
		assert webhook_payment.status == PaymentStatus.REFUNDED
		assert webhook_payment.refunded_amount == 5000

	@patch('stripe.Webhook.construct_event')
	def test_webhook_charge_refunded_missing_payment_intent(
		self,
		mock_construct,
		client: TestClient,
	):
		"""Test charge.refunded webhook with missing payment_intent."""
		event = {
			'type': 'charge.refunded',
			'data': {'object': {'amount_refunded': 5000}},
		}
		mock_construct.return_value = event

		payload = json.dumps(event)

		response = client.post(
			'/api/v1/webhooks/stripe',
			content=payload,
			headers={
				'Content-Type': 'application/json',
				'stripe-signature': 'sig_header',
			},
		)

		# Should still return 200 but log warning
		assert response.status_code == 200


class TestWebhookEventRouting:
	"""Tests for webhook event routing."""

	@patch('stripe.Webhook.construct_event')
	def test_webhook_unhandled_event_type(
		self,
		mock_construct,
		client: TestClient,
	):
		"""Test webhook with unhandled event type."""
		event = {
			'type': 'charge.captured',
			'data': {'object': {'id': 'ch_123'}},
		}
		mock_construct.return_value = event

		payload = json.dumps(event)

		response = client.post(
			'/api/v1/webhooks/stripe',
			content=payload,
			headers={
				'Content-Type': 'application/json',
				'stripe-signature': 'sig_header',
			},
		)

		# Should still return 200 for unhandled event
		assert response.status_code == 200
		assert response.json()['event_type'] == 'charge.captured'
