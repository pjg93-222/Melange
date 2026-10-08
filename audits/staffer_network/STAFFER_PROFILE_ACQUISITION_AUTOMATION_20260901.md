# Staffer/Lobbyist Profile Acquisition Automation — 2026-09-01

## Current outcome

The acquisition path is now an incremental, resumable web-scraping pipeline rather than a serial chat/browser workflow.

- Rapid source manifests: 43 identity-resolved people across four batches.
- Authenticated LinkedIn evidence ledger: 10 profiles, 74 employment episodes, 17 education episodes.
- Structured public-discovery ledger: 72 people, 478 employment episodes, 109 education episodes. The consolidated evidence SHA-256 is `267c39d1b04c30dea8d04397558dd5680af4a2c7b8e4aabcca23d679d65c9476`.
- Public fact-span corpus: 1,442 people; 831 currently have captured candidate spans. The cleaned generation contains 2,038 source spans, 43,780 employment-bearing lines, and 22,656 education-bearing lines. Its evidence SHA-256 is `ee4931ee94bccf45b8c2197b1908d108447fc3a0eb48e16bb211586181e8361b`.
- Bulk measurement covers all 1,442 mapped people in seven 200-person shards and one 42-person remainder. It contains 43,699 quality-filtered employment candidates, 43,191 dated employment candidates, 3,133 identity-token-matched employment candidates, and 12,231 education candidates; 10,506 low-quality lines were rejected.
- Bulk coverage states: 692 `DATED_IDENTITY_MATCHED_CANDIDATES`, 127 `DATED_CANDIDATES_REVIEW_REQUIRED`, 5 `UNDATED_EMPLOYMENT_CANDIDATES`, and 618 `NO_EMPLOYMENT_CANDIDATES`.
- Incremental public fan-out ledger: 2,384 discovered URLs. Current dispositions are 1,917 captured, 58 fetch errors, 125 HTTP errors, and 284 explicit skips. The capture ledger SHA-256 is `6802786556fd33916c89f5892e5d470ab8311e549924abfda55737608772a10a`.
- The PDF overlay processed 355 captured PDFs: 278 repaired and 77 retained as explicit extraction-timeout gaps. Successful repairs and failures are cached incrementally.
- The latest end-to-end cycle `profile-acquisition-20260901T044427Z` passed all component receipts with eight workers, a two-second shared per-domain pacer, a ten-second response ceiling, and two bounded attempts.
- Canonical identity promotions: 0.
- Canonical employment promotions: 0.
- Complete lifetime-employment assertions: 0.

The evidence ledgers remain candidate-only until identity and episode adjudication. This prevents same-name overlaps from becoming graph edges.

## Automated cycle

The preferred command performs structured-shard conversion, incremental public acquisition, structured consolidation, candidate extraction, and receipt composition in one run:

```powershell
python audits/staffer_network/run_full_profile_acquisition_cycle.py `
  --workers 8 `
  --per-domain-delay 2.0 `
  --timeout 10 `
  --max-attempts 2
```

The current receipt is `audits/staffer_network/full_profile_acquisition_cycle_current.json`. A cross-process lock prevents the scheduled heartbeat and a manual run from writing the capture ledger concurrently.

Every cycle now also writes `bulk_profile_candidate_bundles_generation_<timestamp>` with deterministic 200-person shards. These are the primary acquisition/measurement unit. Small agent-created structured shards are exception-review inputs, not the scaling mechanism.

The expanded discovery manifest `google_profile_search_manifest_20260901_v4_2000` contains 2,000 identities and 6,000 deterministic search queries, replacing the previous 200-person ceiling for the next discovery wave.

The main runner auto-discovers the legacy fan-out, every `rapid_public_profile_seeds_20260901*` directory, and prior capture ledgers:

```powershell
python audits/staffer_network/run_incremental_public_profile_pipeline.py `
  --output-root audits/staffer_network/rapid_public_profile_continuous_20260901 `
  --workers 8 `
  --per-domain-delay 2.0 `
  --timeout 10 `
  --max-attempts 2
