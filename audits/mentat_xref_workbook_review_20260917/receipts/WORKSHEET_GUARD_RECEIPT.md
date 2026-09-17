# Worksheet guard lane - RECEIPT (2026-09-17)

Tree: `C:\Users\pgoff\Mentat`, branch `codex/mentat-crypto`.

    git log -1 --format=%H  at session start      : 3fdfeae8fed6140f705889fbd3a407645050a047
    git log -1 --format=%H  at first copy-back    : 3fdfeae8fed6140f705889fbd3a407645050a047
    git log -1 --format=%H  at hardening copy-back: 3fdfeae8fed6140f705889fbd3a407645050a047
    git log -1 --format=%H  at the end            : 3fdfeae8fed6140f705889fbd3a407645050a047

HEAD never moved. Nothing was staged or committed. No port other than a
throwaway 8834 was bound, and 8834 was stopped (8802, 8806 and 8841 were
verified still listening and untouched; 8808 was not running before or after).

## Files changed (4), and the two that were not

| file | pre-lane sha256 | final sha256 | line endings pre -> post |
|---|---|---|---|
| `C:\Users\pgoff\Mentat\mentat\app\chart-studio-core.js` | `b9605089d31d4f09...` | `170b608ed83d096d2671748df0626ed2ea9bb7d0ebd3b5d9e63f7f601d4b23ab` | CRLF 1054 / LF 0 -> CRLF 1136 / LF 0 |
| `C:\Users\pgoff\Mentat\mentat\app\chart-studio.js` | `6f4c58df5cf49217...` | `660039fd8d937d31f36e6937fa85f6ccec2f4cbfd49126e2984b0cf545b24c84` | CRLF 2772 / LF 0 -> CRLF 2845 / LF 0 |
| `C:\Users\pgoff\Mentat\mentat\app\tests\chart-studio-core.test.js` | `508b5f9440400fc3...` | `9814af9f386b5375ea6dd897f334428e2cb4eacaffe0db3edbad1afcb93186b8` | CRLF 1051 / LF 82 -> CRLF 1201 / LF 82 |
| `C:\Users\pgoff\Mentat\mentat\tests\test_studio_worksheet_guard_browser.cjs` | (new file) | `f20b088f5a5ced762695a72fbd62be7a4ec6a58a2978f3b2affdef547d512711` | CRLF 0 / LF 180 (matches every other `.cjs`) |

Backups, written once before the first copy and deliberately NOT rewritten by
the hardening pass, so each still holds the true pre-lane content:

    mentat\app\chart-studio-core.js.bak-20260917-wsg              58,829 bytes  b9605089d31d4f09...
    mentat\app\chart-studio.js.bak-20260917-wsg                  163,130 bytes  6f4c58df5cf49217...
    mentat\app\tests\chart-studio-core.test.js.bak-20260917-wsg   68,185 bytes  508b5f9440400fc3...

The new `.cjs` has no backup (new file, as instructed).

NOT touched: `mentat/app/index.html`, `mentat/app/chart-studio.css`.
`chart-studio.css` is byte-identical to its pre-lane content with an empty diff.

**`index.html` was changed by ANOTHER lane at 12:03:39, after this lane's last
copy-back, and the change is not mine.** At lane start it was
`8905ab60f403fa1f...`; it is now `9142f61bf1fe25d6...`. The single hunk adds
`evidence-csv-category` and `evidence-csv-find` controls to the PAC evidence
picker - the evidence-CSV lane, not this one. My untouched scratch copy still
hashes to the lane-start `8905ab60f403fa1f...`, and
`grep -c "studio-worksheet-hint" mentat/app/index.html` returns 0, so nothing of
this lane is in that file. This is exactly the collision the coordinator's
addendum anticipated: building the hint node from `chart-studio.js` instead of
editing the markup is what kept this lane from clobbering that work.

Before each of the three copy-backs the live file's sha256 was re-read and
compared with what this session last wrote there; a mismatch would have aborted
the copy. All three checks passed, so the concurrent S3 lane never touched these
files while this lane ran.

### Line-ending census correction

The brief said `index.html` is MIXED 248 CRLF / 56 LF. Measured on raw bytes it
is **pure CRLF, 375 / 0** - the brief's figure is stale. I did not edit it.

The genuinely mixed file the brief did not name is
`app/tests/chart-studio-core.test.js`: **1051 CRLF / 82 LF**, already mixed at
HEAD. Every line this lane appended is CRLF and the 82 pre-existing LFs survive
byte-for-byte. `git diff` prints `warning: ... LF will be replaced by CRLF` for
that path; it does so for the unmodified file too, so it is pre-existing.

A first census using `grep -c $'\r$'` reported that file as pure CRLF and was
WRONG. Every figure in this receipt is `python` counting raw bytes.

## What was built

### 1. Default guard pills (`chart-studio-core.js`, `chart-studio.js`)

New pure functions on `MentatStudioCore`: `defaultGuards(columns, values)`,
`committeeActivitySheet(name)`, `groupWorksheets(catalog)`, `workbookKind(entry)`,
plus `WORKSHEET_GROUP_LABELS`, `NO_DATA_WORKBOOK_HINT`, `COMMITTEE_ACTIVITY_NOTE`.

`defaultGuards` returns `[{column, name, value, note}]` where `column` is the
column INDEX, the key a filter pill already uses. `values` is a function of the
index or anything indexable by it; it is read only for a column already matched
by name, so no sheet is scanned for nothing.

**Owner's ruling applied:** BOTH guards now require their value to be present in
the column. `Fact Type = Recipient` is not added to a sheet whose `Fact Type`
column never holds `Recipient`, exactly as `View = Industry` behaves.

In the client, `applyDefaultGuards()` is called from `scan()` **inside** the
`if (key !== sourceKey)` branch, immediately after `restore(key)`. The guard is
therefore installed on a fresh load of a worksheet and never by a re-render; a
removal stands in the sheet state the existing per-worksheet `localStorage`
entry persists, and returns the next time that worksheet is loaded. The pill is
`{column, op: 'equals', value, stage: 'row'}` - the identical shape
`applyGraphScope()` builds for a carried Graph pill, so it renders, reads
("Fact Type = Recipient") and deletes like any other pill, with no new CSS.
`worksheetGuards()` memoises the guard list per `sourceKey`, because a `View`
guard otherwise costs a full row scan on every render.

### 2. Committee-activity caption and total suppression

`worksheetNotes()` supplies the caption and the note of every active guard, and
is prepended on both the "nothing on the shelves yet" path and the drawn-chart
path. Suppression **reuses the existing mechanism**: `renderView()` sets
`result.totalRefusal`, the field `chart-math.js:100` already sets and
`chart-studio-core.js:848 totalNote()` reads first, so one assignment suppresses
the on-chart overlay, the note and the status-line total together. The refusal
is de-duplicated against the caption already in the note list.

### 3. Companion first (`fillReports()`)

`#studio-report` is rebuilt as optgroups, `Data workbook (tall, chart-ready)`
first then `Overview workbook (report layout)`, with the first Data workbook
preselected. With no Data workbook there is one group plus a one-line hint.

