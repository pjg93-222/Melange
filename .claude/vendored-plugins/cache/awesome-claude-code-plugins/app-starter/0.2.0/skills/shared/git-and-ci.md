# Git and CI (all stacks)

The same branch model and merge workflow across every app.

## Branch model

```
main       production. Deploys go from here. Protected.
develop    integration. Feature branches land here first. CI runs on PRs.
feature/*  daily work. Branch from develop, PR back to develop.
hotfix/*   critical prod fix. Branch from main, PR to main, back-merge to develop.
release/*  version bump when not using release-please. Branch from develop, PR to main.
```

For a small solo project you may start with just `main` + `develop`. Add
`staging` only when a real pre-prod environment exists.

## Conventional commits

`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `perf:`, `ci:`.
Subject in the imperative, under about 70 chars. Body only when the "why" is not
obvious from the subject. Authored as the human owner. No AI trailers (see
`no-ai-attribution.md`).

## Auto-merge on green CI

Do not poll-and-merge by hand. For each PR, enable GitHub auto-merge so it merges
itself the moment required checks pass:

```
gh pr merge <number> --squash --auto
```

Enable "Allow auto-merge" and "Automatically delete head branches" in repo
settings once, up front. Never bypass CI with `--admin` except for a
release-automation bot PR that CI cannot run on by design.

## CI baseline

A `build` job on every PR into `develop` and `main` that runs the stack's
quality gates (lint, typecheck, tests, and a production build). Branch protection
requires that job to pass before merge. See each skill's `quality-gates.md` for
the exact commands.

## Release automation

Prefer release-please to manage version bumps and CHANGELOG from conventional
commits. It opens a release PR on pushes to `main`; merging it tags the release,
which triggers the deploy or publish workflow. Never hand-edit the version or
create tags manually when release-please is in use.
