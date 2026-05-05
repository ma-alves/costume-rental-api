import uuid
from fastapi import HTTPException
from typing import Any, Optional, Tuple
from stripe import StripeClient, StripeError

from app.settings import Settings
from app.models import PaymentStatus


class PaymentService:
	def __init__(self):
		self.client = StripeClient(Settings().STRIPE_SECRET_KEY)

	def _generate_idempotency_key(self, resource_type: str, resource_id: str) -> str:
		"""Generate a consistent idempotency key for payment operations."""
		return f'{resource_type}:{resource_id}:{uuid.uuid4()}'

	def create_customer(self, email: str, name: str) -> str:
		"""Create a Stripe customer for saving cards."""
		try:
			customer = self.client.v1.Customer.create(
				email=email,
				name=name,
			)
		except StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))

		return customer.id

    # alterar return para dict
	def create_payment_intent(
		self,
		amount: int,
		currency: str = 'brl',
		customer_id: Optional[str] = None,
		rental_id: Optional[int] = None,
		metadata: Optional[dict] = None,
	) -> Tuple[str, str | None]:
		"""Create a payment intent for a rental with card saving enabled."""
		try:
			params = {
				'amount': amount,  # in cents, e.g. 5000 = R$50.00
				'currency': currency,
				'payment_method_types': ['card'],
				'capture_method': 'manual',
				'setup_future_usage': 'off_session',  # Always save card
				'metadata': metadata or {},
			}

			if customer_id:
				params['customer'] = customer_id

			if rental_id:
				if 'metadata' not in params:
					params['metadata'] = {}
				params['metadata']['rental_id'] = str(rental_id)

			idempotency_key = self._generate_idempotency_key(
				'payment_intent', f'{customer_id}_{rental_id}'
			)

			payment_intent = self.client.v1.PaymentIntent.create(
				**params,
				idempotency_key=idempotency_key,
			)

		except StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))

		return payment_intent.client_secret, payment_intent.id

	def retrieve_payment_intent(self, payment_intent_id: str) -> dict:
		"""Retrieve payment intent details."""
		try:
			payment_intent = self.client.v1.PaymentIntent.retrieve(payment_intent_id)
		except StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))

		return {
			'id': payment_intent.id,
			'status': payment_intent.status,
			'amount': payment_intent.amount,
			'currency': payment_intent.currency,
			'client_secret': payment_intent.client_secret,
			'charges': payment_intent.charges.data,
		}

	def confirm_payment_intent(
		self, payment_intent_id: str, payment_method: str
	) -> Tuple[str, str]:
		"""Confirm a payment intent with a payment method (usually called from frontend)."""
		try:
			payment_intent = self.client.v1.PaymentIntent.confirm(
				payment_intent_id,
				payment_method=payment_method,
			)
		except StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))

		return payment_intent.id, payment_intent.status

	def capture_payment_intent(self, payment_intent_id: str) -> Tuple[str, str]:
		"""Capture an authorized payment intent (move from pending to succeeded)."""
		try:
			payment_intent = self.client.v1.PaymentIntent.modify(
				payment_intent_id,
				idempotency_key=self._generate_idempotency_key(
					'capture', payment_intent_id
				),
			)

			# Stripe auto-captures if no manual capture is set, but ensure it's captured
			if payment_intent.status != 'succeeded':
				# Actually capture the payment
				charges = payment_intent.charges.data
				if charges:
					first_charge = charges[0]
					if not first_charge.captured:
						self.client.v1.Charge.retrieve(first_charge.id).capture()

		except StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))

		return payment_intent.id, payment_intent.status

	def cancel_payment_intent(self, payment_intent_id: str) -> Tuple[str, str]:
		"""Cancel an authorized payment intent (move to canceled status)."""
		try:
			payment_intent = self.client.v1.PaymentIntent.cancel(payment_intent_id)
		except StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))

		return payment_intent.id, payment_intent.status

	def refund(
		self, payment_intent_id: str, amount: Optional[int] = None
	) -> Tuple[str, str, int]:
		"""Create a refund for a payment (full or partial)."""
		try:
			params: dict[str, Any] = {
				'payment_intent': payment_intent_id,
				'idempotency_key': self._generate_idempotency_key(
					'refund', payment_intent_id
				),
			}

			if amount:
				params['amount'] = amount  # partial refund if provided

			refund = self.client.v1.Refund.create(**params)

		except StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))

		return refund.id, refund.status, refund.amount

	def list_customer_payment_methods(self, customer_id: str) -> list:
		"""List all saved payment methods for a customer."""
		try:
			payment_methods = self.client.v1.PaymentMethod.list(
				customer=customer_id, type='card'
			)
		except StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))

		return payment_methods.data

	def delete_payment_method(self, payment_method_id: str) -> dict:
		"""Delete a saved payment method."""
		try:
			payment_method = self.client.v1.PaymentMethod.detach(payment_method_id)
		except StripeError as e:
			raise HTTPException(status_code=500, detail=str(e))

		return {'id': payment_method.id, 'status': payment_method.status}

	def get_payment_status_enum(self, stripe_status: str) -> PaymentStatus:
		"""Convert Stripe payment status to our PaymentStatus enum."""
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
