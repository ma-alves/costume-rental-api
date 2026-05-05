from datetime import datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, EmailStr

from .models import CostumeAvailability, Role, PaymentStatus


class Message(BaseModel):
	message: str


# Tokens
class Token(BaseModel):
	access_token: str
	token_type: str


class TokenData(BaseModel):
	email: EmailStr | None = None


# Users
class UserInput(BaseModel):
	name: str
	password: str
	email: EmailStr
	phone: str
	cpf: str = ''
	address: str = ''
	role: Role = Role.CUSTOMER


class UserOutput(BaseModel):
	id: int
	name: str
	email: EmailStr
	phone: str
	role: Role = Role.CUSTOMER

	class Config:
		from_attributes = True


class UserList(BaseModel):
	users: List[UserOutput]


# Costumes
class CostumeInput(BaseModel):
	name: str
	description: str
	fee: float
	availability: CostumeAvailability


class CostumeOutput(BaseModel):
	id: int
	name: str
	description: str
	fee: float
	availability: CostumeAvailability


class CostumeList(BaseModel):
	costumes: List[CostumeOutput]


# Rental
class RentalSchema(BaseModel):
	rental_date: datetime
	return_date: datetime
	costume: CostumeOutput
	user: UserOutput


class RentalList(BaseModel):
	rental_list: List[RentalSchema]


class RentalInput(BaseModel):
	costume_id: int
	customer_id: int


class RentalPatch(BaseModel):
	rental_date: datetime | None = datetime.now()
	return_date: datetime | None = datetime.now() + timedelta(days=7)


# Payments
class PaymentCreateRequest(BaseModel):
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
