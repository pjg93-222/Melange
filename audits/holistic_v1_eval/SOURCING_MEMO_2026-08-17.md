# Holistic v1 — Phase-1 Sourcing Decision Memo (input to D6)

**Date:** 2026-08-17 · **Status:** EVIDENCE COMPLETE — the D6 ruling itself is Paul's. Census method + raw results: `census_g1.py` / `census_g1_results.json` (this directory; read-only run over the machine-local archives, executed in the eval workbranch per the 2026-08-17 execution-home directive).

## The census (SRC-1)

Two sources counted per congress × bill type; denominators named. **Self-denominator:** bill numbers are assigned sequentially per type per congress, so `max(number)` is the introduced count; `gap = max − files`. A gap-0 stratum is complete **by construction** (zip entries are unique, so files 1..N with max N admits no missing bill).

| Stratum group | Local BILLSTATUS (2026-08-01 pull) | BICAM snapshot | Reading |
|---|---|---|---|
| **117th, all 8 types** (17,828 measures) | **gap = 0 on every type** (hr 9,709/9,709 · s 5,357/5,357 · hres 1,532 · hjres 106 · hconres 125 · sres 877 · sjres 70 · sconres 52) | 17,836 rows (+8) | BILLSTATUS complete by construction; BICAM cross-agrees to +0.04% |
| **118th, all 8 types** (19,315) | **gap = 0 on every type** (hr 10,564 · s 5,649 · hres 1,627 · hjres 230 · hconres 135 · sres 942 · sjres 122 · sconres 46) | 19,282 rows (−33) | complete by construction; BICAM's known late-session tail (−33 rows, concentrated in sres −20) |
| **119th at vintage** (16,052 files) | gap = 22 total, all in hr (6) and s (16) — 0.14%, consistent with reserved numbers | **131 rows — unusable** | near-complete *as of 2026-08-01*; the 16-day-and-growing staleness is a refresh question, not a completeness question |

Proposed SRC-1 floor (≥99.5% per stratum): **met on every stratum** vs the self-denominator — worst stratum 119/s at 5,190/5,206 = 99.69%. Verdict binds when Paul pins the floor at freeze.

**Official congress.gov cross-check: QUEUED.** congress.gov and govtrack both bot-wall non-interactive fetches (403 / interactive challenge; the legfix5 lane hit the same wall). For 117–118 the external check is a formality per the construction argument; for the 119th it would only quantify post-vintage accrual — which the refresh cadence (below) handles anyway.

**BICAM quirk found (shapes COR-4):** a handful of rows carry bill numbers beyond their congress's range (117/hr max 11,200 vs true 9,709; 117/hjres max 919 vs 106) — congress-misassignment strays, matching the small row surpluses. The Phase-2 identity cross-check must key on `bill_id` and flag strays rather than trust BICAM's congress column raw.

## Recommendation for the D6 ladder

1. **Rung 1 — local BILLSTATUS archive = the primary source for all of 117–119.** Complete by construction for 117–118; 99.86% for the 119th at its 2026-08-01 vintage. Format is the schema the holistic base needs (sponsor, every cosponsor, dates, `isOriginalCosponsor`).
2. **Rung 2 — BICAM = independent cross-check for 117–118 only** (SRC-2 is enforced by the data itself: 131 rows for the 119th). Known −33-row 118th tail; stray-congress rows flagged, not joined.
3. **Rung 3 — govinfo bulk = the 119th refresh route** (same endpoint the archive came from; re-pull `billstatus119` at Phase-2 build time and on the D7(ii) cadence).
4. **Rung 4 — R scraper re-run: moot.** Nothing left for it to provide.

Universe size, measured: **55,195 measures across 117–119** (the guide's ~48k order-of-magnitude estimate was low; window and denominator: all 8 types, congresses 117–119, BILLSTATUS files at the 2026-08-01 vintage).

## The four D6 sub-questions — evidence in hand, decisions Paul's

- **(a) Bill-type set.** All 8 types are present in both sources. Note for the ruling: simple and concurrent resolutions *can* pass their origin chamber (SUCCESS is well-defined for them); they never become law. Options: all 8 types (maximal holism) vs bills + joint resolutions only. The census supports either; the builder takes the set as a dial.
- **(b) SUCCESS parse.** Reference = the R scraper's action regex (snapshot vintage); BILLSTATUS action codes are the native encoding; BICAM `bills_actions.csv` (334MB, on disk) provides an independent parse cross-check for fixtures. Build-contract item for the Codex spec.
- **(c) C definition** (size-norm cosponsor count): full-bill count vs roster-filtered. BICAM `cosponsors_count` is available as a per-bill cross-check either way.
- **(d) Departed-sponsor policy.** Not computable in Phase 1 (needs the roster join — `congestion.json` materialized into this worktree at Phase 2). COR-5 measures the dropped-bill share per congress before the policy binds.

## Refresh cadence (SRC-4)

Archive vintage 2026-08-01; the 119th accrues bills and cosponsors until 2027-01-03. Recommendation: re-pull `billstatus119` immediately before the Phase-2 build, then per the D7(ii) cadence ruling; **owner to be named in that ruling**.
