# FastAPI project structure

Layered structure, matching the owner's shipped backend.

```
<name>/
  app/
    main.py          create_app(), router registration, middleware, /health
    core/
      config.py      Settings (pydantic-settings), reads env
      security.py    JWT encode/decode, password hashing
      database.py    async engine, async_sessionmaker, get_db dependency
    routers/         one module per resource, thin: parse, call service, return
    services/        business logic, the only layer that composes repositories
    models/          SQLAlchemy 2.0 Mapped models
    schemas/         Pydantic v2 request and response models
    utils/           helpers
  alembic/           migration env and versions
  alembic.ini
  scripts/           seed and ops scripts
  tests/
  Dockerfile
  docker-compose.yml # app + postgres for local dev
  .env.example
  requirements.txt   # or pyproject.toml + uv.lock
```

## Patterns

- Routers are thin. They validate input via a `schemas/` model, call a service,
  and return a response model. No business logic or raw SQL in routers.
- The DB session is a dependency:
  ```python
  async def get_db() -> AsyncIterator[AsyncSession]:
      async with async_session() as session:
          yield session
  ```
  Inject it with `db: AsyncSession = Depends(get_db)`.
- Settings come from `pydantic-settings` reading env. Never hardcode secrets or
  URLs. Provide `.env.example` with every key.
- Auth: a `get_current_user` dependency decodes the JWT and loads the user.
  Protected routes depend on it.
- Response models exclude sensitive fields. Never return password hashes or raw
  tokens in a response schema.
- CORS, request logging, and error handlers are registered in `create_app()`.

## Migrations

- Configure Alembic to use the async engine URL from settings.
- Autogenerate after model changes: `alembic revision --autogenerate -m "..."`,
  then review the generated migration before applying. Never edit the DB by hand.
