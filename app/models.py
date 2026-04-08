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
	role: Mapped[Role]
	created_at: Mapped[datetime] = mapped_column(default=datetime.now())

	rental: Mapped[List['Rental']] = relationship(back_populates='users', init=False)


@mapped_as_dataclass(table_registry)
class Rental:
	__tablename__ = 'rental'

	id: Mapped[int] = mapped_column(primary_key=True, init=False)
	user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
	costume_id: Mapped[int] = mapped_column(ForeignKey('costumes.id'))

	users: Mapped['User'] = relationship(back_populates='rental', init=False)
	costumes: Mapped['Costume'] = relationship(back_populates='rental', init=False)

	rental_date: Mapped[datetime] = mapped_column(default=datetime.now())
	return_date: Mapped[datetime] = mapped_column(
		default=datetime.now() + timedelta(days=7)
	)
