import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import RedirectResponse

from .config.setup_logging import setup_logging
from .routes import auth_route, costume_route, rental_route, user_route, payment_route, webhook_route
from .auth_schema import Message

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
	setup_logging()
	yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
	logger.exception(f'Unhandled error: {exc}')
	return JSONResponse(status_code=500, content={'detail': 'Internal server error'})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
	logger.warning(f'HTTP {exc.status_code}: {exc.detail}')
	return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	logger.warning(f'Validation error: {exc.errors()}')
	return JSONResponse(status_code=422, content={'detail': exc.errors()})


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
app.include_router(payment_route.router)
app.include_router(webhook_route.router)


@app.get('/')
async def root():
	return RedirectResponse(url='/api/v1')


@app.get('/api/v1', response_model=Message, status_code=200)
def index():
	return {'message': 'API Swagger: http://127.0.0.1:8000/docs.'}
