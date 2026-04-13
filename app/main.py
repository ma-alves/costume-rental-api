from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from .config.setup_logging import (
	get_logger,
	set_request_id,
	setup_logging,
)
from .routes import auth_route, costume_route, rental_route, user_route
from .schemas import Message
from .settings import Settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
	settings = Settings()
	log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
	setup_logging(level=log_level)
	yield


app = FastAPI(lifespan=lifespan)


@app.middleware('http')
async def log_request_middleware(request: Request, call_next):
	set_request_id()
	start_time = time.time()

	logger.info(
		'Request started',
		extra={'method': request.method, 'path': request.url.path},
	)

	response = await call_next(request)

	duration = time.time() - start_time
	logger.info(
		'Request completed',
		extra={
			'method': request.method,
			'path': request.url.path,
			'status_code': response.status_code,
			'duration_ms': round(duration * 1000, 2),
		},
	)

	return response


origins = ['*']

app.add_middleware(
	CORSMiddleware,
	allow_origins=origins,
	allow_credentials=True,
	allow_methods=['*'],
	allow_headers=['*'],
)

app.include_router(auth_route.router)
app.include_router(user_route.router)
app.include_router(costume_route.router)
app.include_router(rental_route.router)


@app.get('/')
async def root():
	return RedirectResponse(url='/api/v1')


@app.get('/api/v1', response_model=Message, status_code=200)
def index():
	return {'message': 'API Swagger: http://127.0.0.1:8000/docs.'}
