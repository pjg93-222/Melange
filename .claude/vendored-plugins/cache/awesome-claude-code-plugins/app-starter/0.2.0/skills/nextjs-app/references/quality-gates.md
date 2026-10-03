# Next.js quality gates and CI

## Local gates (run before every commit and in CI)

```
pnpm install --frozen-lockfile
pnpm lint            # eslint src/
pnpm typecheck       # tsc --noEmit
pnpm build           # prisma generate && next build
```

Add a `typecheck` script (`tsc --noEmit`) if `create-next-app` did not. The
production `build` is the real gate; a passing dev server is not enough.

## CI workflow

`.github/workflows/ci.yml`, one `build` job on PRs into `develop` and `main`:

```yaml
name: CI
on:
  pull_request:
    branches: [develop, main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version: lts/*
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm typecheck
      - run: pnpm build
        env:
          # a dummy DATABASE_URL so prisma generate and next build succeed
          DATABASE_URL: postgresql://user:pass@localhost:5432/db
```

Pin action versions to the current majors when you write this; do not trust the
numbers above blindly. Set branch protection to require the `build` job, then use
`gh pr merge <n> --squash --auto` per `../shared/git-and-ci.md`.

## Deploy

- Vercel: connect the repo, set env vars in the Vercel dashboard, `main` is the
  production branch. Preview deploys on PRs come for free.
- Self-host: a `Dockerfile` using the Next standalone output and a
  `docker-compose.yml` with the app plus Postgres.

## Smoke check before declaring done

Start the dev server, load the root route, confirm no runtime or hydration
errors in the console. Report the real result.
