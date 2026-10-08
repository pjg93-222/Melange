# Legislative effectiveness lane: status record, 2026-09-12

Frozen vintage. One page for the whole lane as it stands tonight: what is built and where, what Paul ruled, what runs, and what waits on whom. Evidence for every figure sits in the packet `audits/legislative_effectiveness_shadow_20260911/` (live tree and Codex worktree f149).

## 1. Where the lane started

Codex Desktop, 2026-09-10 23:03 ET: Paul commissioned a plan for a Volden-Wiseman five-stage legislative effectiveness score (BILL / AIC / ABC / PASS / LAW; impact weights C = 1, S = 5, SS = 10; later cosponsors discounted by a half-life; CU and trade-publication mention frequency as the substance signal), then ordered its execution and a diff. The implementation thread died on a ChatGPT usage limit at 04:07Z on 09-11 (quota returns 2026-09-17 13:16) after building everything but the validation report and the diff presentation. Claude closed it out on 09-11 and 09-12.

## 2. What is in the live tree now

Applied 2026-09-11 on Paul's order ("Fully implement the new parameters", "Do it for me"): 11 modified modules and 15 new files (9 modules, 6 unittest suites), 26 of 26 hashes matching the Codex worktree, originals backed up at `backups\legislative_effectiveness_20260912\`.

| Live check after apply | Result |
|---|---|
| Six new suites | 77 of 77 pass |
| Production artifacts (ranks, primacy factors, industry tiers, member desk bundle) | byte-unchanged |
| Kernel gate | 187 passed, 4 failed (baseline 186 / 1 on 09-07) |
| Failures caused by this lane | 1: `test_run_legislation_pillars_and_ranks`, a source-literal pin on the refactored Leg% line; the wrapper is off the chain, so the weekly refresh is unaffected |
| Failures not this lane | say-do fail-open (identical with the pre-apply file), a missing legfix3 backup CSV, staffer surface `inspect` errors |
| `test_primacy_tier` | now passes (was the standing failure) |

Every candidate path is opt-in; nothing lobbyists read has changed. Candidate outputs live off-tree at `%LOCALAPPDATA%\Melange\legislative_effectiveness\shadow_20260912\` (generation verified, 766,568 checks).

## 3. What the shadow showed (118th, completed term, as-of 2026-09-06)

- Universe: 16,495 eligible measures (House 10,740, Senate 5,755) from the official BILLSTATUS archives; the CU-credited numerators are the adjudicated selection, 165 unique measures.
- Results-only board (raw realized results across chambers): Tier 1 and 2 were 100 percent House; all six legacy Senate Tier-1 members fell to ranks 90 to 231; members with one enacted CU-aligned vehicle vaulted on 2 to 3 measures. Paul rejected it on sight.
- Today's Tier 1 is exactly the 13 gated Champions, member for member.

## 4. Paul's rulings (brain commits `2a5a10b`, `da0bb56`, `f8ebdf7`, `8e0118c`, `ef5f11f`)

| Ruling | Content |
|---|---|
| D-027 | success, amount and substance are within-chamber percentiles |
| D-026 | results-only headline basis; superseded the same day |
| D-028 | board = P × (0.80 + 0.20 × L), L = 0.35 success + 0.35 amount + 0.30 substance; reporting Leg% = L; seats, gate, conduct ladder and crown law unchanged |

Under D-028 on the 118th: 10 of 13 current champions keep Tier 1; Y. Kim, Huizenga and Daines come up from Tier 2 ranks 14 to 16; Crapo, Vargas and Rounds go to Tier 2; 74 of 533 tiers change; agreement with today's board 0.83; the enforced purity bar (0.556) keeps mid-purity high-volume members out of the top tiers. Cortez Masto sits at rank 18 (purity 0.551; she would need 0.604 at her delivery; delivery alone cannot seat her). Substance is inert until SS is calibrated: every scored bill weighs 5.

## 5. CU publications inventory for SS (opened 2026-09-12)

| Source | Access | Collected |
|---|---|---|
| America's Credit Unions | open; robots disallow its paginated listings and sitemap pages | 14 inventory URLs plus 2,481 known article URLs from the press cache; bodies collecting (run `cupub-bodies-20260912`, PID 55516, login-walled pages metadata only) |
| NCUA newsroom (regulator family, separate) | open | 288 URLs 2023 on; bodies collecting |
| American Banker CU section | open, 10 s crawl-delay, paywalled | 601 URLs 2023-01 to 2026-09; bodies withheld pending Paul |
| CU Times, CUInsight | 403 to every non-browser client | not collected |
| CU Today | robots disallow all but named search engines | not collected |

Store: `%LOCALAPPDATA%\Melange\cu_publications\` (inventory receipt `cupub-inventory-20260912`, 903 URLs, 55 requests, zero blocks). The bootstrap collector is scratch tooling; the production collector is Codex work under `COLLECTOR_CONTRACT_CU_PUBLICATIONS_2026-09-12.md`.

## 6. Queued for Codex after 2026-09-17

1. `ACTIVATION_CONTRACT_2026-09-12_v2.md`: board mode `purity_delivery_v1`, `LEG_MODE=delivery_blend_v1`, chain producer, 119th House reserved-number rule, source-contract re-pin, suite registration, audit block, docs.
2. `COLLECTOR_CONTRACT_CU_PUBLICATIONS_2026-09-12.md`: the production publication collector with dedup, bill linking, exposure denominators and weekly refresh.

## 7. Paul's open calls

- American Banker paywalled bodies: collect or not.
- CU Times, CUInsight, CU Today: license, permission request, or exclusion.
- ACU member-only content: in or out. NCUA: separate family or counted.
- 2023 pre-merger CUNA and NAFCU newsrooms via the Wayback archive: yes or no.
- Cortez Masto's four off-axis acts: adjudicate under a class rule or leave (factor side, not this lane).
- The 117th term in the production aggregate; the distinct-measure gate minimum.
- OneDrive has dehydrated live data files to cloud-only placeholders (`data\stance`, `social_media.db`); hydrate or pin before the Sunday chain.

## 8. Evidence index

Packet root: `LEGISLATIVE_EFFECTIVENESS_SHADOW_VALIDATION_2026-09-11.md`, `README.md`, `ACTIVATION_CONTRACT_2026-09-12_v2.md`, `COLLECTOR_CONTRACT_CU_PUBLICATIONS_2026-09-12.md`, `IMPLEMENTATION_DIFF_2026-09-11.patch`, `NEW_FILES_MANIFEST.txt`. Evidence folder: reproduction and parity proofs, kernel logs, board analyses (`COMPOSITE_BOARDS_118*.md`, `CHAMPION_SHARE_AND_FLOOR_SWEEP.md`, `OUT_OF_SAMPLE_119.md`, `CORTEZ_MASTO_AND_COVERAGE.md`), publication recon and inventory runs.
