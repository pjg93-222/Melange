# FastAPI stack

Default dependency set from the owner's shipped backend. Pin to the live stable
versions from `scripts/check-latest.sh`, not the numbers here.

## Core

- `fastapi` and `uvicorn[standard]` (ASGI server, standard extras for reload and
  websockets).
- `pydantic` v2 and `pydantic-settings` for typed settings loaded from env.
- `python-multipart` for form and file uploads.

## Database (default: async Postgres)

- `sqlalchemy[asyncio]` on the 2.0 line, with `asyncpg` as the async driver.
- `alembic` for migrations.
- Use the 2.0 style: `async_engine`, `async_sessionmaker`, `Mapped[...]` typed
  models, and `select()` statements. Do not write 1.x Query API or the old
  `declarative_base` patterns from memory.

## Auth

- JWT via `python-jose[cryptography]` or `PyJWT`. Hash passwords with `bcrypt`
  or `passlib[bcrypt]`.
- OAuth (Google) via `google-auth` when the app signs users in with Google.

## Optional

- `sqladmin` for a quick admin UI over the SQLAlchemy models.
- `httpx` for outbound HTTP (also the test client transport).

## Tooling

- `ruff` for lint and format (replaces flake8 + black + isort).
- `pytest` + `pytest-asyncio` for async tests.
- `uv` for dependency management and lockfile, or `pip` + `requirements.txt`.

## Version-boundary notes

- SQLAlchemy 2.0 is a hard break from 1.4. If you find yourself writing
  `session.query(...)`, stop and use `select()` with an async session.
- Pydantic v2 changed validators, config, and serialization. `orm_mode` is now
  `from_attributes`; `@validator` is now `@field_validator`. Confirm current
  syntax in the Pydantic v2 docs.
- Do not mix sync and async DB sessions. Pick async end to end.
