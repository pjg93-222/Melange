# Public-source research notes

Research date: 2026-10-05. Scope: neutral Cook PVI provenance and interpretation only. No production changes, district/member joins, priority ranks, donation weights or receptiveness estimates.

## Source status

| Source | Access / evidence | Use |
|---|---|---|
| [Requested 2026 district list](https://www.cookpolitical.com/cook-pvi/2026-partisan-voting-index/district-map-and-list) | Direct web and PowerShell fetches returned HTTP 403; the ordinary browser succeeded without login or a challenge and exposed the public iframe below. | Article title/date and publisher association. |
| [Public table embed](https://datawrapper.dwcdn.net/fejB0/1/) | Ordinary HTTP returned 200. Its public embedded configuration declares `dataset.csv`. | Archived raw HTML and provenance. |
| [Declared table data asset](https://datawrapper.dwcdn.net/fejB0/1/dataset.csv) | Ordinary HTTP returned the complete 435-row table. Despite its filename, it is tab-delimited. | Raw archive and normalized reference extract. |
| [Cook PVI overview and methodology](https://www.cookpolitical.com/cook-pvi) | Official source text exposed by search index and independently read in the ordinary browser; direct web fetch returned HTTP 403. | Methodology below. |
| [Cook staff analysis index](https://www.cookpolitical.com/about/staff/cook-political-report/analysis?cf_cache_bust=p5so6ZLOgldCBx%2F%2BIJlpi5jAZxHyFlIhugnKxaiC79zODpk9chgSqPsJexCoLNGG7Z%2Ftx%2FPyFCGSjjO7nA4AEA%3D%3D.1715611796238&page=2) | Official search result lists the district map/list as free, dated July 29, 2026. | Publication date, not proof of current table revision. |
| [Cook API documentation](https://www.cookpolitical.com/api/documentation) | Direct web tool read succeeded. | Official acquisition option; no API call or credential access performed. |
| [NCSL mid-decade redistricting tracker](https://www.ncsl.org/redistricting-and-census/changing-the-maps-tracking-mid-decade-redistricting?maptype=tile) | Direct web tool read succeeded. Page displays updated September 11, 2026. | Boundary-vintage caveat below. |

## Supported methodology summary

Cook PVI describes presidential partisanship relative to the country. Cook distinguishes this historical measure from its forward-looking race ratings. The current overview uses 2020 and 2024 presidential results, weighting the latter 75% and the former 25%; its Democratic two-party national reference is approximately 50.005%. D+2 denotes a two-percentage-point Democratic lean relative to the national share, rather than a predicted winning margin. Values within half a point receive EVEN. The overview says the 2026 release reflects changes in ten redistricting states. These are publisher methodology statements, not an independently reproduced calculation. The score does not by itself estimate donation effects or later legislative behavior.

Source: [Cook PVI overview](https://www.cookpolitical.com/cook-pvi).

## Available official acquisition route

The documented House JSON endpoint includes `Title`, `State`, `District`, `Incumbent`, `Cook_PVI`, `Rating`, `Cycle` and `Rating_date`. It returns paginated data (the documentation describes 50-item responses) and requires authenticated access. Cook asks for calls no more than once daily. A licensed pull would need to establish whether rating dates also identify PVI revisions; the documentation does not state that equivalence. Preserve PVI and rating vintages separately. The subscriber-only At-A-Glance PDF was excluded as an alternative download.

Source: [Cook API documentation](https://www.cookpolitical.com/api/documentation).

## Boundary-vintage caveat

NCSL lists Alabama, California, Florida, Louisiana, Missouri, North Carolina, Ohio, Tennessee, Texas and Utah among states that changed congressional maps after summer 2025. Its Missouri entry reports the 2025 maps on hold and 2022 maps restored for the general election. Thus a July publication date alone cannot establish current geography for Missouri. The actual Cook table's revision and district boundaries must be checked before any descriptive join. This note does not validate current boundaries district by district.

Source: [NCSL tracker, Missouri entry](https://www.ncsl.org/redistricting-and-census/changing-the-maps-tracking-mid-decade-redistricting?maptype=tile), read 2026-10-05. The retrieved table embed separately reports `lastModifiedAt=2026-07-22T15:17:03.000Z`, `publicVersion=1`, and `publishedAt=null`. The HTML's `lastModifiedAt` is preserved as source metadata; it is not a legal-current geography certificate.

## Data status and predeclared checks

Full official 2026 published table: acquired through the public page's declared embed asset. Preliminary structural extraction: 435 records, 50 states, no repeated canonical district IDs, full publisher rank sequence. Independent validation is a separate receipt. Boundary currency and incumbent currency: **UNVERIFIED-HERE**. No row was inferred from another vintage, imputed or filled from secondary sources.

The plan was locked before parsing (`source_parse_plan.md`); its acquisition addendum documents the later discovery of the declared TSV asset and display-sort syntax. The normalization retains all original six fields, splits validated `@@integer` presentation suffixes into separate fields, assigns separate canonical at-large IDs, and parses rounded labels with D negative, R positive and EVEN zero. EVEN is not an assertion that unrounded PVI equals exactly zero. Alphabetical output is in `cook_pvi_2026_districts.csv` and `.json`; `source_manifest.json` records hashes. No source rank was repurposed as a donation priority.

Historical retrieval limitation, resolved: initial HTTP 403 failures prevented discovery of the table asset. An ordinary-browser inspection subsequently exposed that asset; no authentication, challenge bypass or private endpoint was used.

No access-control challenge or subscription boundary was bypassed.
