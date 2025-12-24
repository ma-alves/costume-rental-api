from .schemas import Message
from .routes import employees, auth, costumes, customers, rental

from fastapi import FastAPI


app = FastAPI()

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(costumes.router)
app.include_router(customers.router)
app.include_router(rental.router)


@app.get('/', response_model=Message, status_code=200)
def index():
	return {'message': 'Go to http://127.0.0.1:8000/docs to access the endpoints.'}
