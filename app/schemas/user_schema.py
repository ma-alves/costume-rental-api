from typing import List

from pydantic import BaseModel, EmailStr

from ..models import Role


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
