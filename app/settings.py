from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

	DATABASE_URL: str
	SECRET_KEY: str
	ALGORITHM: str
	ACCESS_TOKEN_EXPIRE_DAYS: int
	LOG_LEVEL: str = 'INFO'
	STRIPE_SECRET_KEY: str
	STRIPE_PUBLISHABLE_KEY: str
	STRIPE_WEBHOOK_SECRET: str
	RESEND_API_KEY: str
	EMAIL_FROM: str