**No `index.html` edit** (coordinator's addendum about the concurrent S3 lane):
the hint node `#studio-worksheet-hint` is created from `chart-studio.js` and
appended to `#studio-worksheet-source`, reusing the existing `.studio-note`
class. **No request to the server changed.**

`kind` IS delivered to the client - verified on the live server, not inferred:
`server.py:1553-1555` sets it in `published_reports()`, `:1567` returns those
rows verbatim, `:1976-1977` serves them, and the 8834 response carries it (see
below). `workbookKind()` keeps a ` Industry Spending Data.xlsx` filename
fallback for an older server or a fixture that omits the field.

### Design reading the orchestrator should confirm

Item 3 says "list its **sheets** first under a group", but item 4 defines
`groupWorksheets(catalog) -> {data, overview}` over the catalog, which has one
row per `.xlsx`, and the brief forbids changing any request. Listing a second
workbook's sheets would need a second `/api/report-data` call. The grouping was
therefore built on the **workbook** picker, with the Data workbook preselected,
which puts its sheets first without a new request.

## Commands and their exact tails

    cd C:\Users\pgoff\Mentat\mentat

    node --test "app/tests/**/*.test.js"
      i tests 163 / suites 0 / pass 163 / fail 0 / cancelled 0 / skipped 0 / todo 0
      i duration_ms 1403.5117                       (151 before this lane; +12 new)

    node --test "tests/test_studio_wording.cjs"
      i tests 10 / suites 0 / pass 10 / fail 0 / cancelled 0 / skipped 0 / todo 0
      i duration_ms 517.3092

    node --test "tests/test_studio_worksheet_guard_browser.cjs"
      + a cycle sheet opens on the Recipient partition, says why, and lets the reader take it off (51680.3264ms)
      + a committee-activity sheet says whose money it is and refuses a grand total (24634.2587ms)
      + with no Data workbook published, only the heading and a one-line hint change (34615.8957ms)
      i tests 3 / suites 0 / pass 3 / fail 0 / cancelled 0 / skipped 0 / todo 0
      i duration_ms 122629.4063

    node --check mentat/app/chart-studio-core.js   (clean)
    node --check mentat/app/chart-studio.js        (clean)

The 12 new core tests, each with a negative control:

    a Fact Type column earns a Recipient guard, whatever its spacing or case
    a Fact Type column that never holds Recipient earns no pill either      <- the ruling
    no Fact Type column means no pill
    a View column earns a guard only when the sheet actually holds an Industry view
    a sheet carrying both columns is guarded twice, in column order
    the Recipient guard is what makes a cycle sheet sum to the report total
    the guard pill reads as the plain equality a reader can remove
    the four committee-activity sheets carry a caption, and no other sheet does
    a committee-activity caption suppresses the grand total through the engine refusal
    the catalog splits into the tall Data book and the Overview book
    a catalog of Overview books alone has an empty Data group
    a server that sends no kind is read from the filename, the same rule at the other end

The sixth is arithmetic, not wording: over a fixture shaped like a cycle sheet
(Recipient 100, Employee 80, Master 100) the unguarded sum is 280 and the
guarded sum is 100.

Two browser-test failures seen on the way were both my own assertions, never the
product: the filter pill's `textContent` includes its type glyph and menu caret
(`AbcFact Type = Recipient` + caret) so the assertion now reads the
`.studio-pill-name` span; and the status line runs straight into the LOCAL ONLY
badge (`SUM(Amount): 100LOCAL ONLY`) so `\b` after the number never matched and
is now `(?![0-9,])`.

## Evidence from the real Banking workbook (read-only console on 8834)

`python server.py --port 8834 --read-only` from `mentat\app`, stopped afterwards.

`GET /api/reports?id=published-reports` returned 8 workbooks, every one
`kind: "overview"`, so the catalog confirms both that the client receives `kind`
and that **no Data workbook exists on disk for any industry today**:

    153758336550792 overview | Banking                       | Banking Industry Spending Overview.xlsx
    268553814083809 overview | Community Banks               | ...
     82582498474602 overview | Credit Arms                   | ...
    212490812565146 overview | Credit Union                  | ...
    250990233471620 overview | Crypto                        | ...
    143088378310311 overview | Fintech                       | ...
    274330703993300 overview | Property & Casualty Insurance | ...
     29480759889816 overview | Telecom                       | ...

The SHIPPED `defaultGuards` / `committeeActivitySheet` were then run over the
REAL columns and values of Banking's own sheets, read through
`GET /api/report-data`:

    sheet                 rows    cols  guard produced        caption
    2025-2026             4,680   12    Fact Type = Recipient  -
    Cycle Exceptions      1,798   12    (none)                 -
    Recipient List        3,342   30    View = Industry        -
    Beneficiary Summary     300   24    View = Industry        CAPTION
    Beneficiary Bridge    6,791   22    View = Industry        CAPTION
    Transfer Paths       10,000    8    (none)                 CAPTION
    Funding Cohorts       8,050    9    (none)                 -
    Allocation Estimates 10,000    6    (none)                 -
    Downstream Activity      -     -    server refuses the sheet (see below)

    2025-2026        Fact Type holds: ['Master', 'Employee', 'Recipient']
    Cycle Exceptions Fact Type holds: ['Exception']
    Recipient List   View holds:      ['Industry']

### THE RULING PREVENTED A LIVE BUG

`Cycle Exceptions` is a real Banking sheet with a `Fact Type` column whose only
value across all 1,798 rows is `Exception`. Under the brief's original rule
(match on column name alone) that sheet would have opened with
`Fact Type = Recipient`, selecting **zero rows** - an empty chart on a real
sheet, with a note explaining a partition split that sheet does not have. With
the hardening it correctly gets no pill.

### Two measured facts that contradict or extend the brief

1. **`Recipient List` does not hold two views in this workbook.** The column
   named exactly `View` holds only `Industry` across all 3,342 rows, so the
   guard fires but selects everything - correct, but a no-op pill today. The
   brief's premise that this sheet sums to 2x through an Industry/Company view
   split is not what Banking's `View` column contains. (I measured only the
   column named `View`; the doubling may live in one of the other 29 columns or
   in the per-company "... View" sheets. Worth checking before relying on it.)
   The same `View`-holds-only-`Industry` shape appears in `Beneficiary Summary`
   and `Beneficiary Bridge`, which therefore get a no-op guard pill alongside
   their (correct) committee caption.

2. **`Downstream Activity` cannot be opened in worksheet mode at all.** The
   server refuses it: `{"error":"Worksheet exceeds 50,000 rows. Choose a smaller
   report subsection; no partial chart was created."}`. So its committee caption
   is unreachable through this path today. The caption still works for
   `Beneficiary Summary`, `Beneficiary Bridge` and `Transfer Paths`, and the
   browser test exercises the Downstream Activity name over a fixture.

## Not done

- No screenshots. The evidence above is DOM-free: the browser test drives the
  real client over a fixture and asserts what a reader sees, and the 8834 probe
  runs the shipped functions over the real workbook. No image was captured.
- PROGRESS.md was frozen at the coordinator's instruction; this receipt is the
  record. The patch scripts used are kept beside it
  (`patch_core.py`, `patch_tests.py`, `patch_harden.py`) with the scratch tree.
