# Costume Rental API
A RESTful API for a costume rental service using FastAPI as its core technology, as well as JWT for authentication, Pytest for testing and a fastapi-limiter to prevent abuse.

## Tech Stack
- [FastAPI](https://fastapi.tiangolo.com/) - Web Framework
- [PostgreSQL](https://www.postgresql.org) - SQL Database
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL Toolkit and ORM
- [Docker Compose](https://docs.docker.com/compose/) - Environment Development
- [GitHub Actions](https://docs.github.com/en/actions) - CI/CD
- [Pytest](https://docs.pytest.org/en/8.2.x/) - Testing
- [PyJWT](https://pypi.org/project/PyJWT/) - Authentication
- [Alembic](https://alembic.sqlalchemy.org/en/latest/) - Migrating

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

## Examples
### List Costumes
- Request
```sh
curl -X 'GET' \
  'http://127.0.0.1:8000/api/v1/costumes/' \
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
  'http://127.0.0.1:8000/api/v1/rental/' \
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