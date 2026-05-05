import datetime
from typing import Optional

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User,
    Costume,
    Rental,
    Payment,
    StripeCustomer,
)
from app.security import get_password_hash


async def create_user(
    session: AsyncSession,
    name: str = 'Test User',
    email: str = 'test@example.com',
    password: str = 'test1234',
    phone: str = '12345678901',
    cpf: str = '12345678901',
    address: str = 'Test Address',
    role: str = 'CUSTOMER',
) -> User:
    """Create and persist a User instance for tests."""
    user = User(
        name=name,
        email=email,
        passwordHash=get_password_hash(password),
        phone=phone,
        cpf=cpf,
        address=address,
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_costume(
    session: AsyncSession,
    name: str = 'Test Costume',
    description: str = 'A test costume',
    fee: float = 100.0,
    availability: str = 'AVAILABLE',
) -> Costume:
    """Create and persist a Costume instance for tests."""
    costume = Costume(
        name=name,
        description=description,
        fee=fee,
        availability=availability,
    )
    session.add(costume)
    await session.commit()
    await session.refresh(costume)
    return costume


async def create_rental(
    session: AsyncSession,
    user_id: int,
    costume_id: int,
    rent_days: int = 7,
) -> Rental:
    """Create and persist a Rental instance for tests."""
    now = datetime.datetime.now()
    rental = Rental(
        user_id=user_id,
        costume_id=costume_id,
        rental_date=now,
        return_date=now + datetime.timedelta(days=rent_days),
    )
    session.add(rental)
    await session.commit()
    await session.refresh(rental)
    return rental


async def create_payment(
    session: AsyncSession,
    rental_id: int,
    stripe_payment_intent_id: str = 'pi_123456789',
    amount: int = 10000,
    status: str = 'PENDING',
    currency: str = 'brl',
) -> Payment:
    """Create and persist a Payment instance for tests."""
    payment = Payment(
        rental_id=rental_id,
        stripe_payment_intent_id=stripe_payment_intent_id,
        amount=amount,
        status=status,
        currency=currency,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def create_stripe_customer(
    session: AsyncSession,
    user_id: int,
    stripe_customer_id: str = 'cus_123456789',
) -> StripeCustomer:
    """Create and persist a StripeCustomer instance for tests."""
    customer = StripeCustomer(
        user_id=user_id,
        stripe_customer_id=stripe_customer_id,
    )
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer
