# S7 - PAC evidence: committee categories, filter, corporate rows (design)

Session: Fable, 2026-09-17 (worktree pac-evidence-filters-724237; code in C:\Users\pgoff\Mentat,
branch codex/mentat-crypto, HEAD 3fdfeae8f at design time). Status: DESIGN, awaiting Paul's rulings.
Nothing in the tree is edited by this document.

Paul's brief: "In the PAC evidence I am seeing some PACs are missing, for example Fairshake within
Crypto, you may be excluding non-candidate PAC's, trade associations, etc, there should be a filter
option where we can narrow it down to candidate committees, trade associations, carey's, company
pac's, etc."

## 1. What is actually happening (reproduced on consoles 8806 and 8802, data root
C:\Users\pgoff\AppData\Local\Mentat\console, import store evidence-csv/)

1. Fairshake is NOT excluded from the list. The Crypto import `csv-88ea228457b8499d1ec27eeaba967f61`
   (Crypto Industry Spending Overview.xlsx, 6,343 rows, 523 committees) lists
   `FAIRSHAKE - C00835959` with 28 rows. Only 6 rows count: Receipts $1,011,179.52, all employee
   contributions (Armstrong $1,000,000, Pollak $5,000, ...). The other 22 rows are
   `Record Type = CORPORATE` (Source Table `corporate_giving`): Coinbase / Coinbase Commerce
   treasury contributions of $25,000,000, $24,999,995, $23,000,000, $15,500,000 (x3), $15,000,000,
   $8,092,475, $6,000,000, $5,175,000, $5,000,000 (x4), $4,400,000, $3,801,738.87 ... Every one is
   `unsupported` with "The CSV does not identify a supported receipt or activity type." because
   `TYPES` in `app/evidence_csv.py` maps `contribution` and never `corporate`.
   Dollars dropped for Fairshake alone: $161,474,208.87 (rows the workbook marks
   Include in Analysis = Yes and Memo Leg = 0; $176,974,213.87 including memo legs; $293,974,208.87
   raw). The tab shows $1.0M, so the PAC reads as missing.
2. It is every workbook, not Fairshake. Crypto: all 333 unsupported rows are CORPORATE
   (324 of them Include = Yes). Credit Union import: all 202 unsupported rows are CORPORATE.
   Crypto corporate rows (Include = Yes, non-memo) by recipient category: Super PAC
   $172,538,447.47 (40 rows), Carey $44,147,414.56 (23), JFC $8,415,129.44 (141),
   Candidate $255,207.48 (83), Company PAC $117,658.48 (25), Party $100,000 (1),
   Unclassified $69,425.03 (8), Leadership PAC -$672.07 (1).
3. There is no committee-type filter. The PAC control is one 523-entry `<select>` sorted by
   committee ID with no search. The workbook already classifies every recipient in its
   `Recipient Category` column (Paul's pipeline rule, `R/report.R` ~2690-2880: categories table,
   leadership table, company PAC, then FEC fallbacks J -> JFC, D -> Leadership PAC, X/Y/Z -> Party
   Committee, O/U -> Super PAC, V/W -> Carey, H/S/P or A/P -> Candidate) and the Graph tab already
   filters on that vocabulary (`app/graph_data.py:19` CATEGORIES). The evidence reader ignores the
   column entirely. Crypto by category (committees / rows): Super PAC 21 / 2,676; Candidate
   294 / 1,399; Company PAC 2 / 1,359; JFC 65 / 461; Leadership PAC 50 / 168; Party Committee
   53 / 102; Carey 20 / 53; Trade Association 1 / 1; Unclassified + blank ~30 / 124.
   Credit Union: Trade Association 4 committees / 620 rows (CULAC 594, BUILDPAC 21, US Chamber 4,
   MORPAC 1); Super PAC 11 / 19,839; Candidate 149 / 1,972.
4. Non-workbook imports (plain CSV, openFEC JSON, FEC bulk) carry no category. The repo holds the
   FEC committee master for three cycles: `mentat/inputs/fec_committee_master/cm22|cm24|cm26/cm.txt`
   (2.4-2.5 MB, ~20k rows each, no header row; CMTE_DSGN = column 9, CMTE_TP = column 10,
   ORG_TP = column 13, CONNECTED_ORG_NM = 14). Fairshake there is `U|O` (unauthorized, Super PAC).
5. Saved FEC snapshots source: its committee list is the typed committee IDs only (Coinbase
   snapshot: Fairshake, Defend American Jobs, Protect Progress). Not a list problem; label only.

## 2. Design

A. Data rule (Paul): `CORPORATE` becomes kind `corporate_receipt`, channel "Corporate receipts",
   kept apart from "Receipts" (employee and PAC contributions), mirroring the workbook's
   `contributions` vs `corporate_giving` tables. Amount = `Amount`, date = `Date` (already read).
