# Collector contract: CU-sector publications inventory for the substance (SS) layer

Date: 2026-09-12. Status: DRAFT for Codex dispatch after the 2026-09-17 quota reset. Authority: Paul, 2026-09-12, "Start collecting the CU publications for the SS inventory"; plan section 4 (frequency-based sector significance); D-028 keeps substance in the formula at 0.30 of delivery. Frozen once dispatched.

What exists today (bootstrap, not the production collector): `%LOCALAPPDATA%\Melange\cu_publications\inventory_20260912\` (903 URLs, receipt `cupub-inventory-20260912`) and `bodies_20260912\` (detached body run `cupub-bodies-20260912`, receipt on completion). Both were produced by scratch scripts under the session scratchpad; the production collector replaces them.

## OBJECTIVE

A network-free-at-scoring, receipted inventory of whole CU-sector publications (document level, never member excerpts) with verified bill links, per-organization exposure counts and a weekly refresh, so `build_bill_impact.py` can compute M (distinct publications mentioning a bill), U (distinct organizations) and F (exposure-normalized attention) per bill and per bill-age window, and the 5-to-10 threshold can be calibrated by blinded review.

## CONSTRAINTS (numbered; binding)

1. Claude authors no code; Codex writes the collector in a throwaway worktree; Claude reviews; Paul gates merge and the first sweep (SWEEP_APPROVED marker pattern of the C1-2026 collector).
2. Robots and access: fetch and obey robots.txt per host before every sweep; honor crawl-delay; never fetch a disallowed path (americascreditunions.org: `/*?page=` is disallowed, so no paginated listings and no sitemap pages; discover ACU article URLs only through allowed pages, RSS/Atom feeds if any, and the known-URL seed); stop a host on 403/429/503 or any challenge page; never rotate user agents, never impersonate a browser, never bypass a CAPTCHA (DE-014). Honest UA `MelangeCollector/1.0 (+contact)`.
3. Panel v1, by family: association = americascreditunions.org (public pages only; member-only content out of scope until Paul rules); trade_journalism = americanbanker.com `/creditunions/` (10 s crawl-delay); regulator = ncua.gov newsroom (collected, stored as its own family, NOT counted in the CU-sector profile unless Paul rules it in). cutimes.com, cuinsight.com (policy blocks) and cutoday.info (robots disallow) are excluded until licensed or permitted; the panel definition is versioned (`panel_id: cu_panel_v1`) and any change is a new panel id.
4. Unit and storage: one record per originating publication (final URL after redirects), raw HTML bytes plus extracted main text, content sha256, title, publish date with its source field, byline/organization, section, `login_wall` and `truncated_suspect` flags, robots decision, fetch timestamp. Store under `%LOCALAPPDATA%\Melange\cu_publications\<sweep_id>\` with an atomic sweep directory and `receipt.json` (counts by host/family/year/status, budget use, robots summary, sha256 of every ndjson). No production artifact and nothing under the live tree is written by a sweep.
5. Deduplication (plan section 4): remove member-specific URL fragments, duplicate scrape rows, article/PDF/HTML variants, syndicated copies and mechanically repeated newsletter boilerplate; a reproduced congressional-office release is not an association publication (legislator-communication rule) and is flagged, not counted. Substantively new updates are new publications; unchanged reprints are not.
6. Bill linking is a separate pass over stored text (no network): explicit references (`H.R. n`, `S. n`, joint resolutions) resolved to `Congress:type:number` only when the congress is determinable from the document date and the bill's introduction date in the official archives; act names matched against the official short titles of the eligible universe with the ambiguity kept visible; every link carries its evidence excerpt (160 chars). Sentiment, stance, adjectives and endorsement language are never read or stored by this collector.
7. Exposure denominators: per organization and per sweep, the count of eligible documents observed (E_bo) by month, so F can be computed; an organization with zero observed documents in a window is "unavailable", never zero attention.
8. Refresh: weekly, above the chain (like `weekly_refresh.py` collectors), never inside `run_pipeline.py`; incremental by URL with the fold pattern (`test_press_baseline_fold` safety properties: no row without a stored body enters, second fold adds zero rows, schema mismatch refuses).
9. Budgets: per-host request caps per sweep, pacing at or above robots crawl-delay and never below 3 s, and a hard stop on the first block; the receipt records every stop.
10. Glassbox: every sweep emits start / per-host / completion events (`task.cu_publications_sweep`, run id = sweep id).
11. Tests: robots wildcard matcher (the stdlib parser ignores `*`), redirect and final-URL handling, login-wall detection, dedup rules, bill-reference patterns with negative controls (a bill number inside a footnote of an unrelated act name; a reprinted office release), receipt completeness; registered in `run_tests.py`.
12. Docs: a runbook under `audits/` naming the panel, the robots facts, the exclusions and the calibration procedure (blinded historical review, matched bill-age windows 30/90/180 days) before any SS threshold is proposed.

## ACCEPTANCE CRITERIA (observable)

1. A dry sweep over the seed set (ACU known URLs, AB 2023 to date, NCUA 2023 to date) completes with zero robots violations and zero blocks, or stops with receipted reasons; the receipt reconciles request counts to the log.
2. Every stored document has a content hash, a title, a publish date with source, and flags; the login-wall and truncated counts are printed.
3. The dedup pass reports groups removed by rule; a planted syndicated duplicate is removed and a planted substantive update is kept.
4. The bill-linking pass produces `bill_media_evidence`-compatible rows; on a hand-checked sample of 50 references, precision and the unresolved-congress count are reported.
5. E_bo per organization per month is emitted for the sweep window; months with zero observed documents are marked unavailable.
6. The weekly refresh runs once end to end from the scheduler-equivalent entry point and adds only new URLs.
7. Kernel suites for the collector are green; no production artifact changed (hashes).

## IMPACT ENVELOPE

New modules under `fec/collect/` (collector, dedup, bill linker, receipt), tests under `fec/tests/collect/`, one `weekly_refresh.py` hook, one runbook under `audits/`. No change to scoring modules; `build_bill_impact.py` consumes the inventory only through a later, separate contract. Processes: the collector's own sweeps against the panel hosts within the budgets above; unit tests; no chain run.

## CONFIRMATION CONDITIONS

Codex returns the RECEIPT, the diff as before/after text with `git status --porcelain`, the dry-sweep receipt, the sample precision table, and the eight labeled lists. Claude reviews, a fresh read-only Codex thread hunts defects, Paul gates merge and SWEEP_APPROVED.

## Paul's open calls

- CU Times, CUInsight, CU Today: license, permission request, or exclusion (without them the trade-journalism family is American Banker only).
- ACU member-only content: in or out.
- NCUA: separate family only, or counted toward CU-sector attention.
- 2023 coverage of the pre-merger CUNA and NAFCU newsrooms (redirected today): whether an archive source (Wayback CDX over news.cuna.org and nafcu.org) is acceptable for the 118th first session.
