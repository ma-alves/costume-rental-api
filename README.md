# Costume Rental API

*AI generated document reviewed and maintained by ma-alves.*

RESTful API for a costume rental service built with FastAPI. Follows a layered architecture: routes handle HTTP concerns, services encapsulate business logic, and SQLAlchemy models define the data layer. Authentication via JWT with role-based access (admin/customer). Integrates Stripe for payment processing using `StripeClient`, customers create and authorize payment intents with saved cards, while admins capture or refund payments. Webhooks receive async status updates from Stripe.

## Tech Stack
- [FastAPI](https://fastapi.tiangolo.com/) - Web Framework
- [PostgreSQL](https://www.postgresql.org) - SQL Database
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL Toolkit and ORM (async)
- [Stripe SDK](https://github.com/stripe/stripe-python) - Payment Processing
- [Docker Compose](https://docs.docker.com/compose/) - Environment Development
- [GitHub Actions](https://docs.github.com/en/actions) - CI
- [uv](https://github.com/astral-sh/uv) - Package Manager
- [Pytest](https://docs.pytest.org/en/8.2.x/) - Testing
- [PyJWT](https://pypi.org/project/PyJWT/) - Authentication
- [Alembic](https://alembic.sqlalchemy.org/en/latest/) - Migrations
- [Passlib](https://passlib.readthedocs.io/) - Password Hashing

## Project Structure
```
app/
  main.py           # Entry point, registers routers
  models.py         # SQLAlchemy models (User, Costume, Rental)
  schemas/          # Pydantic schemas
  database.py       # Async session factory
  security.py       # JWT & password utilities
  routes/           # API routers (auth, users, costumes, rental)
  services/         # Business logic layer

tests/
  conftest.py       # Pytest fixtures
  factories.py      # Factory Boy test data
  test_*_service.py # Unit tests (mocked)
  test_*_route.py   # Integration tests

docs/               # References
```

## Getting Started
1. Clone the repository:
```sh
git clone https://github.com/ma-alves/costume-rental-api.git
cd costume-rental-api
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

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /api/v1/auth/token | No | Get JWT token |
| POST | /api/v1/auth/refresh_token | Admin | Refresh JWT token |
| GET | /api/v1/users | Admin | List all users |
| GET | /api/v1/users/{id} | Admin | Get user by ID |
| POST | /api/v1/users | No | Create new user |
| PUT | /api/v1/users/{id} | Yes | Update user |
| DELETE | /api/v1/users/{id} | Yes | Delete user |
| GET | /api/v1/costumes | No | List costumes |
| GET | /api/v1/costumes/{id} | No | Get costume by ID |
| POST | /api/v1/costumes | Admin | Create costume |
| PUT | /api/v1/costumes/{id} | Admin | Update costume |
| DELETE | /api/v1/costumes/{id} | Admin | Delete costume |
| GET | /api/v1/rental | Admin | List rentals |
| GET | /api/v1/rental/{id} | Admin | Get rental by ID |
| POST | /api/v1/rental | Yes | Create rental |
| DELETE | /api/v1/rental/{id} | Yes | Delete rental |
| POST | /api/v1/payments/create-payment-intent | Yes | Create payment intent |
| GET | /api/v1/payments/payment-intent/{id} | Yes | Retrieve payment intent |
| POST | /api/v1/payments/capture | Yes | Capture payment |
| POST | /api/v1/payments/refund | Yes | Refund payment |
| POST | /api/v1/payments/create-customer | Yes | Create Stripe customer |
| GET | /api/v1/payments/saved-cards | Yes | List saved cards |
| DELETE | /api/v1/payments/saved-cards/{payment_method_id} | Yes | Delete saved card |
| POST | /api/v1/webhooks/stripe | No | Stripe webhook |

## Authentication
- JWT Bearer token authentication
- Roles: `admin` (full access) and `customer` (limited access)
- Token expires in 7 days (configurable)

## Testing
```sh
# Run all tests
uv run pytest -s -x -vv

# Run with coverage
uv run pytest -s -x --cov=app -vv

# Run specific test file
uv run pytest tests/test_user_route.py -vv
```

Domain test structure:
- `test_*_service.py` - Unit tests with mocked database sessions
- `test_*_route.py` - Integration tests with TestClient

## Examples
### List Costumes
```sh
curl -X 'GET' \
  'http://127.0.0.1:8000/api/v1/costumes/' \
  -H 'accept: application/json'
```

Response:
```json
{
  "costumes": [
    {
      "id": 1,
      "name": "Batman Suit",
      "description": "Full Batman costume",
      "fee": 150.00,
      "availability": "available"
    }
  ]
}
```

### Create Rental
```sh
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/rental/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{
  "costume_id": 1,
  "customer_id": 2
}'
```

Response:
```json
{
  "rental_date": "2024-12-25T10:00:00",
  "return_date": "2025-01-01T10:00:00",
  "costume": {
    "id": 1,
    "name": "Batman Suit",
    "description": "Full Batman costume",
    "fee": 150.00,
    "availability": "unavailable"
  },
  "user": {
    "id": 2,
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "12345678901",
    "role": "customer"
  }
}
```
