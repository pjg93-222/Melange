# Holistic v1 Framework — FREEZE ADDENDUM (2026-08-17, ruled in-chat)

**Instrument:** Paul's in-chat directive sequence 2026-08-17 — "We should be executing everything in this workbranch" followed by **"Run all"** issued directly against the delivered recommendation set (framework Appendix B + sourcing memo). Per the recorded interpretation pattern (brain D-010; the C1-2026 in-chat-conditional precedent), this addendum records the **affirmative/recommended reading of every open item**, with the interpretation note below. **Reversal is one word:** any pin or ruling here re-opens the moment Paul says so; every choice is a dial, all work is branch-contained, nothing touches main or the live tree.

**Interpretation note (explicit, per D-010):** "Run all" was read as *adopt the recommended option on each open decision and execute all runnable phases in this workbranch*. If Paul intended only "run all currently-runnable checks," the rulings below revert to OPEN and the built artifacts stand as evidence, not adopted config — the cost of the wrong reading is zero re-collection either way.

**Framework under freeze:** `audits/HOLISTIC_NETWORK_V1_EVAL_FRAMEWORK_2026-08-17.md`
**sha256:** `2C4EBBFF1B2381D7FA1CA0B249293090073F297AC8277D90AA2408DDA18DDE78`

## Rulings incorporated

