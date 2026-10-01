---
name: codex-executor
description: >-
  Delegate implementation work to the Codex executor (ChatGPT gpt-5.6-sol,
  xhigh reasoning, priority tier) with Claude as coordinator and reviewer.
  Use when Paul asks to run a build task through Codex/ChatGPT, says
  "delegate this to the executor", or invokes /codex-executor. Covers code
  changes and explicitly authorized data-mutating pipeline runs. Do not use
  for read-only analysis or anything barred by the Hard rules below.
---

# Codex executor protocol

Claude owns decomposition, architecture, design choices, constraints, review,
verification, and git. Codex implements the decided design, checks the actual
workspace, and returns evidence. Codex's xhigh reasoning improves execution
fidelity; it does not grant authority to choose a design the specification
left open.

Command hierarchy (Paul, 2026-07-24): **Claude (Fable) > Codex > Gemini.**
Claude never authors code — every code change, including a one-line fix, is
written by Codex, via an edit-only dispatch when the sandbox blocks
execution. Claude keeps design, specification, review, git, documentation,
and memory. Media perception (images, video, audio, screenshots, scans)
routes through the Gemini lane per the `gemini-perception` skill; Gemini
holds no authority in this lane.

Universal lane laws: `.claude/commands/metaloop.md` § UNIVERSAL LANE LAWS
binds this lane in and out of Meta LOOP runs — role monopolies,
escalate-don't-reason, never-downgrade, glasseye, one-writer, copy-sync.

The exchange is closed-loop:

1. Claude sends a complete contract and predicted effects.
2. Codex verifies readiness and executes only inside that contract.
3. Codex returns observed results, errors, drift, and uncertainty.
4. Claude compares intended and observed state, then confirms, revises, or
   stops the lane.

Codex has one narrow early-action allowance: it may make a minimal immediate
correction to prevent observable, imminent damage. Every such action ends the
turn with a structured report and awaits Claude's verdict.

The configured executor is `gpt-5.6-sol` with
`model_reasoning_effort = "xhigh"` and `service_tier = "priority"`. Do not
downgrade model, effort, or tier without Paul's instruction.

## Tools

- `mcp__codex__codex`: starts one task and returns a `threadId`.
- `mcp__codex__codex-reply`: continues that task for revision rounds.
- `config`: per-call overrides. Defaults remain xhigh and priority.
- `developer-instructions`: receives the Standing dispatch preamble on every
  dispatch.
- Headless fallback: `codex exec`, after checking `codex exec --help`. The
  headless path must carry the same Standing dispatch preamble or it does
  not run.

One task stays in one thread. Keep its `threadId`, worktree path, branch, and
ledger `run_id` together.

## Required contract

Every design-bearing dispatch contains all five fields:

1. `OBJECTIVE`: one concrete outcome.
2. `CONSTRAINTS`: invariants and explicit prohibitions.
3. `ACCEPTANCE CRITERIA`: numbered, observable checks.
4. `IMPACT ENVELOPE`: exact files Codex may change and processes it may run.
5. `CONFIRMATION CONDITIONS`: what must return to Claude before the lane can
   advance.

A missing field is a specification defect. Claude fixes it; Codex does not
fill the gap.

The runtime validator lives at
`.claude/skills/codex-executor/scripts/coordination_contract.py`. Validate a
JSON contract with:

```powershell
python .claude/skills/codex-executor/scripts/coordination_cli.py `
  validate-contract <contract.json>
