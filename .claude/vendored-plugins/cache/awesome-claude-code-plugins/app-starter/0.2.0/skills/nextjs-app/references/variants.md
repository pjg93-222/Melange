# Next.js variants: private, open-source, private + open-source

Ask the visibility question first (SKILL step 0), then set the repo up for that
variant. The code is the same; what changes is licensing, README tone, secret
posture, and repo split.

## Private (default product repo)

- `gh repo create <name> --private`.
- README can be terse and internal: what it is, how to run, env keys, deploy.
- No LICENSE required. If you add one, use a proprietary "all rights reserved"
  note, not MIT.
- Secrets in Vercel env and GitHub Actions secrets. `.env*` gitignored.
- Add `CONTRIBUTING.md` only if teammates will work in it.

## Open-source (public)

- `gh repo create <name> --public`.
- Add `LICENSE` (MIT unless the owner says otherwise), `README.md` written for
  strangers (badges, quickstart, screenshots), `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, and `SECURITY.md`.
- Add `.github/ISSUE_TEMPLATE/` and a PR template.
- Absolutely no secrets, no real credentials, no internal URLs in history. If any
  secret ever touched a commit, rotate it and scrub history before going public.
- Ship a working `.env.example` and a seed path so a stranger can run it.

## Private + open-source (product + public core)

Two common shapes:

1. Monorepo with `apps/` split (the owner uses `apps/web`, `apps/mobile`). The
   public repo holds the shareable core; the private product consumes it. Keep
   proprietary code out of the public app folder.
2. Two repos: a public library or SDK, and a private app that depends on it.

Pick based on the owner's answer. Default to a monorepo with `apps/web` when they
already work that way. Draw a hard line: anything with secrets, paid-feature
gating, or customer data stays private. The public side gets an MIT LICENSE and a
stranger-facing README; the private side stays terse and internal.

In all cases the no-AI-attribution rule applies to every published file
(`../shared/no-ai-attribution.md`). A public repo is the worst place to leak an
AI-tool file or AI-cadence prose, so scan before the first push.
