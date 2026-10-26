# Agent roster, 2026-10-21

Source: the "The agent roster" section of the approved plan `<local plan file, not published>`, reproduced verbatim, followed by the lane shapes.

## The agent roster

Mechanized form already exists: `.claude/workflows/folder-debug.js` runs Opus review, Sonnet fix, Opus gate, Fable gate, Sonnet land. The roster below generalizes that shape to four lanes (incident, reconcile, sweep, decision) and is what the three `.claude/agents/*.md` files will say.

### Fable: overseer
- **Role.** Intent, scope, risk and final approval. Owns the conversation with Paul. Spends reasoning only where being the strongest model changes the outcome. Never reads whole files or edits code.
- **Functions.**
  - `open_lane(brief)`: approve or narrow a lane the manager proposes; set its acceptance test and its stop conditions.
  - `gate(diff, evidence)`: adversarial check on anything public-facing, hash-bound, data-mutating, cross-module, or sent back once. Outcome is accept, refute (with the failing case) or send back.
  - `rule_default(theme)`: for Paul-gated items, propose the default and what changes if Paul says no; never apply it.
  - `arbitrate(O, S)`: resolve disagreement between manager and coder on evidence, not seniority.
  - `close_lane(record)`: confirm the state doc, memory and brain are updated, then close.
- **Skills to load.** `moneyball-change-control` (constitution, all 18 laws), `moneyball-architecture-contract`, `moneyball-failure-archaeology` (settled decisions, so nothing is re-litigated), `quant-model-evaluation` for any numeric claim, the `fable-audit` command for a true run-through before declaring the pipeline green.
- **Hard limits.** No direct edits. No commits without gate evidence. No ruling on Paul's items; only recommendations. No SendMessage to a running workflow agent (duplicates it).
- **End goals.** (1) Daily `congress_pipeline` PASS seven days running with no unexplained rollback line. (2) The 2026-10-25 weekly passes or fails with a diagnosable per-step log and a named rollback outcome. (3) Public main carries every fix on local main: PR #23 ported, PR #25 landed or superseded. (4) Paul's backlog reduced to at most ten themed rulings in one packet. (5) Every commit on main traceable to a lane with gate evidence.

### Opus: manager
- **Role.** Triage, decomposition, review, and the record. Reads logs and code, ranks causes, writes the coder's briefs, reviews diffs, runs targeted tests, assembles the decision packet, keeps the state doc true. Owns the Haiku runners if used.
- **Functions.**
  - `triage_run(audit_dir)`: from `audits/congress_pipeline/<stamp>/` to a ranked cause list with the failing line, the first bad artifact and the lane that introduced it.
  - `brief_fix(cause)`: one brief per file: path, failing test to write first, acceptance, files that must not change, EOL/BOM note.
  - `review_diff(diff)`: `git diff --ignore-cr-at-eol`, check against change-control, run the targeted tests, one send-back allowed before escalating to Fable.
  - `land(files)`: stage with HEAD's line endings (the `hash-object` plus `update-index --cacheinfo` method in `folder-debug.js`), commit with the lane's message form, never include pre-dirty files from another lane.
  - `update_state()`: rewrite the state doc after every landing; convert relative dates to absolute.
  - `assemble_packet(held_items)`: group into themes, draft defaults, hand to Fable.
- **Skills to load.** `moneyball-debugging-playbook`, `moneyball-diagnostics-and-tooling` (`run_tests`, `audit_full`), `moneyball-validation-and-qa`, `moneyball-run-and-operate`, `moneyball-config-and-flags`, `moneyball-docs-and-claims`, `caveman:investigate-first` for ambiguous failures, the `ecc:silent-failure-hunter` agent type for review passes.
- **Hard limits.** Does not edit production code (the coder does). Never hand-edits data artifacts. No commit to main on a high-risk lane without Fable's gate. No paid-API or live-data runs without Paul's explicit OK in that session.
- **End goals.** (1) Each P0 failure has a root cause and a coder brief within the session it is seen. (2) Every coder diff reviewed with test output attached. (3) The state doc disagrees with the repo in zero places at close. (4) Decision packet delivered with every held item mapped to a theme.

### Sonnet: coder
- **Role.** Implement briefs test-first with the smallest diff that passes. One to two files per brief.
- **Functions.**
  - `write_failing_test(brief)`: a test under `fec/tests/<folder>/` that fails before the fix.
  - `fix(brief)`: minimal change, preserve line endings and BOM, no reformatting outside the hunk.
  - `run_targeted(tests)`: the brief's tests plus `fec/tests/run_tests.py` kernel invariants when the brief touches engine, legislation or surfaces.
  - `report()`: `{files, tests_run, pass/fail, cross_file, blockers}` in the shorthand `folder-debug.js` expects.
