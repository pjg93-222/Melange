# Mentat collection app

Launch the local console from PowerShell:

```powershell
& .\mentat\app\Start-MentatApp.ps1
```

Open http://127.0.0.1:8802. Upload CSV, TSV, or XLSX, review the parsed names,
choose cycles, and click **Start collection**. Uploads alone make no FEC requests.
The table format uses `canonical_name,alias,industry,exclusion`; only
`canonical_name` is required. Repeat it for every alias. The included template
contains illustrative names. Existing Mentat roster workbooks are also accepted.
Ambiguous aliases fail the existing roster readiness check and cannot start.

The console invokes the existing resilient R/PowerShell runner. It snapshots
`R/`, `tools/`, `inputs/`, and `mentat.R` into a private runtime for each upload,
with the uploaded roster installed as that runtime's `Company Name.xlsx`.
This keeps collector roster resolution and readiness validation aligned.
Existing source inputs and collection databases are not replaced.
The app sets `MENTAT_CUSTOM_ROSTER=1` for its workers, allowing the R importer
to read a roster containing only the uploaded industries. Without this flag,
the standard importer's five required industry sheets remain required.

Run state, raw exports, runtime snapshots, and reports live under
`%LOCALAPPDATA%/Mentat/console`. The interface also discovers the latest 15 runs
in `mentat/.cache/resilient-industry-runs`. It refreshes every three seconds;
the source runner updates on its own checkpoint schedule. A stale update is
explicitly labeled and does not prove the worker is still running.
Verified report rebuilds are listed separately from collection runs through
`mentat/.cache/report-repairs`, preserving the original collection receipts.

Select a worker to see its latest 50 API checkpoints and 25 stored records.
These are provisional and may contain overlapping searches or filing versions;
they are not final giving totals. Final workbook links appear only for industries
whose runner status is `succeeded`. Collection, retries, merge, coverage gates,
and reporting retain the existing runner's behavior. Recovery attempts are shown
separately. The interface does not expose manual cancellation or resumption.

FEC keys entered in the interface are saved with user-scoped Windows DPAPI
encryption in `%LOCALAPPDATA%/Mentat/credentials/fec-keys.dpapi`, outside Git.
Workers receive enabled keys in their environment. The app never puts keys on
a command line or returns them to the browser. Rejected keys remain encrypted
but disabled; transient failures do not disable keys.
Alternatively set `FEC_API_KEY` / `FEC_API_KEYS` before launch or pass `-KeysFile`.
R 4.6 and the existing Mentat dependencies remain required. `-PythonPath`,
`-RScriptPath`, `-Port`, and `-NoBrowser` customize the launcher. Python needs
`openpyxl`, already present in the bundled runtime.

The server binds only to loopback and checks local host, origin, and a session
token for changes. This is a local single-user application, not a remote hosted
service. Closing the browser does not stop collection. Keep the app server
running for its process exit receipt; underlying runner receipts remain available
if the app restarts. A failed startup's diagnostic is in the upload's
`launcher.log`. No collection starts until the user presses the start button.

The PAC evidence panel discovers `mentat/.cache/pac-evidence/*/evidence.json`.
It keeps company receipts, exchange conversions, committee transfers, and
support/opposition activity separate. Candidate names remain as filed beside
their registered names; differences go to review rather than automatic merges.
Changing its cycle or committee only filters a saved snapshot. It does not
silently start another collection. The dates shown distinguish the evidence
snapshot from the financial summary's reporting period.

Create an evidence snapshot with the bundled Python runtime:

```powershell
python mentat/tools/pac_evidence.py --company Coinbase --aliases 'COINBASE COMMERCE (EXCHANGE)' --committees C00835959,C00836221,C00848440 --cycles 2024,2026 --output mentat/.cache/pac-evidence/fairshake-20260908
```

Use a new output directory for a fresh collection. Existing directories resume
from hash-verified API responses. The reusable collector verifies exact counts
and pagination, excludes 24/48-hour notices from regular-report IE totals,
checks those totals against financial summaries, and preserves unresolved
coverage. It does not calculate donor-specific dollar allocations. Committee
IDs explicitly set its network boundary; outgoing destinations beyond that
boundary are recorded in `unexpanded_committees`.

**Clear reviewed notices** acknowledges only the visible warning IDs. The
review receipt is stored outside Git in the console data directory. It binds
the warning text to the run and workbook SHA-256. Changed workbooks or warnings
require another review; hard failures cannot be dismissed. Workbook Data
Quality sheets remain intact.

Offline checks:

```powershell
python mentat/tests/test_collection_console.py
```

The tests use temporary inputs/databases, mock collection launch, and exercise
the real runner's plan-only mode and R's offline ingest when R is installed.
They do not call FEC or execute collection.

The monitor appears first at desktop and narrow widths; the upload form expands
when needed. A separate quality notice reads the saved coverage receipt, inspects
workbook headers for support/opposition columns, and compares the report hash
with the run's receipt. Header presence alone does not validate formulas or
downstream completeness. Source file modification dates are shown separately
from data-through dates, which the console cannot currently verify.

Rebuilt workbooks include committee cash-transfer paths through three transfers,
coverage, source receipts, and a separate conditional pro-rata estimate. These
estimates are not traced company dollars or lower bounds. Opposition stays
against its named target. ActBlue and WinRed use their registered hybrid (Carey)
category; ordinary registered PACs have a separate Other PAC category. Historical
workbooks keep their original evidence and may predate these corrections.
The September 8 audit and repair evidence are in `audits/mentat_20260908/`.
