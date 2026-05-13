from datetime import datetime, timedelta
from typing import List

from pydantic import BaseModel

from schemas.costume_schema import CostumeOutput
from schemas.user_schema import UserOutput

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
