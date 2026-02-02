# Costume Rental API

A RESTful API for a costume rental service using Python, FastAPI and PostgreSQL as its core technologies, as well as JWT for authentication and Pytest for testing.

## Features

- **Manage Costumes:** Create, retrieve, update, and delete costume inventory.
- **Customer Management:** Register and manage customer information and rental history.
- **Rental System:** Create and track costume rentals with automatic availability management.
- **User Authentication:** Secure JWT-based authentication and authorization.
- **Admin Control:** Admin users can manage users, costumes, and rental operations.
- **Comprehensive Testing:** Full test coverage using Pytest.

## Tech Stack
- [FastAPI](https://fastapi.tiangolo.com/) - Web Framework
- [PostgreSQL](https://www.postgresql.org) - SQL Database
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL Toolkit and ORM
- [Docker Compose](https://docs.docker.com/compose/) - Environment Setup
- [GitHub Actions](https://docs.github.com/en/actions) - CI
- [Pytest](https://docs.pytest.org/en/8.2.x/) - Testing
- [PyJWT](https://pypi.org/project/PyJWT/) - Authentication
- [Alembic](https://alembic.sqlalchemy.org/en/latest/) - Migrations

## Usage

### Installation 

1. **Clone the repository:**
```bash
git clone https://github.com/ma-alves/costume-rental-api.git
cd costume-rental-api
```

2. **Set up environment variables:**
```bash
cp .env.example .env
```
Edit `.env` file with your configuration (database credentials, JWT secret, etc.)

3. **Build and run with Docker Compose:**
```bash
docker compose up --build
```

4. **Access the API:**
- **Swagger UI (Interactive API docs):** http://localhost:8000/docs
- **ReDoc (Alternative API docs):** http://localhost:8000/redoc

### Running Tests

```bash
docker compose exec -it <container-id> uv run pytest -s -x -vv
```

For coverage report:
```bash
docker compose exec -it <container-id> uv run pytest --cov
```

### Running Migrations

```bash
docker compose exec -it <container-id> uv run alembic upgrade head
```

## API Endpoints

### **Authentication**

**POST /auth/token** - Login for access token

**POST /auth/refresh_token** - Refresh access token

### **Users**

**GET /users/** - Read users

**POST /users/** - Create user

**GET /users/{user_id}** - Read user

**PUT /users/{user_id}** - Update user

**DELETE /users/{user_id}** - Delete user

### **Costumes**

**GET /costumes/** - Get costumes

**POST /costumes/** - Create costume

**GET /costumes/{costume_id}** - Get costume

**PUT /costumes/{costume_id}** - Update costume

**DELETE /costumes/{costume_id}** - Delete costume

### **Customers**

**GET /customers/** - Get Customers

**POST /customers/** - Create Customer

**GET /customers/{customer_id}** - Get Customer

**PUT /customers/{customer_id}** - Update Customer

**DELETE /customers/{customer_id}** - Delete Customer

### **Rental**

**GET /rental/** - Read Rental List

**POST /rental/** - Create Rental

**GET /rental/{rental_id}** - Read Rental

**PATCH /rental/{rental_id}** - Patch Rental

**DELETE /rental/{rental_id}** - Delete Rental

## Examples

### List Costumes

- **Request**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/costumes/' \
  -H 'accept: application/json'
```

- **Response (200 OK)**
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

- **Request**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/rental/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "costume_id": 0,
  "customer_id": 0
}'
```

- **Response (201 Created)**
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