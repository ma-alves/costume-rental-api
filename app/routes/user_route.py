from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.setup_logging import get_logger, set_user_id
from app.database import get_session
from app.models import Role, User
from app.schemas import Message, UserInput, UserList, UserOutput
from app.security import get_current_user, RoleChecker
from app.services.user_service import UserService

logger = get_logger(__name__)

router = APIRouter(prefix='/api/v1/users', tags=['users'])

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
role_checker = Depends(RoleChecker([Role.ADMIN]))
user_service = UserService()


@router.get('/', response_model=UserList, dependencies=[role_checker])
async def read_users(
	session: Session,
	current_user: CurrentUser,
	skip: int = 0,
	limit: int = 100,
):
	set_user_id(current_user.id)
	users = await user_service.get_all(session, skip=skip, limit=limit)
	return {'users': users}


@router.get(
	'/{user_id}',
	response_model=UserOutput,
	status_code=200,
	dependencies=[role_checker],
)
async def read_user(session: Session, current_user: CurrentUser, user_id: int):
	set_user_id(current_user.id)
	user = await user_service.get_by_id(session, user_id)
	return user


@router.post('/', response_model=UserOutput, status_code=201)
async def create_user(session: Session, user: UserInput):
	db_user = await user_service.create(session, user)
	return db_user


@router.put('/{user_id}', response_model=UserOutput)
async def update_user(
	session: Session,
	current_user: CurrentUser,
	user: UserInput,
	user_id: int,
):
	set_user_id(current_user.id)
	db_user = await user_service.update(session, user_id, user, current_user)
	return db_user


@router.delete('/{user_id}', response_model=Message)
async def delete_user(
	session: Session,
	current_user: CurrentUser,
	user_id: int,
):
	set_user_id(current_user.id)
	await user_service.delete(session, user_id, current_user)
	return {'message': 'User deleted.'}
