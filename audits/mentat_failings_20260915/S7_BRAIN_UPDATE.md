# S7 brain update draft (for Paul to apply and commit to the melange-systems-brain)

## STATE.md - add under "Current position", newest first

- MENTAT FAILINGS S7 (2026-09-17, worktree pac-evidence-filters-724237; code in C:\Users\pgoff\Mentat
  on codex/mentat-crypto): PAC evidence committee categories, type filter and corporate rows BUILT,
  COMMITTED as 882f1f93f at 12:59 ET (patch audits/mentat_failings_20260915/patches/S7_pac_evidence_categories.patch,
  185,507 B, 15 diffs, cut as bytes, `git apply --cached --check` exit 0 on f0181e523). Paul's brief:
  "Fairshake missing within Crypto ... filter ... candidate committees, trade associations, carey's,
  company pac's". DIAGNOSIS (measured on 8806/8802, data root C:\Users\pgoff\AppData\Local\Mentat\console):
  Fairshake was never excluded; the Crypto import listed it with 28 rows of which 22 were
  `Record Type = CORPORATE` (Coinbase treasury giving) and `TYPES` in app/evidence_csv.py mapped
  `contribution` but never `corporate`, so every corporate row in every workbook read as unsupported
  (Crypto 333/333, Credit Union 202/202) and Fairshake showed $1.0M instead of $177,980,393.39; the PAC
  control was one 523-entry select in ID order with no search, while the workbook's Recipient Category
  column and graph_data.py CATEGORIES already carried the taxonomy. RULINGS (Paul): CORPORATE folds
  into Receipts; Include in Analysis = No rows visible, out of totals, status `excluded` with the
  workbook's reason; FEC committee master fallback (mentat/inputs/fec_committee_master/cm22|24|26,
  gitignored local inputs) in report.R's order plus ORG_TP T/C-W/L-M-V for bare files; file beats
  master; one type select plus a search box. Fable refinement: a file "Unclassified" is unclassified,
  so the master fills it (Chamber of Digital Commerce PAC -> Trade Association; Senate Conservatives
  Fund, Equality PAC -> Carey); with a file category column, ORG_TP C/W -> Other PAC, never Company PAC.
  Built by the Opus architect on Fable's S7_DESIGN.md (one dispatch + one review fix pass): row and
  committee categories (modal rule), categories[] rollup, catalog_version 2 with background re-read of
  stale imports on the first listing (side-by-side sqlite, row-count guard, read-only consoles report
  stale only), contract evidence-csv-import.json v3 (4 negative controls), UI type select + search +
  name-sorted options with category and row counts, snapshot committees labelled at read time,
  upload-before-token 403 race fixed. Measured on the real Crypto workbook: 6,343 rows, 523
  committees, 6,273 supported / 70 excluded / 0 unsupported; Fairshake 22/6/0, Receipts
  $177,980,393.39; Super PAC 21, Trade Association 2, JFC 65, Company PAC 2, Leadership PAC 50,
  Carey 23, Other PAC 4, Candidate 294, Party Committee 54, Unclassified 8. Tests 112 OK (system
  Python), 91 OK (launcher Python), node 163/0, browser 35/35; independent sweep green; Fable review on
  a scratch console reproduced every figure. Foreign: tests/test_console_browser.cjs not run (dirty
  from another lane, known red at :188); Credit Union and Community Banks imports re-read only on
  Paul's first listing (row-count guard protects them). NEXT: Paul commits (receipts and contract
  need `git add -f`), re-runs the launcher for 8806/8802.

## DECISIONS.md - add

## D-040 - PAC evidence committee categories: the file's classification first, the FEC master fills blanks
Date: 2026-09-17
Status: ACTIVE
Decision: In the Mentat console's PAC evidence tab a committee's category is the Graph vocabulary
(Super PAC, Trade Association, JFC, Company PAC, Leadership PAC, Carey, Other PAC, Candidate,
Party Committee, Unclassified). The imported file's Recipient Category column decides it (modal
non-blank value over the committee's rows; "Unclassified" counts as blank); a committee the file
leaves blank or Unclassified is classified from the FEC committee master (cm26, then cm24, then cm22)
in the report pipeline's fallback order J -> JFC, D -> Leadership PAC, X/Y/Z -> Party Committee,
O/U -> Super PAC, V/W -> Carey, H/S/P or A/P -> Candidate, then ORG_TP T -> Trade Association,
C/W -> Company PAC only when the file has no category column (Other PAC when it has one),
L/M/V -> Other PAC; every category carries its source. Workbook CORPORATE rows are Receipts. Rows the
workbook marks Include in Analysis = No are visible, out of every total, status `excluded`, with the
workbook's reason. Catalogs carry catalog_version and a console re-reads stale imports itself.
Context: Paul's rulings 1-5 of 2026-09-17 on S7_DESIGN.md ("Go"); the Unclassified and Other PAC
refinements are Fable's under ruling 4, stated to Paul with the build.
Rationale: the workbook is the industry pipeline's own classification and knows which PAC is the
company's; the master is a registration record that resolves what the pipeline left blank (7 of 15
Unclassified Crypto recipients, including the crypto trade association PAC). One vocabulary keeps the
Graph and evidence filters agreeing.
Reversal condition: Paul rules that a file "Unclassified" must stand, or the master's ORG_TP rules
mislabel a committee in a real workbook.

## DEADENDS.md - add

## DE-026 - Replaying a stored reader option that the reader itself overwrites
Date: 2026-09-17
Approach: The first S7 re-read implementation re-ran an import from its stored source with the
options recorded in import.json, including `sheet`, to rebuild its catalog under new rules.
Failure mode: read_source overwrites `record['sheet']` with the worksheet the reader settled on, so
replaying it narrowed the 4-sheet Crypto workbook to one sheet: 6,343 rows became 1,063, Fairshake
vanished and select answered 400. Measured on the real workbook before it shipped.
Root cause: the record holds what the reader produced, not what it was asked; a recorded output
replayed as an input is a different request.
Would reconsider if: never. Derive the original request from something the reader does not rewrite
(the import id folds a chosen worksheet in, so an id equal to the bare digest means "no sheet
chosen") and guard the swap with an invariant the new run must reproduce (same bytes, same options,
same row count), refusing rather than replacing.
