from pydantic import BaseModel, EmailStr


class Message(BaseModel):
	message: str


class Token(BaseModel):
	access_token: str
	token_type: str


class TokenData(BaseModel):
	email: EmailStr | None = None
