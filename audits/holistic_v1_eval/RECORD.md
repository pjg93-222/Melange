# Holistic v1 Evaluation Record

**Opened:** 2026-08-17 · **Framework:** `audits/HOLISTIC_NETWORK_V1_EVAL_FRAMEWORK_2026-08-17.md` (sha256 `2C4EBBFF1B2381D7FA1CA0B249293090073F297AC8277D90AA2408DDA18DDE78`)
**Tree state at open:** live head `56f1f84c7` · worktree head `22c55d0ac` (branch `claude/holistic-network-config-60c11c`)
**Glassbox run:** `holistic-eval-framework-20260817-30180` (lane claude)
**Status banner:** Gate G0 EXECUTED this session (verdict below). Gates G1–G5 are BLOCKED by design — no build exists; the framework's thresholds are unfrozen (PROPOSED) until the FREEZE ADDENDUM carries Paul's pins. Nothing in this record weakens or re-pins any bar.

---

## Gate G0 — VERDICT: PASS, with 3 recorded findings

All four DOC bars pass on the evidence below. The three findings are living-plane corrections to the frozen guide (per the FROZEN VINTAGE constraint the guide is not edited); none reopens a guide conclusion — finding F2 *reinforces* one.

### DOC-1 — anchor audit: PASS (18/18 sampled anchors resolve; 0 content misses)

Sampled 2026-08-17 against the worktree's code plane (identical lineage to main for `fec/`). "exact" = cited lines contain the claimed content at the claimed numbers.

