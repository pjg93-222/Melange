# OneDrive conflict-copy quarantine — 2026-07-27

Seventeen `*-PaulComputer.*` files were **moved** here from `fec/` and
`audits/`. Nothing was deleted. The repo-relative directory structure is
preserved inside this folder, so every file can be put back with a plain move
to the same path under the repo root:

```
fec/_quarantine_paulcomputer_20260727/<repo-relative path>  ->  <repo-relative path>
```

`quarantine_manifest.json` in this folder is the machine-readable record: for
each file it carries the source path, byte size, SHA-256 **before and after**
the move (verified equal for all 18), the canonical twin, and the file's
modification time.

## Why these files exist

OneDrive mints a `-PaulComputer` copy when it cannot reconcile two versions of
a file. Every copy here is a **pre-fix revision** that was additionally
written through an over-escaping transform, which:

* converted LF line endings to CRLF,
* replaced backticks with `§`,
* doubled backslashes (`\` → `\\`),
* stripped the trailing newline.

**Size is not a content proxy for this corruption.** Three of the seventeen are
*larger* than their canonical twin purely because CRLF and `\\` expansion added
bytes, not because they contain more content. Do not use "bigger file wins" to
adjudicate any of these.

Every one of the seventeen has an intact canonical twin still in place, and an
audit established that removing them is safe. They are quarantined rather than
deleted so the action is reversible.

## Inventory

Twin sizes are a snapshot taken at quarantine time; several canonical twins are
under active edit, so their current size will differ.

| Quarantined conflict copy | Canonical twin (still in place) | Copy bytes | Twin bytes | Δ | Copy SHA-256 (16) |
| --- | --- | ---: | ---: | ---: | --- |
| `audits/legfix5/congress_advanced_pages_20260725/congress_advanced_memberships-PaulComputer.ndjson` | `audits/legfix5/congress_advanced_pages_20260725/congress_advanced_memberships.ndjson` | 22,793,206 | 65,297,543 | -42,504,337 | `50b518c8171d0b42` |
| `audits/legfix5/congress_advanced_pages_20260725/congress_advanced_records-PaulComputer.ndjson` | `audits/legfix5/congress_advanced_pages_20260725/congress_advanced_records.ndjson` | 48,842,347 | 53,118,184 | -4,275,837 | `ec299835300ba857` |
| `fec/GLASSBOX_PROCESS_MATRIX-PaulComputer.md` | `fec/GLASSBOX_PROCESS_MATRIX.md` | 4,164 | 4,021 | **+143** | `b9ee04c4c9906134` |
| `fec/LEGISLATION_CULLING_INTEGRATION_ARCHITECTURE-PaulComputer.md` | `fec/LEGISLATION_CULLING_INTEGRATION_ARCHITECTURE.md` | 7,156 | 10,100 | -2,944 | `aadcf5d16e8bd88c` |
| `fec/OFFICIAL_ROLLCALL_SOURCE_CONTRACT-PaulComputer.md` | `fec/OFFICIAL_ROLLCALL_SOURCE_CONTRACT.md` | 1,855 | 1,819 | **+36** | `461e40193884a932` |
| `fec/__pycache__/collect_govinfo_bill_xml_versions-PaulComputer.cpython-312.pyc` | `fec/__pycache__/collect_govinfo_bill_xml_versions.cpython-312.pyc` | 39,992 | 48,289 | -8,297 | `2ca8dcea39ef9453` |
| `fec/build_legislation_staged_integration_gate-PaulComputer.py` | `fec/build_legislation_staged_integration_gate.py` | 21,171 | 39,334 | -18,163 | `af9b6eef0300869f` |
| `fec/collect_govinfo_bill_xml_versions-PaulComputer.py` | `fec/collect_govinfo_bill_xml_versions.py` | 28,148 | 35,982 | -7,834 | `1ab0fb8c795c2dc9` |
| `fec/harvest_congress_text_httr-PaulComputer.R` | `fec/harvest_congress_text_httr.R` | 33,764 | 40,216 | -6,452 | `52195635f70f6f23` |
| `fec/legislation_culling_integration_contract-PaulComputer.py` | `fec/legislation_culling_integration_contract.py` | 14,074 | 16,095 | -2,021 | `6b56e90e33bede5d` |
| `fec/open_glassbox_process_matrix-PaulComputer.ps1` | `fec/open_glassbox_process_matrix.ps1` | 47,611 | 46,946 | **+665** | `c4855b7b2cb61af2` |
| `fec/reconcile_congress_advanced-PaulComputer.py` | `fec/reconcile_congress_advanced.py` | 8,457 | 24,621 | -16,164 | `4007d43ee0ce33c5` |
| `fec/run_reversible_legislation_culling-PaulComputer.py` | `fec/run_reversible_legislation_culling.py` | 42,389 | 71,330 | -28,941 | `fc72fe79636d540d` |
| `fec/tests/run_focused_tests-PaulComputer.py` | `fec/tests/run_focused_tests.py` | 4,924 | 7,873 | -2,949 | `0d0d342a970b5a23` |
| `fec/tests/test_collect_govinfo_bill_xml_versions-PaulComputer.py` | `fec/tests/test_collect_govinfo_bill_xml_versions.py` | 9,256 | 19,822 | -10,566 | `29036af61a11f06b` |
| `fec/tests/test_run_reversible_legislation_culling-PaulComputer.py` | `fec/tests/test_run_reversible_legislation_culling.py` | 14,227 | 37,695 | -23,468 | `e91116118c26e0bd` |
| `fec/watch_govinfo_collector_glassbox-PaulComputer.ps1` | `fec/watch_govinfo_collector_glassbox.ps1` | 3,921 | 3,929 | -8 | `d3f3fe69faf37efb` |

## The `.pyc`: what it does and does not prove

`fec/__pycache__/collect_govinfo_bill_xml_versions-PaulComputer.cpython-312.pyc`
is a build artifact, not source, and is quarantined with the rest. Its header
carries:

* embedded source mtime `2026-07-27 05:23:49` and source size `28148` bytes,
* which match `collect_govinfo_bill_xml_versions-PaulComputer.py` **exactly**;
* the `.pyc` itself was written at `2026-07-27 07:41:20`, about two hours after
  that source file landed.

Those header facts are confirmed. **The conclusion originally drawn from them —
that the pre-fix collector "was imported and executed" — is wrong, and a later
2026-07-27 forensic pass retracted it.** A `.pyc` records *compilation*, and
compilation is not execution:

* `py_compile` / `compileall` write a `.pyc` and run **none** of the module's
  code. Verified on this machine's CPython 3.12: a probe module's side effect
  never fired, yet the `.pyc` appeared.
* Running a script as `__main__` (`python collector.py …`) executes it and
  writes **no** `.pyc` at all — CPython does not cache the `__main__` module.
  So this artifact is evidence *against* the "ran it directly" reading.

The artifact is fully accounted for by compilation alone. Recompiling the
quarantined source with its original mtime and original absolute path
reproduces it **byte-identical**:

```
sha256 2ca8dcea39ef9453b62afa624b23238437bcb3b395415c4704a6ade945898774
```

Bytes cannot separate compile from import, since both write the same `.pyc`.
That distinction does not matter here: `collect_govinfo_bill_xml_versions.py`
keeps all work behind `if __name__ == "__main__":` and has no module-level
executable statements, so an import runs nothing either. **Every route
consistent with this evidence produces zero artifacts.** Given that
`py_compile` is the routine syntax check on every diff in this repo, a compile
sweep over `fec/*.py` while the conflict copy sat in that directory is the
straightforward explanation.

### Nothing was produced, and nothing needs re-deriving

The sweep of the 05:23–08:30 window found:

* **zero** files under `audits/legfix5/govinfo_bill_xml_versions/` — the
  collector's only output root (no second root exists in the repo or under
  `%LOCALAPPDATA%\Melange`);
* all six run directories immutable (`mkdir(exist_ok=False)`, so a re-run must
  mint a new `--run-id`), every one finished before the window opened. The
  last, `full-18440-20260727b`, completed `2026-07-27T05:07:51Z` = **00:07:51
  local** — fifteen minutes *before* the conflict copy's source mtime — with
  18,406 accepted / 34 failures, matching the documented canonical outcome;
* the in-window artifacts that carry producer receipts name **other** tools:
  `build_legislation_candidate_evidence.py` v1.0.0
  (`candidate_evidence/evidence-20260727r/receipt.json`, 05:53:05) and
  `build_legislation_category_review_queue.py` v1.0.0
  (`category_review_queue/queues/…/manifest.json`, 07:58:33). Neither names the
  collector; the former *consumes* `full-18440-20260727b` as an input.

Everything else in the window belongs to the `harvest_congress_text_httr` R
lanes, including the live `text_relevance_httr_full_20260727z` collection.

**No artifact is implicated. The earlier instruction to treat 05:23–07:41
output as suspect is withdrawn.**

### Receipt gap worth recording

Settling this took a byte-level reproduction rather than a receipt lookup,
because the collector's own receipts cannot identify their producer: the
`plan_receipt` in `fec/collect_govinfo_bill_xml_versions.py` records
`plan_sha256`, counts and flags, but **no producer module name or module
hash**. Receipt-proof for or against a specific collector revision was never
obtainable from this lane. Adding a producer identity (module path + SHA-256)
to the plan receipt would make this class of question answerable directly.

Deleting the `.pyc` would have destroyed the evidence that settled this, which
is a second reason nothing here was deleted.

## The eighteenth file — renamed, not quarantined

```
audits/legfix5/congress_advanced_pages_20260725/
  text_relevance_httr_full_stage_20260726/accepted_html/117/hr/3664/
    page.html-PaulComputer.gz   ->   page.html.gz
```

This one had **no canonical twin**: OneDrive renamed the canonical file away,
so the conflict copy was the *only* file at that path and moving it here would
have left a hole in that stage. It was therefore **renamed back in place**
rather than quarantined.

Verified before and after the rename:

* SHA-256 `7c7e14da2d2086b8c0c27a84bc281fb45e29fc3c9d045b6fa048bcb2fefd1d7c`,
  61,486 bytes — **identical before and after**;
* byte-identical to the copies of the same page held in six other stages,
  including two newer ones
  (`text_relevance_httr_full_stage_20260727r`, `text_relevance_httr_full_20260727z`)
  plus `..._orchestrator_smoke_20260727T123018`, `..._safeguard_probe`,
  `..._canary_postfix2` and `..._collision_test`;
* the gzip member still decompresses to the expected
  `<!DOCTYPE html>` Congress.gov page.

Because the bytes are identical everywhere, this file was never touched by the
over-escaping transform — OneDrive only renamed it. No data was lost, and the
rename closes the one-file hole in the 20260726 stage.

## Restoring

To put a file back, move it from its path under this folder to the same
repo-relative path, then re-verify its SHA-256 against
`quarantine_manifest.json`. Do not restore anything without deciding first
whether the canonical twin (which has moved on since 2026-07-27) should be
overwritten — in every case examined, the canonical twin is the newer and
uncorrupted revision.
