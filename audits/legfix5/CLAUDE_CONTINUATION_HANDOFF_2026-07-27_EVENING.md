# Claude continuation handoff — legfix5, evening 2026-07-27

Generated 2026-07-27 evening, America/Chicago. Supersedes the state section of
`CLAUDE_CONTINUATION_HANDOFF_2026-07-27.md`; that file's **policy is unchanged and
still binding**. This session closed out full-text collection and a five-agent
audit-repair pass. The next session is for **debugging / continued hardening**,
not collection.

## Non-negotiable policy (unchanged, still binding)

- Congress.gov Advanced Search is the discovery authority. Quorum is a 44-row
  recall floor only (verified this session: discovery clears it 44/44).
- Preserve every candidate, membership, exclusion, failure, restoration. Never
  silently delete or overwrite evidence.
- Missing or incomplete evidence is always `flagged`, never `junk`.
- Do not score, sync, promote, or write the main corpus until every gate passes
  and the user explicitly authorizes integration.
- Ask before substantive changes; present findings and wait. The apply step is
  the gate.
- Every process emits to the shared Glass Box stream
  (`C:\Users\pgoff\.claude\glassbox\events`) or it is not acceptable.
- Never evade a Cloudflare challenge. Blocks are time-windowed; wait them out.

## What is DONE

- **Full-text collection: COMPLETE, 18,557/18,557.** 18,555 pages collected +
  2 bills with no published text (`119:hr:9821`, `119:hr:9900` — BillStatus
  `text_versions=[]`, an authoritative absence, recorded in the generation's
  `accounted_no_text.json`). Generation:
  `audits/legfix5/congress_advanced_pages_20260725/text_relevance_httr_full_20260727z`.
  `overall_progress.json` is `completed`. No collector or watcher loops remain
  running.
- **Audit-repair pass COMMITTED** (`852eb62`, `a719807`, `e09db5e`, `62d477e`),
  126/126 tests. The safety gates that used to *assert* now *derive*. The whole
  legfix5 lane is now tracked in git — a resync can no longer silently revert it.
- 18 `-PaulComputer` conflict copies quarantined to
  `fec/_quarantine_paulcomputer_20260727/` (reversible; README inside).

## The single most important correction to prior belief

**Culling is NOT blocked by text, and finishing collection changed nothing.**
Verified by running the contract's own predicates over all 18,557 candidates:
`category_evidence` is empty on every row → `category_audit_ready = 0` →
`semantic_review_ready = 0` → `membership_is_finalizable` is False corpus-wide.
Separately, only 57 of 64,004 memberships carry any decision (62,628 unresolved).
Culling today reproduces the existing all-flagged partition and teaches nothing.

**Summaries were never a missing fetch.** We already HOLD the summary prose:
58.5% of BillStatus records carry `/summaries` text. Congress.gov
`/bill/.../summaries` is a 404. The contract stamps GovInfo-BillStatus summaries
`available_pending_congress_gov_fetch` (not `available`) purely because it
demands congress.gov provenance — the same rule that bars GovInfo XML from the
full-text gate. So this is a **provenance decision**, not a collection job.

## Real blockers before culling is worth running (ranked)

1. Adjudicate the 63,947 undecided memberships. Largest by far (99.9%).
2. Perform the 19-category review (populates `category_evidence`).
3. Decide summary provenance (does GovInfo-BillStatus count as evidence of
   record for summaries?). Same class as the open GovInfo-full-text question.

None is sufficient alone. See `fec/LEGISLATION_19_CATEGORY_ADJUDICATION_DESIGN.md`
and the queue at `audits/legfix5/category_review_queue/` (64,004 rows, tiered).

## Do this FIRST next session (cheap, additive, unblocks honest counts)

**Rebuild candidate evidence against the live receipts.** ~13,700 already-collected
pages are stranded because evidence still points at the old 2,886-receipt
`text_relevance_httr_full_stage_20260726`. Use
`fec/rebuild_evidence_when_collection_completes.ps1` or call
`build_legislation_candidate_evidence.py` directly with
`--full-text-receipts …/text_relevance_httr_full_20260727z/receipts`. It writes
a NEW generation, mutates nothing. Then run `fec/audit_pre_culling_inventory.py`
for the lay of the land.

**Correct evidence input is `evidence-20260727a`, NEVER `-r`.** `-r` was built
from OneDrive conflict copies and declares discovery hashes that are not on disk.

## Pending USER decisions — do not fabricate

- `role_weight_policy_approval.json`, `legislation_workbook_computation_policy_approval.json`
  are absent (manual_inputs holds only the REQUEST). Four of five items are
  already answered by `Moneyball Main Version - Blended.xlsx` (17 efficiency
  slots, CU Tax = honest zero, legacy decay 119:1/118:.8/117:.64/116:.512, press
  misalignment on 5 members). Only CFPB bill routing is genuinely open
  (CU/CW = manual letters, CV/CX = audited dead-zero, implementation registry
  empty by design). An agent offered to draft the two files from workbook-verified
  legacy values; the user has not yet said go.
- Rank-drift tolerance defaults to zero (any movement blocks) — user's call.
- Shadow recompute requires `authored_by:"human"` on changed baseline
  attributions — machine boilerplate no longer counts.

## Landmine: self-pinning producers

`build_accepted_legislation_workbook.py`,
`audit_postrefresh_behavior_stance_semantics.py`,
`audit_postrefresh_planning_dashboard_semantics.py` hash their own source; any
byte edit flips downstream readiness to STALE_OR_INVALID and needs a producer
re-run. Two agents hit this today. **Grep `Path(__file__).resolve()` near a hash
before editing any fec file.** The workbook producer's capability receipt is
already stale from this pass's `scoring_eligible` fix — it needs a re-mint
(which runs the producer and writes under audits/, so it is a user-authorized
action).

## Ops surface

- Glass Box codex view: `fec/open_glassbox_codex.ps1` + desktop shortcut
  "GLASS BOX (codex)". Binds `overall_progress.json` FIRST. Use `-Command`,
  never `-File` (array params do not bind under `-File`).
- Chrome harvest profile `C:\Users\pgoff\.melange\chrome-harvest`, DevTools 9222.
- R 4.6.0 at `C:\Program Files\R\R-4.6.0\bin\x64\Rterm.exe`; Python 3.12 at
  `C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe`. No pytest;
  runner is `python fec/tests/run_focused_tests.py <files...>`.
- PowerShell 5.1 `Out-File -Encoding utf8` writes a BOM that breaks R and git —
  write those files with `[System.IO.File]::WriteAllText(path, text, UTF8Encoding($false))`.
