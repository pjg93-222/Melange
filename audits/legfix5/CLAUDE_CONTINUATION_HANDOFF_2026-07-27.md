# Claude continuation handoff: six-year legislation acceptance

Generated: 2026-07-27 America/Chicago. Supersedes `CLAUDE_CONTINUATION_HANDOFF_2026-07-26.md`, which remains on disk as evidence. Policy from that document is unchanged and still binding; only the state section below is newer.

## Non-negotiable policy (unchanged)

- Congress.gov Advanced Search is the discovery authority. Quorum is a 44-row recall floor only.
- Preserve every candidate, membership, exclusion, failure, and restoration. Never silently delete or overwrite evidence.
- Missing or incomplete evidence is always `flagged`, never `junk`.
- Decisions are membership-level `(canonical_key, query_id)`. Global junk requires every membership explicitly excluded with no keep, flagged, legacy, or restored edge.
- Do not score, sync, promote, or write the main corpus until every gate passes and the user explicitly authorizes integration.

## What changed on 2026-07-27

### GovInfo official-XML lane — COMPLETE

Two immutable full runs under `audits/legfix5/govinfo_bill_xml_versions/runs/`:

| Run | Dispatched | Accepted | Quarantined | Retry waits |
|---|---|---|---|---|
| `full-18440-20260727a` | 18,440 | 18,366 | 74 | 0 |
| `full-18440-20260727b` | 18,440 | **18,406** | **34** | 0 |

Plan SHA-256 `b4f85fcc986e5a4bfd6136ae5ce0c96f1fecda231efa0029a77a3c0f7cefb11b` stable across both. Every dispatch reconciled to exactly one terminal receipt. Object store: **18,406 documents, 1.74 GiB**, content-addressed; a 400-file random rehash found zero mismatches.

Run B is authoritative. Run A is preserved as the pre-fix evidence.

### The 34 residual quarantines, fully diagnosed

| Count | Cause | Evidence lost |
|---|---|---|
| 28 | USLM-format enrolled bills. USLM is a *different official schema* — identity is `citableAs`/DC title (`"119 HR 2483 ENR"`), not `<legis-num>`. The validator only knows the legacy Congress DTD. | No — legacy `/xml/` sibling accepted |
| 4 | PLAW `/xml/`. **GovInfo publishes public laws only under `/uslm/`**; `/xml/` 302s to `/error` for *every* PLAW package. Phantom URLs in the plan. | No — `/uslm/` accepted |
| 1 | `116:s:309` — **upstream GPO error**: `BILLS-116s309is` header says "115th CONGRESS" while `legis-num` (S. 309), title, and action date (2019-01-31 = 116th) all confirm the right bill. User decision: leave flagged, do not override. | Yes |
| 1 | `118:s:2051` (`eah`) has no `<metadata>`/`dublinCore` block at all — no identity surface. Correctly fails closed. | Yes |

**`116:s:309` is the only candidate corpus-wide with zero accepted official text.**

### Validator fix (the `eah` gap)

`amend.dtd` carries **no `<legis-num>`**. Engrossed-amendment identity lives only in the Dublin Core title (`"116 S178 EAH:"`, `"117 HR 1437 EAH:"` — spacing varies). Added `AMENDMENT_DC_TITLE_RE` binding congress + measure + **version code**, which is strictly stronger than the `<legis-num>` path it substitutes for. Guarded by `and not measure_values`, so it only fills the gap and never weakens an existing accept path. Recovered **40 of 41**.

### New components (all in `fec/`, untracked)

