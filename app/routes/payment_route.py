from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Role, User
from app.security import get_current_user, RoleChecker
from app.services.payment_service import PaymentService

router = APIRouter(prefix='/api/v1/users', tags=['users'])

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
role_checker = Depends(RoleChecker([Role.ADMIN]))
payment_service = PaymentService()


# provisório
@router.post('/create-checkout-session', dependencies=[role_checker])
async def create_checkout_session(
    current_user: CurrentUser,
    amount: int,
    currency: str = "brl",
    customer_id: str = "",
):
    payment_intent_client_secret, payment_intent_id = payment_service.create_payment_intent(
        amount=amount,
        currency=currency,
        customer_id=customer_id
    )

    return {
        "client_secret": payment_intent_client_secret,
        "id": payment_intent_id
    }