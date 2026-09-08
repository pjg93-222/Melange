# Mentat collection app

The console uses the palette and typography pairing from
[America's Credit Unions](https://www.americascreditunions.org/), inspected on
September 8, 2026: plum `#342649`, ivory `#F7EDE4`, gold `#ECA91C`, purple
`#57447B`, and teal `#327A7A` / `#9ED4D5`. The theme is in `acu-theme.css`;
`theme.js` shares its colors and font stacks with charts and image exports.
Headings prefer locally installed **Freight Text Pro**, with **Georgia** as the
offline fallback. Controls, tables and chart labels prefer **Articulat CF**, with
**Arial** as the offline fallback. No Adobe Fonts kit, remote font download, logo,
or organization account flow is embedded in the application.

Launch the local console from PowerShell:

```powershell
& .\mentat\app\Start-MentatApp.ps1
```

Open http://127.0.0.1:8802. The **Loading** tab accepts a sector, companies,
and alternative names directly, or CSV, TSV, and XLSX uploads. Enter each alias
on its own line; a comma stays part of a name. Add/remove companies, click
**Review roster**, choose cycles, and click **Start collection**. Reviewing
or uploading alone makes no FEC requests. Aliases group under a canonical
company; they are not subsidiary or ownership relationships.

Manual drafts persist in this browser's local storage, without credentials.
Editing a draft invalidates its previous review and disables collection until
it is reviewed again. Validated rosters persist on the server through the same
readiness checks and isolated runner as uploaded workbooks. In **Collection**,
select a ready roster and use **Continue collection setup** to resume it.
The **PAC evidence** tab is independent of the selected collection run.

The table format uses `canonical_name,alias,industry,exclusion`; only
`canonical_name` is required. Repeat it for every alias. The included template
contains illustrative names. Existing Mentat roster workbooks are also accepted.
Ambiguous aliases fail the existing roster readiness check and cannot start.
`sector` is accepted as an alternative to `industry`; if both are supplied,
their values must agree. Manual entry rejects duplicate canonical companies.

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
coverage. Observed evidence does not assert donor-specific traced dollars. Committee
IDs explicitly set its network boundary; outgoing destinations beyond that
boundary are recorded in `unexpanded_committees`.

The evidence collector also produces `cash-estimates.json` using
`tools/pac_cash_model.py`. This is a separate conditional company cash estimate;
it does not replace the earlier industry allocation in Excel. The sidecar binds
to both the source snapshot and observed evidence by SHA-256. Rebuild it offline:

```powershell
python mentat/tools/pac_cash_model.py --evidence-dir mentat/.cache/pac-evidence/fairshake-20260908
```

The dated proportional pool carries funding shares through uniquely paired
transfers, charges operating costs, keeps unspent balances, and uses payment
dates for independent expenditures. Same-day arrivals precede outgoing payments;
this ordering is an explicit modeling assumption. It is not a probability of
influence or a causal estimate. All-source cash conservation and reported
closing balances must pass before numbers are returned. The automatic Form 3X
adapter withholds estimates for missing cash dates, financial gaps, unpaired
transfers, negative adjustments, donor-unresolved opening balances, assets that
need liquidation/offset links, or refunds that need original-donor links.
The normalized core supports identified refunds and donor-labeled opening cash;
the automatic adapter does not guess these labels. Existing Fairshake 2024/2026
snapshots are withheld with specific reasons. Unknown is displayed as unavailable,
not zero. Method, current limitations and validation are documented in
`audits/mentat_20260908/PAC_CASH_APPROXIMATION.md`.

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

Loading is the default tab at desktop and narrow widths; each tab has a stable
URL fragment (`#loading`, `#collection`, `#evidence`). A separate quality notice
in Collection reads the saved coverage receipt, inspects
workbook headers for support/opposition columns, and compares the report hash
with the run's receipt. Header presence alone does not validate formulas or
downstream completeness. Source file modification dates are shown separately
from data-through dates.

**Report freshness** in Collection reads each workbook's `Source Freshness`
sheet, its companion `.audit/source_freshness.csv` when both workbook and CSV
hashes match the audit manifest, and hash-bound `source_freshness.csv` references
in `Source Receipts`. Referenced files must stay inside the report directory.
Missing, malformed or changed receipts remain visible as unknown. The panel
separates download/retrieval, last check, local source file modification, server
last-modified, and report file modification. A check is not a download. The run's
pinned source receipts can supply download and local file dates only for sources
whose family, cycle and SHA-256 match the report and the actual source file.
A newly activated source never upgrades an old report's freshness.

A receipt establishes a displayed verified data-through date only with a valid
ISO date in `verified_data_through`, or `data_through` together with an explicit
`data_through_verified: true`. Display headers such as `Verified Data Through`
are also accepted. This displays the receipt's assertion; it does not independently
certify completeness. Check timestamps, file dates, election cycles and latest
transaction dates cannot substitute for it. The panel counts verified source dates
and keeps overall report freshness unknown because source receipts do not prove
complete company/employer search coverage.

**Graph** is a peer section of the console; Loading remains the default. Choose
an industry, company (or all companies), employee level and election cycle.
The employee labels are **Chief / Middle-Management / Employees**. They map to
the existing report tiers without changing any classification; Employees retains
the existing fallback for unrecognized titles. Corporate giving is a separate
giving scope, not an employee level. Choosing a level selects personal giving.

Graph separates **Scope**, **Analysis**, and **Details & methodology**. The compact
scope applies across **Overview / Recipients / Candidates / Companies**. Overview
shows net giving, direct candidate contributions, giving to recipient organizations,
a recipient-type chart, and a five-entry candidate preview. Recipient organizations
exclude candidate-category receipts; unresolved candidate links stay visible in the
candidate note, so the two summary amounts need not exhaust net giving.

Recipients contains the complete type breakdown and a five-entry organization
preview. JFC stays separate, as do Super PAC, Trade Association, Company PAC,
Leadership PAC, Carey/hybrid, Other PAC, Candidate, Party Committee and Unclassified
receipts. Companies shows company comparisons and the selected scope's personal
giving by Chief, Middle-Management and Employees, retaining unknown levels. A
single-company selection still shows its amounts and level breakdown without an
empty comparison placeholder. Click a type, organization, company or level to
filter; click a candidate for its included receipt groups. These can be aggregates,
not individual transactions. **View all** and **Full table** expose complete values.

**Sources & freshness** opens a keyboard-accessible drawer containing the selected
reports' source receipts, retrieval timestamps, file modification timestamps,
verified data-through dates, unknown states and SHA-256 fingerprints. Retrieval
never establishes currency. The drawer also selects the saved run. Graph remains
`#graph`; old `#charts` links redirect to it. Reset restores the latest cycle,
all companies/levels/giving, and the Overview direct-contribution view.

The contextual **Export chart** control exports a selected breakdown as PNG or SVG,
or every value as CSV. Images contain the displayed preview (five entries except
for the complete recipient-type breakdown), with scope, interpretation notes and
report fingerprints attached. Empty or unavailable views cannot be exported.

Guided graphs read the per-cycle receipt tables, using Recipient facts only in
workbooks that also contain duplicate Master and Employee summaries. Recipient
amounts must reconcile to Master totals by company, level, cycle and category.
Raw layouts use only explicitly included rows. Overlapping report cycles are
rejected. Direct candidate rankings require a unique candidate ID linked to a
principal or authorized committee; JFC, leadership and unauthorized links cannot
be promoted to direct contributions. Unresolved candidate-category amounts remain
visible outside the rankings.

The candidate-view selector separates **Direct contributions**, **Downstream PAC
activity**, and **Conditional industry estimates**. Downstream activity shows
the full reported activity of committees funded within the current selection,
counting each committee/cycle once regardless of how many selected companies
funded it. Support, opposition, and contributions/other activity remain separate.
It is not company-attributed money; company views may overlap. Industry estimates
require all companies, all levels and all giving, and the full allocation CSV
bound to the workbook by its audit manifest. Missing or changed receipts withhold
estimates. Partial downstream worksheet previews cannot produce rankings. These
views make no new source requests or model runs and do not rewrite reports.

**Create chart** opens an advanced builder that scans completed report worksheets locally and suggests bar,
box, pie, line, scatter and histogram charts from their columns. Select a run,
report and worksheet, then choose columns and an aggregation. Change the detected
header row and use **Rescan columns** for another table within a sheet. Filters
combine with AND; first/last worksheet row controls isolate subsections. Use
**Create chart** after changing options. PNG, SVG and chart-data CSV downloads include
the worksheet, filters, aggregation and report SHA-256 in their provenance.

Missing/non-numeric observations are excluded and counted, never converted to
zero; Count rows counts selected rows regardless of missing measures. Pie charts
reject negative values and zero totals. Box plots use linearly interpolated
quartiles and observed whiskers within 1.5 times the interquartile range. Formula
cells use their last saved cached results; this explorer does not recalculate
Excel formulas. Totals and overlapping summary rows can double count, so choose
the appropriate worksheet subsection. The current local limits are 50,000 rows,
200 columns, 60 groups, and 5,000 scatter points. Oversized requests require a
smaller worksheet or filters rather than silently creating a partial chart.
Graphs do not call Higgsfield, FEC, or any external service; all scripts and
rendering are served locally, with no CDN dependencies.

Additional offline regression checks (browser checks require local Playwright
and Chrome; `MENTAT_BROWSER_CHANNEL` can select another installed channel):

```powershell
python mentat/tests/test_report_insights.py
python mentat/tests/test_graph_data.py
node --test mentat/tests/test_chart_math.cjs
node mentat/tests/test_console_browser.cjs
```

The browser suite starts a temporary loopback fixture and checks Graph's default
direct view, company/level/JFC filters, downstream directions, estimate withholding,
dataset switching, all six chart types, PNG/SVG/CSV exports, escaped labels, narrow layouts,
keyboard navigation and dialog dismissal/focus restoration, and the
absence of external requests. `MENTAT_NODE_MODULES` and `MENTAT_PYTHON` override
the local test dependencies. Neither test suite reads credentials or collects data.

Rebuilt workbooks include committee cash-transfer paths through three transfers,
coverage, source receipts, and a separate conditional pro-rata estimate. These
estimates are not traced company dollars or lower bounds. Opposition stays
against its named target. ActBlue and WinRed use their registered hybrid (Carey)
category; ordinary registered PACs have a separate Other PAC category. Historical
workbooks keep their original evidence and may predate these corrections.
The September 8 audit and repair evidence are in `audits/mentat_20260908/`.
