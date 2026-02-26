# Costume Rental API
It is a RESTful API for a costume rental service using Python, FastAPI and PostgreSQL as its core technologies, as well as JWT for authentication and Pytest for testing.

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
**POST /api/v1/auth/token** : Login for access token \
**POST /api/v1/auto/refresh_token** : Refresh access token

### Users
**GET /api/v1/users/** : Read users \
**POST /api/v1/users/** : Create user \
**GET /api/v1/users/{user_id}** : Read user \
**PUT /api/v1/users/{user_id}** : Update user \
**DELETE /api/v1/users/{user_id}** : Delete user 

### Costumes
**GET /api/v1/costumes/** : Get costumes \
**POST /api/v1/costumes/** : Create costume \
**GET /api/v1/costumes/{costume_id}** : Get costume \
**GET /api/v1/costumes/{costume_id}** : Update costume \
**DELETE /api/v1/costumes/{costume_id}** : Delete costume

### Customers
**GET /api/v1/customers/** Get Customers \
**POST /api/v1/customers/** Create Customer \
**GET /api/v1/customers/{customer_id}** Get Customer \
**PUT /api/v1/customers/{customer_id}** Update Customer \
**DELETE /api/v1/customers/{customer_id}** Delete Customer

### Rental
**GET /api/v1/rental/** : Read Rental List \
**POST /api/v1/rental/** : Create Rental \
**GET /api/v1/rental/{rental_id}** : Read Rental \
**PATCH /api/v1/rental/{rental_id}** : Patch Rental [broken] \
**DELETE /api/v1/rental/{rental_id}** : Delete Rental

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