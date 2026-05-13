from typing import List

from pydantic import BaseModel

from ..models import CostumeAvailability


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
