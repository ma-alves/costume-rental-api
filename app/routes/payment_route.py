from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User, Rental, Payment, StripeCustomer, PaymentStatus
from app.security import get_current_user
from app.services.payment_service import PaymentService
from app.schemas import (
	PaymentCreateRequest,
	PaymentIntentResponse,
	PaymentCaptureRequest,
	PaymentCaptureResponse,
	PaymentRefundRequest,
	PaymentRefundResponse,
	PaymentRetrieveResponse,
	StripeCustomerResponse,
	PaymentMethodListResponse,
)
from sqlalchemy import select

router = APIRouter(prefix='/api/v1/payments', tags=['payments'])

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
payment_service = PaymentService()


@router.post(
	'/create-payment-intent',
	response_model=PaymentIntentResponse,
)
async def create_payment_intent(
	current_user: CurrentUser,
	request: PaymentCreateRequest,
	session: Session,
):
	"""
	Create a payment intent for a rental.
	Customers can initiate payment for their rentals.
	"""
	# Verify rental exists and belongs to current user
	rental = await session.get(Rental, request.rental_id)
	if not rental:
		raise HTTPException(status_code=404, detail='Rental not found')

	if rental.user_id != current_user.id:
		raise HTTPException(
			status_code=403, detail='Not authorized to pay for this rental'
		)

	# Check if payment already exists
	existing_payment = await session.execute(
		select(Payment).where(Payment.rental_id == request.rental_id)
	)
	if existing_payment.scalar_one_or_none():
		raise HTTPException(
			status_code=400, detail='Payment already exists for this rental'
		)

	# Get or create Stripe customer
	stripe_customer = await session.execute(
		select(StripeCustomer).where(StripeCustomer.user_id == current_user.id)
	)
	stripe_customer = stripe_customer.scalar_one_or_none()

	if not stripe_customer:
		# Create new Stripe customer
		stripe_customer_id = payment_service.create_customer(
			email=current_user.email,
			name=current_user.name,
		)
		stripe_customer = StripeCustomer(
			user_id=current_user.id,
			stripe_customer_id=stripe_customer_id,
		)
		session.add(stripe_customer)
		await session.flush()
	else:
		stripe_customer_id = stripe_customer.stripe_customer_id

	# Calculate payment amount in cents (using rental fee)
	amount = int(rental.costumes.fee * 100)

	# Create payment intent
	client_secret, payment_intent_id = payment_service.create_payment_intent(
		amount=amount,
		currency='brl',
		customer_id=stripe_customer_id,
		rental_id=request.rental_id,
		metadata={
			'rental_id': str(request.rental_id),
			'user_id': str(current_user.id),
		},
	)

	# Save payment record
	payment = Payment(
		rental_id=request.rental_id,
		stripe_payment_intent_id=payment_intent_id,
		amount=amount,
		status=PaymentStatus.PENDING,
		currency='brl',
	)
	session.add(payment)

	# Update rental payment status
	rental.payment_status = PaymentStatus.PENDING
	rental.payment_amount = amount

	await session.commit()

	return PaymentIntentResponse(
		client_secret=client_secret,
		payment_intent_id=payment_intent_id,
		amount=amount,
		currency='brl',
	)


@router.get(
	'/payment-intent/{payment_intent_id}',
	response_model=PaymentRetrieveResponse,
)
async def retrieve_payment_intent(
	current_user: CurrentUser,
	payment_intent_id: str,
	session: Session,
):
	"""Retrieve payment intent details."""
	# Verify payment belongs to current user
	payment = await session.execute(
		select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
	)
	payment = payment.scalar_one_or_none()

	if not payment:
		raise HTTPException(status_code=404, detail='Payment not found')

	rental = await session.get(Rental, payment.rental_id)
	if rental.user_id != current_user.id:
		raise HTTPException(status_code=403, detail='Not authorized')

	# Get payment details from Stripe
	details = payment_service.retrieve_payment_intent(payment_intent_id)

	return PaymentRetrieveResponse(
		id=details['id'],
		status=details['status'],
		amount=details['amount'],
		currency=details['currency'],
		client_secret=details['client_secret'],
	)


