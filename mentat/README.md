# Mentat R pipeline

Mentat has one entry point: `mentat.R`. It ingests the registers, collects FEC Schedule A receipts, reconciles the Crypto acceptance fixture, and writes the spending and QA reports. The modules in `R/` are implementation details and are sourced by the entry point.

## Requirements

- Windows with R 4.6.0.
- Installed packages: `chromote`, `data.table`, `DBI`, `RSQLite`, `readxl`, `writexl`, `zip`, `jsonlite`, and `curl`. If `httr2` is installed, the API engine may use it.
- A free registered openFEC API key from https://api.data.gov/signup for the default API engine.
- No report workbook open in Excel while Mentat replaces it.

Set the R library before starting R or RStudio:

```powershell
$env:R_LIBS_USER = "C:/Users/pgoff/AppData/Local/R/win-library/4.6"
```

Set the API key in the environment. Mentat never prints or persists its value:

```powershell
$env:FEC_API_KEY = "your-registered-key"
```

`MENTAT_DATA_ROOT` holds all mutable state: `mentat.db`, checkpoints, the roster summary, optional `bulk/` supersets, and `reports/`. It defaults to `%LOCALAPPDATA%/Mentat`; set it to another local, nonsynchronized directory if desired. `MENTAT_BULK_DIR` can point the optional bulk inputs elsewhere.

## Standard from-scratch run

Use the resilient industry runner for production collection. It discovers
industries from `inputs/Company Name.xlsx`, gives each active lane its own API
key and SQLite shard, retries a failed R lane in a fresh process, then splits
unresolved work into fresh company-cycle processes before the gated merge.

```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  tools/parallel/Start-MentatResilientIndustryReports.ps1 `
  -Industries Fintech -NoCache
```

Omit `-Industries` to run every roster-discovered industry. Every run writes
atomic fanout, coverage, warehouse, generator, and phase-timing receipts below
`.cache/resilient-industry-runs/`, including one summary timing line per
industry.

`tools/parallel/Start-MentatIndustryReports.ps1` retains its historical CLI,
but now delegates from-scratch work to the resilient runner. Its long-lived
serial Chrome collection is reachable only with the explicit
`-LegacySerialCollection` switch. Report-only `-SkipCollection` behavior is
unchanged.

Directly sourcing `mentat.R` is intended for focused development and explicit
single-process diagnostics:

```powershell
& "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" mentat.R --skip-scrape
```

The R entry point defaults to the FEC JSON API, all three cycles, up to eight
adaptive concurrent work units, and the contributor-name identity pass
disabled. Use `--phase2-names` to opt in to that request-heavy pass.

Supported flags are documented at the top of `mentat.R` and by `Rscript mentat.R --help`:

```text
--cycles=2022,2024,2026
--data-root=PATH
--engine=api|chrome
--concurrency=N
--skip-scrape
--phase2-names
--skip-phase2-names
--resume-after=YYYY-MM-DDTHH:MM:SS...
--retag-only
--help
```

The equivalent environment controls are `MENTAT_ENGINE` (default `api`), `MENTAT_CONCURRENCY` (default `8`), `MENTAT_DATA_ROOT`, `MENTAT_BULK_DIR`, `MENTAT_RESCUE_CAP` (default `50` requests), and optional `MENTAT_SPENDING_TEMPLATE`. The Chrome engine remains available as a fallback with `MENTAT_ENGINE=chrome` or `--engine=chrome`.

`--skip-scrape` performs ingest, fixture reconciliation, and reporting without opening a browser or making an API request. `--retag-only` recomputes stored leg and company tags and rewrites reports without ingest or collection.

## Add an industry

Industry onboarding is data-driven:

1. Add a worksheet to `inputs/Company Name.xlsx`. The worksheet name is the
   industry name. Put one company block per blank-line-delimited section; the
   first parsed variant is the canonical company. Prefix exclusion patterns
   with `NOT `.
2. Run the single offline readiness command:

   ```powershell
   & "C:/Users/pgoff/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" `
     tools/validate_industry_coverage.py `
     --roster "inputs/Company Name.xlsx" `
     --output ".cache/industry-roster-readiness.json"
   ```

   The receipt reports parsed industries, companies, variants, exclusion
   coverage, duplicate/ambiguous variants, and a fail-closed `ready` result.
