from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from psycopg import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User
from app.schemas import (
	Message,
	UserInput,
	UserList,
	UserOutput,
)
from app.security import get_current_user, get_password_hash

router = APIRouter(prefix='/users', tags=['users'])

CurrentUser = Annotated[User, Depends(get_current_user)]
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get('/', response_model=UserList)
async def read_users(session: Session, skip: int = 0, limit: int = 100):
	users_scalar = await session.scalars(select(User).offset(skip).limit(limit))

	users = users_scalar.all()

	return {'users': users}


@router.get('/{user_id}', response_model=UserOutput, status_code=200)
async def read_user(session: Session, user_id: int):
	user = await session.scalar(select(User).where(User.id == user_id))

	if not user:
		raise HTTPException(404, detail='User not registered.')

	return user


@router.post('/', response_model=UserOutput, status_code=201)
async def create_user(user: UserInput, session: Session):
	"""
	Open endpoint so anyone can test the API's permissions.
	"""
	db_user = await session.scalar(select(User).where(User.email == user.email))
	if db_user:
		raise HTTPException(400, detail='User already registered.')

	hashed_password = get_password_hash(user.password)

	db_user = User(
		name=user.name,
		email=user.email,
		password=hashed_password,
		phone_number=user.phone_number,
		is_admin=user.is_admin,
	)

	session.add(db_user)
	await session.commit()
	await session.refresh(db_user)

	return db_user


@router.put('/{user_id}', response_model=UserOutput)
async def update_user(
	current_user: CurrentUser,
	session: Session,
	user: UserInput,
	user_id: int,
):
	if current_user.id != user_id or not current_user.is_admin:
		raise HTTPException(status_code=400, detail='Not enough permissions')

	db_user = await session.scalar(select(User).where(User.id == user_id))

	if not db_user:
		raise HTTPException(404, detail='User not registered.')

	try:
		db_user.name = user.name
		db_user.password = get_password_hash(user.password)
		db_user.email = user.email
		db_user.phone_number = user.phone_number
		db_user.is_admin = False if not current_user.is_admin else user.is_admin

		await session.commit()
		await session.refresh(db_user)

		return db_user

	except IntegrityError:
		raise HTTPException(
			status_code=HTTPStatus.CONFLICT,
			detail='Username or Email already exists.',
		)


@router.delete('/{user_id}', response_model=Message)
async def delete_user(
	current_user: CurrentUser,
	session: Session,
	user_id: int,
):
	if current_user.id != user_id or not current_user.is_admin:
		raise HTTPException(status_code=400, detail='Not enough permissions')

	db_user = await session.scalar(select(User).where(User.id == user_id))

	if not db_user:
		raise HTTPException(404, detail='User not registered.')

	await session.delete(db_user)
	await session.commit()

	return {'message': 'User deleted.'}
