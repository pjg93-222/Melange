# Holistic Network v1 — Evaluation & Acceptance Framework

**Date:** 2026-08-17 · **Status:** DESIGN — PROPOSED. Nothing here is ratified. Every numeric threshold is a PROPOSED pin awaiting Paul (Appendix B); registering the tests/audit checks named below, adopting this framework, and every APPLY step are Paul-gated.
**Object under evaluation:** the **first draft of the holistic network configuration** — the Phase 1–5 deliverables specified by the implementation guide `HOLISTIC_NETWORK_DESIGN_2026-08-17.md` (commit `b99c52589` on `claude/holistic-network-analysis-config-dc9e36`; sha256 md `bf15821d`, per brain STATE 2026-08-17) — plus an entry gate (G0) over the design draft itself, so "does the first draft live up to standard" is answerable at both levels Paul might mean.
**Authored:** 2026-08-17 session, after brain boot (D-011 and DE-004 are the governing precedents cited below), grounded in `moneyball-validation-and-qa`, `moneyball-diagnostics-and-tooling`, the brain procedures `verify-a-rank-moving-change` / `examine-a-findings-document`, and nine live-code anchor verifications executed today (§4, worked example).
**Frozen-vintage note:** this file lives in `audits/` and is preserved as written. Threshold pins and amendments land as a separate dated FREEZE ADDENDUM (the F1 ready-to-lock-addendum pattern), never as edits here.

---

## 0. The sufficiency rule (the one-paragraph verdict)

The first draft **lives up to sufficient standards** if and only if Gates G0–G5 all return PASS under §2's rules: every BINDING HARD bar passes (zero unexplained CU-side deltas, zero unruled config deltas, every fail-closed behavior and negative control demonstrated), every DELIVERABLE lands receipt-bearing, every fired TRIGGER has a named finding dispositioned by Paul, and the adversarial review round is complete with its CONFIRMED findings resolved. A BLOCKED bar anywhere blocks acceptance — it is never a deferral that rounds up to PASS (D-011: empty strata fail closed; verdicts mean what they say). **PASS authorizes acceptance of the draft only.** Live-surface exposure (D7), rank-chain contact, bipartisan/say-do/stance contact, and any CU-side change remain separately Paul-gated regardless of the verdict (guide §4.6; INV-2, INV-5).

This framework borrows preregistration's **freeze** (bars pinned before the build exists, so the draft can never negotiate its own bar) but not its look-accounting: engineering bars are re-runnable at will and nothing here spends a research look. The one measurement with decision semantics — the Gate-5 distribution report feeding D8 — is a decision input produced fresh per draft, not a consumable look (`moneyball-research-methodology` governs research claims; this framework governs engineering acceptance).

## 1. Imported law (what this framework inherits, with sources)

1. **Fail-closed verdicts, per-stratum.** Bars bind per stratum; strata whose preconditions are absent are BLOCKED or REPORT-ONLY-with-arming-condition, never silently passed (brain D-011, ratified 2026-08-17).
2. **Verification order for anything rank-adjacent:** baseline hashes + full board captured first → independent adversarial review of the DRAFT → revert dial proves byte-identity → mirror reproduces the shipped artifact before any counterfactual is trusted → enumerate every mover (brain CONSTRAINTS, Tooling; `verify-a-rank-moving-change`).
3. **Never weaken a bar to pass.** A failing test/floor/count is the finding; re-pinning to a ratified state is the only permitted change and it requires Paul (change-control law 7; brain Never-do).
4. **Every figure names its window and denominator in-sentence**; pooled quantities over a named fault line (party, chamber) show strata or carry an UNSTRATIFIED label (brain CONSTRAINTS, Claims; D-007).
5. **Every new artifact requires a schema guard** — required keys, coverage floor, malformed-record count, observed numbers in the detail string, incident-dated comment (`moneyball-validation-and-qa` §4).
6. **No silent caps:** every bound/cap/fallback/skip is named, printed at run time, floored in the audit where load-bearing, and carries a declared failure direction (`moneyball-validation-and-qa` §6).
7. **Byte-identity is the idempotency bar** for JSON artifacts (the 12/12 double-run precedent @f17dc2c); hash drift with no input change is an S1 regression unless proven input-driven via the input-purity recipe (`moneyball-proof-and-analysis-toolkit` Recipe 5). For xlsx artifacts the bar is a **canonical content hash** (§G2/COR-7) because openpyxl embeds wall-clock timestamps — the CU AUG artifact itself stamps `datetime.now()` at `build_multilayer_network.py:106`.
8. **Gate on tail text, not exit codes alone**: `KERNEL TESTS — N passed, 0 FAILED` / `ALL MODULES CLEAN.`; any FAILED is the finding, a higher count than documented is not (`moneyball-diagnostics-and-tooling` §1).
9. **Findings documents get the six-pass examination** (D-007; `examine-a-findings-document`), and corrections propagate to every restatement (DE-004). The causal-claims lint runs over banner-gated audits docs — evaluation reports written under this framework are in scope.
10. **Machine judgment never relabels Paul's domains.** Stance/press classification, seat rulings, and threshold pins are his; the evaluator reports and waits (ask-before-substantive-changes; press-classification-user-domain).
11. **Visible work + glassbox.** Evaluation runs are visible PowerShell where practical, and every evaluation process emits to `C:\Users\pgoff\.claude\glassbox\events` (standing rules 2026-07-24 / 2026-07-27).