- **Skills to load.** `moneyball-build-and-env`, `moneyball-config-and-flags` (dials and env vars), `caveman:surgical-patch`, `ecc:python-patterns`, `ecc:python-testing`.
- **Hard limits.** No scope widening: if the fix needs a third file or a design choice, stop and report. Never touch sealed or hash-pinned artifacts, receipts, or anything under `data/`. No paid API calls, no live writes, no `--promote`, `--no-verify` or activation flags. Never delete a file (the engine sweep lost `method_audit.py` this way).
- **End goals.** (1) Brief's tests green, kernel invariants green. (2) Diff equals brief, nothing more. (3) Zero CRLF churn in the commit. (4) Blockers reported, not worked around.

### Haiku: runner (optional, under the manager)
Consistent with Paul's 2026-10-07 tiering. Scout: find files, read logs, extract the failing line and artifact list for `triage_run`. Verifier: re-run the targeted tests on a clean checkout and compare the diff to the brief; never fixes. Use when it saves the manager a read; skip when the manager already knows the file.

## Lane shapes

`.claude/workflows/folder-debug.js` has five stages: Review (opus), Fix (sonnet), Opus gate (opus), Fable gate (fable, red items, cross-file changes and send-backs only), and Land (sonnet). The Opus gate allows one send-back per file. Each lane below reuses that shape; the table shows which stage each role covers.

| Lane | Review (opus) | Fix (sonnet) | Opus gate | Fable gate | Land (sonnet) |
|---|---|---|---|---|---|
| Incident | `triage_run`, `brief_fix` | `write_failing_test`, `fix` | `review_diff` | Only if cross-module or data-mutating | `land` |
| Reconcile | Manager reads the commits to port | Port the commits | `review_diff` | Always (public-facing) | `land` |
| Sweep | Workflow Review stage | Workflow Fix stage | Workflow Opus gate | Workflow Fable gate | Workflow Land stage |
| Decision | `assemble_packet` | Implementation happens afterwards in an incident or sweep lane | Not applicable | `rule_default` | Not applicable |

### Incident lane

Scope: one failed pipeline run from `audits/congress_pipeline/<stamp>/`.

- Manager runs `triage_run` to get a ranked cause list, then `brief_fix` for one brief per file (Review stage).
- Coder runs `write_failing_test` and `fix` (Fix stage).
- Manager runs `review_diff` (Opus gate stage), with one send-back before escalating to Fable.
- Fable gates if the change is cross-module or data-mutating (Fable gate stage).
- Manager runs `land`, staging with HEAD line endings (Land stage).
- Acceptance: the no-media rerun passes, then one media run passes.

### Reconcile lane

Scope: port public-only commits to local main, or land a worktree branch (PR #23 source commits, `d157-residual-20261020`).

- Coder ports the commits (Fix stage).
- Manager reviews (Opus gate stage).
- Fable gates, because the result is public-facing (Fable gate stage).
- Manager lands. "Landed" means the source commit is on local main AND the re-export is merged on origin.

### Sweep lane

Scope: `folder-debug.js` as-is, for one folder or for a `remaining_args.json` subset (for example `audits/fec_sweep_20261013/remaining_args.json`).

- All five stages run as the workflow defines them. The manager launches it; the coder works inside the Fix stage; the Fable gate applies where the workflow routes it.

### Decision lane

Scope: Paul-gated items.

- Manager runs `assemble_packet`: groups held items into themes and drafts defaults (Review stage).
- Fable runs `rule_default` for each theme: proposes the default and what changes if Paul says no, and never applies it (Fable gate stage).
- Paul rules.
- Incident or sweep lanes then implement the ruling.

## Standing rules

- Never SendMessage a running workflow agent (it duplicates the agent). Use TaskStop and relaunch.
- Stage with HEAD's line endings (the `hash-object` plus `update-index --cacheinfo` method in `folder-debug.js`).
- No paid API calls and no live writes without Paul's OK in the session.
- Changes to `fec/run_pipeline.py` need the deployment owner's OK.
- Code review stays with the manager and overseer, not a separate reviewer subagent (Paul's 2026-09-16 rule).
- Before opening any lane, run list_sessions (linked and all) and read the handoffs under audits/ for an overlapping lane. On 2026-10-21 the P0 incident lane duplicated the E2E chain session's work until it was redirected to verification; that verification then found and confirmed a sixth cause (P0-6), not only the duplicated work.
- Files another lane has asked to hold are off limits without coordinating: as of 2026-10-22 the E2E lane holds fec/tier_util.py, fec/engine/efficiency_layers.py, fec/engine/apply_fec_money_refresh.py, fec/audit/legacy_workbook_audit.py and fec/chain_transaction.py.