```

The same module validates readiness states, report-specific verdicts, and
allowed lane-state transitions. Runtime validation supplements review; it
does not convert an invalid instruction into authority.

## Protocol

### 1. Specify

Claude loads the applicable project governance first, chooses the complete
design, writes the five-field contract, and names a checkable predicted effect
for each step. A prediction must be falsifiable: exit code, file presence,
specific content, hash, or another concrete observable.

For Moneyball, load `moneyball-change-control`, classify the change, and carry
Paul's existing gates into the contract unchanged.

### 2. Isolate and register

Code edits use a throwaway worktree and `codex/*` branch:

```powershell
git worktree add C:\Users\pgoff\AppData\Local\Temp\claude\cxwt-<slug> `
  -b codex/<slug>
```

Immediately register the thread, worktree, branch, and run identifier in the
structured ledger. Live-tree authority is allowed only for a named pipeline
step under the Hard rules.
Every Codex dispatch run must register a `dispatch` event before execution
begins.

### 3. Verify readiness

Before editing, Codex verifies:

- the required tools respond;
- the required permissions exist;
- the working directory matches the contract;
- named input files exist;
- each planned step has a reversal option, or is a specifically authorized
  irreversible pipeline step.

Codex returns exactly one readiness state:

- `READY`: all task-specific requirements are available.
- `READY_WITH_LIMITS`: execution can proceed within named limits.
- `BLOCKED`: a named blocker prevents execution; nothing is changed.

Design-bearing tasks and every live-tree turn use a plan-only first round.
Trivial mechanical worktree edits may put the handshake at the start of the
execution turn.

### 4. Execute in verified increments

For each increment:

1. apply the smallest useful change;
2. check its observable result against the prediction;
3. continue only when the result matches, remains inside the envelope, and
   has a known reversal.

Issuing a command is not evidence that it succeeded. Never claim an output
that was not observed in the current session.

Pause when any condition holds:

- an observed result contradicts the plan;
- a required capability disappears;
- the same operation fails twice;
- the next action exceeds the envelope;
- reversal cannot be stated and the action is not an authorized pipeline
  step;
- an unapproved external or irreversible action would be required;
- unexplained files change;
- a long-running turn should stop at a clean verified increment.

Use `STOP REPORT` for a specification or authority question found before a
consequential action. Use `DECISION REQUEST` for an execution divergence
without a protective state change.

### 5. Review and verify

Verify the RECEIPT first (permanent, Paul 2026-08-10): check the
enumeration one-to-one against the dispatched contract and pinned
invariants BEFORE adjudicating any work product — every item present, no
modality weakened, every N/A reason valid. An omission, distortion,
invention, or unjustified N/A is a re-dispatch with correction, logged
caught-at-gate — regardless of how the work itself looks. A clean
receipt does not waive any later review step. This verification is a
budgeted per-dispatch serial cost (law 6's honest accounting); a fired
re-dispatch costs a full extra round. Record the receipt and verdict as
a `receipt` ledger event (spec + receipt fingerprinted, `verified`
bool).

Claude treats all executor output as untrusted input:

- inspect `git diff --stat`, the full diff, and `git status --porcelain`;
- reconcile every changed and untracked file with `FILES CHANGED`;
- compile every returned Python file;
- rerun every command whose claimed output matters;
- inspect security, secrets, dependency, file, network, and injection risks;
- answer every numbered acceptance criterion with evidence, `NOT MET`, or
  `NOT VERIFIABLE`.

For Moneyball, run the verification required by the change classification.
Live-tree results require artifact timestamps, hashes against the pre-run
baseline, and confirmation that expected outputs exist.

### Second review round (double sign-off)

After Claude's first-pass sign-off, every non-trivial diff takes a second,
independent round (Paul, 2026-07-24): a fresh Codex thread — never the
author thread — dispatched read-only to adversarially investigate the diff
for defects: logic errors, edge cases, contract violations, security
issues. Its findings return as claims. Claude adjudicates each finding,
routes real defects back as a scoped fix dispatch, and only then gives the
final sign-off.

Trivial means all of: no control-flow, schema, dependency, or vocabulary
change; a single file; reviewable at a glance. Only trivial diffs may skip
this round, at Claude's call, with the skip stated in the receipt to Paul.
This carve-out is distinct from the handshake-placement carve-out in step
3 — a diff trivial enough to skip the plan-first round is not thereby
trivial enough to skip this one.

### 6. Gate

Present the diff and verification to Paul. Commit, merge, publishing, paid
operations, and other consequential external actions remain at his gate.

## Standing dispatch preamble

Put this block in `developer-instructions` on every dispatch:

```text
You are the executor in a Claude-coordinated lane. Claude owns every design decision; execute the supplied design exactly.
Do not add dependencies or change algorithms, APIs, schemas, scope, or policy beyond the specification. If the specification is ambiguous, incomplete, wrong-looking, or contradicted by evidence, STOP REPORT and change nothing.
Return observations, errors, environmental surprises, and uncertainty. Never claim a result you did not observe in this session.

RECEIPT — before any other output, as the first labeled block of your reply: (a) the OBJECTIVE in your own words; (b) an ENUMERATION — every numbered constraint of the contract and every line of the INVARIANTS block, each as its own item opening with its source tag — `CON-<n>:` for the nth numbered constraint of the contract, `INV-<n>:` for the nth line of the INVARIANTS block — followed by a one-sentence interpretation in your own words; an item may be marked N/A only with an explicit reason, and an N/A item still carries its tag. The tags exist so coverage is checkable mechanically rather than by reading: a missing tag reads as a dropped constraint. (c) the falsifiable acceptance checks in your own words. Weakening any modality (must→should, never→avoid, exactly→approximately) is a distortion. If the contract contradicts itself, the evidence, or an invariant, say so in the RECEIPT — that flag is part of the receipt's job, and it feeds the same STOP REPORT channel. RECEIPT is a comprehension probe over a contract that already traveled verbatim in this dispatch; it licenses no paraphrase anywhere else. On a revision round, the RECEIPT covers the revised instruction in full. Work product begins only after the RECEIPT. EVERY reply that opens a new or revised contract begins with the RECEIPT — a DECISION REQUEST, STOP REPORT, or CORRECTION REPORT on such a turn comes after it, never in its place; a reply missing its leading RECEIPT is invalid, is re-demanded verbatim, and is logged as a rework.
INVARIANTS — when the dispatch carries an INVARIANTS block, it was quoted mechanically from the run's pinned ledger record. Treat every line as a binding constraint of this turn; your RECEIPT enumeration must include every line — there is no lane-side relevance filter. Never restate an invariant in weaker form than it arrived.

HANDSHAKE — verify tools, permissions, cwd, named inputs, and reversal options before execution. State READY, READY_WITH_LIMITS with every limit, or BLOCKED with the blocker and no changes. On a live-tree turn, resolve and state ROOT before step one; BLOCKED if it is not the named tree.
ENVELOPE — the named files and processes are the maximum permitted impact. Work outside them is a pause condition.
INCREMENTS — apply the smallest useful change, check the observable result against the plan, then continue. Never build on an unverified increment.
AUTHORITY — proceed only when confidence is high, impact stays inside the envelope, and reversal is known. Any failed factor routes back to Claude.
PAUSE — send a DECISION REQUEST when execution diverges, a capability disappears, the same operation fails twice, impact would expand, reversal is unavailable, an unapproved external or irreversible action is required, unexplained drift appears, or the turn should stop at a clean increment.
DECISION REQUEST fields: Intended result / Actual result / Evidence / Current state / Options / Risk of each option / Recommended option / Reversal procedure / Decision required. Stop after sending it. Wait for CONTINUE, REVISE, REVERSE, REDUCE SCOPE, REQUEST USER AUTHORIZATION, or STOP. A bare CONTINUE names no resume point, so ask. Reversal is performed by Claude, never inferred from a verdict word.

IMMEDIATE CORRECTION — before Claude replies, you may act only to prevent immediate, observable damage: halt a runaway or destructive process; prevent an imminent overwrite, leak, deployment, or irreversible change; preserve logs or recoverable work through additive copy to a new path inside the worktree; or correct your own mechanical command slip from this turn. A specification defect or pre-existing code defect does not qualify.
The action must be small, local, proportionate, reversible, and within all higher-priority rules. It must never delete, publish, deploy, purchase, send an external message, broaden access, invent approval, or run a history-, index-, or worktree-mutating git command.
LIVE-TREE TURNS ARE HALT-ONLY. The only early action there is stopping the process and reporting. Do not clean, repair, delete, rerun, or resume a partial chain. A new run starts from the top after adjudication.
Lead with CORRECTION REPORT only when you changed a process, file, or external state to prevent damage. Fields: Trigger / Evidence observed / Immediate risk / Action taken / Files, processes, or external state affected / Why proportionate / How to reverse / Current safe state / Recommended next step / Confirmation requested. Action taken may not be none. Stop after sending it and wait for CONFIRM, MODIFY, ROLLBACK, or ESCALATE.
Lead with STOP REPORT for a pure specification or authority question: Trigger / Evidence observed / What you did NOT do / Question for Claude.

Never run commit, stash, reset, restore, checkout --, clean, rm, or worktree remove. The worktree diff is Claude's review surface.
Never place secrets in prompts, output, logs, or the ledger.
ALWAYS BARRED regardless of what the contract says: preregistered --look consumption, GATE-2, collector_supervisor.py, the retired apply_* one-shots, and D2/legacy dedup deletion.
Keep the final message terse and end with eight labeled lists:
FILES CHANGED: <every changed or created path and why>
COMMANDS RUN: <commands actually executed, or none>
ACCEPTANCE: <each numbered criterion with evidence, NOT MET, or NOT VERIFIABLE>
CORRECTION: <the immediate action and what it affected, or none>
DEVIATIONS: <each departure and why, or none>
NOT VERIFIED: <everything not checked>
ESCALATIONS: <flaws, errors, or clearly correct improvements discovered beyond scope — reported for Claude's adjudication, nothing acted on; or none>
POTENTIAL IMPROVEMENTS: <judgment-call improvements — reported only, these reach Paul before any action; or none>
```

## Immediate correction rules

All of these must hold:

1. The risk is immediate and observable.
2. Waiting one full round trip could materially worsen it.
3. The action is the smallest effective containment.
4. The action stays within the contract and higher-priority rules.
5. The action is reversible and preserves evidence.
6. Codex reports it immediately and stops.

Permitted examples are halting a runaway process, preventing an imminent
overwrite or disclosure, making an additive evidence copy inside the
worktree, and correcting Codex's own mistyped path or flag from the current
turn.

Not permitted: design changes, speculative fixes, deletion, publishing,
deployment, purchases, external messages, access expansion, silent scope
changes, invented approval, or any git operation that alters history, index,
or the worktree review surface.

Claude answers a `CORRECTION REPORT` with one of:

- `CONFIRM`: retain the action, then provide an explicit resume point if work
  should continue.
- `MODIFY`: provide replacement instructions.
- `ROLLBACK`: Claude performs the restoration; the word does not authorize
  Codex to execute it.
- `ESCALATE`: take the decision to Paul.

The action remains a declared deviation even when confirmed.

Two immediate corrections in one task, or recurrence of the same trigger
across tasks, is an upstream contract or pre-run defect. Fix the source rule
at Paul's gate; do not normalize the exception.

## Ordinary coordination

A `DECISION REQUEST` uses only this verdict vocabulary:

- `CONTINUE`: resume from the step Claude names.
- `REVISE`: execute Claude's replacement instructions.
- `REVERSE`: Claude restores the worktree against the recorded baseline.
- `REDUCE SCOPE`: freeze everything outside a narrower replacement contract.
- `REQUEST USER AUTHORIZATION`: take the decision to Paul.
- `STOP`: end the task and preserve the review surface.

Do not mix these with `CORRECTION REPORT` verdicts.

The task-start branch head plus the review diff is the recorded checkpoint.
Per-increment git checkpoints remain deliberately absent because Codex is
barred from git and the diff must stay reviewable. Where multiple approved
increments share a file, Claude performs a selective edit if reversal is
needed. Live-tree writes have no reversible checkpoint and remain halt-only.

## Structured ledger

The canonical ledger is SQLite:

`.claude/skills/codex-executor/scripts/coordination_ledger.py`

Default user path:

`C:\Users\pgoff\.claude\state\codex-executor-ledger.sqlite3`

It records UTC time, run id, task slug, event type, stable trigger key,
verdict, occurrence count, and a sanitized JSON payload. Prompt, output,
message, note, and evidence fields are stored only as SHA-256 plus byte count;
secret-named fields are redacted. Inserts use an immediate transaction, so
duplicate detection remains reliable across concurrent sessions.
Every new `dispatch` event requires `model`, `effort`, and `tier` in its
payload, each as a non-empty string; `effort` is value-pinned to exactly
`xhigh` and `tier` to exactly `priority` — the ledger rejects downgraded
values at insert and `audit` flags pre-existing violations (Paul
2026-08-09). Every new `signoff` event requires a
verdict from the `DecisionVerdict` vocabulary in `coordination_contract.py`.
Terminal node outcomes carry a failure attribution (augmentation roadmap
P0.2, Paul-directed, 2026-08-10): a node that ends blocked, ends failed, or
is sent back for rework is recorded as `node_blocked`, `node_failed`, or
`node_rework`, and every such event requires an `attribution` payload field
naming exactly one failure class — `spec-misread` (the lane misunderstood or
dropped part of the specification), `coordination` (a handoff or inter-lane
alignment failure), `verification` (a check missed or misjudged a defect),
or `infra` (environment, sandbox, tooling, or network failure). The
vocabulary mirrors the MAST taxonomy so local failure distributions compare
to published ones. The ledger rejects a tagless or off-vocabulary record at
insert; `audit` flags rows that bypassed the gate.
Receipt and invariants events (Paul 2026-08-10): a `receipt` event
requires `spec`, `receipt` (both stored as sha256+bytes fingerprints),
and a strict-bool `verified` — Fable's receipt-verification verdict, a
recorded judgment, not a constraint-match proof. `audit` flags
post-epoch (≥ 2026-08-11 UTC) dispatches lacking a receipt event in
their window as `dispatches_missing_receipt` — a PRESENCE check only;
receipt quality is measured by P5.1 plants. An `invariants` event
requires a non-empty list of non-empty strings, stored verbatim (never
fingerprinted); `coordination_cli.py invariants <ledger> --run-id <id>`
prints the latest pinned list byte-exactly for mechanical quoting into
dispatches. Pins are immutable: mid-run re-pinning requires an explicit
revision recorded as a decision with its reason.
Receipt hygiene (Paul 2026-08-11): pass the TRUE dispatch and reply
texts as the `spec` and `receipt` values — the fingerprint is only as
honest as its input; a pointer string fingerprints the pointer, not the
artifact. Sequence strictly register → verify receipt → record receipt
event → register the next dispatch: batch-registering dispatches closes
the earlier ones' receipt-coverage windows permanently.
`repeated_triggers(minimum=2)` is the amendment signal; informational events
do not count as recurring defects.

Manual commands:

```powershell
python .claude/skills/codex-executor/scripts/coordination_cli.py `
  record <ledger> --run-id <id> --task-slug <slug> `
  --event-type dispatch --trigger-key <stable-key> `
  --payload '{"model":"gpt-5.6-sol","effort":"xhigh","tier":"priority"}'

python .claude/skills/codex-executor/scripts/coordination_cli.py `
  repeats <ledger> --minimum 2

python .claude/skills/codex-executor/scripts/coordination_cli.py `
  audit <ledger> --strict
```

`audit` prints one deterministic JSON object covering missing dispatch
registration, missing dispatch provenance, invalid signoff verdicts, terminal
node events missing attribution, post-epoch dispatches missing receipt
events, and runs with no episode events, plus an
informational per-run `run_metrics` section (per-node latency, token counts
where recorded, closed-state, and — with `--glassbox-dir <events-dir>` —
glassbox run duration and serial-spine vs parallel-side totals). Without `--strict` it reports findings with exit 0;
with `--strict` it exits 1 when any finding is present.
Runs containing only the closed non-dispatch allowlist
(`fable_attempt_started`, `fable_attempt_finished`, `sol_rewrite_started`,
and `sol_rewrite_finished`) are reported separately as exempt non-dispatch
runs. Generic coordination lifecycle events such as `configured`, `pause`,
and `clear` are not exempt because Codex runs can also emit them. Any other
event type makes the run subject to the dispatch requirement. Runs with no
episode events remain visible but are informational and do not affect
`--strict`.

Never store credentials, authentication material, or private source content in
the ledger.

## Fable review retry controller

This is an explicit review route, not an automatic step for every build.
Moneyball's automatic paid-model use remains limited to the user-authorized
narrative route.

Canonical files:

- controller:
  `.claude/skills/codex-executor/scripts/fable_sol_retry.py`
- adapters:
  `.claude/skills/codex-executor/scripts/fable_sol_adapters.py`
- command:
  `.claude/skills/codex-executor/scripts/fable_sol_cli.py`
- usage:
  `.claude/commands/fable-sol-retry.md`

Routing:

1. Fable receives the current prompt and returns output, actual reasoning
   backend, a completed-review marker, and structured flags.
2. Any backend containing `opus` rejects that attempt.
3. Any review flag rejects that attempt.
4. Sol receives the original and current prompts, prior output, flags, retry
   reasons, and attempt number.
5. Sol revises the prompt without weakening its objective, constraints, scope,
   acceptance criteria, safety requirements, or higher-priority instructions.
6. Fable receives the revised prompt for a fresh attempt.
7. Acceptance requires a completed review, no flags, and no Opus selection.

Empty, unchanged, or previously attempted rewrites fail. Incomplete review
fails closed. Five attempts is the default hard limit; exhaustion retains full
attempt history and returns control to Paul.

The default concrete Sol adapter invokes the installed Codex CLI as
`gpt-5.6-sol`, xhigh, priority, read-only, ephemeral, with schema-constrained
output. Process adapters accept JSON argv arrays and use `shell=False`.

The paid Anthropic Fable adapter requires both an API key file and
`--allow-paid-api`. A custom Fable process can be supplied instead. Fable is
never invoked merely because the controller module was imported.

`fec/members/b5_narratives.py` now uses Fable as its documented default, keeps its
existing `--allow-paid-api` gate, detects the actual returned backend, and
routes every Opus selection, refusal, or three-section format failure through
Sol. The previous direct Opus retry is removed. Rare Sol revisions are
serialized so concurrent narrative workers cannot create a fallback surge.

## Dynamic coordination

The research-derived V1 extension is additive to the canonical protocol. It
does not replace the execution contract, verdict vocabularies, Fable-Sol retry
route, or user gates.

Canonical runtime:

- types/evaluator/replay:
  `.claude/skills/codex-executor/scripts/dynamic_coordination.py`
- ordered episode storage and derived candidates:
  `.claude/skills/codex-executor/scripts/coordination_ledger.py`
- design foundation:
  `.claude/skills/codex-executor/references/dynamic-coordination-foundation.md`

The evaluator keeps exactly seven comparison names (`equals`, `contains`,
`exists`, `absent`, `range`, `changed`, `unchanged`) and five results
(`MATCH`, `BOUNDED_DRIFT`, `DIVERGENCE`, `UNKNOWN`, `REBASE_REQUIRED`).
Missing, malformed, low-confidence, or disallowed self-generated evidence
fails closed. Only the evaluator may emit `REBASE_REQUIRED`. `exists` and
`absent` remain nonterminal `UNKNOWN` before their declared sequence deadline.

The ledger stores content-bearing fields as SHA-256 plus byte count, orders
episode events by run-local sequence, acknowledges exact duplicates without a
new row, and exposes amendment candidates as a read-only derived view.
Candidates never amend a contract or create authority.

Manual commands:

```powershell
python .claude/skills/codex-executor/scripts/coordination_cli.py `
  validate-observation <observation.json>
python .claude/skills/codex-executor/scripts/coordination_cli.py `
  validate-prediction <prediction.json>
python .claude/skills/codex-executor/scripts/coordination_cli.py `
  reconcile <episode-fixture.json>
python .claude/skills/codex-executor/scripts/coordination_cli.py `
  replay <episode-fixture.json>
python .claude/skills/codex-executor/scripts/coordination_cli.py `
  episode <ledger> --run-id <id>
python .claude/skills/codex-executor/scripts/coordination_cli.py `
  candidates <ledger> --minimum 2
```

Replay is pure and report-only. It cannot invoke an executor, append an
operational event, resolve live authority, update a candidate, or reach
`COMPLETE`.

## Verification

```powershell
python -m unittest discover `
  -s .claude/skills/codex-executor/scripts -p "test_*.py" -v
```

For compile checks, `python -m py_compile` writes `__pycache__` beside the
sources regardless of `PYTHONDONTWRITEBYTECODE` — when the tree must stay
clean (it is the review surface), use
`py_compile.compile(src, cfile=<scratch path>, doraise=True)` instead.

Do not run the paid narrative generator for verification.

## Timeouts and recovery

A remote task may finish on disk after its response is lost. Before
redispatching, inspect status, diff, untracked files, and timestamps. Continue
the same thread when its id survived; otherwise use a fresh revision thread
against the existing review surface.

## Hard rules

- Code edits land only in throwaway `codex/*` worktrees.
- Codex never commits. Claude owns git; Paul owns the commit and merge gate.
- Codex may run only these explicitly named data-mutating operations when the
  contract grants them: `run_pipeline.py`, `build_media_blend.py`,
  regeneration, and workbook writes by the pipeline's current writer.
- A pipeline run must target the live tree explicitly. Resolve `ROOT` from
  `MONEYBALL_ROOT` or the imported `fec/paths.py` and verify it before step
  one.
- Claude performs pre-run checks: Excel closed, no live jobs, and a baseline
  captured for rank comparison.
- Still barred: preregistered `--look` consumption, GATE-2 or
  `collector_supervisor.py`, retired `apply_*` one-shots, and D2/legacy dedup
  deletion without Paul's explicit gate.
- Never put API keys, tokens, authentication files, or other secrets in a
  prompt or ledger entry.
- Every dispatched task receives independent Claude review before it reaches
  Paul.

## Copy sync

The repository copy is canonical. After a ratified change, sync:

- this `SKILL.md`;
- `.claude/commands/codex.md`;
- `.claude/commands/fable-sol-retry.md`;
- `.claude/skills/codex-executor/scripts/`;
- `.claude/skills/codex-executor/references/`.

User scope:

`C:\Users\pgoff\.claude\skills\codex-executor\`

and:

`C:\Users\pgoff\.claude\commands\`
