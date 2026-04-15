from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from .routes import auth_route, costume_route, rental_route, user_route
from .schemas import Message


@asynccontextmanager
async def lifespan(app: FastAPI):
	yield


app = FastAPI(lifespan=lifespan)

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
