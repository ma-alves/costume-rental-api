from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, mapped_as_dataclass, registry


table_registry = registry()

class CostumeAvailability(str, Enum):
	AVAILABLE = 'available'
	UNAVAILABLE = 'unavailable'


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
class Customer:
	__tablename__ = 'customers'

	id: Mapped[int] = mapped_column(primary_key=True, init=False)
	cpf: Mapped[str] = mapped_column(String(11))
	name: Mapped[str]
	email: Mapped[str]
	phone_number: Mapped[str] = mapped_column(String(11))
	address: Mapped[str]

	rental: Mapped[List['Rental']] = relationship(back_populates='customers', init=False)


@mapped_as_dataclass(table_registry)
class Employee:
	__tablename__ = 'employees'

	id: Mapped[int] = mapped_column(primary_key=True, init=False)
	name: Mapped[str]
	email: Mapped[str]
	password: Mapped[str]
	phone_number: Mapped[Optional[str]] = mapped_column(String(11))
	is_admin: Mapped[bool]

	rental: Mapped[List['Rental']] = relationship(back_populates='employees', init=False)


@mapped_as_dataclass(table_registry)
class Rental:
	"""
	Neste formato o cliente não tem relação direta com o funcionário,
	apenas com o aluguel, que pelo seu registro liga o cliente ao
	funcionário indiretamente. Essa relação também ocorre da mesma
	forma com a fantasia, tendo a tabela 'Rental' como centro.
	"""

	__tablename__ = 'rental'

	id: Mapped[int] = mapped_column(primary_key=True, init=False)
	employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'))
	customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'))
	costume_id: Mapped[int] = mapped_column(ForeignKey('costumes.id'))

	employees: Mapped['Employee'] = relationship(back_populates='rental', init=False)
	customers: Mapped['Customer'] = relationship(back_populates='rental', init=False)
	costumes: Mapped['Costume'] = relationship(back_populates='rental', init=False)

	rental_date: Mapped[datetime] = mapped_column(default=datetime.now())
	return_date: Mapped[datetime] = mapped_column(
		default=datetime.now() + timedelta(days=7)
	)