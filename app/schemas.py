from datetime import datetime, timedelta
from typing import List

from pydantic import BaseModel, EmailStr

from .models import CostumeAvailability


class Message(BaseModel):
	message: str


# Tokens
class Token(BaseModel):
	access_token: str
	token_type: str


class TokenData(BaseModel):
	email: EmailStr | None = None


# Employees
class EmployeeInput(BaseModel):
	name: str
	password: str
	email: EmailStr
	phone_number: str
	is_admin: bool = False


class EmployeeOutput(BaseModel):
	id: int
	name: str
	email: EmailStr
	phone_number: str
	is_admin: bool


class EmployeeList(BaseModel):
	employees: List[EmployeeOutput]


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


# Customers
class CustomerSchema(BaseModel):
	cpf: str
	name: str
	email: str
	phone_number: str
	address: str


class CustomerList(BaseModel):
	customers: List[CustomerSchema]


# Rental
class RentalSchema(BaseModel):
	rental_date: datetime
	return_date: datetime
	costume: CostumeOutput
	customer: CustomerSchema
	employee: EmployeeOutput


class RentalList(BaseModel):
	rental_list: List[RentalSchema]


class RentalInput(BaseModel):
	costume_id: int
	customer_id: int


class RentalPatch(BaseModel):
	rental_date: datetime | None = datetime.now()
	return_date: datetime | None = datetime.now() + timedelta(days=7)
