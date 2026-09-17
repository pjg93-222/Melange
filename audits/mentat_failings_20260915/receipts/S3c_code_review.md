# Code review — PAC evidence ingestion (lane S3/S3b/S3c), 2026-09-16 evening

**Reviewed:** 2026-09-16 23:05 ET, by Fable (no agents), on Paul's `/ecc:code-review`.
**Repo:** C:\Users\pgoff\Mentat, branch codex/mentat-crypto, HEAD `9262614c2` (S4's ledger commit on top of S3b `21c9cab6d`).
**Scope:** the uncommitted S3c changes (two test files) plus the committed S3b code paths that carry security weight: upload byte handling, zip member handling, the directory browser, the path import, and the POST routes. Other lanes' uncommitted files (R, tools, S4 test files) are out of scope.
**Decision:** REQUEST CHANGES — three HIGH items are open and being fixed in this lane; nothing CRITICAL.

## Summary

The transport and store design is sound and the local-only trust boundary holds (POST-only, Host + Origin + constant-time token). The defects that bit Paul are all in the workbook reader's *selection* logic, not in security or transport: it took the first sheet's first row as the header, so a Mentat industry workbook (title rows, header on row 4, data on later sheets) was refused with a misleading message. Two of the three warnings builders drop per-import warnings. Both are fix-in-flight.

## Findings

### CRITICAL
None.

### HIGH
1. **`evidence_csv.py` workbook reader — header row and sheet selection** (`workbook_reader`, ~:903). The header is the first non-empty row of the first sheet. Paul's `Credit Union Industry Spending Overview.xlsx` has 26 sheets; sheet 1 starts with a title, so the header became `['credit_union_master_overview']` and the import failed in 2.2 s with `The CSV needs a Committee ID, CMTE_ID, or Source Committee ID column.` The data sheets (`2021-2022`, `2023-2024`, `2025-2026`, `Cycle Exceptions`) share a 35-column header on row 4 with `Committee ID`, `Recipient Key` (`FEC:C…`), `Amount`, `Date`, `Cycle`, `Record Type`. Fix: header = first row whose keyed cells contain a committee field (else first row with ≥ 3 cells); rank sheets (committee+amount+date > committee+net_included_amount > committee only); read every sheet with the identical header as one table; record `sheets_read` and a warning naming them; a workbook with no qualifying sheet fails with a message naming its sheets. Tests for this are in `tests/test_evidence_readers.py::MentatWorkbookSelection` (red now by design).
2. **`evidence_csv.py` `TYPES` lacks `'contribution'`** (~:27-32). Mentat's own contribution sheets carry `Record Type = CONTRIBUTION`; `key()` gives `contribution`, which maps to nothing, so every row is `unsupported` and no channel total is produced even when the right sheet is read. Fix: `'contribution': 'receipt'`; also `NAME_FIELDS` gains `recipient` so the catalog shows the recipient committee's name. (The FEC bulk `TRANSACTION_TP` mapping is a separate data rule and stays with Paul: `receipts/S3b_bulk_channel_proposal.md`.)
3. **Warnings dropped in two of three builders** (`evidence_csv.py` ~:1353 and ~:1619 use `list(WARNINGS)`; ~:1515 appends the record's extra warnings). The Windows-1252 note and the bulk header note never reach `select()`/`catalog()` output, which the page renders. Found by the browser test at step 26. Fix: one helper used by all three.

### MEDIUM
4. **Failed workbook record has `sheets: []`** (`Store.refusal` / the failure path in `read_source`). The page cannot tell the reader which sheets exist when the chosen one is refused. Fix: populate `sheets` on the failure path (part of item 1).
5. **Zip member decompression is bounded only by the declared size** (`bulk_reader` :854 trusts `member.file_size`; `bulk_rows` streams `archive.open(member)` with no byte counter). A crafted archive with a lying header could feed an unbounded single line into `csv.reader`, which buffers a line in memory. Delimited files cannot do this because the stored source is capped at 500 MB, but a zip member's real size is not. Fix: wrap the member stream in a counting reader that raises `bytes_message()` past `MAX_BYTES`. Low likelihood on Paul's own box; cheap to close.
6. **`test_evidence_readers.py`: the new `MentatWorkbookSelection` class sits after the `if __name__ == '__main__'` guard** (my S3c patch appended it at end of file). It runs under `python -m unittest` because the module is imported, but the guard belongs last. Fixed in this pass.
7. **`evidence_csv.py` is ~1,700 lines** (readers, store, browser, legacy API in one module). Not wrong, but the reader layer (`text_encoding`, `delimited_reader`, `bulk_*`, `workbook_reader`, `json_reader`) would read better as `evidence_readers.py`. Defer; not before the fix lands.

### LOW
8. **Streaming branch parses `Content-Length` with bare `int()`** (`server.py` :2013). A hand-crafted non-numeric header yields a 400 whose text is Python's `invalid literal for int()` — the same class as the closed DEFECT-INT-LEAK, unreachable from the page. Fix: guard with a `ValueError` → `M_SHORT`-style message.
9. **`read_chosen_path` records `source_path` as typed, not resolved** (:1174, :1215). A junction or relative path is recorded as given. Fix: store `str(chosen.resolve())` for the receipt; keep the typed text in the error messages.
10. **`browse()` reason for a file path is `'it is not a folder'`**, which is not in the contract's reason list (`no such file`, `it is a folder`, `permission denied`, `larger than N MB`). Harmless; document or align.
11. **`Store.refusal` writes one store directory per refused path** (:1144). Swept hourly, bounded by the token; note only.

### Security review (explicit)
- Path import and browser read anything the console's Windows user can read. That is the design Paul asked for ("look anywhere in a computer"); both are POST-only behind `valid_host`, the Origin allow-list and `secrets.compare_digest` on `X-Mentat-Token` (:1998-2004). `do_GET` has no token check, so neither may ever be served on GET; the code comment at :2106 says so.
- `X-Evidence-Name` is percent-decoded then reduced to `Path(name).name` (`Upload.__init__` :550); incoming files are `uuid4().hex + suffix`; import ids are regex-gated before every path join. No traversal path found.
- No credentials, keys or tokens in the diff. No `innerHTML` with raw names in the client (names go through `textContent` / `new Option` / `escapeHtml`).
- Legacy JSON import stays bounded by the generic 7 MB gate; the streaming branch is bounded by `MAX_BYTES` before reading and by `Upload.write` during.

## Validation

| Check | Result |
| --- | --- |
| `py_compile` evidence_csv.py, server.py, test_evidence_readers.py | Pass |
| `node --check` evidence-csv.js, test_evidence_csv_browser.cjs | Pass |
| `tests.test_evidence_csv_stream` + `tests.test_evidence_csv` + `tests.test_pac_evidence_errors` | 35/35 OK (198 s; host slow) |
| `tests.test_evidence_readers` | 38/41 — the 3 new `MentatWorkbookSelection` cases red by design until item 1-2 land |
| `tests/test_evidence_csv_browser.cjs` | not run in this review (33-step run pending the reader fix; last run green through step 25, step 26 = item 3) |

## Files reviewed
- Modified, uncommitted: `mentat/tests/test_evidence_readers.py` (+96), `mentat/tests/test_evidence_csv_browser.cjs` (+219/−9)
- Committed at `21c9cab6d`, read for security: `mentat/app/evidence_csv.py` (:484-633 upload/ids, :840-900 bulk/zip, :992-1222 open_source/browse/path import), `mentat/app/server.py` (:1363-1379 Console methods, :1986-2030 POST auth + streaming branch, :2084-2112 path/browse routes)

## Next
Items 1-4 land with the reader fix now in progress (architect, or Fable directly if it does not report); items 5, 8, 9 are small and go in the same commit; 6 is fixed in this pass; 7 and 10-11 are deferred and recorded here.
