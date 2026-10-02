# Giving Forecast anchors

Mentat's own levels that the Giving Forecast applies its estimated relationships to (owner rulings of 2026-09-30: the forecast applies to
MENTAT data; OpenSecrets only estimated the relationships). One read-only builder writes one snapshot; the console reads it.

```
& "$env:LOCALAPPDATA\Mentat\venv\Scripts\python.exe" mentat\forecast\anchors\build_giving_anchors.py            # build all four datasets
  ... build_giving_anchors.py --industry credit_unions                                                          # one registry id
  ... build_giving_anchors.py --check                                                                          # fresh (exit 0) or stale / missing (exit 2)
```

Output: `mentat\state\giving-anchors\giving-anchors-v1.json` and `giving-anchors-v1.receipt.json` (runtime state, brain D-048: never in git;
`MENTAT_GIVING_ANCHORS` overrides the path the console reads). The schema and a real example live in `mentat/forecast/contracts`.

## What it reads (everything read-only)

| Input | Where | Used for |
|---|---|---|
| Published workbook | report directory (`config/report-directory.json` or `MENTAT_REPORT_DIRECTORY`) | its sha256 is the freshness key |
| Contribution-analytics index | `state/contribution-analytics/*.sqlite`, the newest whose `provenance.workbook_sha256` equals the workbook's | general giving (`receipt_cents`, the workbook's Analysis Amount, less the non_giving receipts: see the first rule below), funding-source split, employees' D/R by cycle |
| Pinned source database | `.cache/...` (registry globs), the file whose sha256 equals the index's `database_sha256` | FEC `recipient_committee_type` (H / S) joined on sub_id; the collection date (`MAX(scraped_at)`); work-unit progress |
| FEC pas2 / cn / cm bulk files | `inputs/active_fec_sources.json` -> `fec_beneficiary/pas2YY`, `fec_beneficiary/cnYY`, `fec_committee_master/cmYY` | the roster companies' PACs' own giving to House / Senate candidates (D-049 `count_latest`) |
| Melange LDA | `%LOCALAPPDATA%\Melange\lda_rebuild\derived\sector_spend\sector_spend.csv` | `income_total` and `expenses_total`, never summed; bank TOTAL for banks |
| CPI | `sector_growth_study/data/00_controls.xlsx` | `cpi[2025] / mean(cpi[t-1], cpi[t])` per cycle (2026 has none: face value) |

Every SQLite file is opened `mode=ro&immutable=1` with `PRAGMA query_only=ON`. No receipt-counting or collection code is imported or run.
The two output files are the only thing written, through a temporary file and an atomic replace, and only after the snapshot validates
against the shared schema and invariants; an invalid build leaves the previous snapshot in place. Every run emits Glass Box events
(`ANCHORS_GLASSBOX_DIR` overrides the folder; lane `claude`, source `giving-forecast-anchors`).

## Rules it implements

* **Non-giving receipts are left out of the forecast** (owner ruling 2026-10-01, forecast-integrity decision D4 option b). Receipts that Mentat's accounting
  engine buckets as `non_giving` (the index's `funding_source` is the engine's bucket; the FEC records them as interest, refunds, insurance claims, loans)
  are in the workbook's Analysis Amount but are not giving. In the forecast only, `mentat_sources.FORECAST_EXCLUDED_FUNDING_SOURCES` (`{"non_giving"}`) leaves
  them out of (1) each cycle's `general_giving.cycles`, (2) the monthly `observed` cuts and the observed-to-date amounts, and (3) the House / Senate employee
  `candidate_receipts` (cycles, observed cuts, thin-base flags). The workbook, the index and every money-collection view are untouched.
  `general_giving.by_funding_source` stays the full split of the Analysis Amount; `general_giving.excluded_non_giving` and `candidate_receipts.excluded_non_giving`
  report what was left out, per cycle (levels + excluded = the published Analysis Amount), and the industry flag prints the amounts. The index's own
  receipt-total check still compares the full Analysis Amount with the index manifest. A partial build (`--industry`) carries over only industries whose
  published general-giving and candidate blocks both name exactly `FORECAST_EXCLUDED_FUNDING_SOURCES` as the sources they left out (anchors from before the
  rule name none, and an empty list names none either); the others are listed as `unavailable` until rebuilt.
* **Coverage end** (by rule, because none of the pinned databases has a verified coverage-through date): the last calendar quarter-end whose
  report due date (the 15th of the following month) was on or before the collection date. Banks, P&C, Community Banks: 2026-06-30. Credit
  unions are cut back to 2026-05-31 ("June incomplete") for as long as the rule end is 2026-06-30. Observed amounts are cumulative month-end
  cuts of the open cycle up to the coverage end; rows dated later stay in the remainder window.
* **Thin base**: under $100,000 of D + R per chamber, per cycle, per basis (`thin_base`).
* **Roster PACs**: `registry.json`. Trade-association PACs are not counted. Credit unions have one PAC (SchoolsFirst), flagged `single_pac`.
* **Separate datasets**: `community_banks` is its own entry (`forecast_industry: null`), never merged into banks. Auto has no Mentat workbook
  and no entry. P&C has general giving and candidate receipts, no roster PACs and no Melange LDA sector (both `unavailable`, with the reason).
* **Refusal**: an industry whose published workbook has no matching index, or whose pinned source or FEC input cannot be verified, is listed in
  `unavailable` with the reason, never invented. The console refuses (`anchor_stale`) when `mentat.workbook_sha256` differs from the workbook
  published now.

## Running it on a schedule

The build takes about a minute on this box (Banking's 861 MB source database join is most of it; it ran locally, so the RunPod pod was not
needed). Run it nightly and after each Mentat publish, FEC refresh or Melange LDA refresh. A scheduled task is Paul's to create: this lane
changed no publish or refresh script. `--check` exits 2 when a workbook was republished since the last build.

## Tests

`python -m pytest -p no:cacheprovider mentat/tests/test_giving_anchors.py` builds against a synthetic Mentat (hand-computed expectations,
D-049 cases, the non_giving exclusion in every sum, coverage rule table, read-only and refusal guarantees, the shared negative controls).
`MENTAT_ANCHORS_REAL=1` also re-derives the credit-union numbers of ADDENDUM section F (less the non_giving receipts) from the real tree, `=all` the
banks and property & casualty too (about four minutes).
