# Costume Rental API
It is a RESTful API for costume rental with JWT Authentication using Python, FastAPI and PostgreSQL as its core technologies.

## Tech Stack
- [FastAPI](https://fastapi.tiangolo.com/) - Web Framework
- [PostgreSQL](https://www.postgresql.org) - SQL Database
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL Toolkit and ORM
- [Docker Compose](https://docs.docker.com/compose/) - Environment Setup
- [GitHub Actions](https://docs.github.com/en/actions) - CI
- [Pytest](https://docs.pytest.org/en/8.2.x/) - Testing
- [PyJWT](https://pypi.org/project/PyJWT/) - Authentication
- [Alembic](https://alembic.sqlalchemy.org/en/latest/) - Migrations

## Getting Started
1. Clone the repository:
```sh
git clone https://github.com/ma-alves/costume-rental-api.git
```
2. Copy the environment variables to .env and change the values:
```sh
cp .env.example .env
```
3. Build and run the containers with Docker Compose:
```sh
docker compose up --build
```
4. The API Swagger will be available at http://localhost:8000/docs

## API Endpoints
### Auth
**POST /auth/token** : Login for access token \
**POST /auto/refresh_token** : Refresh access token

### Users
**GET /users/** : Read users \
**POST /users/** : Create user \
**GET /users/{user_id}** : Read user \
**PUT /users/{user_id}** : Update user \
**DELETE /users/{user_id}** : Delete user 

### Costumes
**GET /costumes/** : Get costumes \
**POST /costumes/** : Create costume \
**GET /costumes/{costume_id}** : Get costume \
**GET /costumes/{costume_id}** : Update costume \
**DELETE /costumes/{costume_id}** : Delete costume

### Customers
**GET /customers/** Get Customers \
**POST /customers/** Create Customer \
**GET /customers/{customer_id}** Get Customer \
**PUT /customers/{customer_id}** Update Customer \
**DELETE /customers/{customer_id}** Delete Customer

### Rental
**GET /rental/** : Read Rental List \
**POST /rental/** : Create Rental \
**GET /rental/{rental_id}** : Read Rental \
**PATCH /rental/{rental_id}** : Patch Rental [broken] \
**DELETE /rental/{rental_id}** : Delete Rental

## Examples
### List Costumes
- Request
```sh
curl -X 'GET' \
  'http://127.0.0.1:8000/costumes/' \
  -H 'accept: application/json'
```
- Successful Response
```json
{
  "costumes": [
    {
      "id": 0,
      "name": "string",
      "description": "string",
      "fee": 0,
      "availability": "available"
    }
  ]
}
```
### Create Rental
- Request
```sh
curl -X 'POST' \
  'http://127.0.0.1:8000/rental/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "costume_id": 0,
  "customer_id": 0
}'
```
- Successful Response
```json
{
  "rental_date": "2025-12-25T19:59:58.512Z",
  "return_date": "2025-12-25T19:59:58.512Z",
  "costume": {
    "id": 0,
    "name": "string",
    "description": "string",
    "fee": 0,
    "availability": "available"
  },
  "customer": {
    "cpf": "string",
    "name": "string",
    "email": "string",
    "phone_number": "string",
    "address": "string"
  },
  "user": {
    "id": 0,
    "name": "string",
    "email": "user@example.com",
    "phone_number": "string",
    "is_admin": true
  }
}
```