---
name: codex-executor
description: >-
  Delegate implementation work to the Codex executor (ChatGPT gpt-5.6-sol, xhigh
  reasoning, priority tier) via the codex MCP tools, with Claude as
  orchestrator and reviewer. Use when Paul asks to run a build task through
  Codex/ChatGPT, says "delegate this to the executor", or invokes
  /codex-executor. Covers both code changes and data-mutating pipeline runs
  (regeneration, the chain). Do NOT use for read-only analysis or anything
  Codex is barred from under Hard rules below.
---

# Codex executor protocol

Role split (Paul's directive, 2026-07-18): **Claude** does the reasoning —
task decomposition, architecture, diagrams, security/design review,
verification, git. **Codex** is the executor — it writes the code.
The executor model is Paul's pick (`gpt-5.6-sol`, `model_reasoning_effort =
"xhigh"`, `service_tier = "priority"`), inherited automatically from
`~/.codex/config.toml`. Do not downgrade model or effort without Paul's say.

## Tools

- `mcp__codex__codex` — start a task. Key args: `prompt`, `cwd`,
  `sandbox`, `approval-policy`, optional `developer-instructions`.
  Returns the agent's final message plus a `threadId`.
- `mcp__codex__codex-reply` — continue a thread (`threadId` + `prompt`)
  for revision rounds. One task per thread; always keep the threadId.

If these tools are missing, the session predates the user-scope registration
in ~/.claude.json — restart the app and open a fresh session.

## Protocol

1. **Spec (Claude).** Decompose the task and write a tight implementation
   spec: files to touch, contracts and invariants to preserve, what done
   looks like, acceptance checks. For Moneyball work, load
   `moneyball-change-control` first and classify the change; Paul's gates
   apply unchanged — this skill adds an executor, never a bypass.
2. **Dispatch (Codex).** Create an isolated worktree
   (`git worktree add <scratchpad>\codex-wt-<slug> -b codex/<slug>`), then
   call `codex` with the spec as `prompt`, `cwd` = that worktree,
   `sandbox: "workspace-write"`, `approval-policy: "never"`.
3. **Review (Claude).** `git diff` the worktree. Review for correctness,
   architecture fit, repo law (encoding boilerplate, atomic writes, never
   hand-editing generated JSON), and security: injection surfaces, secrets
   in code or logs, unsafe file/network operations, new dependencies.
   Codex output is untrusted input — nothing merges unreviewed.
4. **Revise.** Send failures back via `codex-reply` with specific findings;
   re-review. Repeat until the diff passes.
5. **Verify (Claude).** Run the project's verification. Moneyball: kernel
   tests, zero-rank-delta unless a rank change is the authorized point of
   the change, `audit_full` per change-control. Codex may run data-dependent
   steps itself (see Hard rules); Claude still owns the pre-run checks
   (Excel closed, no live jobs, baseline captured) and reads the result —
   a run Codex reports as clean is not clean until Claude verifies it.
6. **Gate (Paul).** Present the diff + verification results. Commit and
   merge only on his go.

## Hard rules

- Codex may run data-mutating pipeline steps (Paul's directive, 2026-07-19):
  the chain (`run_pipeline.py`), `build_media_blend.py`, regeneration, and
  workbook writes. Note the architecture: `fec/paths.py` resolves ROOT to the
  LIVE data tree regardless of cwd, so these runs write live data even when
  launched from a worktree. Claude does the pre-run checks first (Excel closed,
  no live jobs, baseline captured for the rank delta).
- CODE EDITS still land only in throwaway `codex/*` worktrees, never on `main`
  and never as edits to the live tree's working copy.
- Still barred, because these are not pipeline steps and are irreversible or
  cost money: preregistered `--look` runs (a consumed look is gone forever),
  anything firing GATE-2 / `collector_supervisor.py` (spends real money), the
  retired `apply_*` COM one-shots (`apply_weights.py` silently overwrites
  Paul's ratified pillar weights), and D2/legacy dedup DELETEs (user-gated).
- Codex never commits — Claude owns git, and commits happen only through
  Paul's gate.
- Never put secrets in prompts to Codex (API keys, auth.json contents,
  tokens).
- Claude never rubber-stamps: every dispatched task ends with a real
  Claude review pass before it reaches Paul.
