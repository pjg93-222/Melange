# Next.js folder structure and patterns

Feature-first layout under `src/`, matching the owner's shipped apps.

```
src/
  app/
    (auth)/           route group for sign-in and sign-up
    (app)/            route group for the authenticated product
    api/              route handlers (webhooks, integrations)
    layout.tsx
    page.tsx
  components/
    ui/               shadcn primitives (generated)
    layout/           shell, nav, sidebar
    shared/           cross-feature widgets
    charts/
  features/           optional: per-feature folders when the app grows
  lib/                framework glue: db client, auth config, utils
  actions/            server actions, grouped by domain
  repositories/       data access, one module per aggregate
  schemas/            zod schemas, shared client and server
  services/           business logic that is not a server action
  stores/             zustand stores
  auth/               auth helpers and session access
```

## Patterns

- Server Components by default. Add `"use client"` only where interactivity or
  browser APIs require it.
- Data access goes through `repositories/`. Server actions in `actions/` call
  repositories; components do not touch the DB client directly.
- Validate every server action input with a `zod` schema from `schemas/`. Never
  trust client input.
- The Prisma client is a single instance in `lib/` guarded against hot-reload
  duplication in dev.
- Route handlers under `app/api/` are for webhooks and external integrations, not
  for your own UI data. Prefer server actions and server components for internal
  data flow.
- Keep secrets in env, read through a typed config module in `lib/`. Never inline
  `process.env` reads across the codebase.

## Files to create at the root

- `.env.example` with every key blank or placeholder.
- `eslint.config.mjs`, `tsconfig.json` (strict), `next.config.ts`.
- `prisma/schema.prisma` and `prisma/seed.ts` when using Prisma.
- `docker-compose.yml` for local Postgres when using Prisma + Postgres.
