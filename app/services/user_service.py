from typing import Optional

from fastapi import HTTPException
from psycopg import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.setup_logging import get_logger
from app.models import Role, User
from app.schemas import UserInput
from app.security import get_password_hash

logger = get_logger(__name__)


class UserService:
	async def get_all(self, session: AsyncSession, skip: int = 0, limit: int = 100):
		users_scalar = await session.scalars(select(User).offset(skip).limit(limit))
		users = users_scalar.all()
		logger.info('Users retrieved', extra={'count': len(users)})
		return users

	async def get_by_id(self, session: AsyncSession, user_id: int) -> User:
		user = await session.scalar(select(User).where(User.id == user_id))
		if not user:
			logger.error('User not found', extra={'user_id': user_id})
			raise HTTPException(404, detail='User not registered.')
		logger.info('User retrieved', extra={'user_id': user_id})
		return user

	async def get_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
		user = await session.scalar(select(User).where(User.email == email))
		if not user:
			logger.error('User not found by email', extra={'email': email})
			raise HTTPException(404, detail='User not registered.')
		logger.info(
			'User retrieved by email', extra={'user_id': user.id, 'email': email}
		)
		return user

	async def create(self, session: AsyncSession, user_data: UserInput) -> User:
		existing = await self.get_by_email(session, user_data.email)
		if existing:
			logger.error(
				'User already registered',
				extra={'user_id': existing.id, 'email': user_data.email},
			)
			raise HTTPException(400, detail='User already registered.')

		hashed_password = get_password_hash(user_data.password)
		role = Role.CUSTOMER

		db_user = User(
			name=user_data.name,
			email=user_data.email,
			passwordHash=hashed_password,
			phone=user_data.phone_number,
			role=role,
			cpf='',
			address='',
		)

		session.add(db_user)
		await session.commit()
		await session.refresh(db_user)
		logger.info(
			'User created',
			extra={'user_id': db_user.id, 'email': db_user.email, 'role': db_user.role},
		)
		return db_user

	async def update(
		self,
		session: AsyncSession,
		user_id: int,
		user_data: UserInput,
		current_user: User,
	) -> User:
		if current_user.role != Role.ADMIN or current_user.id != user_id:
			logger.error(
				'Permission denied for user update',
				extra={
					'user_id': user_id,
					'current_user_id': current_user.id,
					'current_user_role': current_user.role,
				},
			)
			raise HTTPException(status_code=403, detail='Not enough permissions')

		db_user = await self.get_by_id(session, user_id)

		try:
			db_user.name = user_data.name
			db_user.passwordHash = get_password_hash(user_data.password)
			db_user.email = user_data.email
			db_user.phone = user_data.phone_number
			db_user.role = (
				Role.CUSTOMER if not current_user.role == Role.ADMIN else user_data.role
			)

			await session.commit()
			await session.refresh(db_user)
			logger.info(
				'User updated',
				extra={'user_id': db_user.id, 'email': db_user.email},
			)
			return db_user
		except IntegrityError:
			await session.rollback()
			logger.error(
				'User update failed - duplicate',
				extra={'user_id': user_id, 'email': user_data.email},
			)
			raise HTTPException(
				status_code=409,
				detail='Username or Email already exists.',
			)

	async def delete(
		self, session: AsyncSession, user_id: int, current_user: User
	) -> None:
		if current_user.role != Role.ADMIN or current_user.id != user_id:
			logger.error(
				'Permission denied for user deletion',
				extra={
					'user_id': user_id,
					'current_user_id': current_user.id,
					'current_user_role': current_user.role,
				},
			)
			raise HTTPException(status_code=403, detail='Not enough permissions')

		db_user = await self.get_by_id(session, user_id)

		await session.delete(db_user)
		await session.commit()
		logger.info('User deleted', extra={'user_id': user_id})