| File | Purpose | Tests |
|---|---|---|
| `build_legislation_candidate_evidence.py` | **The missing producer** for `acu-legislation-candidate-evidence-v1`. The contract defined it and the culling engine consumed it, but nothing built it. | 12 |
| `build_legislation_membership_decisions.py` | Projects resolved review-ledger rows into membership decisions without upgrading them. | 9 |
| `audit_legfix5_coverage_reconciliation.py` | Reconciles every evidence source against the discovery universe. | 6 |
| `tests/run_focused_tests.py` | Dependency-free test runner. **There is no pytest on this machine**; this shims `raises`/`mark.parametrize`/`tmp_path` and also runs `unittest.TestCase` suites. | — |
| `watch_govinfo_collector_glassbox.ps1` | Read-only live Glassbox watcher for a collector run. | — |
| `emit_legfix5_pipeline_glassbox.ps1` | Registers completed pipeline stages into the Glassbox from their real receipts. | — |

### Culling engine repaired: 9/11 → 15/15

1. **`membership_universe_mismatch`** — evidence `membership_query_ids` must exactly equal the discovered universe; mismatch flags every affected row and blocks finalization.
2. **Rerun idempotency** — `new_junk_exclusions_appended` is per-invocation, not generation state. Embedding it in the sealed manifest made an identical rerun collide. Moved to `generations/<id>/invocations/<sha>.json`; still returned to callers. **Verified idempotent on the real 64,004-row corpus.**
3. **Tamper test** wrote CRLF on Windows and tripped the CRLF guard before the hash guard. Test now writes LF; a separate CRLF test was added.

### Pipeline artifacts produced

| Stage | Location | Result |
|---|---|---|
| Candidate evidence | `audits/legfix5/candidate_evidence/evidence-20260727a` | 18,557 envelopes, sha `eb497ebb…` |
| Membership decisions | `audits/legfix5/membership_decisions/decisions-20260727a` | 57 emitted of 59 resolved, 2 dropped, sha `205d86fb…` |
| Reversible culling | `audits/legfix5/reversible_culling/culling-20260727a` | generation `241cbbb1…` |
| Coverage reconciliation | `audits/legfix5/coverage_reconciliation/recon-20260727a` | `COVERAGE_GAPS_PRESENT` (7 pass, 2 fail) |
| Staged integration gate | `audits/legfix5/staged_integration/plan-20260727a` | `BLOCKED`, 13 blockers |

**Culling result: 64,004 memberships → 64,004 flagged, 0 junk, 0 keep. 18,557 candidates → all flagged.** All 8 gates true, both ledgers 0 bytes, nothing deleted. Flag reasons: 63,947 `missing_membership_decision`, 57 `decision_not_finalizable_against_official_evidence`.

User-facing review file (64,004 rows, with `review_decision` / `review_reason` / `reviewer` columns):

`audits/legfix5/reversible_culling/culling-20260727a/generations/241cbbb105a623409afb3cdbb35bee30598a696ad76652a85a837fdd48036af1/flagged_memberships.csv`

## Evidence coverage (18,557 candidates)

| Signal | Count |
|---|---|
| Official title available (Congress.gov) | 18,557 |
| Relationships complete or not required | 18,557 |
| Stage available (BillStatus) | 14,854 |
| Congress.gov full text accepted and physically reverified | **2,886 (15.6%)** |
| Summary officially unavailable (authoritative absence) | 4,122 |
| Summary present in BillStatus, not yet fetched from Congress.gov | 10,732 |

## THE blocker

**The 19-category adjudication has never been performed for any candidate.** `category_evidence` is empty corpus-wide, so `membership_is_finalizable` returns False universally *regardless of text coverage*. This — not text collection — is what gates final culling. Collecting more text will not move it.

Second blocker: 15 historical probes covering 598 identifiers remain uncollected (`historical_probe_gate_complete: false`).

## Two findings that correct earlier records

