# AGENTS.md - Costume Rental API

## Quick Commands
```sh
uv run fastapi dev --host 0.0.0.0 --port 8000 --reload  # Dev server
uv run uvicorn app.main:app --port 8000 --host 0.0.0.0  # Production
uv run pytest -s -x --cov=app -vv                        # Run tests
uv run ruff check --fix && uv run ruff format            # Lint & format
uv run alembic revision --autogenerate -m "msg"          # New migration
uv run alembic upgrade head                              # Run migrations
docker compose up --build                                # Full stack
```

## Architecture
- **Framework**: FastAPI with async SQLAlchemy
- **Database**: PostgreSQL (dev), SQLite+aiosqlite (tests)
- **Auth**: JWT via OAuth2PasswordBearer, bcrypt hashing
- **Package Manager**: uv (not pip)
- **Python**: 3.12

### Directory Structure
```
app/
  main.py           # Entry point, registers routers
  models.py         # SQLAlchemy models (User, Costume, Rental)
  schemas.py        # Pydantic schemas
  database.py       # Async session factory
  security.py       # JWT & password utilities
  routes/           # API routers (auth, users, costumes, rental)
  services/         # Service layer (costume, rental, user)
```

### Known Issues
- **Patch rental endpoint missing** - PATCH route not implemented, tests skipped
- **fastapi-limiter v0.2.0 is broken** - middleware.py not installed, waiting on PR #78

### Code Style (enforced by ruff)
- Single quotes: `'string'`
- Tabs for indentation
- Line length: 88

## Testing
- Tests use in-memory SQLite with aiosqlite (not PostgreSQL)
- Fixtures in `tests/conftest.py`
- Async builder functions for test data (`tests/factories.py`)
- Default test password: `test1234`
- **Test structure**: `test_{entity}_service.py` for unit tests, `test_{entity}_route.py` for integration tests

## Migrations
- **DO NOT modify migrations/ manually** - use Alembic only
- Migration script: `migrations/versions/ed55aec8da79_from_scratch.py`
- Alembic reads `DATABASE_URL` from environment

## Environment
Required `.env` variables:
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/appdb
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_DAYS=7
```

## CI/CD
- GitHub Actions runs on push to main
- Order: `uv sync` → `alembic upgrade` → `pytest -s -x -vv`
- All env vars from GitHub Secrets

## Rules
- Don't you dare updating stripe client.v1. This is the ACTUAL way of using the SDK. Don't touch it.