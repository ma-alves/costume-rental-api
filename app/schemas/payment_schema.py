from typing import List, Optional

from pydantic import BaseModel


class IntentCreateRequest(BaseModel):
	rental_id: int
	save_card: bool = True


class PaymentIntentResponse(BaseModel):
	client_secret: str
	payment_intent_id: str
	amount: int
	currency: str


class PaymentCaptureRequest(BaseModel):
	payment_intent_id: str


class PaymentCaptureResponse(BaseModel):
	payment_intent_id: str
	status: str


class PaymentRefundRequest(BaseModel):
	payment_intent_id: str
	amount: Optional[int] = None


class PaymentRefundResponse(BaseModel):
	refund_id: str
	status: str
	amount: int


class PaymentRetrieveResponse(BaseModel):
	id: str
	status: str
	amount: int
	currency: str
	client_secret: str


class StripeCustomerResponse(BaseModel):
	stripe_customer_id: str
	user_id: int


class PaymentMethodResponse(BaseModel):
	id: str
	type: str
	billing_details: dict


class PaymentMethodListResponse(BaseModel):
	payment_methods: List[PaymentMethodResponse]
