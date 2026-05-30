import logging
from typing import Annotated

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Payment, PaymentStatus, Rental
from app.services.email_service import email_service
from app.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1/webhooks', tags=['webhooks'])


@router.post('/stripe')
async def stripe_webhook(
	request: Request,
	background_tasks: BackgroundTasks,
	session: Annotated[AsyncSession, Depends(get_session)],
):
	"""
	Handle Stripe webhook events.
	Verifies webhook signature and updates payment/rental status.
	"""

	webhook_secret = Settings().STRIPE_WEBHOOK_SECRET

	payload = await request.body()
	sig_header = request.headers.get('stripe-signature')

	if not sig_header:
		raise HTTPException(status_code=400, detail='Missing stripe-signature header')

	try:
		event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
	except ValueError as e:
		logger.error(f'Invalid payload: {e}')
		raise HTTPException(status_code=400, detail='Invalid payload')
	except stripe.SignatureVerificationError as e:
		logger.error(f'Invalid signature: {e}')
		raise HTTPException(status_code=400, detail='Invalid signature')

	try:
		if event['type'] == 'payment_intent.succeeded':
			payment_intent = event['data']['object']
			payment_id = await _handle_payment_succeeded(payment_intent, session)
			if payment_id:
				background_tasks.add_task(
					email_service.send_payment_receipt_by_payment_id,
					payment_id,
				)

		elif event['type'] == 'payment_intent.payment_failed':
			payment_intent = event['data']['object']
			payment_id = await _handle_payment_failed(payment_intent, session)
			if payment_id:
				background_tasks.add_task(
					email_service.send_payment_failed_by_payment_id,
					payment_id,
				)

		elif event['type'] == 'charge.refunded':
			charge = event['data']['object']
			payment_id = await _handle_charge_refunded(charge, session)
			if payment_id:
				background_tasks.add_task(
					email_service.send_refund_notice_by_payment_id,
					payment_id,
				)

		return {'success': True, 'event_type': event['type']}

	except Exception as e:
		logger.error(f'Error handling webhook: {e}')
		raise HTTPException(status_code=500, detail='Webhook processing error')


async def _handle_payment_succeeded(
	payment_intent: dict, session: AsyncSession
) -> int | None:
	"""Handle successful payment intent."""
	payment_intent_id = payment_intent['id']

	result = await session.execute(
		select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
	)
	payment = result.scalar_one_or_none()

	if not payment:
		logger.warning(f'Payment record not found for intent: {payment_intent_id}')
		return None

	payment.status = PaymentStatus.SUCCEEDED

	rental = await session.get(Rental, payment.rental_id)
	if rental:
		rental.payment_status = PaymentStatus.SUCCEEDED

	await session.commit()
	logger.info(f'Payment succeeded: {payment_intent_id}')
	return payment.id


async def _handle_payment_failed(
	payment_intent: dict, session: AsyncSession
) -> int | None:
	"""Handle failed payment intent."""
	payment_intent_id = payment_intent['id']

	result = await session.execute(
		select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
	)
	payment = result.scalar_one_or_none()

	if not payment:
		logger.warning(f'Payment record not found for intent: {payment_intent_id}')
		return None

	payment.status = PaymentStatus.FAILED

	rental = await session.get(Rental, payment.rental_id)
	if rental:
		rental.payment_status = PaymentStatus.FAILED

	await session.commit()
	logger.info(f'Payment failed: {payment_intent_id}')
	return payment.id


async def _handle_charge_refunded(charge: dict, session: AsyncSession) -> int | None:
	"""Handle refunded charge."""
	payment_intent_id = charge.get('payment_intent')

	if not payment_intent_id:
		logger.warning('Refund event missing payment_intent')
		return None

	result = await session.execute(
		select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
	)
	payment = result.scalar_one_or_none()

	if not payment:
		logger.warning(f'Payment record not found for intent: {payment_intent_id}')
		return None

	payment.status = PaymentStatus.REFUNDED
	payment.refunded_amount = charge.get('amount_refunded', 0)

	rental = await session.get(Rental, payment.rental_id)
	if rental:
		rental.payment_status = PaymentStatus.REFUNDED

	await session.commit()
	logger.info(
		f'Charge refunded: {payment_intent_id}, amount: {charge.get("amount_refunded")}'
	)
	return payment.id
