# Open-source docs checklist

When the visibility variant is open-source (public) or the public side of a
private-plus-open-source split, the repo must ship the documents a stranger and a
contributor expect. Create all of these before the first public push.

## Required

- `README.md` written for strangers: what it is, a screenshot or demo, quickstart
  (clone, install, env, run), and how to contribute. Not the terse internal
  version.
- `LICENSE` a real license file (MIT unless the owner says otherwise). Set the
  copyright holder and year.
- `CONTRIBUTING.md` how to set up, branch, commit (Conventional Commits), run the
  checks, and open a PR.
- `CODE_OF_CONDUCT.md` the behavior standard and how to report.
- `SECURITY.md` how to report a vulnerability privately (advisory or email), and
  what is in scope.
- `.gitignore` covering env files, secrets, build output, and AI-tool files.
- `.env.example` every key present, values blank or placeholder, so a stranger
  can run it.

## GitHub templates

- `.github/ISSUE_TEMPLATE/bug_report.yml` and `feature_request.yml`, plus
  `config.yml` (`blank_issues_enabled: false`).
- `.github/PULL_REQUEST_TEMPLATE.md` with a short checklist.

## Recommended

- `CHANGELOG.md` maintained by release-please from Conventional Commits, not by
  hand.
- `docs/` with `architecture.md`, `git-workflow.md`, and `release-process.md`
  (see `docs-and-context.md`).
- Badges in the README (CI status, license, latest release) once CI exists.
- A CI workflow that runs the stack's quality gates on every PR (see each skill's
  `quality-gates.md`).

## Before the public push

Run the open-source hard gate in `no-ai-attribution.md`: no AI-tool files, no AI
references anywhere in tree or history, no smart punctuation, human commit author
on every commit, and no secret ever committed (rotate and scrub if one was).
