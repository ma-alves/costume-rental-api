from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User
from app.security import get_current_user
from app.services.payment_service import PaymentService
from app.schemas.payment_schema import (
	IntentCreateRequest,
	PaymentIntentResponse,
	PaymentCaptureRequest,
	PaymentCaptureResponse,
	PaymentRefundRequest,
	PaymentRefundResponse,
	PaymentRetrieveResponse,
	StripeCustomerResponse,
	PaymentMethodListResponse,
)

router = APIRouter(prefix='/api/v1/payments', tags=['payments'])

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
payment_service = PaymentService()


@router.post('/create-payment-intent', response_model=PaymentIntentResponse)
async def create_payment_intent(
	current_user: CurrentUser,
	request: IntentCreateRequest,
	session: Session,
):
	return await payment_service.create_payment_intent(session, current_user, request)


@router.get(
	'/payment-intent/{payment_intent_id}', response_model=PaymentRetrieveResponse
)
async def retrieve_payment_intent(
	current_user: CurrentUser,
	payment_intent_id: str,
	session: Session,
):
	return await payment_service.retrieve_payment_intent(
		session, current_user, payment_intent_id
	)


@router.post('/capture', response_model=PaymentCaptureResponse)
async def capture_payment(
	current_user: CurrentUser,
	request: PaymentCaptureRequest,
	session: Session,
):
	return await payment_service.capture_payment(session, current_user, request)


@router.post('/refund', response_model=PaymentRefundResponse)
async def refund_payment(
	current_user: CurrentUser,
	request: PaymentRefundRequest,
	session: Session,
):
	return await payment_service.refund_payment(session, current_user, request)


@router.post('/create-customer', response_model=StripeCustomerResponse)
async def create_customer(
	current_user: CurrentUser,
	session: Session,
):
	return await payment_service.create_customer(session, current_user)


@router.get('/saved-cards', response_model=PaymentMethodListResponse)
async def list_saved_cards(
	current_user: CurrentUser,
	session: Session,
):
	return await payment_service.list_saved_cards(session, current_user)


@router.delete('/saved-cards/{payment_method_id}')
async def delete_saved_card(
	current_user: CurrentUser,
	payment_method_id: str,
	session: Session,
):
	return await payment_service.delete_saved_card(
		session, current_user, payment_method_id
	)
