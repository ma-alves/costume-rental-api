from datetime import datetime, timedelta
from typing import List, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import decode, encode
from jwt.exceptions import DecodeError, ExpiredSignatureError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session
from .models import User
from .schemas import TokenData
from .settings import Settings

settings = Settings()
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/token')
credentials_exception = HTTPException(
	status_code=status.HTTP_401_UNAUTHORIZED,
	detail='Could not validate credentials',
	headers={'WWW-Authenticate': 'Bearer'},
)

def get_password_hash(password: str):
	return pwd_context.hash(password)


def verify_password_hash(plain_password: str, hashed_password: str):
	return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
	to_encode = data.copy()
	expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
	to_encode.update({'exp': expire})
	encoded_jwt = encode(
		payload=to_encode,
		key=settings.SECRET_KEY,
		algorithm=settings.ALGORITHM,
	)

	return encoded_jwt


async def get_current_user(
	session: AsyncSession = Depends(get_session),
	token: str = Depends(oauth2_scheme),
):

	try:
		payload = decode(
			jwt=token, key=settings.SECRET_KEY, algorithms=settings.ALGORITHM
		)
		email = payload.get('sub')
		if not email:
			raise credentials_exception
		token_data = TokenData(email=email)
	except DecodeError:
		raise credentials_exception
	except ExpiredSignatureError:
		raise credentials_exception

	user = await session.scalar(select(User).where(User.email == token_data.email))

	if user is None:
		raise credentials_exception

	return user


class RoleChecker:
    def __init__(self, allowed_roles: List[str]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> Any:
        if current_user.role in self.allowed_roles:
            return True

        raise credentials_exception
