import logging
from typing import Annotated
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import stripe

from app.database import get_session
from app.models import Payment, Rental, PaymentStatus
from app.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1/webhooks', tags=['webhooks'])


@router.post('/stripe')
async def stripe_webhook(
	request: Request, session: Annotated[AsyncSession, Depends(get_session)]
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
			await _handle_payment_succeeded(payment_intent, session)

		elif event['type'] == 'payment_intent.payment_failed':
			payment_intent = event['data']['object']
			await _handle_payment_failed(payment_intent, session)

		elif event['type'] == 'charge.refunded':
			charge = event['data']['object']
			await _handle_charge_refunded(charge, session)

		return {'success': True, 'event_type': event['type']}

	except Exception as e:
		logger.error(f'Error handling webhook: {e}')
		raise HTTPException(status_code=500, detail='Webhook processing error')


async def _handle_payment_succeeded(payment_intent: dict, session: AsyncSession):
	"""Handle successful payment intent."""
	payment_intent_id = payment_intent['id']

	result = await session.execute(
		select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
	)
	payment = result.scalar_one_or_none()

	if not payment:
		logger.warning(f'Payment record not found for intent: {payment_intent_id}')
		return

	payment.status = PaymentStatus.SUCCEEDED

	rental = await session.get(Rental, payment.rental_id)
	if rental:
		rental.payment_status = PaymentStatus.SUCCEEDED

	await session.commit()
	logger.info(f'Payment succeeded: {payment_intent_id}')


async def _handle_payment_failed(payment_intent: dict, session: AsyncSession):
	"""Handle failed payment intent."""
	payment_intent_id = payment_intent['id']

	result = await session.execute(
		select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
	)
	payment = result.scalar_one_or_none()

	if not payment:
		logger.warning(f'Payment record not found for intent: {payment_intent_id}')
		return

	payment.status = PaymentStatus.FAILED

	rental = await session.get(Rental, payment.rental_id)
	if rental:
		rental.payment_status = PaymentStatus.FAILED

	await session.commit()
	logger.info(f'Payment failed: {payment_intent_id}')


async def _handle_charge_refunded(charge: dict, session: AsyncSession):
	"""Handle refunded charge."""
	payment_intent_id = charge.get('payment_intent')

	if not payment_intent_id:
		logger.warning('Refund event missing payment_intent')
		return

	result = await session.execute(
		select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
	)
	payment = result.scalar_one_or_none()

	if not payment:
		logger.warning(f'Payment record not found for intent: {payment_intent_id}')
		return

	payment.status = PaymentStatus.REFUNDED
	payment.refunded_amount = charge.get('amount_refunded', 0)

	rental = await session.get(Rental, payment.rental_id)
	if rental:
		rental.payment_status = PaymentStatus.REFUNDED

	await session.commit()
	logger.info(
		f'Charge refunded: {payment_intent_id}, amount: {charge.get("amount_refunded")}'
	)