## 2. Verdict system

**Bar types.**
- **HARD** — mechanical pass/fail with a stated procedure and threshold. Auto-verdicts.
- **DELIVERABLE** — a report/measurement that must exist, receipt-bearing, with named windows and denominators. Existence+integrity is mechanical; *content* judgment is Paul's.
- **TRIGGER** — an escalation condition. Firing is not failure; an un-dispositioned fired trigger is.

**Bar verdicts:** `PASS` / `FAIL` / `BLOCKED` (precondition absent — blocks the gate) / `N/A(D#)` (mooted by a cited ruling; an N/A without a ruling ID is invalid — no quiet scope-shrink).

**Stratum status (D-011 architecture):** each bar is **BINDING** now or **REPORT-ONLY with a mechanical arming condition**. Standing REPORT-ONLY strata in v1: press/HCoI holism (arms on an all-topic press corpus), social holism (arms on a broadened vendor query), amendments/committee/letter edge types (arm on their D5/D11 rulings + data), the wscale bar MEA-2 (arms on the MEA-1 report), holistic-`bpf` (arms on a D12 commissioning).

**Gate verdict:** PASS iff all BINDING HARD bars PASS, all DELIVERABLEs delivered, all fired TRIGGERs dispositioned, and the gate's negative controls demonstrated. No averaging across bars; one FAIL fails the gate.

**Re-run and invalidation:** a single unexplained failure may be re-run once to exclude read contention (`verify-a-rank-moving-change` step 10); a second failure is real. Any Gate-2 artifact change voids G3–G5 verdicts; any Gate-3 code change voids G4–G5. Verdicts are dated reads, never live invariants (examine-skill PASS 6).

## 3. ENV — preconditions (re-verified at every gate)

| ID | Bar | Type |
|---|---|---|
| ENV-1 | **Run location pinned.** All data-dependent verification runs in the live tree (or with `MONEYBALL_ROOT` pointed at it — in which case writes hit live and are said so). Worktrees have empty data planes: `fec/paths.py:7-8` roots at the parent of the imported `paths.py` (verified today; brain CONSTRAINTS). Receipt: print resolved ROOT per run. | HARD |
| ENV-2 | **Clean shell proven.** `env_dials.py` "shell clean" before every baseline and every CU-side gate; `NET_CONFIG` unset for CU-side runs, set to `holistic` only for holistic-side runs, never ambient. Note the live trap: `run_tests.py:163-166` binds whatever graph the shell's config selects — kernel gates run in a `NET_CONFIG=holistic` shell would silently test the wrong graph (and its `0<w<=10` sanity bound is a CU-vintage pin that must not be weakened for holistic weights; holistic invariants get their own config-scoped tests). | HARD |
| ENV-3 | **No concurrent writers.** Check for Paul's live python jobs + fresh artifact mtimes first; never concurrent with the weekly refresh; Excel closed for workbook operations; one writer per family (guide §6.3). | HARD |
| ENV-4 | **Baseline manifest FIRST.** Before any holistic code or artifact lands: sha256 of every `congress_cosponsor_network_*.xlsx`, `dashboard_data.json`, `bipartisan.json`, `ranks_python.json`, plus the full 533-board dump to the eval record (imported law 2, step 1). | HARD |
| ENV-5 | **Sandbox recipe for plants.** Negative controls that plant files run only in a sealed scratch `MONEYBALL_ROOT` root with copied minimal inputs (`run_legislation_network_dependents.py` precedent) — never in the live tree. | HARD |
| ENV-6 | **Glassbox emission.** Every evaluation run emits `{schema_version, timestamp_utc, lane, source, run_id, kind, status, stage, summary, detail, current, total}` events to the shared stream; the eval record names the run_ids. | HARD |

