# Next.js stack

This is the default dependency set, drawn from the owner's shipped apps. It is a
starting point, not a lockfile. Always pin to the live stable versions from
`scripts/check-latest.sh`, not the numbers written here.

## Core

- `next` (App Router), `react`, `react-dom` at the current stable majors.
- TypeScript strict mode on. `@types/node`, `@types/react`, `@types/react-dom`.
- ESLint flat config (`eslint.config.mjs`) with `eslint-config-next`.
- Package manager: pnpm. Set `engines` for node and pnpm in package.json.

## Data layer (default: Prisma + Postgres)

- `prisma` and `@prisma/client`.
- The current Prisma major uses a driver adapter for Postgres:
  `@prisma/adapter-pg` + `pg`. Wire the adapter in the Prisma client init; do not
  copy an old direct-connection setup from memory. Confirm the current pattern in
  the Prisma docs before writing the client.
- `postinstall` runs `prisma generate`. Build script runs
  `prisma generate && next build`.
- Scripts: `db:push`, `db:migrate`, `db:seed` (via `tsx`), `db:studio`, using
  `dotenv-cli` to load `.env`.

## Auth (default: next-auth v5)

- `next-auth` (v5 line) + `@auth/prisma-adapter`. v5 is the current standard even
  though it carries a beta tag; note that in one line where you pin it.

## UI (default: shadcn/ui + Tailwind v4)

- Tailwind v4 with `@tailwindcss/postcss`. No legacy `tailwind.config.js` content
  array unless the installed version needs it; confirm the current setup.
- shadcn/ui components (Radix primitives, `class-variance-authority`, `clsx`,
  `tailwind-merge`, `lucide-react`). Initialize with the shadcn CLI so
  `components.json` and the current component source land correctly.
- Alternative UI kit: Mantine (`@mantine/core` + hooks + form + dates +
  notifications, `postcss-preset-mantine`). Pick one kit, not both.

## Common libraries

- Forms and validation: `react-hook-form` + `@hookform/resolvers` + `zod`.
- Client state: `zustand`. Server state: `@tanstack/react-query` when you fetch
  from a separate API; for server components and server actions you often need
  neither.
- Tables: `@tanstack/react-table`. Charts: `recharts`. Dates: `date-fns` or
  `dayjs`. Toasts: `sonner`. Theme: `next-themes`.
- Analytics on Vercel: `@vercel/analytics`.

## What NOT to do

- Do not use the Pages Router. App Router only.
- Do not use `getServerSideProps` / `getStaticProps` (Pages-era APIs).
- Do not reach for a version or API from memory. The Next, React, Prisma, and
  Tailwind majors move fast; verify against `check-latest.sh` and current docs.
