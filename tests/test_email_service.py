from unittest.mock import MagicMock, patch

import pytest
from resend.exceptions import ResendError

from app.models import PaymentStatus
from app.services.email_service import EmailService, email_service


class TestEmailServiceHelpers:
	def test_render_template_payment_receipt(self):
		service = EmailService()
		html = service._render_template(
			'payment_receipt.html',
			{
				'name': 'Test User',
				'rental_id': 1,
				'amount': 100.0,
				'currency': 'BRL',
				'payment_intent_id': 'pi_test',
			},
		)
		assert 'Test User' in html
		assert 'pi_test' in html

	@patch('app.services.email_service.resend.Emails.send')
	def test_send_returns_response(self, mock_send):
		mock_send.return_value = MagicMock(id='email_123')
		service = EmailService()
		response = service._send({
			'from': 'test@resend.dev',
			'to': ['user@example.com'],
			'subject': 'Test',
			'html': '<p>hi</p>',
		})
		assert response.id == 'email_123'
		mock_send.assert_called_once()


class TestEmailServiceWebhookSends:
	@pytest.mark.asyncio
	@patch('app.services.email_service.resend.Emails.send')
	@patch.object(EmailService, '_load_payment_for_email')
	async def test_send_payment_receipt_success(
		self, mock_load, mock_send, customer_payment
	):
		mock_load.return_value = customer_payment
		mock_send.return_value = MagicMock(id='email_receipt')

		await email_service.send_payment_receipt_by_payment_id(customer_payment.id)

		mock_send.assert_called_once()
		params = mock_send.call_args[0][0]
		assert params['to'] == ['customer@example.com']
		assert 'Payment Receipt' in params['subject']

	@pytest.mark.asyncio
	@patch('app.services.email_service.resend.Emails.send')
	@patch.object(EmailService, '_load_payment_for_email')
	async def test_send_payment_failed_success(
		self, mock_load, mock_send, customer_payment
	):
		mock_load.return_value = customer_payment
		mock_send.return_value = MagicMock(id='email_failed')

		await email_service.send_payment_failed_by_payment_id(customer_payment.id)

		mock_send.assert_called_once()
		params = mock_send.call_args[0][0]
		assert 'Payment Failed' in params['subject']

	@pytest.mark.asyncio
	@patch('app.services.email_service.resend.Emails.send')
	@patch.object(EmailService, '_load_payment_for_email')
	async def test_send_refund_notice_success(
		self, mock_load, mock_send, customer_payment
	):
		customer_payment.refunded_amount = 5000
		customer_payment.status = PaymentStatus.REFUNDED
		mock_load.return_value = customer_payment
		mock_send.return_value = MagicMock(id='email_refund')

		await email_service.send_refund_notice_by_payment_id(customer_payment.id)

		mock_send.assert_called_once()
		params = mock_send.call_args[0][0]
		assert 'Refund Processed' in params['subject']

	@pytest.mark.asyncio
	@patch('app.services.email_service.resend.Emails.send')
	@patch.object(EmailService, '_load_payment_for_email')
	async def test_send_payment_receipt_does_not_raise_on_resend_error(
		self, mock_load, mock_send, customer_payment
	):
		mock_load.return_value = customer_payment
		mock_send.side_effect = ResendError(
			code=500,
			error_type='internal_error',
			message='API down',
			suggested_action='Retry',
		)

		await email_service.send_payment_receipt_by_payment_id(customer_payment.id)

	@pytest.mark.asyncio
	@patch('app.services.email_service.resend.Emails.send')
	@patch.object(EmailService, '_load_payment_for_email')
	async def test_send_skips_when_payment_not_found(self, mock_load, mock_send):
		mock_load.return_value = None

		await email_service.send_payment_receipt_by_payment_id(999)

		mock_send.assert_not_called()
