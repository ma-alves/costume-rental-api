from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter.middleware import RateLimiterMiddleware
from pyrate_limiter import Duration, Limiter, Rate

from .routes import auth_route, costume_route, customers, rental_route, user_route
from .schemas import Message

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# biblioteca quebrada v0.2.0: middleware.py não instalado
# aguardando aprovação do PR que corrige issue #78
app.add_middleware(
	RateLimiterMiddleware,
	limiter=Limiter(Rate(100, Duration.MINUTE * 1)),
)

app.include_router(auth_route.router)
app.include_router(user_route.router)
app.include_router(costume_route.router)
app.include_router(customers.router)
app.include_router(rental_route.router)


@app.get('/api/v1', response_model=Message, status_code=200)
def index():
	return {'message': 'API Swagger: http://127.0.0.1:8000/docs.'}