## 4. Gate G0 — the design draft (runnable now)

| ID | Bar | Type |
|---|---|---|
| DOC-1 | **Anchor audit.** Sample ≥12 Appendix-A anchors, mandatory-including every selection-surface anchor (`select_network_file`, `load_network_directed`, augmenter base-pick, bundle selection). 100% resolve against live code, or each miss is adjudicated (drift vs error). | HARD |
| DOC-2 | **Decision traceability.** Every code-shaping choice in guide Phases 2–4 maps to a ruling D1–D12 or a pinned invariant; zero orphan choices. | HARD |
| DOC-3 | **Contradiction sweep vs the brain.** Guide statements checked against CONSTRAINTS/DECISIONS; conflicts adjudicated under boot rule 7 (CONSTRAINTS > DECISIONS > STATE > session text). | HARD |
| DOC-4 | **Ruling record.** D1 recorded with attribution; open decisions enumerated with gate dependencies (D3/D6 → G1–G2; D10 + D2 → G3; D7 → G4; D8 → G5; D9 → HON; D11/D12 → scope labels). | HARD |

**Worked example — executed 2026-08-17 (this session, worktree `holistic-network-config-60c11c`, clean checkout of main-lineage code):**

- DOC-1 **partial: 9/9 sampled anchors exact.** `select_network_file :232-237` ✓ (glob + AUG-prefer + newest mtime); `load_network :238-255` ✓ (roster filter, mean-symmetrize, memo `_c['adj']`; bonus contract: every member keyed, isolated → `{}` at `:252`); `select_network_file_directed`/`load_network_directed :256-292` ✓ (non-AUG glob; AUG direction documented as a sort artifact); `build_P :305-312` ✓ (`p = w·cpf·σᵥ/(w·cpf·σᵥ+6)`); augmenter base-pick `:31-32` ✓, 3-col read `:35-37` ✓, kernel-inverse `:59` ✓, HCoI isolates-gate `:68` ✓, output `:100-108` ✓; `cosponsor_route.py:16` ✓ (module-level `adj=MBC.load_network()`, print-only); `paths.py:7-8` ✓. Three sampled facts the guide does not state, folded into bars below: the augmenter **skips a missing layer input with only a printed notice** (`except FileNotFoundError` at `:62,76,98` → PAR-5); the AUG workbook **embeds a wall-clock build stamp** (`:106` → COR-7's canonical-hash bar); `run_tests.py:166` pins `0<w<=10` on the shell-selected graph (→ ENV-2).
- DOC-3 **one finding:** guide §6.7 says "Worktrees don't isolate the data plane." CONSTRAINTS (sourced to `fec/paths.py`, corrected 2026-07-19 in `moneyball-validation-and-qa`) and today's check say the opposite mechanism — a worktree roots to its own **empty** data plane. The **operative rule is identical in all sources** (verify in the live tree), so this is a wording defect, not a contradiction halt. Per the frozen-vintage law the guide is not edited; this framework is the living-plane correction.
- DOC-2/DOC-4 **spot-checked, not exhausted:** D1 is recorded (STATE append + guide INV-3); the open-decision → gate map above matches the guide's §7. Full DOC-2 enumeration remains for the G0 run proper.

## 5. Gate G1 — sourcing census (Phase 1)

| ID | Bar | Type |
|---|---|---|
| SRC-1 | **Coverage census.** Per congress × bill-type table: bills present in the chosen source(s) vs official congress.gov counts, both named in-sentence. PROPOSED floor: ≥99.5% per included stratum; below-floor strata go to a gap ledger for Paul (include/exclude ruling) — the honest-gap rule, never relabel. | HARD + DELIVERABLE |
| SRC-2 | **BICAM vintage limits.** BICAM used as cross-check for 117–118 only; the 119th is never BICAM-sourced (mixed-vintage drop: 131-bill early-January sliver, data-last-updated 2025-01-25 — brain STATE). | HARD |
| SRC-3 | **Build contract written before code.** D6 ladder ruled + the four §4.4 sub-questions answered in writing: (a) bill-type set, (b) SUCCESS action-code parse per type, (c) C definition for the size-norm, (d) departed-sponsor policy. | HARD |
| SRC-4 | **Refresh cadence + owner named** for the accruing 119th (cosponsors accrue until 2027-01-03; congress set comes from the dial, so the 120th rollover is a config bump) (D7ii). | DELIVERABLE |

## 6. Gate G2 — the base producer (Phase 2)

| ID | Bar | Type |
|---|---|---|
| COR-1 | **Weight-formula fixtures**, registered as a config-scoped test module: role dials (default 1.0/0.2 per the D1 ruling), `SUCCESS_MULT=3.0`, decay `0.8^(119−congress)` (scraper table, not the legislation-lane table — D4), size-norm as a **multiplied** `1/√C` discount, per-pair summation, sponsor→cosponsor orientation, congress set read from the dial (no hardcoded 119). | HARD |
| COR-2 | **Re-weighting identity.** Every BASE row satisfies `Weight = HOLISTIC_ORIGINAL_W·WOriginal + HOLISTIC_REGULAR_W·WRegular` to 1e-9 relative tolerance; zero-weight-role rows are emitted (verified by a dial=0 test build). This is what makes any future D1 re-ruling a recompute + augmenter re-run, never a re-collection (guide §4.5). | HARD |
| COR-3 | **Parity-mode dominance reconcile (the mirror proof).** Build with `HOLISTIC_REGULAR_W=0.5`; on the live CU graph's directed edges require `w_holistic ≥ w_cu − tol` for 100% of CU edges, with PROPOSED ≥99.5% matching-or-dominant strictly; every violation root-caused to a named source-discrepancy class (congress.gov scrape vs BILLSTATUS) in an exceptions ledger — an unexplained violation is FAIL. Doubles as the scraper snapshot-vs-live drift check (guide §2.1). Rationale for dominance rather than equality: the holistic universe is a superset and the CU scrape's bill list is not recoverable per-edge, so per-edge equality is not testable without the 17-template universe; superset-dominance is. | HARD |
| COR-4 | **BICAM identity cross-check.** Stratified sample (PROPOSED n=500, congresses 117–118 only per SRC-2): per-bill cosponsor set symmetric difference 0 vs BICAM for PROPOSED ≥99% of sampled bills; every non-zero case root-caused (BICAM staleness vs builder bug); unexplained → FAIL. Calibration honesty: the existing identity-perfect record (1,288/1,288 over 304 acts, B0 runs 3–4) sampled the CU act universe — evidence of join mechanics, not an all-bills prior. | HARD |
| COR-5 | **Departed-sponsor policy conformance.** The build implements the ruled D6-(d) option, and the dropped-bill share per congress is measured and reported with window + denominator named. | HARD + DELIVERABLE |
| COR-6 | **Schema guards** (audit checks, incident-dated comments, observed numbers in detail): BASE = 8 base columns + `WOriginal`/`WRegular`, directed, both directions preserved; AUG = Edges 3-col + Provenance with a layer tag from the allowed vocabulary on **every** edge; coverage floors (row counts, member counts) + malformed-record count. | HARD |
| COR-7 | **Determinism.** Double-build → identical **canonical content hash** (sheet rows serialized in fixed order, excluding the Provenance build-stamp row; raw xlsx bytes are explicitly not the bar — openpyxl embeds timestamps). Any sampling uses the CRN kernel / pinned seeds. | HARD |
| COR-8 | **Roster join + no-silent-skip.** Both endpoints roster-joined against the 533; dropped-member and dropped-edge counts **printed in the summary line** (the only line the chain runner shows) and floored in the audit; the every-member-key contract preserved (isolated → `{}`, matching `load_network`'s `:252` contract). | HARD |
| COR-9 | **Naming assert at write time.** The builder refuses to write any filename matching `congress_cosponsor_network_*.xlsx` (the `PRODUCTION_WORKBOOK_RE` prohibition precedent), and emits only the `holistic_network_BASE_/AUG_` family. | HARD |

Gate G2 also carries PRO-1 (executor protocol: contract with pinned invariants → build → independent adversarial review of the draft → adjudication → coordinator verification), and its live-tree reads schedule outside the weekly-refresh write window (ENV-3).

## 7. Gate G3 — selection dial + augmenter (Phase 3)

| ID | Bar | Type |
|---|---|---|
| ISO-1 | **Selection-surface census, mechanical.** Repo-wide grep for the production glob pattern and AUG-selection logic; every hit enumerated in the eval record and classified config-keyed or config-immune. (The augmenter's own docstring still says "NINE existing loaders" — the census supersedes any remembered list, including the guide's four.) | HARD |
| ISO-2 | **Glob invisibility, read side.** In a sandbox with both families planted and holistic newest by mtime: default-env engine loader, directed loader, and bundle selection all still select the CU file. | HARD |
| ISO-3 | **Augmenter base-pick immunity, write side.** Sandboxed augmenter run with holistic files present picks the CU base (`build_multilayer_network.py:31-32`) and its output Edges content-hash equals the no-holistic-present control run. This is the highest-severity contamination path (guide §6.1) — a glob-matching holistic file would be folded into the production CU AUG artifact at the next weekly refresh. | HARD |
| ISO-4 | **Default-config identity (the inert proof).** With `NET_CONFIG` unset, post-merge: `ranks_python.json` byte-identical (`rank_delta.py` exit 0), `dashboard_data.json` + `bipartisan.json` byte-identical vs the ENV-4 baseline (any drift proven input-driven via the input-purity recipe), kernel tests and audit tails clean. | HARD |
| ISO-5 | **Cache isolation.** One process loads CU → holistic → CU through **both** loaders; distinct adjacencies served per config; memo keys config-scoped across `adj`/`dadj`/`netfile`/`dnetfile`; the test restores cache state to the lazy-loader sentinel afterward (the `MC._CORR=None` pattern). | HARD |
| ISO-6 | **Fail-closed selection.** `NET_CONFIG=holistic` with zero holistic files of the needed vintage → raise, both loaders; intra-family ambiguity per the D3 rules → raise; **no silent CU fallback** (assert the exception, not just absence of output). | HARD |
| ISO-7 | **Barred consumers stay barred.** Static check: no `NET_CONFIG` consumption in the bipartisan producer, say-do gate, stance machinery, or rank chain; `BP_SRC=aug` remains gated; ISO-4's rank byte-identity is the behavioral half. (The reverse arrow — the holistic kernel consuming CU-scoped `bpf` — is expected and labeled, HON-1, not a violation.) | HARD |
| PAR-1 | **Shared code, parameterized.** The holistic augmenter is the same module/code path under config parameters, not a fork; diff receipt in the record. | HARD |
| PAR-2 | **Effective-dial diff = ruled deltas only.** Dump effective constants for both configs (`ENG_CAP`, `HCOI_W`, `SOC_CAP`, `SOC_REINF`, kernel constant, floors, `HOLISTIC_*`); every difference cites a ruling ID; zero unruled deltas. | HARD |
| PAR-3 | **Admission-rule conformance per the D10 ruling** (keep-rules vs `max(base, layer)`); if the fork is chosen, the D9 scope table records the re-injected CU-corpus mass. | HARD |
| PAR-4 | **Symmetrization semantics.** Holistic AUG min/max re-keyed and mean-symmetrized exactly as CU (`:38,:42`); holistic BASE stays directed; the directed loader binds BASE only. | HARD |
| PAR-5 | **Layer-presence manifest.** The CU augmenter *prints and continues* on a missing layer input (`:62,76,98`) — acceptable for CU, not for an artifact claiming a layer inventory. The holistic build records every folded layer + input file + sha256 in the manifest and **fails loudly** when a D2-expected layer input is absent. | HARD |
| PAR-6 | **Co-appearance conformance** (only if D2 promotes it): the count→probability transform implemented exactly as specified (fixtures), with its admission branch named; admitted-edge count reported. | HARD, N/A(D2) if not promoted |
| HON-1 | **Manifest completeness:** per-layer scope (`all-bills`/`cu-corpus`), `bpf: cu-scoped`, `wscale` + effective kernel constant `6/s` when applied, congress window, decay table identity, dial values, build stamp, input sha256 PIN dict (the `b5_n_matrix.py` PIN pattern), folded-layer list. | HARD |

## 8. Gate G4 — pathfinders + surfaces (Phase 4)

| ID | Bar | Type |
|---|---|---|
| PATH-1 | **Engine family runs green under `NET_CONFIG=holistic`.** Named run list agreed with Paul (at minimum: `cosponsor_route`, `budget_frontier`, `per_topic_coalition`, `scenario`, `kb_benchmark`); outputs redirected via the `*_OUT` dials into the eval record; post-run CU artifact hashes unchanged (mechanical no-clobber proof). | HARD |
| PATH-2 | **Route capture + side-by-side.** A `ROUTE_OUT`-style no-clobber dial (or captured stdout) delivers the CU-vs-holistic route comparison for Paul-chosen members — shape/order comparisons only, labeled per HON-2/3. | DELIVERABLE |
| PATH-3 | **Bundle separation.** Holistic bundle via `DASH_OUT` to a separate file; live `dashboard_data.json` byte-identical; preview on 8802 (8801 is Paul's server); the surface visibly labeled HOLISTIC. No live-dashboard toggle in v1 (D7). | HARD |
| PATH-4 | **JS-mirror parity.** Recompute the template's `PE` formula against Python `build_P` on PROPOSED ≥1,000 sampled holistic edges (or all): max abs Δp ≤ 1e-9. Contains the known hand-maintained-mirror drift risk without touching the live template. | HARD |
| PATH-5 | **Determinism of holistic engine outputs.** Double-run byte-identity per engine (CRN discipline), reusing the audit's determinism-gate pattern. | HARD |
| HON-2 | **Surface labels.** Every holistic output — pathfinder stdout headers included — names config + window + scope pointer (D9). Test: run `cosponsor_route` under holistic and assert the header block. | HARD |
| HON-3 | **No cross-config numeric claims shipped.** Raw p/reach/weight deltas CU-vs-holistic are a defect in any shipped report (different universes and role weights — guide §4.3); route shape, rankings, and structure comparisons only. The D8 calibration diagnostics are exempt but stay inside the eval record labeled DIAGNOSTIC. | HARD (review) |

## 9. Gate G5 — measurement, diagnostics, review (Phase 5)

| ID | Bar | Type |
|---|---|---|
| MEA-1 | **Distribution report.** Edge count, density (denominator named: 141,778 = 533·532/2 roster pairs), degree and weight distributions, induced p-distribution (median + tail masses above 0.5/0.8/0.9/0.99) for the holistic graph, with CU reference values alongside labeled DIAGNOSTIC-ONLY; party-stratified or explicitly UNSTRATIFIED (cross-party edges ride `cpf`·`bpf`, so pooling hides a named fault line). | DELIVERABLE |
| MEA-2 | **D8 trigger evaluation** (arms on MEA-1): PROPOSED working thresholds — holistic tail mass above p=0.5 differing >2× from CU's, or median p differing >0.1 — fire the wscale question to Paul with the report. The wscale decision, and any concave-transform fork if a scalar cannot fix shape, are Paul's (D8). If applied: HON-1 in-band disclosure + MEA-1 re-run. | TRIGGER |
| MEA-3 | **Role-mass shares.** Per-dyad regular-mass share `0.2·WRegular/(1.0·WOriginal+0.2·WRegular)`: distribution quantiles + top-K dyads, delivered **before** anyone reads the holistic graph as a costly-signal network. TRIGGER: median share >0.5 → headline finding that regular mass dominates (the guide §4.2 warning, measured). | DELIVERABLE + TRIGGER |
| MEA-4 | **Per-layer admitted-edge counts, CU vs holistic** (engagement-new, HCoI, social-new, social-reinforced, co-appearance) — the D10 vacuity measurement. TRIGGER: a promoted layer admitting ≈0 edges → named vacuity finding. | DELIVERABLE + TRIGGER |
| MEA-5 | **Isolate census.** Cosponsor-isolated members in the holistic base (expected ≈0 on an all-bills universe); every isolate individually investigated as a join-bug lead; cross-read with MEA-4 (isolates ≈0 mechanically implies HCoI ≈0 under keep-rules — D10 observed, not assumed). | HARD + TRIGGER |
| MEA-6 | **`kb_benchmark` on the holistic graph** — runs clean; results REPORT-ONLY. The CU-recorded readings (allocator −0.21 BY DESIGN, KB↔legislative +0.62) are CU-vintage; holistic values are fresh diagnostics, and nothing gets "fixed toward KB". | DELIVERABLE |
| MEA-7 | **MC sufficiency re-check.** `mc_stability_check.py` under `NET_CONFIG=holistic`: the recorded 100% seed-overlap validation is CU-vintage evidence only, and a denser, saturation-prone graph is exactly where MC=20 could stop sufficing (guide §6.2). Degraded overlap → escalate; the remedy is a holistic-run MC dial, never a CU default change. | HARD + TRIGGER |
| MEA-8 | **Harness registration meta-bar.** Every bar marked for `run_tests.py`/`audit_full.py` above is actually registered and green (tail counts grew; new checks print OK; out-of-chain artifacts get if-exists gating with an explicit else-FAIL where mandatory); the two `data\network\` orphans (`sna_data.json`, `_affinity_tables.json`, both Jun 26, no producer) adjudicated; `artifact_freshness.py` table extended or the deferral recorded. | HARD |

Gate G5 closes with PRO-2..6 (below) — including the adversarial review round over the full diff, run under imported law 2's ordering.

## 10. PRO — process bars (cross-gate)

| ID | Bar |
|---|---|
| PRO-1 | Codex-built phases follow the executor protocol: contract with pinned invariants → build → independent adversarial review of the DRAFT in a fresh thread → adjudicated findings → coordinator verification (the C1-collector precedent). |
| PRO-2 | Gates run in order; a gate not run is BLOCKED, and BLOCKED blocks acceptance. Single failures re-run once for read contention, then they are real. |
| PRO-3 | No bar is weakened by its evaluator; threshold changes are Paul's re-pins, logged in the FREEZE ADDENDUM chain. |
| PRO-4 | Per-gate report contract: commit ids, gate outputs with counts, mover list (expected empty), revert instruction, and an explicit list of everything NOT verified. |
| PRO-5 | Eval record at `audits/holistic_v1_eval/` (proposed): `RECORD.md` scoring sheet, `baseline_hashes.json`, env dumps, run logs, glassbox run_ids. Every verdict carries command + sha256 + date + tree state. |
| PRO-6 | Acceptance ≠ deployment: a full PASS changes nothing about D7 (exposure), rank-chain contact, or CU-side behavior — those stay individually Paul-gated. |

## 11. Negative-control battery (a gate that cannot fail proves nothing)

Every control runs in the ENV-5 sandbox, never the live tree. Each demonstrates the corresponding bar CAN fail (examine-skill PASS 5: what would this say if the claim were false?).

| Control | Must produce |
|---|---|
| Inverted size-norm mutant (multiply by √C) | COR-1 fixture FAIL |
| Swapped edge orientation mutant | COR-1 fixture FAIL |
| One corrupted `WOriginal` subtotal | COR-2 identity FAIL |
| Builder forced to a `congress_cosponsor_network_*` name | COR-9 raise |
| Glob-**matching** planted file | selectors DO pick it up (proves ISO-2/3 tests watch the real mechanism) |
| Zero holistic files under `NET_CONFIG=holistic` | ISO-6 raise, both loaders |
| Cache keying reverted to single `'adj'` | ISO-5 FAIL |
| Hidden co-appearance input (if D2 promoted) | PAR-5 loud FAIL, not print-and-continue |
| One perturbed weight in the serialized bundle | PATH-4 parity FAIL |

## 12. Traceability matrix (every risk, invariant, and ruling → bars)

| Source | Covered by |
|---|---|
| INV-2 (additive; CU untouched, default) | ISO-1..7, ENV-2, PATH-3, PRO-6 |
| D1 ruling (regular @0.2) | COR-1, COR-2, MEA-3 |
| Guide §6.1 selection trap | ISO-1, ISO-2, ISO-3, ISO-6, COR-9 |
| §6.2 kernel scale / saturation | MEA-1, MEA-2, MEA-7, HON-1 |
| §6.3 one writer | ENV-3 |
| §6.4 memoization | ISO-5 |
| §6.5 JS mirror drift | PATH-3, PATH-4 |
| §6.6 language discipline | HON-3, HON-4 (imported law 4), HON-5 |
| §6.7 scope discipline | ISO-7, PRO-6, ENV-1 |
| §6.8 external corpora stay external | HON-6 + REPORT-ONLY strata (§2) |
| §6.9 rollover | COR-1 congress-dial fixture, SRC-4 |
| §6.10 admission vacuity | PAR-3, MEA-4, MEA-5 |
| §4.4 sub-questions (a)–(d) | SRC-3, COR-5 |
| §4.5 schema / re-ruling basis | COR-2, COR-6 |
| D2 co-appearance | PAR-6, MEA-4 |
| D3 identity mechanism | ISO-2, ISO-5, ISO-6, ISO-1 |
| D4 window/decay | COR-1 decay fixture, HON-1, HON-4 |
| D6 sourcing | SRC-1..3, COR-3..5 |
| D7 exposure/cadence | PATH-3, SRC-4, PRO-6 |
| D8 wscale | MEA-2 |
| D9 partial holism | HON-1, HON-2, HON-6 |
| D10 admission fork | PAR-3, MEA-4 |
| D11/D12 (out of v1 scope) | REPORT-ONLY strata + HON-1 `bpf` label |
| validation-and-qa: schema guards / no-silent-caps / byte bar / determinism / fingerprints | COR-6 / COR-8 + PAR-5 / ISO-4 / COR-7 + PATH-5 / HON-1 + PRO-5 |

Self-test: this matrix has no empty rows; a future amendment that empties a row (or adds a risk with no bar) is a framework defect to fix at the next FREEZE ADDENDUM.

**HON-4/5/6 (not tabulated above):** HON-4 = imported law 4 applied to every deliverable; HON-5 = descriptive-language-only for structure findings (INV-4/FEC×LDA R3), citations honest-analogical, routes labeled "general collaboration reach," never CU-recruitment plans; HON-6 = partial-holism disclosure on every output surface.

## 13. Freeze, amendment, and the record

1. **Freeze order:** Paul rules D3 + D6 (+ D10 before G3, D2 before PAR-6) → Appendix B pins filled in a dated FREEZE ADDENDUM (sha256-pinned, the F1 pattern) → only then does Phase-2 code start. Bars exist before the artifact they judge.
2. **Amendments** after freeze are Paul's, logged as further addendum entries; the evaluator's only permitted response to a failing bar is a finding.
3. **Adoption** (optional, Paul's call): a brain DECISIONS entry naming this file, the D-007 pattern.
4. The scoring sheet (Appendix A) is filled per gate into `audits/holistic_v1_eval/RECORD.md`; the completed record plus the §0 rule yields the final verdict sentence: *"the first draft DOES / DOES NOT live up to sufficient standards, per bars X…"* with the failure list when it does not.

## Appendix A — scoring sheet template

One row per bar (ENV-1..6, DOC-1..4, SRC-1..4, COR-1..9, ISO-1..7, PAR-1..6, HON-1..6, PATH-1..5, MEA-1..8, PRO-1..6 — 51 bars):

| Bar | Gate | Type | Stratum | Verdict | Receipt (command · sha256 · date · tree) | Notes |
|---|---|---|---|---|---|---|
| ENV-1 | all | HARD | BINDING | | | |
| … | | | | | | |

## Appendix B — PROPOSED pins for Paul (filled at freeze)

| Pin | Proposed value | Bar |
|---|---|---|
| Census coverage floor | ≥99.5% per congress×type stratum | SRC-1 |
| Dominance reconcile | 100% explained; ≥99.5% strict | COR-3 |
| BICAM sample / identity rate | n=500 (117–118); ≥99% symdiff-0, rest explained | COR-4 |
| Re-weighting identity tolerance | 1e-9 relative | COR-2 |
| JS parity sample / tolerance | ≥1,000 edges / ≤1e-9 | PATH-4 |
| D8 triggers | tail-mass(p>0.5) ratio >2× or median Δp >0.1 (guide-proposed; Paul may re-pin) | MEA-2 |
| Role-mass trigger | median regular share >0.5 | MEA-3 |
| Anchor sample | ≥12, selection-surface anchors mandatory | DOC-1 |
| Engine run list | route, frontier, coalition, scenario, kb_benchmark (minimum) | PATH-1 |
| Eval record home | `audits/holistic_v1_eval/` | PRO-5 |

*Every value in this table is PROPOSED. None is binding until the FREEZE ADDENDUM carries Paul's pin.*
