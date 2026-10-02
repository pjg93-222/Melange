# House rules (all stacks)

These rules apply to every app the starter skills scaffold. Read them before
writing any code. They exist because a model's training data is always older
than the packages you are about to install.

## 1. Trust the injected current date, not your training cutoff

Claude Code injects the real current date into the session. Believe it. Your
training cutoff is months behind it. Any statement like "the latest version is
X" from memory is a guess and is probably wrong. Confirm versions live (rule 2).

## 2. Latest stable packages, verified live (never hardcoded)

Order of operations, every time:

1. Read the injected current date (rule 1). That is "now".
2. As of that date, query the real registry for current stable versions by
   running the skill's `scripts/check-latest.sh` (npm, pub.dev, PyPI).
3. Pin what the script reports.

No version number is hardcoded anywhere in these skills. The `references/*.md`
files describe the stack by package NAME and never carry a pinned version,
because versions go stale the moment they are written. If you ever see a version
number in a reference file, treat it as a bug and ignore it in favor of the live
check. Pin what the registry says now, not what you remember.

- Prefer the latest STABLE release. Do not pull prereleases (alpha, beta, rc)
  unless the ecosystem norm requires it (for example next-auth v5 is beta but is
  the current auth standard). When you use a prerelease, say why in one line.
- After install, run the project's own version print (`next --version`,
  `flutter --version`, `pip show fastapi`) and record the real installed
  versions in the project's docs.

## 3. No deprecated APIs

Deprecated code is the single most common failure when a model scaffolds with
stale memory. Defend against it:

- Consult current docs through Context7 (see `docs-and-context.md`) for the
  framework before writing framework-specific code. Do this even for frameworks
  you think you know. APIs move.
- Heed every deprecation warning the tooling prints. Do not silence it, fix it.
- When the installed major version differs from what you remember, assume the
  API changed and read the migration notes before writing code.

## 4. Write like a human developer

The output repo must read as if a human wrote it. See `no-ai-attribution.md`
for the hard rules. In short: plain ASCII punctuation, no em or en dashes, no
curly quotes, no AI-cadence prose, and no reference to any AI tool anywhere in
the code, comments, docs, commits, or metadata.

## 5. Git, commits, and CI

Follow `git-and-ci.md`: conventional commits authored as a human, feature branch
into an integration branch, PR, and auto-merge on green CI. No AI co-author
trailers, ever.

## 6. Security defaults

- Never commit secrets. `.env*`, keystores, service-account JSON, and signing
  credentials are gitignored from the first commit.
- Provide a `.env.example` with keys and blank or placeholder values.
- Secrets live in the platform secret store (GitHub Actions secrets, Vercel env,
  platform keychain), never in the repo.

## 7. Ask the few decisions that change scaffolding, then proceed

Each skill asks a short set of variant questions up front (license, visibility,
deploy target, and so on). Ask those, then build without further hand-holding.
Do not re-litigate settled choices or narrate options you will not take.