| # | Anchor (guide citation) | Result |
|---|---|---|
| 1 | `select_network_file` `moneyball_core.py:232-237` — glob + AUG-prefer + newest mtime | exact |
| 2 | `load_network :238-255` — roster filter, mean-symmetrize, memo `_c['adj']` | exact (+ contract: every member keyed, isolated → `{}` at `:252`) |
| 3 | directed pair `:256-292` — non-AUG glob; AUG direction = sort artifact | exact |
| 4 | `build_P :305-312` — `p = w·cpf·σᵥ/(w·cpf·σᵥ+6)` | exact |
| 5 | physics `:293-298` — `cpf_diffusion`/`cpf_pressure` | exact |
| 6 | augmenter base-pick `build_multilayer_network.py:31-32` (newest non-AUG) | exact |
| 7 | augmenter 3-col read `:35-37`, kernel-inverse `:59`, HCoI isolates-gate `:68`, social `:77-97`, output `:100-108`, dials `:26,:83` | exact |
| 8 | `cosponsor_route.py:16` — module-level `adj=MBC.load_network()`, print-only | exact |
| 9 | `paths.py:7-8` — ROOT = MONEYBALL_ROOT or parent of `fec/` | exact |
| 10 | `run_tests.py:158-175` — roster/network/physics block | exact (note: `:166` pins `0<w<=10` on the shell-selected graph → ENV-2) |
| 11 | `audit_full.py:106-124` — co-sponsor-route block (subprocess, inherits ambient env) | exact |
| 12 | `audit_full.py:184-206` — press-SNA schema guards incl. `dashboard_data.json` read | exact |
| 13 | bundle display-graph selection via `select_network_file` — cited as `build_dashboard_bundle.py:77` | exact at `fec/surfaces/build_dashboard_bundle.py:77` (path imprecision: file is under `fec\surfaces\`) |
| 14 | bundle BP source (newest non-AUG, `BP_SRC` gate) `:94-100` | exact (`:99-100`) |
| 15 | co-appearance + signed refs dashboard-only `:179-194` | resolves at `:181-196` (±2-line drift; content exact: display layers only, floors `n>=2`) |
| 16 | `bill_rules.py:16-23` — canonical CATEGORIES registry | exact |
| 17 | `PRODUCTION_WORKBOOK_RE` prohibition `build_legislation_base_network.py:99-101` | exact (+ bonus: `FIXED_ZIP_TIME=(1980,1,1,0,0,0)` at `:111` — shipped deterministic-xlsx precedent, adopted into COR-7) |
| 18 | shadow-lane contracts `run_legislation_network_dependents.py:64-68` + second-AUG ambiguity guard `:474-476`; `CU_TERMS` `process_quorum.py:19-34` (at `fec\network\`); `bills_audit.csv` + `canonical_category` `cosponsor_selectivity.py:96,102` (at `fec\lobbying\`); disk inventory "7 base + 8 AUG, newest AUG20260802" | all exact (two bare-filename path imprecisions) |

Not sampled: bundle `ADJ` serialization `:235` (queued for the G3 sweep). Negative claims verified mechanically: **no `network.json` anywhere** (glob, 0 hits); **no network builder reads `bill_beneficiary_tags`** (grep `fec/network/`, 0 hits).

### ISO-1 pre-census (read-only, 2026-08-17) — the selection-surface inventory

Repo-wide grep for `congress_cosponsor_network_`: 58 files; live-code mtime-selectors below (excluding `audits/` snapshots, skills, docs, tests, and the legislation shadow lane, whose globs are sealed-root/pinned by design):

| Selector | Pick rule | Classification for holistic v1 |
|---|---|---|
| `moneyball_core.py:243` (engine loader) | AUG-prefer, newest | config-key at G3 (the NET_CONFIG dial) |
| `moneyball_core.py:280` (directed loader) | newest non-AUG | config-key at G3 |
| `build_multilayer_network.py:31` (augmenter base) | newest non-AUG | must stay CU-only — ISO-3 regression |
| `surfaces/build_dashboard_bundle.py:77` (display graph) | AUG-prefer | config-key at G3/G4 (D7) |
| `surfaces/build_dashboard_bundle.py:100` (BP source) | newest non-AUG (`BP_SRC` gate) | barred consumer — stays CU (ISO-7) |
| `network/press_hcoi.py:87` | **newest ANY** | immune-by-naming (CU-lane producer) |
| `network/press_engagement_layer.py:71` | **newest ANY** | immune-by-naming |
| `stance/stance_dynamics.py:89` | **newest ANY** | immune-by-naming |
| `members/behavior_panel.py:66` | newest non-AUG | immune-by-naming |
| `members/persona_homophily_validate.py:28` | newest non-AUG | immune-by-naming (diagnostic) |
| `attic/im_allocate2.py:24` | newest ANY, hardcoded live path | attic — inert unless run; immune-by-naming |
| `audit/audit_legislation_downstream_readiness.py:1146` | census glob | read-only audit surface — G3 sweep |
| `legislation/freeze_legislation_production_baseline.py:156` | census glob | read-only baseline freezer — G3 sweep |

**Reading:** the naming rule (holistic family must fail the production glob) is load-bearing for **9+ live selectors**, not the guide's four — which is exactly why ISO-2's regression asserts the naming rule wholesale and ISO-1 re-runs this census at G3. "Immune-by-naming" entries need zero code changes *only while the naming rule holds*.

### DOC-2 — decision traceability: PASS (zero orphan choices)

| Code-shaping choice (guide Phases 2–4) | Traces to |
|---|---|
| `holistic_network_BASE_/AUG_` naming fails production glob | D3 + §4.1 (census above reinforces) |
| `NET_CONFIG` gates both loaders + augmenter base-pick + bundle | D3 |
| Fail-closed zero-file / ambiguity selection | D3 + shadow-lane precedent |
| Role dials 1.0 / 0.2 | **D1 (RULED 2026-08-17)** |
| `WOriginal`/`WRegular` subtotals + zero-role rows | §4.5 (D1 consequence, pinned in guide) |
| Congress window + decay dials (scraper table) | D4 |
| Source ladder (BILLSTATUS → BICAM → govinfo → scraper) | D6 |
| Bill types / SUCCESS parse / C definition / departed sponsor | D6(a)–(d) |
| Co-appearance promotion + transform; refs display-only | D2 |
| Admission-rule keep vs `max(base,layer)` | D10 |
| `HOLISTIC_WSCALE` | D8 |
| Partial-holism scope labels | D9 |
| `DASH_OUT` separate bundle, preview-only; build cadence + stamp | D7(i)/(ii) |
| `ROUTE_OUT`-style capture dial | guide §5 Phase 4 — explicitly phase-gated (not an orphan) |
| `bpf: cu-scoped` label | D12 |
| No committee/letter/roll-call/amendment edges in v1 | D5/D11 (deferred, REPORT-ONLY strata) |

### DOC-3 — contradiction sweep: PASS, findings adjudicated

- **F1 (wording defect):** guide §6.7 "Worktrees don't isolate the data plane" vs CONSTRAINTS + `paths.py:7-8` (worktree data plane is EMPTY). Operative rule identical everywhere — verify in the live tree. No halt; guide frozen; framework is the correction of record.
- **F2 (undercount, conclusion reinforced):** guide names four selection surfaces; the census finds 9+ live mtime-selectors (table above). The guide's conclusion — the holistic name must fail the glob entirely — is *strengthened*. ISO-1/ISO-2 are census-based, not list-based, in the framework.
- **F3 (anchor imprecision):** three bare-filename citations resolve under subdirectories (`fec\surfaces\`, `fec\network\`, `fec\lobbying\`); one ±2-line drift. Content exact in all four.

### DOC-4 — ruling record: PASS (one queued receipt)

D1 is doubly recorded (brain STATE append at guide delivery `b99c52589`; guide INV-3). The meta-run coordination-ledger receipt (`decision-resolved: d1-regular-cosponsor-ruling`) is **UNVERIFIED-HERE** — outside this session's reach; queued, not demolished. Open decisions and their gate dependencies match the framework §DOC-4 map.

---

## ENV log (this session)

| Bar | Status | Receipt |
|---|---|---|
| ENV-1 | PASS (as-executed) | Code reads only this session; live-tree paths used for hashing; `paths.py:7-8` re-verified |
| ENV-2 | PASS (as-executed) | No `fec` engine executed this session; no dials set |
| ENV-3 | PASS | 2026-08-17: no python processes; no live-root writes in prior 30 min |
| ENV-4 | **CAPTURED** | `baseline_hashes.json` — 18 files (7 base + 8 AUG + ranks/dashboard/bipartisan), live head `56f1f84c7`; `board_baseline_20260817.csv` — 533 members. **Recapture rule:** re-hash at G3 start; deltas between now and then are Paul's chain activity, adjudicated via the input-purity recipe, never assumed. |
| ENV-5 | PENDING | No plants needed yet; sandbox recipe unexercised |
| ENV-6 | PASS | Glassbox events emitted (run ids in header + commit-time event) |

## Scoring sheet (all 51 bars)

| Bar | Gate | Verdict | Note |
|---|---|---|---|
| ENV-1..3, ENV-6 | all | PASS (this session's scope) | re-verify at every gate |
| ENV-4 | all | CAPTURED | recapture at G3 |
| ENV-5 | all | PENDING | first exercised at G2/G3 negative controls |
| DOC-1..4 | G0 | **PASS** | 3 findings recorded above |
| SRC-1 | G1 | MET vs PROPOSED floor | census run 2026-08-17; every stratum ≥99.69% vs self-denominator; official cross-check QUEUED (bot-walled); verdict binds at freeze |
| SRC-2 | G1 | PASS | data-enforced: BICAM 119th = 131 rows, never joined |
| SRC-3 | G1 | BLOCKED (Paul) | the sourcing memo is the D6 input; ruling pending |
| SRC-4 | G1 | PARTIAL | vintage measured (2026-08-01); cadence owner unnamed until D7(ii) |
| COR-1..9 | G2 | BLOCKED | awaits freeze + build |
| ISO-1 | G3 | PRE-RUN (this record) | re-run mechanically at G3 |
| ISO-2..7 | G3 | BLOCKED | awaits dial + build |
| PAR-1..6 | G3 | BLOCKED | PAR-6 becomes N/A(D2) if not promoted |
| HON-1..6 | G3–G5 | BLOCKED | |
| PATH-1..5 | G4 | BLOCKED | |
| MEA-1..8 | G5 | BLOCKED | |
| PRO-1..6 | cross | OPEN | PRO-5 record = this directory |

**Current overall answer to "does the first draft live up to sufficient standards":** the only draft that exists today is the design draft, and **it passes its gate (G0) with findings recorded**. The implementation draft cannot yet be evaluated (G2–G5 BLOCKED — which per the framework blocks acceptance, exactly as it should while nothing is built). Next unblock: Paul rules D3 + D6 and pins Appendix B via the freeze addendum.

---

## AMENDMENT 2026-08-17 — execution home is this workbranch (Paul directive, in-chat)

Paul's directive ("We should be executing everything in this workbranch") re-pins the run-location bars for this lane, effective immediately and to be carried into the freeze addendum:

- **ENV-1 (amended):** the execution home for all holistic-lane work — census runs, builders, holistic artifacts, records, reports — is worktree `holistic-network-config-60c11c` on branch `claude/holistic-network-config-60c11c`. `paths.py` roots code to its own tree, so holistic artifacts born here are **physically invisible to the nine production globbers** until merge: containment by construction, layered on top of the naming rule. Live-tree contact is limited to (a) read-only baseline captures (ENV-4), (b) copying parity inputs *into* this worktree (COR-3), and (c) the merge-time CU-invariance proofs (ISO-4, rank gate), which by nature run where production artifacts live.
- **ENV-5 (amended):** the plant sandbox for negative controls is a scratch root, or this worktree's own data plane — never the live tree (unchanged in substance; the worktree is now the default sandbox).
- **Materialization manifest (Phase 2 precondition):** before the base-builder runs here, copy into this worktree: `data/engine/congestion.json` (roster), the newest CU base + AUG workbooks (parity + ISO sandbox inputs), and any layer JSONs a bar exercises. Record each copy's source sha256 in this record. The machine-local archives (BILLSTATUS at `%LOCALAPPDATA%\Melange\lda_rebuild\raw`, BICAM at `C:\melange-data\bicam_snapshot`) are read in place — they are outside both trees.
- The design guide is now IN this branch — pulled from `claude/holistic-network-analysis-config-dc9e36` with **blob identity proven** (`e729e772cf5df191754cafdd4d76ef14bf183d5a`, working-vs-branch diff empty). Pin-object lesson recorded: STATE's `bf15821d` sha named the meta-run's pre-commit LF bytes; under CRLF checkout the on-disk hash legitimately differs — future pins should name the git blob OID alongside the file sha.

## Gate G1 — sourcing census EXECUTED 2026-08-17 (evidence complete; ruling is Paul's)

Method + raw results: `census_g1.py` / `census_g1_results.json`; narrative: `SOURCING_MEMO_2026-08-17.md` (all this directory).

- **SRC-1:** per-stratum census run over both archives. Local BILLSTATUS (2026-08-01 pull): **gap=0 on all 16 strata of 117–118** — complete by construction (sequential numbering + unique entries) — and 22/16,052 missing numbers on the 119th (0.14%, hr+s only, reserved-number-consistent). BICAM cross-agrees 117–118 within 0.04–0.17% (known −33-row 118th tail). Proposed ≥99.5% floor met on every stratum (worst 119/s = 99.69%). Official congress.gov cross-check QUEUED — congress.gov and govtrack 403/bot-wall non-interactive fetches; not bypassed. Verdict binds at freeze.
- **SRC-2 PASS:** BICAM's 119th is 131 rows — the bar is enforced by the data; nothing to misuse.
- **SRC-3 BLOCKED (by design):** the memo puts the ladder recommendation + all four sub-question evidence packets in front of Paul; D6 is now ruleable on measurements instead of estimates.
- **SRC-4 PARTIAL:** vintage measured (2026-08-01; 119th staleness 16 days and accruing); re-pull recommended at Phase-2 build; cadence owner named in D7(ii).
- **New census findings:** universe = **55,195 measures across 117–119** (guide's ~48k estimate low); BICAM carries congress-misassignment strays (117/hr max 11,200 vs true 9,709) → COR-4 keys on `bill_id` and flags strays; BICAM's historical span reaches congress 6 (bonus fact, no v1 consumer).

---

## "RUN ALL" EXECUTION 2026-08-17 (Paul in-chat; freeze addendum recorded same file date) — Gates G2–G5 executed in-branch

**Built:** `fec/network/build_holistic_base.py` (BASE producer; scraper-parity formula, D1 dials, main-guarded) → `holistic_network_BASE_20260817.xlsx` + manifest (93,952 directed edges; 533/533 members; 0 isolates; 0 parse failures over 55,195 bills; per-congress bill totals match the census exactly). `NET_CONFIG` dial in `moneyball_core` (per-call read, config-keyed cache `adj@holistic`/`dadj@holistic`/netfile keys, `_select_holistic` fail-closed, HON-2 banners; CU path byte-identical incl. cache-key layout). `build_multilayer_network.py` parameterized (CFG branch; holistic: fail-closed base pick, PAR-5 hard-fail on missing layers, D2 co-appearance layer `w=min(COAP_CAP, COAP_W·n)` untied-only floor n≥2, COR-9 name assert, HON-1 manifest; CU path byte-identical, tail print made config-honest) → `holistic_network_AUG_20260817.xlsx` + manifest.

**Gate verdicts (this run):**

| Bar | Verdict | Evidence |
|---|---|---|
| COR-1 + COR-9 | **PASS 27/27** | `fec/tests/holistic/test_holistic_base.py` — incl. 4 negative-control mutants (inverted sizenorm, swapped orientation, production-name, non-family-name) |
| COR-2 | **PASS** | identity exact on all 93,952 rows (1e-9 rel); single-role rows present |
| COR-5 | **MEASURED** | departed-sponsor drops: 4,219/17,828 (23.7%) 117th · 2,695/19,315 (14.0%) 118th · 208/18,052 (1.2%) 119th |
| COR-7 | **PASS** | rebuild canonical row-hash identical (`1d190ab4d9a5`) |
| COR-3 | **FAIL — real finding, bar stands** | strict dominance 77.96% (1,461/1,874) vs 99.5% pin; 405 violations + 8 missing (pair coverage 99.6%). Diagnosis: the bar's premise (superset ⇒ per-edge dominance) is unsound for ACCRUING bills — C grows between the CU scrape (6/25) and BILLSTATUS (8/1), shrinking 1/√C; deficit signature (small %-deficits, identical values repeated per sponsor-star) matches; a few −26/−32% cases suggest SUCCESS-parse divergence on single bills inside sums. Evaluator design defect OWNED; vintage-aware re-pin is Paul's (PRO-3). `cor3_ledger.json` |
| ISO-2/3/5/6 + D3 ambiguity + HON-2 + PAR-4 | **PASS 17/17** | `fec/tests/holistic/test_holistic_config.py` — default env picks CU on both loaders despite newer holistic mtimes; sandbox augmenter picks CU base; zero-file and unclassifiable-name raises; in-process config switch serves distinct cached graphs; banner prints |
| PAR-5 | **PASS (by construction + build)** | holistic AUG hard-fails on missing layer inputs; manifest lists folded layers + input shas |
| MEA-1/2 (D8) | **RUN — trigger FIRED on tail ratio** | holistic 62,996 pairs (44.43% of 141,778) vs CU 2,555 (1.80%); median p 0.0282 vs 0.0213 (Δ0.0069 — median trigger NOT fired); tail>0.5: 0.59% vs 0.12% = **5.04× > 2× pin**; tail>0.9 = 0.0000 (zero saturation). Reading for D8: median calibrated, tail heavy-but-unsaturated — a scalar wscale would distort the healthy median to chase shape; recommend NO WSCALE; Paul rules. `g5_measurement.json` |
| MEA-3 | **RUN — trigger NOT fired** | median regular-mass share 0.232; 36.2% of dyads regular-dominated (noted); costly-signal reading survives D1 pricing at the median |
| MEA-4 | **RUN** | admitted: engagement +21, **HCoI +0 (vacuity confirmed, as §6.10 predicted)**, social +171 new / 559 reinforced, co-appearance +198 (NOT vacuous — real non-cosponsor signal) |
| MEA-5 | **PASS** | 0 isolates (all-bills universe connects all 533) |
| PATH-1/2 | **PASS (route mandatory) / DELIVERED** | `cosponsor_route` exit 0 both configs; captures with labeled headers (`route_capture_cu.txt` / `route_capture_holistic.txt`); CU low-risk route: 0 recruitments under $300k cap; holistic: live whip chains (Cruz→Cornyn p=0.85). Frontier/coalition/scenario not attempted this pass (named shortfall per the pin) |
| MEA-6 | **BLOCKED (permission)** | kb rerun needs `ranks_python.json` materialization the classifier declined; rerunnable anytime |
| MEA-7 | **NOT RUN** | mc_stability rides the frontier chain; queued with MEA-6 |
| HON-1/2 | **PASS** | manifests carry scope labels + `bpf: cu-scoped` + dials + input shas + admitted counts; banners print on holistic loads |
| PRO-1 | **OWED** | adversarial round on the full diff at the pre-merge gate (freeze addendum debt #1) |
| ISO-4 full / MEA-8 | **OWED at merge** | live-tree byte-identity + rank gate + harness registration (debts #2/#3) |

**Overall at end of run:** the implementation first draft now EXISTS and clears every bar runnable in-branch except **COR-3 (real FAIL, diagnosed, re-pin Paul's)**, with MEA-6/7 queued and the three merge-gate debts recorded. Per the framework §0, acceptance remains NOT GRANTED until COR-3 is dispositioned and the merge-gate debts run — which is the framework behaving exactly as designed.

---

## REVIEW WINDOW 2026-08-17 late evening — full framework re-verification + downstream update (Paul: "review with the framework … update the social network and the downstream effects … both configurations")

Independent re-runs in a fresh context window against the artifacts as they sit on disk (verify-don't-infer: the run-all commit's claims were re-executed, not trusted):

| Check | Result |
|---|---|
| COR-1 fixtures | **27/27 re-run PASS**, all negative controls firing |
| ISO battery | **17/17 re-run PASS** — dual-config served in one process (holistic 62,996 pairs / CU 2,555 on 141,778), cache-isolated, fail-closed raises, augmenter base-pick immune |
| COR-2 identity | PASS on every BASE row (re-run) |
| COR-7 determinism | **PASS across independent invocations**: a background rebuild from cold start reproduced the BASE byte-for-byte except the manifest `built_utc` line (git diff = 1 line) and canonical row-hash `1d190ab4d9a5` matches the shipped build |
| MEA refresh | numbers reproduce exactly: D8 FIRED (tail ratio 5.043, tail>.9 = 0.0000, median Δp 0.0069 — NO-WSCALE recommendation stands, ruling Paul's); MEA-3 median regular share 0.232 (trigger clear; 36.2% of dyads regular-dominant — surfaced, not alarming); MEA-4 hcoi=0 (D10 vacuity confirmed), engagement 21 / social 171+559 / co-appearance 198; MEA-5 isolates 0 |
| **PATH-4 (newly closed)** | **PASS both configs, max Δp = 0.000e+00 exactly** — `path4_parity.py` re-implements the tpl's own kernel math (`make_dashboard_html_00.tpl:414-417`, not build_P — non-circular) over ALL directed edge checks: CU 5,110, holistic 125,992 |
| AUG chain idempotence | rebuild from the current BASE → canonical hash **IDENTICAL** (`ce9c74af6a3d` shipped and refreshed); layer folds reproduce exactly |
| COR-9 live demonstration | the augmenter's name assert fired on a non-compliant temp filename during this window — the negative control observed in the wild |
| **PATH-3** | **BLOCKED(worktree-inputs)** — bundle probe's first missing input: `legislation_culling_receipt.json` (the legislation-lane receipt). PATH-3 completes at the merge gate from the live tree via `DASH_OUT` per D7(i); recorded as merge-gate item #4 |
| COR-3 | FAIL **stands** (strict 77.96% vs 99.5% pin; 405 dominance violations + 8 missing of 1,874) — the diagnosed vintage-drift premise defect; re-pin is Paul's, never the evaluator's |

**Configurations after this window:** CU untouched and default everywhere (ISO re-proofs above; live tree never written); holistic BASE+AUG artifacts current, chain-idempotent, manifest-labeled, served only under `NET_CONFIG=holistic`. Downstream consumers verified against both: engine loaders, directed loader, cascade kernel + JS-mirror parity, route captures (both-config side-by-side in this record), kb_benchmark holistic capture. Remaining downstream exposure (dashboard bundle/preview) rides the merge gate with the other debts: PRO-1 adversarial round, ISO-4 live byte-identity + rank gate, MEA-8 registration, PATH-3 bundle, COR-3 disposition, D8 ruling.

---

## MERGE GATE 2026-08-17/18 — pre-merge battery (Paul: "commit and merge")

Executed in a fresh context before any merge, in the order the framework's imported law 2 requires.

**Pre-merge baselines captured (live tree at `44687cdef`):**

| Baseline | Value |
|---|---|
| Kernel gate | **154 passed, 0 FAILED** |
| `audit_full` | **202 passed, 1 FAILED** — the single failure is the known Paul-gated legfix5 culling item (`culling surface reports the hash-bound production promotion state`), matching the documented baseline exactly |
| Artifact hashes | `premerge_baseline_20260818T021050Z.txt` — ranks/dashboard/bipartisan/category_stance/member_receptivity |

**CU-path behavioral parity (ISO-4 pre-proof — stronger than a post-merge artifact compare, because it isolates THIS change from other lanes' input drift):** rather than reading the diff, main's version of each changed file was executed head-to-head against the branch version on identical inputs, default env.

| Proof | Method | Result |
|---|---|---|
| `moneyball_core.py` loaders | main's module loaded from a staged path (with an assert on `__file__` so the right module is provably loaded), vs branch module; both call `load_network()` + `load_network_directed()` | **IDENTICAL** — undirected `43f1de6c89b425aa` (533 nodes / 5,110 slots), directed `21402979d182c17d` (533 / 1,874), same `netfile`/`dnetfile` selected, same cache-key set |
| `build_multilayer_network.py` | main's augmenter staged inside `fec/network/` (so `paths.py` resolution matches) and run with `AUG_OUT` to temp, vs the branch augmenter, both with `NET_CONFIG` unset | **IDENTICAL** — Edges 2,895 rows `d422b078081da289`, Provenance 2,895 rows `e08a30f316285f01`, and byte-identical stdout including the D4 reconnection line that downstream tooling parses |

*Method note (recorded because it nearly produced a false green):* the first parity attempt staged main's module under a Git-Bash `/tmp` path, which native-Windows Python cannot resolve — both runs silently loaded the NEW module and "passed". The probe's `__file__` print caught it; the rerun added a hard assert. A parity test that cannot fail proves nothing (framework §11).

**Merge safety:** merge-base `22c55d0ac`; main carries 10 newer commits; `merge-tree` reports **0 conflicts** and the two changed-file sets are **fully disjoint** (main 25 files, branch 28, intersection empty).

**COR-3 → DISPOSITIONED via COR-3v2** (delegated re-pin; see the freeze addendum): presence **PASS** (1,866/1,874 direct; all 8 misses root-caused to a single CU-side scrape defect. **CORRECTED 2026-08-18 — the original wording named the wrong members; see the CORRECTION OF RECORD block at the end of this document.** `M001226` is **Robert Menendez** (House, NJ-08), not Nathaniel Moran: the scrape credits **Senator** Robert Menendez's (`M000639`, departed 2024, absent from the 533) sponsorships to his son the **Representative**, a full-name collision across the roster boundary. The holistic builder, keyed on native BILLSTATUS bioguides, carries Menendez correctly at 89 out-edges / 182 in-edges), aggregate mass **PASS at 4.26×**, per-edge dominance demoted to REPORT-ONLY (median ratio 2.13, 78.3% dominant). **Side finding routed to the CU lane (corrected):** the production CU graph carries the **Menendez** misattribution — all 9 of Rep. Robert Menendez's out-edges belong to the Senator; 14 of 2,895 shipped AUG pairs, 0.58% of edge weight — an external-scraper defect, flagged, deliberately not fixed here.

**D8 RULED: no WSCALE in v1** — the tail trigger fired (5.043×) but with zero mass above p=0.9 and median Δp 0.0069, the graph is denser without approaching saturation; path discrimination intact. Re-evaluate on any rebuild that shifts MEA-1.

**MEA-8 registered:** `test_holistic_base` (always-on, pure fixtures) and `test_holistic_config` (certifies the pinned 2026-08-17 artifact bed) are in `run_tests.py`. The config battery carries a **per-vintage bed guard**: when either family's newest file moves past its pins it prints a visible SKIP-CLEAN and exits 0 rather than firing on lawful drift. Pre-verified against the live tree: the CU pins match there, holistic artifacts are absent, so it will SKIP-CLEAN post-merge until the artifacts are placed — at which point it runs FULL in the live tree.

---

## PRO-1 ADVERSARIAL ROUND + FIX ROUND — 2026-08-17/18 (the merge-gate debt, discharged)

Five independent lenses over the full `main...HEAD` diff, each finding then put to a **refutation-biased**
verifier (default position: the finding is wrong). **32 findings · 9 serious put to refutation · 2 refuted ·
7 surviving · 0 rated merge-blocking.** The CU production path was independently confirmed inert by the
lens whose only job was to break it — matching the old-vs-new behavioral parity proof run separately. What
the round actually caught was that the **test net protecting that path had holes**, several of them the
evaluator's own.

### Independently re-verified before acting (verify-don't-infer; a reviewer can be wrong)

| Claim | Check | Verdict |
|---|---|---|
| `latestAction` misses real origin-chamber passage | `118hres5`: latestAction "Motion to reconsider laid on the table…" no match, while the actions list contains "Passed/agreed to in House…"; `118hconres86` likewise | **CONFIRMED** |
| Duplicate cosponsor items on one bill | `118hr6116`: 30 items, 27 distinct — G000578/L000596/S001214 each twice, as (original, withdrawn) then (regular, live) | **CONFIRMED** |
| COR-5 mixes denominator populations | tie-capable shares are 29.5% / 17.2% / 1.5%, not the reported 23.7% / 14.0% / 1.2% | **CONFIRMED** |

### FIXED, each with a regression test that fails without the fix

| # | Defect | Fix | Evidence |
|---|---|---|---|
| 1 | **The config battery self-retired into a scored PASS on every tree but the build worktree.** Its pinned artifacts are `*.xlsx` — gitignored — so post-merge the kernel gate would have counted "1 passed, 0 FAILED" while running **zero** contamination assertions, indefinitely. One weekly refresh would also have retired it even where artifacts existed. | Battery **restructured into two tiers**: TIER A (contamination) runs ALWAYS against **synthetic plants** in a sandbox root and depends on no real artifact; TIER B (artifact invariants) runs on ANY holistic vintage present and is pinned to no filename, so lawful drift cannot retire it. Skips are reported separately and never counted as passes. | artifacts present **38 / 0 / 0**; artifacts absent (live-tree condition, simulated by hiding them) **22 passed, 0 FAILED, 1 SKIPPED** — up from a vacuous 1 |
| 2 | **ISO-3 — the highest-severity contamination path — was a stdout grep**, and the grepped line prints *before* any layer folding, so a contaminated fold was invisible to it. The record claimed PASS. | Replaced with the **content-hash control comparison the framework actually specifies**: the augmenter runs twice in-sandbox, with and without a holistic file at the root, and the Edges hashes are compared. | passes; now catches fold-level contamination the old check could not see |
| 3 | **Directed-cache isolation was never really checked** — the assertion tested cache-key *membership*, which stays true even when a holistic graph clobbers the production key, and it omitted the two keys that matter. | Checks **object identity and content** of both caches across a full config round trip, and asserts `_c['dadj'] is not _c['dadj@holistic']`. | 5 new assertions, all passing |
| 4 | **Duplicate cosponsor items were double-counted**: one member on one bill became two ties of two different roles and inflated C, depressing every other tie on that bill through 1/√C. | Collapse to the last item per bioguide; C is the DISTINCT count; collapses are counted, never silent. | rebuild: **9 items collapsed, 410,411 → 410,406 ties** (exactly the predicted 5); fixture plus a negative control that the pre-fix value fails |
| 5 | **COR-5 (a HARD + DELIVERABLE bar) reported against the wrong denominator** — zero-cosponsor bills can never carry a tie, so including them understated the loss by up to 5.8pp. | Share now divides by the **tie-capable** population; the all-bills figure is still printed for reference. | **29.5% / 17.2% / 1.5%**; fixture pins 1/2, not 1/3 |
| 6 | **PAR-5 / PAR-6 / COR-9 write-side had zero automated coverage** while the record carried verdicts for them. | New sandboxed write-side block: the co-appearance transform value and its n≥2 floor, the hard-fail on a missing declared layer, and the production-name refusal. | 5 new assertions, all passing |
| 7 | **Manifest provenance overstated**: it pinned every zip in the archive directory including ones the build never read, recorded no hash of its own output, and the name asserts checked prefix but not extension. | Pins only the zips the dial actually read; **fail-closed** when a dialled bill type has no zip (a silently dropped type would produce a plausible-but-wrong graph); records a canonical content hash of its own output; extension enforced. | fixture for the extension refusal |
| 8 | **PATH-4 tested Python against Python** — it re-implemented the template's kernel in this repo's language, so it could not see drift in the shipped JS. | Kept the numeric comparison, **made it state its own scope in its output**, and added a check that reads the template TEXT and asserts the three load-bearing JS lines still say what the mirror assumes. | passes; template lines verified present |

Re-verified after the fixes, on the corrected artifacts: **COR-7 determinism PASS** (double-build canonical hash `9530a3ea7e0e`), **COR-2 identity PASS on every row**, **COR-3v2 aggregate mass PASS at 4.26×**, **PATH-4 max Δp 0.000e+00 on both configs**, MEA figures unchanged, base fixtures **34 / 0**.

### CORRECTIONS OF RECORD (claims this document made that the evidence did not support)

1. **"ISO-3 … PASS"** in the run-all scoring sheet rested on a stdout grep, not the specified content-hash comparison. The bar is now implemented as specified; the earlier PASS is **withdrawn and re-earned**, not carried forward.
2. **PAR-5 / COR-9 / PAR-6 verdicts** were recorded with no automated coverage behind them. Coverage now exists; those verdicts are likewise re-earned rather than inherited.
3. **PATH-4** was described as "re-implements the tpl's own kernel math … non-circular". True as far as it went, but it does **not** execute or read the shipped JS — a limitation the wording did not convey. The test now says so in its own output.
4. **MEA-4's "co-appearance +198 → real non-cosponsor signal"** stands as a *count* but **not** as a magnitude claim — see open item B.

### OPEN — genuinely Paul's to rule (recorded, not silently decided)

**A. D6-b re-open: the SUCCESS multiplier is nearly inert.** `latestAction` is the *last* action, not the high-water mark, so a bill that passed its origin chamber and then died across the Capitol scores SUCCESS = 1.0. Measured over 117–119: `PASSED_RE` fires on `latestAction` for 1,083 of 55,195 bills (2.0%) but on some `<actions>` item for 5,019 (9.1%); **2,652 of the 37,076 tie-contributing bills are affected, carrying 39,390 of 410,406 ties**, and scoring them would raise unrolled tie-weight about 14.9%. The builder is **faithful to the ruling** — D6-b pinned scraper parity, and the CU scraper reads the same field — so this is an *inherited* limitation, not a holistic regression. But unlike the scraper, this builder has the full `<actions>` list in hand. Scanning it is a **spec change that breaks CU parity**, which is Paul's call. The builder documents the caveat in its own docstring and does not act on it.

**B. D2 re-open: the co-appearance layer's transform and calibration.** Two linked issues. (i) The freeze addendum named a Fink-style volume-normalized transform; the code implements the guide's *other* sanctioned option, a fixed per-episode weight — because `co_appearance.json` **carries no per-member appearance volume at all**, so the named transform was not implementable from the shipped input. That blocker should have been surfaced as a D2 re-open rather than routed around; it is surfaced now. (ii) `COAP_CAP=0.5` is **4.2× the HCoI-style cap it claims to mirror** (HCoI tops out at 0.12): the co-appearance floor weight of 0.10 sits at roughly the 36th percentile of real cosponsor weights and the cap at roughly the 77th, so all 198 admitted edges outrank a third of genuine cosponsorship ties. Options: lower the cap to HCoI parity (~0.12), emit per-member volume from `co_appearance_layer.py` and implement the Fink transform, or ratify the current dial. Rebuilding on a new dial is minutes, not a re-collection.

### Debts still carried past this round (unchanged, recorded)

The `audit_full` holistic schema-guard section (deliberately deferred — editing a 1,200-line audit harness at a merge boundary is worse risk than a recorded follow-up); PATH-3 holistic bundle; MEA-6/7 (`kb_benchmark`, `mc_stability_check`) under the holistic config — each of which wants the live tree's full data plane.

---

## CORRECTION OF RECORD — 2026-08-18: the COR-3v2 root cause was WRONG (Menendez, not Moran)

Paul asked for a collision check. Running it caught an error in this document, made by the evaluator, in
the merge-gate section and carried into the freeze addendum, the brain, and three commit messages.

### The wording being corrected, quoted verbatim

> "all 8 misses root-caused to ONE CU-side scrape defect: the scrape attributed Senator Jerry Moran's
> (`M000934`) sponsorships (`117s321`, `117sres470`, `119s410`) to Representative Nathaniel Moran's
> bioguide (`M001226`) — the ambiguous-surname mapping failure class"

and its restatement:

> "**Side finding routed to the CU lane:** the production CU graph carries the Moran misattribution
> (Nathaniel 9 out-edges including Jerry's Senate ties; Jerry 3)"

### What is actually true

`M001226` **is not Nathaniel Moran.** Verified against `congestion.json` and against the CU workbook's own
`From_label` column, which says so in plain text:

| bioguide | actual member | in the 533 roster? |
|---|---|---|
| `M001224` | Nathaniel Moran (House, TX) | yes |
| `M001226` | **Robert Menendez** (House, NJ-08) | yes |
| `M000934` | Jerry Moran (Senate, KS) | yes |
| `M000639` | **Robert Menendez** (Senate, NJ) | **no — departed** |

The real mechanism is a **full-name collision across the roster boundary**: Senator Robert Menendez
(`M000639`, NJ, left the Senate in 2024 and is therefore **absent from the 533**) sponsored **232 bills**
across the 117th–118th. His son, Representative Robert Menendez (`M001226`, NJ-08), **is** in the roster.
The CU scrape credits the Senator's sponsorships to the Representative.

Per-edge proof, against BILLSTATUS as ground truth: for each of the 8 targets, the number of bills
sponsored by Menendez-**senator** that the target cosponsored vs by Menendez-**representative** —
B001288 77/0 · C001056 21/0 · C001075 20/0 · G000555 35/0 · H001079 4/0 · K000393 9/0 · V000128 58/0 ·
W000437 11/0. The Representative sponsored **zero** bills with any of them.

### How the wrong claim was reached (so the method error is on the record too)

The original query asked "which sponsors have ≥6 of these 8 members as cosponsors?" and Jerry Moran came
back with 3 such bills. That is a **co-occurrence artifact**: those 8 senators are a common cosponsor bloc,
and the actual top sponsors by that measure are E000295 (9 bills), P000145 (5), G000386 (5), W000790 (5) —
Moran is not even in the top eight. A pattern query was read as a causal answer. The correct test is
per-edge and restricted to the candidate sponsor, which is what the table above reports.

### Corrected finding, with its blast radius measured

**The production CU cosponsor graph's Rob Menendez node is entirely misattributed.** All **9** of his
directed out-edges in the CU base (weight 4.077) are unsupported by BILLSTATUS; BILLSTATUS shows his real
figures as 89 out-edges and 182 in-edges over the all-bills universe. In the **shipped production AUG**
(`congress_cosponsor_network_AUG20260802.xlsx`), 14 of 2,895 pairs touch him — **0.48% of pairs and 0.58%
of total edge weight**. Small in magnitude, total in scope for that one member. It is an **external
R-scraper defect** (the scrape resolves a sponsor string to a roster member), flagged for the CU lane and
deliberately **not** fixed here.

### The collision census Paul asked for — complete, with denominators

| Census | Result |
|---|---|
| Full display-name collisions **within** the 533 roster | **0** |
| Surname collisions within the roster | **29 surnames covering 78 members** when a matcher keeps a hyphenated surname whole, **30 / 81** when it splits on the hyphen — splitting additionally collides Mariannette Miller-Meeks with Gregory Meeks, and Cindy Hyde-Smith with the five Smiths. (The first pass quoted only the 29/78 figure, which silently picked one matcher model; both are now reported, and `fec/tools/identity_collision_census.py` prints both.) 13 of these surnames span both chambers (Collins, Cruz, Johnson, Kelly, Kennedy, Kim, Lee, McCormick, Moran, Murphy, Peters, Scott, Smith) — a first-name-blind matcher collides on any of them |
| Roster member sharing **first+last name with a non-roster sponsor** in the 117–119 universe | **exactly 1: Robert Menendez** (`M001226` roster ↔ `M000639` departed, 232 sponsored bills), against a denominator of **192 non-roster sponsors with a known name** |
| Of those, **actually exploited** in the shipped CU graph | **1 of 1** — all 9 out-edges unsupported |
| CU roster-internal edges unsupported by BILLSTATUS, repo-wide | **8 of 1,874 (0.43%)**, every one of them a Menendez edge — so the misattribution is **confined to this single member** |

The load-bearing lesson: the within-roster census returns **zero** collisions and would have declared the
graph clean. The defect lives in the pair that the roster **cannot see** — a departed member colliding with
a sitting one. Any future identity guard must be checked against the historical member universe, not just
against the current 533.

### What changed and what did not

**No holistic-configuration number changes.** The COR-3v2 verdict is unaffected: presence still 1,866/1,874
direct with all 8 root-caused (to a different, now-correct cause), aggregate mass still 4.26×, and the
holistic builder — which keys on native BILLSTATUS bioguides — carries Menendez correctly at 89/182. Only
the *attribution of the cause* was wrong. Corrected here, in the freeze addendum, and in the brain; the
three commit messages that carry the wrong wording are frozen in git history and are superseded by this
block rather than rewritten.

### Shipped as a reusable tool

`fec/tools/identity_collision_census.py` — read-only, prints, writes nothing, asserts nothing. It runs
all four sections above against any tree, and every section that lacks an input SKIPS with a visible
notice rather than passing silently. Two of its own bugs were caught by running it and were fixed before
it shipped, both by the printed denominators: section 2 originally read the roster-filtered holistic
graph, which contains zero non-roster sponsors *by construction*, and so reported “none found” against a
denominator of 0 (it now reads the raw bill cache, denominator 192); and section 1 quoted a single
surname figure, silently picking one hyphen-matcher model.

It is deliberately **NOT registered as a kernel test**: the CU graph currently fails section 3, and
encoding a known-failure exception into a gate is Paul’s call, never a tool’s (change-control law 7).
Arm it as a gate once the scraper defect is fixed or the exception is explicitly ratified. It is also the
natural pre-flight check for the **120th-Congress rollover**, where an arriving freshman sharing a name
with a departing member reproduces the Menendez class exactly.

---

## ARTIFACT DEPLOYMENT TO THE LIVE TREE — 2026-08-18 (Paul: "Deploy the holistic artifacts to the live tree")

The one operational choice held back at the merge. Executed with the contamination proofs re-run **in the
live tree**, because placing a second network family at the production root is precisely the risk the
naming discipline exists to contain.

### Deployed

| Artifact | Size | Source → live sha256 |
|---|---|---|
| `holistic_network_BASE_20260817.xlsx` | 6.08 MB | `a7e927335b8f8287` → identical |
| `holistic_network_AUG_20260817.xlsx` | 3.29 MB | `2abf6920c882e950` → identical |
| `data/holistic/billcache_{117,118,119}.ndjson` | 21 MB | identical (3/3) |

Copied temp-then-atomic-rename, so no glob could ever observe a partial file; the `.tmp` names match
neither the production nor the holistic pattern. Pre-flight verified the BASE artifact against the
`output_canonical_rows_sha256` recorded in the manifest merged into main — `e5630b802c5495d8`, match.
The bill caches were included so the live tree is self-sufficient for both a rebuild and for
`identity_collision_census.py`, which defaults to `<root>/data/holistic`.

### Post-deployment proofs, run in the live tree with the holistic family present at the production root

| Proof | Result |
|---|---|
| Engine loader under default env | `congress_cosponsor_network_AUG20260802.xlsx` — **unchanged** |
| Directed loader under default env | `congress_cosponsor_network_20260625_205554.xlsx` — **unchanged** |
| Weekly-refresh augmenter base-pick | the CU base, 2,173 edge rows — **unchanged** |
| `ranks_python.json` / `dashboard_data.json` / `bipartisan.json` | **byte-identical** across the deployment |
| `NET_CONFIG=holistic` | now live: 62,996 pairs (AUG) / 93,952 directed edges (BASE) |
| Kernel gate | **156 / 0** |
| Config battery in the live tree | **38 / 0 / 0** — up from 22 passed + 1 skipped, i.e. TIER B armed |
| `identity_collision_census.py` | now runs with no env vars: 192-sponsor denominator, Menendez found |

### TWO UNINTENDED PRODUCTION WRITES BY THE EVALUATOR — both caught, both remediated

Recorded because the corrector's own defects belong in the corrector's own record, and because both came
from the same root cause: **running a producer without first reading what it writes.**

1. **`congress_cosponsor_network_AUG20260818.xlsx` was created at the live root.** Demonstrating the
   augmenter's base-pick, I ran `build_multilayer_network.py` with `AUG_OUT` unset — so it wrote a real CU
   AUG. Being the newest AUG, *every production loader would have selected it*. Content compared against
   the shipped `AUG20260802` before any action: **2,895 rows, canonical hash `d422b078081da289` on both —
   identical**, so no behavior would have changed. Removed anyway; the file was unauthorized, carried a
   fresh mtime that would trip freshness audits, and leaving it would have made an accident into the
   production graph selection. Verified afterwards: 8 AUG files, newest Aug 2, loaders restored.
   *Silver lining, recorded as evidence not as justification:* it is an independent confirmation that the
   CU augmenter is idempotent on current inputs.
2. **`data/network/kb_benchmark.json` was overwritten with holistic-config results.** I ran MEA-6 under
   `NET_CONFIG=holistic` describing the run as "KB_OUT redirected" — but `kb_benchmark.py` **has no output
   dial**; I asserted a safeguard that does not exist. Blast radius is genuinely low (the file is a
   diagnostic the chain does not consume, and the script says so itself), but it held holistic numbers
   under a production filename. Restored by re-running under the default config. **Stated precisely: that
   is a fresh CU-config run, not a byte-restoration of the prior file** — kb_benchmark is regenerated on
   demand and consumed by nothing, so a current CU run *is* its correct production-meaning state. The
   restored output shows the documented CU signature (top-decile-unallocated led by Barr, Hill, Emmer —
   matching `AUDIT_FINDINGS_2026-07-04.md`).

**Practice adopted for the rest of this lane:** read a producer's write targets *before* running it. Applied
immediately afterwards, and it paid: `build_dashboard_bundle.py` writes **two** artifacts, and the second
is `bipartisan.json` — a production kernel input that ISO-7/D12 explicitly bar the holistic graph from
feeding. Inspecting first showed `DASH_OUT` redirects *both*, so PATH-3 could be run safely.

### Debts closed by the deployment

- **PATH-3 — CLOSED.** Holistic bundle built under `NET_CONFIG=holistic` with `DASH_OUT` pointed outside
  the live root: 481.1 KB, 533 nodes, 420 drawn edges, 19 issues. The holistic-derived `bipartisan.json`
  landed **in the scratch directory** while production's stayed byte-identical (`429bf5deaa178036` before
  and after) — the ISO-7/D12 bar proven operationally, not just on paper.
- **MEA-6 — CLOSED (REPORT-ONLY).** `kb_benchmark` runs clean on the holistic graph: spectral radius
  ~19.07, δ=0.0446, KB↔legislative-score ρ=+0.464, KB↔optimizer-allocation ρ=+0.225 (all members, n=533).
  **Labeled observation for Paul, not a validated claim:** the CU configuration's recorded reading has the
  allocator *anti*-correlating with centrality (−0.21, 2026-07-04, "by design" — the model buys marginal
  persuasion, not access), whereas the holistic graph shows a positive allocator correlation. That is a
  qualitative structural difference worth a look; per HON-3 the two numbers are **not** a comparable delta
  (different universes, different vintages, different role weights), so no magnitude claim is made here.
- **MEA-7 — IN FLIGHT.** `mc_stability_check` under the holistic config is still running: it builds four
  budget frontiers, and the holistic graph is ~25× denser than CU (62,996 vs 2,555 pairs), so it is far
  slower than the CU-vintage run. Self-cleaning by design (`_mcstab_*.json` created and removed); live
  root verified clear of temps. Result to be recorded when it lands.

### Revert

Deleting `holistic_network_BASE_20260817.xlsx`, `holistic_network_AUG_20260817.xlsx` and `data/holistic/`
from the live root returns it to the pre-deployment state exactly; the merged code then fails closed under
`NET_CONFIG=holistic`, and TIER B of the config battery returns to a visible SKIP. The manifests are
tracked in git and would remain, which is correct — they document artifacts that can be rebuilt.

### CORRECTION — PATH-3 is NOT closed (same day, before the claim could travel)

The commit immediately above claims "PATH-3 CLOSED". That is **wrong**, caught by checking the artifact's
own metadata instead of trusting the run's exit status. Recorded here rather than amended away.

**What gave it away:** the produced bundle reports **2,555 drawn edges**. The holistic AUG has **62,996**
pairs. A holistic bundle cannot have the CU pair count.

**Verified:** the produced bundle's `engine.adj` is an **identical edge set** to the production bundle's
(2,555 vs 2,555, set-equal). So the display graph came from the CU family, not the holistic one.

**Root cause:** `fec/surfaces/build_dashboard_bundle.py:77` selects its display graph with its **own
hardcoded glob** — `select_network_file(glob.glob(MB_ROOT + r'\congress_cosponsor_network_*.xlsx'))` —
and `:100` does the same for the BP source. Neither goes through the config-keyed `load_network()`.
**This is exactly what the ISO-1 census flagged at Gate 0** ("`build_dashboard_bundle.py:77` — config-key
at G3/G4 (D7)"), and it was never wired, because D7 ruled *engines + labeled preview only* and the bundle
was deferred. The census was right; the PATH-3 claim forgot it.

**Where the holistic banner came from** (which is what misled me): `fec/engine/flip_model.py:52` calls
`MC.load_network()` at **module level**, so merely importing it under `NET_CONFIG=holistic` binds the
holistic graph and prints the banner — while the bundle's own display graph stays CU. A banner is not
evidence of what an artifact contains.

**Was the rest of the bundle contaminated?** No, and this is worth stating precisely rather than
hand-waving: the exported engine vectors `pmult`, `emult`, `dmult` and `bpf` are **0 of 533 values
different** from production, because those are derived from `member_receptivity.json` and
`bipartisan.json` — files, not the graph. So the run produced a **CU bundle**, not a mixed one, and not a
holistic one.

**Two claims in the preceding commit are corrected:**
1. "PATH-3 CLOSED" → **PATH-3 REMAINS OPEN.** Producing a holistic bundle requires config-keying the
   bundle builder's two globs, which is a code change under D7's deferred branch — Paul's gate, not a
   run-time env var.
2. "the holistic-derived `bipartisan.json` landed in scratch" → the redirected `bipartisan.json` was
   **CU-derived** (the BP source at `:100` is the non-AUG CU glob). The **safety** half of that claim
   still holds and was independently measured: production `bipartisan.json` is byte-identical
   (`429bf5deaa178036`) before and after, and `DASH_OUT` does redirect both writes out of the live root.
   Only the *characterization* of the redirected file was wrong.

**What this does not change:** nothing about the deployment, the CU-safety proofs, the kernel gate, the
config battery, MEA-6, or any holistic artifact. The scratch bundle is discarded as evidence of nothing
beyond this finding.

**Standing lesson, third instance in this arc:** an exit status and a banner are not verification. The
check that caught this was reading the artifact's own contents and comparing a count against a number I
already knew (62,996). Each of the three corrections in this arc came from doing that; none came from a
tool telling me something was wrong.

### MEA-7 — CLOSED, PASS (`mea7_mc_stability_holistic.txt`)

`mc_stability_check` under `NET_CONFIG=holistic`, TOPIC=Interchange, on the 62,996-pair graph:

| Variant | Seeds picked | Set overlap vs production | Prefix agreement | Spread delta |
|---|---|---|---|---|
| MC=100, SEED=7 (5× MC budget) | 45 | **100% (Jaccard)** | first 2 identical | −1.6 |
| MC=20, SEED=1 (different RNG) | 44 | 98% | first 4 identical | −0.7 |
| MC=20, SEED=13 (different RNG) | 44 | 98% | first 6 identical | +2.4 |

**Reading: MC=20 + CRN is not draw-overfit on the holistic graph.** This was a real open question — the
recorded 100%-overlap validation is CU-vintage, and a graph ~25× denser is exactly where a fixed MC budget
could stop sufficing (guide §6.2). Measured, not assumed, and it holds. No MC dial change is warranted for
the holistic config. Self-cleaning confirmed: no `_mcstab_*.json` left at the live root.
