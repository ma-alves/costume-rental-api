import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
	PaymentStatus,
)


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
	async def test_customer_payment_intent_succeeded(
		self,
		mock_construct,
		client: TestClient,
		test_session: AsyncSession,
		customer_payment,
	):
		"""Test payment_intent.succeeded webhook handling."""
		event = {
			'type': 'payment_intent.succeeded',
			'data': {
				'object': {
					'id': 'pi_123456789',
					'status': 'succeeded',
					'metadata': {'rental_id': str(customer_payment.rental_id)},
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
		await test_session.refresh(customer_payment)
		assert customer_payment.status == PaymentStatus.SUCCEEDED

	@patch('stripe.Webhook.construct_event')
	def test_customer_payment_intent_succeeded_not_found(
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
	async def test_customer_payment_intent_failed(
		self,
		mock_construct,
		client: TestClient,
		test_session: AsyncSession,
		customer_payment,
	):
		"""Test payment_intent.payment_failed webhook handling."""
		event = {
			'type': 'payment_intent.payment_failed',
			'data': {
				'object': {
					'id': 'pi_123456789',
					'status': 'canceled',
					'metadata': {'rental_id': str(customer_payment.rental_id)},
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
		await test_session.refresh(customer_payment)
		assert customer_payment.status == PaymentStatus.FAILED


class TestWebhookChargeRefunded:
	"""Tests for charge.refunded webhook event."""

	@patch('stripe.Webhook.construct_event')
	@pytest.mark.asyncio
	async def test_webhook_charge_refunded(
		self,
		mock_construct,
		client: TestClient,
		test_session: AsyncSession,
		customer_payment,
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
		await test_session.refresh(customer_payment)
		assert customer_payment.status == PaymentStatus.REFUNDED
		assert customer_payment.refunded_amount == 5000

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
