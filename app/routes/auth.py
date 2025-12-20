from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Employee
from app.schemas import Token
from app.security import (
	create_access_token,
	get_current_employee,
	verify_password_hash,
)

OAuth2Password = Annotated[OAuth2PasswordRequestForm, Depends()]
Session = Annotated[AsyncSession, Depends(get_session)]
router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/token', response_model=Token)
async def login_for_access_token(form_data: OAuth2Password, session: Session):
	employee = await session.scalar(
		select(Employee).where(Employee.email == form_data.username)
	)

	if not employee:
		raise HTTPException(404, detail='Employee not registered.')

	if not verify_password_hash(form_data.password, employee.password):
		raise HTTPException(400, detail='Incorrect email or password.')

	access_token = create_access_token(data={'sub': employee.email})

	return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/refresh_token', response_model=Token)
def refresh_access_token(employee: Employee = Depends(get_current_employee)):
	new_access_token = create_access_token(data={'sub': employee.email})

	return {'access_token': new_access_token, 'token_type': 'bearer'}
