from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Role, User
from app.schemas.auth_schema import Token
from app.security import (
	RoleChecker,
	create_access_token,
	get_current_user,
	verify_password_hash,
)

router = APIRouter(prefix='/api/v1/auth', tags=['auth'])

Session = Annotated[AsyncSession, Depends(get_session)]
OAuth2Password = Annotated[OAuth2PasswordRequestForm, Depends()]
role_checker = Depends(RoleChecker([Role.ADMIN]))


@router.post('/token', response_model=Token)
async def login_for_access_token(form_data: OAuth2Password, session: Session):
	user = await session.scalar(select(User).where(User.email == form_data.username))

	if not user:
		raise HTTPException(404, detail='User not registered.')

	if not verify_password_hash(form_data.password, user.passwordHash):
		raise HTTPException(400, detail='Incorrect email or password.')

	access_token = create_access_token(data={'sub': user.email})

	return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/refresh_token', response_model=Token, dependencies=[role_checker])
def refresh_access_token(user: User = Depends(get_current_user)):
	new_access_token = create_access_token(data={'sub': user.email})

	return {'access_token': new_access_token, 'token_type': 'bearer'}