```

Properties:

- Eight workers across domains.
- One shared in-flight request and monotonic pacer per domain.
- Robots enforcement.
- Hard per-response wall-clock ceiling.
- Content-addressed raw and visible-text artifacts.
- Completed-URL reuse; only new URLs and bounded retries are submitted.
- Atomic deterministic capture ledger.
- Explicit HTTP, fetch, robots, authentication, and search-transport dispositions.
- No CAPTCHA solving, cache rotation, cookie inspection, or access-control evasion.

Structured discovery shards are converted into scraper seeds automatically:

```powershell
python audits/staffer_network/structured_discovery_to_seed_shard.py `
  --input-root audits/staffer_network/rapid_structured_discovery_20260901 `
  --output audits/staffer_network/rapid_public_profile_seeds_20260901_structured_auto/legistorm_lda_profile_fanout_20260901_slice_9000.ndjson
```

Structured episodes consolidate with duplicate-ID and promotion guards:

```powershell
python audits/staffer_network/consolidate_rapid_structured_profile_evidence.py `
  --input-root audits/staffer_network/rapid_structured_discovery_20260901 `
  --output-root audits/staffer_network/rapid_structured_profile_evidence_20260901_current
```

The public-text parser converts captured pages into person-linked, review-only employment/education spans:

```powershell
python audits/staffer_network/build_incremental_public_fact_candidates.py `
  --seed-root audits/staffer_network/legistorm_fanout `
  --seed-root audits/staffer_network/rapid_public_profile_seeds_20260901 `
  --seed-root audits/staffer_network/rapid_public_profile_seeds_20260901_batch2 `
  --seed-root audits/staffer_network/rapid_public_profile_seeds_20260901_batch3 `
  --seed-root audits/staffer_network/rapid_public_profile_seeds_20260901_batch4 `
  --capture-ledger audits/staffer_network/rapid_public_profile_continuous_20260901/incremental_public_page_captures.ndjson `
  --output-root audits/staffer_network/incremental_public_fact_candidates_<generation>
```

## Discovery transport state

- Google browser search: stopped at `CAPTCHA_UNUSUAL_TRAFFIC`.
- DuckDuckGo HTML: stopped at `BOT_CHALLENGE_HTTP_202`.
- Bing HTML: automated search path disallowed by robots policy.
- Direct public/official/employer pages: active.
- Authenticated LinkedIn: browser exception lane only; no messaging, connecting, or following.
- LegiStorm Pro-only employment/education text: explicit gated gap; anonymous page titles and independently accessible evidence may still be captured.

## Important adjudication defect found

The local StoryCorps/TDR Capital association for `JIM MOORE` is a same-name merge and must not be used for the lobbyist identity. The LDA-linked person is James M. “Jim” Moore, former Schumer regional staff and current O’Donnell & Associates vice president/policy director. The structured discovery workflow records the competing identity as a rejection.

## Continuous execution

The existing heartbeat `finish-staffer-lda-reconciliation` has been reactivated under the name **Finish accelerated staffer profile acquisition**. It runs every 15 minutes in this thread, consumes new discovery shards, executes the incremental scraper and parsers, validates hashes/counts, and preserves unresolved/gated states. It must not report completion until measured complete/partial/unresolved counts and required adjudication are available.

## Verification and external-review state

- `python -m pytest fec/tests/staffer_network audits/staffer_network -q`: **222 passed, 73 subtests passed**.
- The Claude Fable/Opus 5 maximum-effort acquisition review prompt is `data/staffer_network/reviews/CLAUDE_OPUS5_ACQUISITION_REVIEW_PROMPT_20260901.md`.
- The 2026-09-01 review attempt did not run because the Claude account reported an exhausted Fable 5 usage-credit balance. No Sonnet substitution was made. Acquisition and local verification continue, but the requested fresh external review remains an explicit open gate.