3. Run the standard resilient command with the new worksheet name:

   ```powershell
   & powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
     tools/parallel/Start-MentatResilientIndustryReports.ps1 `
     -Industries "New Industry" -NoCache
   ```

No script-maintained industry list or per-industry runner is required.

## Collection and correctness rules

The API engine uses `/v1/schedules/schedule_a/`, 100 rows per request, descending receipt-date sort, and openFEC keyset cursors. It reconciles collected rows to `pagination.count`, rejects partial or cyclic cursors, and adapts concurrency downward after a 429 and upward after successful batches. Retryable responses honor a per-request `Retry-After` capped at 120 seconds. Raw pages, cursors, and a persistent 1,000-request hourly budget are checkpointed in `mentat.db`; a local budget limit or sustained 429 pauses cleanly for a later resume. Logs include requests used and remaining. The API key is never checkpointed.

The optional `bulk/indiv22_crypto_superset.psv`, `indiv24_crypto_superset.psv`, and `indiv26_crypto_superset.psv` files build an observed-employer register through the same matcher used for API rows. If a broad employer query returns 504 twice, the API engine replaces it with narrower observed spellings and records the decomposition in `run_log`. Bulk candidate `sub_id` values still missing afterward receive exact-ID name rescue, capped by `MENTAT_RESCUE_CAP`; never-fetched overflow is written to `reports/bulk_rescue_overflow.csv`. `reports/bulk_audit.csv` and `reports/bulk_audit_unmatched.csv` provide company-cycle completeness counts and remaining IDs.

Employer attribution uses exact aliases, prefix-anchored corporate qualifiers, and narrowly qualified squashed prefixes for forms such as `BINANCEUS`. Nonqualifying anchored extensions go to `reports/review_queue_company_match.csv`. Decisions in `inputs/company_match_overrides.csv` persist across runs. Roster exclusions inspect contributor name, employer, and occupation on every pass. The data-driven nickname seed is `inputs/name_diminutives.csv`; variants shared by more than one canonical name are not used alone to establish identity.

Organization entities and company-name contributors are emitted to `Sheet4` as `CORPORATE` / `Corporate`; they never enter Chief, Middle Management, or Employee tiers. Every current FEC row counts to the recipient shown on that row, including memo-code-X, conduit, passthrough, refund, and redesignation rows. Leg fields remain analytical flags; only earlier filing versions superseded by an amendment are omitted.

## Spending workbook

`reports/spending_report.xlsx` contains:

- `Stats (XXX Company)`, preserving the supplied formula layout and its repeated-Super-PAC/Carey header quirk, with Corporate Giving appended;
- `Employees (XXX Company)` for individual contributors only;
- one presentation sheet for every organization/cycle with rows;
- one `Crypto Industry <cycle>` presentation rollup for every cycle with rows;
- `Sheet4`, the single A:G fact table used by every Stats formula.

Presentation sheet columns are `Name | Recipient | Date | Amount | CSZ | Employer | Occupation`. Excel names are sanitized to 31 characters. Case-insensitive collisions use deterministic `~2`, `~3`, … suffixes after truncating the base to make room.

Recipient registers retain 527 and 501c classifications, but their Sheet4 records use `EXCLUDED_527_501C` and do not enter reported totals. Unclassified recipients are exported to `reports/unclassified_recipients.csv`; the report fails if its counted category columns do not reconcile to Total Giving.

All CSV report writes are UTF-8 with a BOM for Excel on Windows and are installed atomically. Workbook output is rebuilt with stable entry order, normalized timestamps, and atomic replacement.

## Offline tests

Each test uses synthetic fixtures or temporary data roots and makes no network call:

```powershell
Get-ChildItem tests/test_*.R | ForEach-Object {
  & "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" $_.FullName
  if ($LASTEXITCODE -ne 0) { throw "Test failed: $($_.Name)" }
}
```

PowerShell-specific runtime guards are separate from the R fixture suite:

```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  tests/Test-MentatNodeHeapPlan.ps1
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  tests/Test-MentatWorkbookBuilderGuards.ps1
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  tests/Test-MentatLastGoodGuard.ps1
```