@router.post(
	'/capture',
	response_model=PaymentCaptureResponse,
)
async def capture_payment(
	current_user: CurrentUser,
	request: PaymentCaptureRequest,
	session: Session,
):
	"""
	Capture an authorized payment.
	This moves payment from pending to succeeded.
	"""
	# Verify payment exists and belongs to current user
	payment = await session.execute(
		select(Payment).where(
			Payment.stripe_payment_intent_id == request.payment_intent_id
		)
	)
	payment = payment.scalar_one_or_none()

	if not payment:
		raise HTTPException(status_code=404, detail='Payment not found')

	rental = await session.get(Rental, payment.rental_id)
	if rental.user_id != current_user.id:
		raise HTTPException(status_code=403, detail='Not authorized')

	# Capture payment
	payment_intent_id, status = payment_service.capture_payment_intent(
		request.payment_intent_id
	)

	# Update payment status
	payment.status = payment_service.get_payment_status_enum(status)
	rental.payment_status = PaymentStatus.CAPTURED

	await session.commit()

	return PaymentCaptureResponse(
		payment_intent_id=payment_intent_id,
		status=status,
	)


@router.post(
	'/refund',
	response_model=PaymentRefundResponse,
)
async def refund_payment(
	current_user: CurrentUser,
	request: PaymentRefundRequest,
	session: Session,
):
	"""
	Refund a payment (full or partial).
	Partial refunds allowed for cancellations during rental period.
	"""
	# Verify payment exists and belongs to current user
	payment = await session.execute(
		select(Payment).where(
			Payment.stripe_payment_intent_id == request.payment_intent_id
		)
	)
	payment = payment.scalar_one_or_none()

	if not payment:
		raise HTTPException(status_code=404, detail='Payment not found')

	rental = await session.get(Rental, payment.rental_id)
	if rental.user_id != current_user.id:
		raise HTTPException(status_code=403, detail='Not authorized')

	# Validate refund amount
	if request.amount:
		if request.amount > payment.amount:
			raise HTTPException(
				status_code=400,
				detail='Refund amount cannot exceed payment amount',
			)
		if request.amount <= 0:
			raise HTTPException(
				status_code=400,
				detail='Refund amount must be positive',
			)

	# Create refund
	refund_id, status, refund_amount = payment_service.refund(
		request.payment_intent_id,
		amount=request.amount,
	)

	# Update payment status and refund amount
	payment.status = PaymentStatus.REFUNDED
	payment.refunded_amount = request.amount or payment.amount
	rental.payment_status = PaymentStatus.REFUNDED

	await session.commit()

	return PaymentRefundResponse(
		refund_id=refund_id,
		status=status,
		amount=refund_amount,
	)


@router.post(
	'/create-customer',
	response_model=StripeCustomerResponse,
)
async def create_customer(
	current_user: CurrentUser,
	session: Session,
):
	"""Create a Stripe customer for the current user if not already created."""
	# Check if customer already exists
	existing = await session.execute(
		select(StripeCustomer).where(StripeCustomer.user_id == current_user.id)
	)
	existing_customer = existing.scalar_one_or_none()

	if existing_customer:
		return StripeCustomerResponse(
			stripe_customer_id=existing_customer.stripe_customer_id,
			user_id=current_user.id,
		)

	# Create new Stripe customer
	stripe_customer_id = payment_service.create_customer(
		email=current_user.email,
		name=current_user.name,
	)

	stripe_customer = StripeCustomer(
		user_id=current_user.id,
		stripe_customer_id=stripe_customer_id,
	)
	session.add(stripe_customer)
	await session.commit()

	return StripeCustomerResponse(
		stripe_customer_id=stripe_customer_id,
		user_id=current_user.id,
	)


@router.get(
	'/saved-cards',
	response_model=PaymentMethodListResponse,
)
async def list_saved_cards(
	current_user: CurrentUser,
	session: Session,
):
	"""List all saved payment methods (cards) for the current user."""
	# Get user's Stripe customer
	stripe_customer = await session.execute(
		select(StripeCustomer).where(StripeCustomer.user_id == current_user.id)
	)
	stripe_customer = stripe_customer.scalar_one_or_none()

	if not stripe_customer:
		return PaymentMethodListResponse(payment_methods=[])

	# Get payment methods from Stripe
	methods = payment_service.list_customer_payment_methods(
		stripe_customer.stripe_customer_id
	)

	return PaymentMethodListResponse(
		payment_methods=[
			{
				'id': method.id,
				'type': method.type,
				'billing_details': method.billing_details,
			}
			for method in methods
		]
	)


@router.delete('/saved-cards/{payment_method_id}')
async def delete_saved_card(
	current_user: CurrentUser,
	payment_method_id: str,
	session: Session,
):
	"""Delete a saved payment method."""
	# Get user's Stripe customer to verify ownership
	stripe_customer = await session.execute(
		select(StripeCustomer).where(StripeCustomer.user_id == current_user.id)
	)
	stripe_customer = stripe_customer.scalar_one_or_none()

	if not stripe_customer:
		raise HTTPException(status_code=404, detail='No saved payment methods')

	# Delete payment method
	result = payment_service.delete_payment_method(payment_method_id)

	return {'message': 'Payment method deleted', 'result': result}
