from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Role, User
from app.schemas import (
	Message,
	RentalInput,
	RentalList,
	# RentalPatch,
	RentalSchema,
)
from app.security import get_current_user, RoleChecker
from app.services.rental_service import RentalService

router = APIRouter(prefix='/api/v1/rental', tags=['rental'])

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
role_checker = Depends(RoleChecker([Role.ADMIN]))
rental_service = RentalService()


@router.get('/', response_model=RentalList, dependencies=role_checker)
async def read_rental_list(
	session: Session,
	current_user: CurrentUser,
	skip: int = 0,
	limit: int = 100,
):
	rentals = await rental_service.get_all(session, skip, limit)
	return {'rental_list': rentals}


@router.get('/{rental_id}', response_model=RentalSchema, dependencies=role_checker)
async def read_rental(session: Session, current_user: CurrentUser, rental_id: int):
	rental = await rental_service.get_by_id(session, rental_id)
	return rental


@router.post('/', response_model=RentalSchema, status_code=201)
async def create_rental(
	session: Session, current_user: CurrentUser, rental: RentalInput
):
	db_rental = await rental_service.create(session, rental, current_user)
	return db_rental


# @router.patch('/{rental_id}', response_model=RentalSchema)
# async def patch_rental(
# 	session: Session,
# 	current_user: CurrentUser,
# 	rental_id: int,
# 	rental: RentalPatch,
# ):
# 	db_rental = await rental_service.patch(session, rental_id, rental)
# 	return db_rental


@router.delete('/{rental_id}', response_model=Message)
async def delete_rental(session: Session, current_user: CurrentUser, rental_id: int):
	await rental_service.delete(session, rental_id)
	return {'message': 'Rental register has been deleted successfully.'}
