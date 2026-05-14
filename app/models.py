from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import (
	Mapped,
	mapped_as_dataclass,
	mapped_column,
	registry,
	relationship,
)

table_registry = registry()


class CostumeAvailability(str, Enum):
	AVAILABLE = 'available'
	UNAVAILABLE = 'unavailable'
	UNRETURNED = 'unreturned'


class Role(str, Enum):
	ADMIN = 'admin'
	CUSTOMER = 'customer'


class PaymentStatus(str, Enum):
	PENDING = 'pending'
	SUCCEEDED = 'succeeded'
	CAPTURED = 'captured'
	FAILED = 'failed'
	REFUNDED = 'refunded'


@mapped_as_dataclass(table_registry)
class Costume:
	__tablename__ = 'costumes'

	id: Mapped[int] = mapped_column(primary_key=True, init=False)
	name: Mapped[str]
	description: Mapped[str]
	fee: Mapped[float]
	availability: Mapped[CostumeAvailability]

	rental: Mapped[List['Rental']] = relationship(back_populates='costumes', init=False)


@mapped_as_dataclass(table_registry)
class User:
	__tablename__ = 'users'

	id: Mapped[int] = mapped_column(primary_key=True, init=False)
	name: Mapped[str]
	cpf: Mapped[str] = mapped_column(String(11))
	email: Mapped[str]
	passwordHash: Mapped[str]
	address: Mapped[str]
	phone: Mapped[Optional[str]] = mapped_column(String(11))
	role: Mapped[Role] = mapped_column(String(10), default=Role.CUSTOMER)
	created_at: Mapped[datetime] = mapped_column(default=datetime.now())

	rental: Mapped[List['Rental']] = relationship(back_populates='users', init=False)

	@property
	def is_admin(self) -> bool:
		return self.role == Role.ADMIN


@mapped_as_dataclass(table_registry)
class Rental:
	__tablename__ = 'rental'

	id: Mapped[int] = mapped_column(primary_key=True, init=False)
	user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
	costume_id: Mapped[int] = mapped_column(ForeignKey('costumes.id'))

	users: Mapped['User'] = relationship(back_populates='rental', init=False)
	costumes: Mapped['Costume'] = relationship(back_populates='rental', init=False)
	payment: Mapped[Optional['Payment']] = relationship(
		back_populates='rental', init=False, uselist=False
	)

	rental_date: Mapped[datetime] = mapped_column(default=datetime.now())
	return_date: Mapped[datetime] = mapped_column(
		default=datetime.now() + timedelta(days=7)
	)
	actual_return_date: Mapped[Optional[datetime]] = mapped_column(default=None)
	payment_status: Mapped[PaymentStatus] = mapped_column(
		String(20), default=PaymentStatus.PENDING
	)
	payment_amount: Mapped[int] = mapped_column(default=0)


@mapped_as_dataclass(table_registry)
class StripeCustomer:
	__tablename__ = 'stripe_customers'

	id: Mapped[int] = mapped_column(primary_key=True, init=False)
	user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True)
	stripe_customer_id: Mapped[str] = mapped_column(unique=True)
	created_at: Mapped[datetime] = mapped_column(default=datetime.now())

	user: Mapped['User'] = relationship(init=False)


@mapped_as_dataclass(table_registry)
class Payment:
	__tablename__ = 'payments'

	id: Mapped[int] = mapped_column(primary_key=True, init=False)
	rental_id: Mapped[int] = mapped_column(ForeignKey('rental.id'), unique=True)
	stripe_payment_intent_id: Mapped[str] = mapped_column(unique=True)
	amount: Mapped[int]
	status: Mapped[PaymentStatus] = mapped_column(String(20))
	currency: Mapped[str] = mapped_column(default='brl')
	refunded_amount: Mapped[int] = mapped_column(default=0)
	created_at: Mapped[datetime] = mapped_column(default=datetime.now())
	updated_at: Mapped[datetime] = mapped_column(
		default=datetime.now(), onupdate=datetime.now()
	)

	rental: Mapped['Rental'] = relationship(
		back_populates='payment', init=False, uselist=False
	)
