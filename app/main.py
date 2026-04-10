from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import auth_route, costume_route, rental_route, user_route
from .schemas import Message

app = FastAPI()

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


@app.get('/api/v1', response_model=Message, status_code=200)
def index():
	return {'message': 'API Swagger: http://127.0.0.1:8000/docs.'}