B. Workbook inclusion (Paul): rows with `Include in Analysis = No` stay visible and leave the
   totals with "Excluded by the workbook: <Inclusion Reason>" (S3f's visible-but-excluded pattern).
   Applies to CONTRIBUTION rows too (Crypto: 61 such rows are counted today). Recommended: yes,
   the workbook already made the call and its duplicate legs ($23M/$25M memo twins) would otherwise
   double the corporate channel.
C. Category per row: `normalize()` reads `recipient_category` (also `category`,
   `committee_category`), canonicalised to the Graph vocabulary (case-insensitive exact match;
   unknown text -> Unclassified; blank stays blank). Per committee: the modal non-blank category
   over its rows; `category_source = "file:Recipient Category"`.
D. Fallback for committees with no file category: the committee master, loaded once per process
   (cm26, then cm24, then cm22; newest cycle wins), keyed by ID. Rule = the pipeline's own FEC
   fallback order: J -> JFC, D -> Leadership PAC, X/Y/Z -> Party Committee, O/U -> Super PAC,
   V/W -> Carey, H/S/P or A/P -> Candidate; then, for bare files only, ORG_TP T -> Trade
   Association, ORG_TP C/W -> Company PAC, L/M/V -> Other PAC; else Unclassified.
   `category_source = "fec_master:cm24"` (or `fec_master:org_type:cm24`); an ID in no master ->
   Unclassified, source "not in the 2022-2026 committee master". File category wins when both exist.
E. API (additive; contract `contracts/evidence-csv-import.json` v2 -> v3, examples asserted
   against the producers with negative controls, DE-021): listing `sources[].committees[]` gains
   `category`, `category_source`; `sources[].categories[]` = [{category, committees, rows,
   supported_rows}] in vocabulary order; select response `committee.category`,
   `committee.category_source`, rows carry `category`; totals gain the new channel and an
   `excluded_rows` count. No new query key. Filtering is client-side over the listing.
   URL: none now. S6 owns the evidence keys (D-039) and no new localStorage scope key is allowed,
   so the filter is page state; S6 folds it into `?category=` (already a Graph key, same
   vocabulary) when it builds the pane-state round-trip.
F. UI (`index.html` evidence block, `evidence-csv.js`): above the PAC select, "Committee type"
   select (All types, then each category present with its committee count, vocabulary order) and
   a "Find a PAC" text box (name or ID substring, instant). The PAC select is rebuilt from
   filter AND search, sorted by name, option text `FAIRSHAKE - C00835959 - Super PAC - 28 rows`.
   Status line: "523 PACs in file - 21 shown (Super PAC)". Results heading shows the category and
   its source. The current selection is kept while still visible, else the first visible one.
   Catalog warning 2 ("committee type has not been independently verified") is replaced by a
   sentence naming the classification source.
G. Snapshot source: `committee_finances[].category` labelled from the master at `/api/evidence`
   read time (server.py, one hunk; label only, no filter).
H. Tests: `tests/test_evidence_categories.py` (file column, modal rule, blanks, canonicalisation,
   master fallback on a 6-row fixture plus a real-master smoke on C00835959, CORPORATE channel,
   workbook exclusion, contract examples vs producers with negative controls);
   `tests/test_evidence_csv_browser.cjs` +3 steps (filter Super PAC shows FAIRSHAKE and hides
   DCCC; search "fair"; corporate totals line). Red-before / green-after receipts under
   `receipts/S7_*.txt`; real-client pass on a scratch port with the real Crypto import id
   (content-addressed, so the same file gives the same id); Paul's 8806/8802 untouched.
I. Files: `app/evidence_csv.py` (S3-owned; S3f landed 3fdfeae8f at 11:00 ET today, so hunk-exact
   staging and a HANDOFF S7 section before the first edit), `app/evidence-csv.js`,
   `app/index.html` (evidence block only), `app/server.py` (G only), the contract, the tests,
   HANDOFF, receipts. Console restart afterwards (server code changes).
J. Out of scope: Graph and Chart Studio (already filter by category); the roster; the workbook's
   own classification tables; Downstream/Graph corporate giving (a different lane's finding).

## 3. Rulings (Paul, 2026-09-17, "Go")
1. CORPORATE rows: FOLD INTO RECEIPTS (Paul chose the alternative, not the recommended separate
   channel). So `corporate` maps to kind `receipt`, channel "Receipts"; section 2.A is superseded.
2. Honour the workbook's Include in Analysis for totals: YES (rows visible, out of totals, status
   `excluded`, issue "Excluded by the workbook: <Inclusion Reason>").
3. Committee-master fallback in the pipeline's order plus the ORG_TP extension for bare files: YES.
4. File category beats the master when both exist: YES.
5. Filter control: single select plus search box: YES.

Build: one Opus architect build on this design (brief carries the rulings, the write path and the
acceptance figures), then Fable review against a scratch console, then Paul commits and restarts
8806/8802. Existing imports re-read themselves on the first listing (catalog_version 2).