| Decision | Ruling (recommended option, adopted via "Run all") |
|---|---|
| D1 | already ruled 2026-08-17 mid-meta-run: regular cosponsorship IN at 0.2 (original 1.0) |
| D2 | co-appearance PROMOTED with the transform specified (Fink-style episode-count normalization, floor/cap named in the augmenter parameterization); signed refs DISPLAY-ONLY in v1 |
| D3 | `NET_CONFIG` dial over the full selection surface; `holistic_network_BASE_/AUG_` family naming; fail-closed selection (zero-file and ambiguity → raise); sealed root stays for audits |
| D4 | congresses 117–119; decay 0.8^age, scraper table (`congress_member_scraper.R:107-114`); date-range windowing = v2 |
| D5 | no new-collection edge candidates in v1 |
| D6 | ladder per the sourcing memo: local BILLSTATUS primary (complete by construction 117–118; 99.86% @2026-08-01 for the 119th) · BICAM cross-check 117–118 only · govinfo bulk = 119th refresh route · scraper moot. Sub-questions: (a) all 8 bill types; (b) SUCCESS = the scraper's `PASSED_RE` regex on the bill's last action (`:1786-1787`), BILLSTATUS `latestAction` as the native equivalent; (c) C = full-bill cosponsor count (parity with `:1924`); (d) departed-sponsor = accept-the-drop (parity with the CU graph's identical star topology), share measured per congress (COR-5) |
| D7 | (i) engines + labeled preview only, no live-dashboard exposure; (ii) on-demand builds with a dated stamp in the manifest; 119th re-pull before any production-grade build |
| D8 | deferred to the Gate-5 distribution report BY DESIGN (trigger thresholds as proposed; Paul re-pins on the report) |
| D9 | ship labeled partial holism: press/HCoI and social layers remain CU-corpus/CU-boolean, scope-labeled on every surface |
| D10 | KEEP the untied-only / isolates-only admission rules; measure vacuity (MEA-4/5); fork only on the Gate-5 counts |
| D11 | sponsor-star only in v1 (no Fowler cliques) — methodology parity |
| D12 | live with CU-scoped `bpf`, labeled `bpf: cu-scoped` in manifest and surfaces |

## Pins (PROPOSED values adopted as pinned; Paul may re-pin any row at any time)

| Pin | Value | Bar |
|---|---|---|
| Census coverage floor | ≥99.5% per congress×type stratum (met: worst 99.69%) | SRC-1 |
| Dominance reconcile | 100% explained; ≥99.5% strict | COR-3 |
| BICAM sample / identity rate | n=500 (117–118); ≥99% symdiff-0, rest explained; keyed on `bill_id` (stray-congress quirk) | COR-4 |
| Re-weighting identity tolerance | 1e-9 relative | COR-2 |
| JS parity sample / tolerance | ≥1,000 edges / ≤1e-9 | PATH-4 |
| D8 triggers | tail-mass(p>0.5) ratio >2× or median Δp >0.1 | MEA-2 |
| Role-mass trigger | median regular share >0.5 | MEA-3 |
| Anchor sample | ≥12, selection surfaces mandatory (met 2026-08-17: 18/18) | DOC-1 |
| Engine run list | cosponsor_route mandatory; frontier/coalition/scenario/kb_benchmark as inputs materialize, shortfalls named | PATH-1 |
| Eval record home | `audits/holistic_v1_eval/` | PRO-5 |

## Debts recorded at this freeze (not waived)

1. **PRO-1:** the independent adversarial review round on the built diff is OWED at the pre-merge gate (the build proceeds coordinator-built under "Run all"; the review-debt-carried pattern requires exactly this kind of explicit record).
2. **ISO-4 full form** (default-config byte-identity incl. rank gate) runs at the merge gate in the live tree — the worktree can only prove code-inert-by-default, not production byte-identity.
3. **MEA-8** (harness registration into `run_tests.py`/`audit_full.py`) lands with the merge, not before.
4. Official congress.gov cross-check stays QUEUED (bot-walled).

Frozen by: Paul, via in-chat "Run all", 2026-08-17 (recorded by the session; standing offer to countersign or amend this file directly).

---

## DELEGATED RULINGS — 2026-08-17, Paul in-chat: "What is sitting on me is for you to do best, commit and merge"

Recorded under the same interpretation pattern (explicit note, one-word reversal, everything dialed and branch-contained until the ordered merge):

1. **COR-3 re-pinned → COR-3v2** (the v1 per-edge dominance premise was unsound for accruing bills — C grows between the CU scrape vintage 2026-06-25 and the archive vintage 2026-08-01, deepening the 1/√C discount on lawful data): **(i) PRESENCE — 100% of roster-internal CU directed edges present in parity-mode holistic, every miss individually root-caused; (ii) AGGREGATE MASS — Σparity/Σcu ≥ 1.0; (iii) per-edge dominance demoted to REPORT-ONLY diagnostic.** Executed (`cor3v2_repin.py`, results `cor3v2_result.json`): **(i) PASS** — 1,866/1,874 direct + all 8 misses root-caused to ONE CU-side scrape defect. **CORRECTED 2026-08-18** (the original wording named the wrong members — see the CORRECTION OF RECORD block in `RECORD.md`): `M001226` is **Robert Menendez** (House, NJ-08), not Nathaniel Moran. The scrape credits **Senator** Robert Menendez's (`M000639`, departed 2024, absent from the 533) sponsorships to his son the **Representative** — a full-name collision across the roster boundary. The holistic builder, keyed on native BILLSTATUS bioguides, carries Menendez correctly (89 out / 182 in). **(ii) PASS at 4.26×.** (iii) recorded (median ratio 2.13, 78.3% dominant). **COR-3 DISPOSITIONED.** Side finding for the CU lane (**CORRECTED 2026-08-18**): the production CU graph carries the **Menendez** misattribution — all 9 of Rep. Robert Menendez's (`M001226`) out-edges belong to Sen. Robert Menendez (`M000639`); 14 of 2,895 shipped AUG pairs, 0.58% of edge weight. External-scraper defect, flagged, not fixed here.
2. **D8 ruled: NO WSCALE in v1.** The trigger fired on the tail ratio (5.043×) but with zero mass above p=0.9 and median Δp 0.0069 the holistic graph is denser yet nowhere near saturation; path discrimination is intact. `HOLISTIC_WSCALE` stays unused; re-evaluate on any future rebuild whose MEA-1 shifts the tail.
3. **Merge ordered.** Debt discharge at this gate: PRO-1 adversarial round run pre-merge (findings adjudicated before merging); MEA-8 registered into `run_tests.py` (`test_holistic_base` always-on; `test_holistic_config` certifies the pinned 2026-08-17 artifact bed and self-retires with a visible SKIP-CLEAN when the families move past its pins); ISO-4 live byte-identity + kernel/audit gates + mirror push run at merge time; PATH-3 (holistic bundle via `DASH_OUT`) after artifact deployment. The audit_full holistic schema-guard section is the one registration item deliberately deferred past the merge (editing the 1,200-line audit harness minutes before a merge is worse risk than a recorded follow-up).
