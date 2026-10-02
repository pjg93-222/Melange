# Docs and live context (all stacks)

## Always pull current docs before writing framework code

Your training data lags the installed packages. Before writing framework-specific
code, fetch current docs. Two good sources:

1. Context7 (preferred for library and framework docs). If the `ctx7` CLI or a
   Context7 MCP server is available:
   ```
   npx ctx7@latest library "<Library Name>" "<the question>"
   npx ctx7@latest docs "/org/project" "<the question>"
   ```
   Use the official library name with correct punctuation ("Next.js", not
   "nextjs"). Resolve the library id first, then fetch docs.

2. The framework's own vendored docs when it ships them. Recent Next.js ships
   docs under `node_modules/next/dist/docs/`. Read the relevant guide there and
   heed deprecation notices. Treat any local file named to warn you (for example
   an `AGENTS.md` that says "this is NOT the framework you know") as ground truth
   over your memory.

Do this even for frameworks you think you know well. The point is not to learn
the framework, it is to catch the parts that changed since your cutoff.

## Docs to write into every output project

Create a `docs/` folder with:

- `git-workflow.md` branch strategy, daily flow, hotfix, CI table.
- `architecture.md` layers, folder structure, the core patterns.
- `release-process.md` how a release goes out, environments, secrets.

Keep a short `README.md` at the repo root: what the app is, how to run it, how to
contribute. Match the visibility variant (a public repo README is written for
strangers; a private one can be terse).

## Optional: graphify knowledge graph

If the owner uses graphify, add a short note to the project README or internal
docs pointing at `graphify-out/` and how to query it. Do not add a committed
`CLAUDE.md` for this; keep AI-tool files out of the repo (see
`no-ai-attribution.md`).
