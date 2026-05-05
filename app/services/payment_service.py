import uuid
from typing import Optional, Tuple

import stripe
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PaymentStatus, Rental, StripeCustomer, User, Payment
from app.schemas import (
	PaymentMethodResponse,
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
from app.settings import Settings


class PaymentService:
	def __init__(self):
		stripe.api_key = Settings().STRIPE_SECRET_KEY

	# private helpers
	def _generate_idempotency_key(self, resource_type: str, resource_id: str) -> str:
		"""Generate a consistent idempotency key for payment operations."""
		return f'{resource_type}:{resource_id}:{uuid.uuid4()}'

	def _create_stripe_customer(self, email: str, name: str) -> str:
		"""Create a Stripe customer (sync)."""
		try:
			customer = stripe.Customer.create(email=email, name=name)
		except stripe.StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))
		return customer.id

	def _create_stripe_payment_intent(
		self,
		amount: int,
		currency: str = 'brl',
		customer_id: Optional[str] = None,
		rental_id: Optional[int] = None,
		metadata: Optional[dict] = None,
	) -> Tuple[str | None, str]:
		"""Create a Stripe PaymentIntent (sync). Returns (client_secret, payment_intent_id)."""
		try:
			params = {
				'amount': amount,
				'currency': currency,
				'payment_method_types': ['card'],
				'capture_method': 'manual',
				'setup_future_usage': 'off_session',
				'metadata': metadata or {},
			}
			if customer_id:
				params['customer'] = customer_id
			if rental_id:
				params['metadata']['rental_id'] = str(rental_id)

			idempotency_key = self._generate_idempotency_key(
				'payment_intent', f'{customer_id}_{rental_id}'
			)
			payment_intent = stripe.PaymentIntent.create(
				**params, idempotency_key=idempotency_key
			)
		except stripe.StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))
		return payment_intent.client_secret, payment_intent.id

	def _retrieve_stripe_payment_intent(self, payment_intent_id: str) -> dict:
		"""Retrieve PaymentIntent from Stripe (sync)."""
		try:
			payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
		except stripe.StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))
		return {
			'id': payment_intent.id,
			'status': payment_intent.status,
			'amount': payment_intent.amount,
			'currency': payment_intent.currency,
			'client_secret': payment_intent.client_secret,
			'charges': payment_intent.charges.data,
		}

	def _capture_stripe_payment_intent(self, payment_intent_id: str) -> Tuple[str, str]:
		"""Capture an authorized PaymentIntent (sync). Returns (id, status)."""
		try:
			payment_intent = stripe.PaymentIntent.modify(
				payment_intent_id,
				idempotency_key=self._generate_idempotency_key('capture', payment_intent_id),
			)
			if payment_intent.status != 'succeeded':
				charges = payment_intent.charges.data
				if charges and not charges[0].captured:
					stripe.Charge.retrieve(charges[0].id).capture()
		except stripe.StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))
		return payment_intent.id, payment_intent.status

	# TODO! retirar amount externo, usar PRICE_ID
	def _refund_stripe_payment(self, payment_intent_id: str, amount: Optional[int] = None) -> Tuple[str, str, int]:
		"""Create a refund (sync). Returns (refund_id, status, refund_amount)."""
		try:
			params: dict[str, str | int] = {
				'payment_intent': payment_intent_id,
				'idempotency_key': self._generate_idempotency_key('refund', payment_intent_id),
			}
			if amount:
				params['amount'] = amount
			refund = stripe.Refund.create(**params)
		except stripe.StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))
		return refund.id, refund.status, refund.amount

	def _list_stripe_payment_methods(self, customer_id: str) -> list:
		"""List saved cards for a Stripe customer (sync)."""
		try:
			methods = stripe.PaymentMethod.list(customer=customer_id, type='card')
		except stripe.StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))
		return methods.data

	def _delete_stripe_payment_method(self, payment_method_id: str) -> dict:
		"""Detach/delete a payment method (sync)."""
		try:
			pm = stripe.PaymentMethod.detach(payment_method_id)
		except stripe.StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))
		return {'id': pm.id, 'status': pm.status}

	def _get_payment_status_enum(self, stripe_status: str) -> PaymentStatus:
		"""Convert Stripe status to internal enum."""
		status_map = {
			'requires_payment_method': PaymentStatus.PENDING,
			'requires_confirmation': PaymentStatus.PENDING,
			'requires_action': PaymentStatus.PENDING,
			'processing': PaymentStatus.PENDING,
			'requires_capture': PaymentStatus.SUCCEEDED,
			'succeeded': PaymentStatus.CAPTURED,
			'canceled': PaymentStatus.FAILED,
		}
		return status_map.get(stripe_status, PaymentStatus.PENDING)

	# public methods for routing
	async def create_payment_intent(
		self,
		session: AsyncSession,
		current_user: User,
		request: PaymentCreateRequest,
	) -> PaymentIntentResponse:
		"""Full business logic to create a payment intent for a rental."""
		# 1. Verify rental exists and belongs to user
		rental = await session.get(Rental, request.rental_id)
		if not rental:
			raise HTTPException(status_code=404, detail='Rental not found')
		if rental.user_id != current_user.id:
			raise HTTPException(status_code=403, detail='Not authorized to pay for this rental')

		# 2. Check if payment already exists for this rental
		existing_payment = await session.execute(
			select(Payment).where(Payment.rental_id == request.rental_id)
		)
		if existing_payment.scalar_one_or_none():
			raise HTTPException(status_code=400, detail='Payment already exists for this rental')

		# 3. Get or create Stripe customer record
		stripe_customer_record = await session.execute(
			select(StripeCustomer).where(StripeCustomer.user_id == current_user.id)
		)
		stripe_customer = stripe_customer_record.scalar_one_or_none()

		if not stripe_customer:
			stripe_customer_id = self._create_stripe_customer(
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

		# 4. Calculate amount (in cents)
		amount = int(rental.costumes.fee * 100)

		# 5. Create Stripe PaymentIntent
		client_secret, payment_intent_id = self._create_stripe_payment_intent(
			amount=amount,
			currency='brl',
			customer_id=stripe_customer_id,
			rental_id=request.rental_id,
			metadata={
				'rental_id': str(request.rental_id),
				'user_id': str(current_user.id),
			},
		)

		# 6. Save payment record
		payment = Payment(
			rental_id=request.rental_id,
			stripe_payment_intent_id=payment_intent_id,
			amount=amount,
			status=PaymentStatus.PENDING,
			currency='brl',
		)
		session.add(payment)

		# 7. Update rental payment status
		rental.payment_status = PaymentStatus.PENDING
		rental.payment_amount = amount

		await session.commit()

		return PaymentIntentResponse(
			client_secret=client_secret,
			payment_intent_id=payment_intent_id,
			amount=amount,
			currency='brl',
		)

	async def retrieve_payment_intent(
		self,
		session: AsyncSession,
		current_user: User,
		payment_intent_id: str,
	) -> PaymentRetrieveResponse:
		"""Retrieve a payment intent details with authorization."""
		# 1. Verify payment belongs to user
		payment = await session.execute(
			select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
		)
		payment = payment.scalar_one_or_none()
		if not payment:
			raise HTTPException(status_code=404, detail='Payment not found')

		rental = await session.get(Rental, payment.rental_id)
		if rental.user_id != current_user.id:
			raise HTTPException(status_code=403, detail='Not authorized')

		# 2. Fetch details from Stripe
		details = self._retrieve_stripe_payment_intent(payment_intent_id)

		return PaymentRetrieveResponse(
			id=details['id'],
			status=details['status'],
			amount=details['amount'],
			currency=details['currency'],
			client_secret=details['client_secret'],
		)

	async def capture_payment(
		self,
		session: AsyncSession,
		current_user: User,
		request: PaymentCaptureRequest,
	) -> PaymentCaptureResponse:
		"""Capture an authorized payment."""
		# 1. Verify payment exists and belongs to user
		payment = await session.execute(
			select(Payment).where(Payment.stripe_payment_intent_id == request.payment_intent_id)
		)
		payment = payment.scalar_one_or_none()
		if not payment:
			raise HTTPException(status_code=404, detail='Payment not found')

		rental = await session.get(Rental, payment.rental_id)
		if rental.user_id != current_user.id:
			raise HTTPException(status_code=403, detail='Not authorized')

		# 2. Capture in Stripe
		pi_id, status = self._capture_stripe_payment_intent(request.payment_intent_id)

		# 3. Update local records
		payment.status = self._get_payment_status_enum(status)
		rental.payment_status = PaymentStatus.CAPTURED
		await session.commit()

		return PaymentCaptureResponse(payment_intent_id=pi_id, status=status)

	async def refund_payment(
		self,
		session: AsyncSession,
		current_user: User,
		request: PaymentRefundRequest,
	) -> PaymentRefundResponse:
		"""Refund a payment (full or partial)."""
		# 1. Verify payment
		payment = await session.execute(
			select(Payment).where(Payment.stripe_payment_intent_id == request.payment_intent_id)
		)
		payment = payment.scalar_one_or_none()
		if not payment:
			raise HTTPException(status_code=404, detail='Payment not found')

		rental = await session.get(Rental, payment.rental_id)
		if rental.user_id != current_user.id:
			raise HTTPException(status_code=403, detail='Not authorized')

		# 2. Validate refund amount
		if request.amount:
			if request.amount > payment.amount:
				raise HTTPException(
					status_code=400, detail='Refund amount cannot exceed payment amount'
				)
			if request.amount <= 0:
				raise HTTPException(status_code=400, detail='Refund amount must be positive')

		# 3. Create refund in Stripe
		refund_id, status, refund_amount = self._refund_stripe_payment(
			request.payment_intent_id, amount=request.amount
		)

		# 4. Update local records
		payment.status = PaymentStatus.REFUNDED
		payment.refunded_amount = request.amount or payment.amount
		rental.payment_status = PaymentStatus.REFUNDED
		await session.commit()

		return PaymentRefundResponse(refund_id=refund_id, status=status, amount=refund_amount)

	async def create_customer(
		self, session: AsyncSession, current_user: User
	) -> StripeCustomerResponse:
		"""Create a Stripe customer for the user if not already existing."""
		# Check if already exists
		existing = await session.execute(
			select(StripeCustomer).where(StripeCustomer.user_id == current_user.id)
		)
		existing_customer = existing.scalar_one_or_none()
		if existing_customer:
			return StripeCustomerResponse(
				stripe_customer_id=existing_customer.stripe_customer_id,
				user_id=current_user.id,
			)

		# Create new
		stripe_customer_id = self._create_stripe_customer(
			email=current_user.email, name=current_user.name
		)
		stripe_customer = StripeCustomer(
			user_id=current_user.id, stripe_customer_id=stripe_customer_id
		)
		session.add(stripe_customer)
		await session.commit()

		return StripeCustomerResponse(
			stripe_customer_id=stripe_customer_id, user_id=current_user.id
		)

	async def list_saved_cards(
		self, session: AsyncSession, current_user: User
	) -> PaymentMethodListResponse:
		"""List all saved cards for the current user."""
		# Get Stripe customer record
		stripe_customer = await session.execute(
			select(StripeCustomer).where(StripeCustomer.user_id == current_user.id)
		)
		stripe_customer = stripe_customer.scalar_one_or_none()
		if not stripe_customer:
			return PaymentMethodListResponse(payment_methods=[])

		methods = self._list_stripe_payment_methods(stripe_customer.stripe_customer_id)
		return PaymentMethodListResponse(
			payment_methods=[
				PaymentMethodResponse(
					id=method.id,
					type=method.type,
					billing_details=method.billing_details,
				)
				for method in methods
			]
		)

	async def delete_saved_card(
		self, session: AsyncSession, current_user: User, payment_method_id: str
	) -> dict:
		"""Delete a saved payment method after verifying ownership."""
		# Ensure user has a Stripe customer record (proxy for ownership)
		stripe_customer = await session.execute(
			select(StripeCustomer).where(StripeCustomer.user_id == current_user.id)
		)
		if not stripe_customer.scalar_one_or_none():
			raise HTTPException(status_code=404, detail='No saved payment methods')

		result = self._delete_stripe_payment_method(payment_method_id)
		return {'message': 'Payment method deleted', 'result': result}
