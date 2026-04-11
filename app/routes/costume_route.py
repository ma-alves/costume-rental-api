from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import CostumeAvailability, User, Role
from app.schemas import CostumeInput, CostumeList, CostumeOutput, Message
from app.security import get_current_user, RoleChecker
from app.services.costume_service import CostumeService

router = APIRouter(prefix='/api/v1/costumes', tags=['costumes'])

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
role_checker = Depends(RoleChecker([Role.ADMIN]))
costume_service = CostumeService()


@router.get('/', response_model=CostumeList)
async def get_costumes(
	session: Session,
	availability: CostumeAvailability = Query(None),
	skip: int = Query(None),
	limit: int = Query(None),
):
	costumes = await costume_service.get_all(session, skip, limit, availability)
	return {'costumes': costumes}


@router.get('/{costume_id}', response_model=CostumeOutput)
async def get_costume(session: Session, costume_id: int):
	costume = await costume_service.get_by_id(session, costume_id)
	return costume


@router.post(
	'/',
	response_model=CostumeOutput,
	status_code=HTTPStatus.CREATED,
	dependencies=role_checker,
)
async def create_costume(
	session: Session,
	current_user: CurrentUser,
	costume: CostumeInput,
):
	db_costume = await costume_service.create(session, costume)
	return db_costume


@router.put('/{costume_id}', response_model=CostumeOutput, dependencies=role_checker)
async def update_costume(
	session: Session,
	current_user: CurrentUser,
	costume: CostumeInput,
	costume_id: int,
):
	db_costume = await costume_service.update(session, costume_id, costume)
	return db_costume


@router.delete('/{costume_id}', response_model=Message, dependencies=role_checker)
async def delete_costume(
	current_user: CurrentUser,
	session: Session,
	costume_id: int,
):
	await costume_service.delete(session, costume_id)
	return {'message': 'Costume deleted.'}