1. **The membership edge gap is larger than recorded.** `progress.json` recorded `raw_coverage_edges_not_in_effective_review_ledger: 748`. The true disagreement is **2,225 edges**:
   - **1,771** discovery edges absent from the review ledger — 748 from `credit_union_headline_recall_net` (the previously recorded figure counted only this one query) and 1,023 from `title_alias_probe_*` queries. Affects 1,620 candidates. These are likely excluded from the effective ledger by design (non-dispositive probe/recall record kinds), but that has not been confirmed.
   - **454** review-ledger edges absent from discovery, in five real scoring categories (`cdfi_fund` 175, `mortgage_lending_housing` 138, `examination_supervision` 67, `technology_emerging_issues` 62, `fraud_prevention` 12). These may indicate discovery under-coverage and deserve a decision.
   - Arithmetic reconciles exactly: 64,004 − 1,771 + 454 = 62,687.
   - The culling run reads discovery directly, so all 64,004 are in the partition. Nothing is lost — but a review driven off the ledger would never see the 1,771.

2. **The staged integration gate requires 6 gates, not 27.** The 27-item `REQUIRED_INTEGRATION_GATES` list in the contract module is used elsewhere. `build_legislation_staged_integration_gate.py` requires: `coverage_reconciliation`, `culling_validity_reversibility`, `evidence_completeness`, `recomputation`, `regression_currentness_hash_binding`, `role_attribution`.

## Architectural catch — do not assume otherwise

`validate_candidate_evidence` requires **congress.gov** URLs for `full_text`. **GovInfo XML does not satisfy it.** GovInfo supplies version inventory and official text; the evidence-of-record path remains the Congress.gov httr archives (2,886). Do not claim the GovInfo run closes the full-text gate.

## Verified state

- **88/88** focused tests across nine suites (`python fec/tests/run_focused_tests.py <modules...>`).
- Production baseline: **33/33 frozen copies intact, 0 drift**; **10 of 33 live sources drifted** since the 2026-07-26 freeze. That is an integration blocker, not data loss.
- Zero tracked git files modified; all legfix5 work is untracked.
- No scoring, sync, promotion, or main-corpus write occurred.

## Glassbox

It is a **read-only viewer**, not a runner. A dead lane leaves a stale `running` row forever.

Critical operational note: on 2026-07-26 the open window was launched with `-EventsDirectory` pointed at the **stopped R/httr lane's** event directory, so events emitted to the default stream were invisible in it. Always confirm what a viewer instance is actually reading:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'open_glassbox_process_matrix' } | Select-Object ProcessId,CommandLine
```

The current viewer (correct stream) was launched as:

```powershell
& '.\fec\open_glassbox_process_matrix.ps1' -EventsDirectory 'C:\Users\pgoff\.claude\glassbox\events' -ProgressJson @('.\audits\legfix5\glassbox_progress_20260727.json') -ArtifactPath @('<culling generation dir>','<govinfo accepted receipts dir>') -WindowTitle 'GLASS BOX - LEGFIX5 GOVINFO + CULLING 20260727'
```

Array parameters must be passed via `-Command`, not `-File`; `-File` will not bind them and the window exits immediately.

## Recommended next order

1. Decide the 1,771 / 454 edge question — is the effective ledger's exclusion of recall-net and title-alias probes intended, and are the 454 orphan edges a discovery gap?
2. Decide how the 19-category review will be produced. This is the only path that moves any membership out of flagged.
3. If routing through the Claude lane: configure a transport privately, set a hard dollar cap, send only the deterministic flagged queue, and keep `human_ratification_required`.
4. Extend the Congress.gov full-text lane beyond 2,886, or decide that GovInfo text may serve as evidence of record (a contract change, not an implementation detail).
5. Only then: recomputation, rank drift vs the 33-file baseline, regression currentness, and the staged gate.
6. Stop before any score/sync/promotion/mainframe write pending explicit authorization.

## Safe commands

From `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`:

```powershell
& 'C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe' fec\tests\run_focused_tests.py fec\tests\test_run_reversible_legislation_culling.py fec\tests\test_collect_govinfo_bill_xml_versions.py fec\tests\test_build_legislation_candidate_evidence.py fec\tests\test_build_legislation_membership_decisions.py fec\tests\test_audit_legfix5_coverage_reconciliation.py
```
