import logging
from pathlib import Path

import resend
from jinja2 import Environment, FileSystemLoader
from resend.exceptions import ResendError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import Payment, Rental
from app.settings import Settings

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / 'email_templates'


class EmailService:
	def __init__(self):
		resend.api_key = Settings().RESEND_API_KEY
		self.email_from = Settings().EMAIL_FROM
		self.template_env = Environment(
			loader=FileSystemLoader(TEMPLATE_DIR),
		)

	def _render_template(self, template_name: str, context: dict) -> str:
		template = self.template_env.get_template(template_name)
		return template.render(**context)

	def _send(self, params: resend.Emails.SendParams) -> resend.Emails.SendResponse:
		return resend.Emails.send(params)

	async def _load_payment_for_email(self, payment_id: int) -> Payment | None:
		async with AsyncSessionLocal() as session:
			return await session.scalar(
				select(Payment)
				.where(Payment.id == payment_id)
				.options(
					selectinload(Payment.rental).selectinload(Rental.users),
					selectinload(Payment.rental).selectinload(Rental.costumes),
				)
			)

	async def send_payment_receipt_by_payment_id(self, payment_id: int) -> None:
		try:
			payment = await self._load_payment_for_email(payment_id)
			if not payment or not payment.rental or not payment.rental.users:
				logger.warning(
					'Skipping receipt email: payment or rental not found payment_id=%s',
					payment_id,
				)
				return

			rental = payment.rental
			user = rental.users
			html = self._render_template(
				'payment_receipt.html',
				{
					'name': user.name,
					'rental_id': rental.id,
					'amount': payment.amount / 100,
					'currency': payment.currency.upper(),
					'payment_intent_id': payment.stripe_payment_intent_id,
				},
			)
			response = self._send({
				'from': self.email_from,
				'to': [user.email],
				'subject': f'Payment Receipt — {payment.currency.upper()} {payment.amount / 100:.2f}',
				'html': html,
			})
			logger.info(
				'Sent receipt email_id=%s payment_id=%s',
				response.id,
				payment_id,
			)
		except ResendError:
			logger.exception('Failed receipt email payment_id=%s', payment_id)

	async def send_payment_failed_by_payment_id(self, payment_id: int) -> None:
		try:
			payment = await self._load_payment_for_email(payment_id)
			if not payment or not payment.rental or not payment.rental.users:
				logger.warning(
					'Skipping failed-payment email: payment or rental not found payment_id=%s',
					payment_id,
				)
				return

			rental = payment.rental
			user = rental.users
			html = self._render_template(
				'payment_failed.html',
				{
					'name': user.name,
					'rental_id': rental.id,
					'payment_intent_id': payment.stripe_payment_intent_id,
				},
			)
			response = self._send({
				'from': self.email_from,
				'to': [user.email],
				'subject': f'Payment Failed — Rental #{rental.id}',
				'html': html,
			})
			logger.info(
				'Sent failed-payment email_id=%s payment_id=%s',
				response.id,
				payment_id,
			)
		except ResendError:
			logger.exception('Failed payment-failed email payment_id=%s', payment_id)

	async def send_refund_notice_by_payment_id(self, payment_id: int) -> None:
		try:
			payment = await self._load_payment_for_email(payment_id)
			if not payment or not payment.rental or not payment.rental.users:
				logger.warning(
					'Skipping refund email: payment or rental not found payment_id=%s',
					payment_id,
				)
				return

			rental = payment.rental
			user = rental.users
			html = self._render_template(
				'refund_notice.html',
				{
					'name': user.name,
					'rental_id': rental.id,
					'amount': payment.refunded_amount / 100,
					'currency': payment.currency.upper(),
					'payment_intent_id': payment.stripe_payment_intent_id,
				},
			)
			response = self._send({
				'from': self.email_from,
				'to': [user.email],
				'subject': f'Refund Processed — Rental #{rental.id}',
				'html': html,
			})
			logger.info(
				'Sent refund email_id=%s payment_id=%s',
				response.id,
				payment_id,
			)
		except ResendError:
			logger.exception('Failed refund email payment_id=%s', payment_id)


email_service = EmailService()
