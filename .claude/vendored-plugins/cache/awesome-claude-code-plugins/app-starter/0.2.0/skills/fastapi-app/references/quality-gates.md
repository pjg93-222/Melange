# FastAPI quality gates, CI, and deploy

## Local gates (run before every commit and in CI)

```
ruff check .
ruff format --check .
pytest
python -c "from app.main import app"   # imports cleanly
```

Run the app locally and confirm `/health` responds and `/docs` renders the
OpenAPI UI.

## CI workflow

`.github/workflows/ci.yml`, a job on PRs into `develop` and `main`:

```yaml
name: CI
on:
  pull_request:
    branches: [develop, main]
jobs:
  build:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 10s
          --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
```

Pin the Python version to the one you install and the action majors to current.
Set branch protection to require the `build` job, then use
`gh pr merge <n> --squash --auto`.

## Docker

- `Dockerfile` on a slim Python base, install deps, run
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- `docker-compose.yml` with the app plus Postgres for local dev.

## Vercel (serverless option)

- A `vercel.json` routing all paths to the ASGI app. Note serverless cold starts
  and connection limits; use a pooled or serverless Postgres and keep the async
  engine pool small.

## Verify before declaring done

`ruff check` clean, `pytest` green, the app imports and starts, `/health`
responds, and `alembic revision --autogenerate` produces a sane migration.
Report real results.
