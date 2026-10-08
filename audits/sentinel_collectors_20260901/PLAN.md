# STAGING rehearsal plan — press recovery, section C

Written BEFORE execution. All numbered facts below are quoted from the worktree code at
`C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\sentinel-collectors-progress-f7de7d\fec\`.

## 0. Roots

| Symbol | Value |
|---|---|
| MAIN (read-only, LIVE) | `C:\Users\pgoff\OneDrive\Desktop\Melange Systems` |
| WORKTREE (code to run) | `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\sentinel-collectors-progress-f7de7d` |
| STAGING (every write) | `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-sentinel-collectors-progress-f7de7d\d573ef55-b2ca-4ec1-a60f-2784a7960ad4\scratchpad\staging` |

Environment set on EVERY python invocation (PowerShell shell state does not persist between
tool calls, so the assignments are repeated inline each time):

```
$env:MONEYBALL_ROOT  = <STAGING>
$env:MONEYBALL_DRAFT = <STAGING>\draft
$env:TMP = $env:TEMP = $env:TMPDIR = <STAGING>\tmp
cwd = <WORKTREE>
```

Verified before any run (`python -c "import sys; sys.path.insert(0,'fec'); import paths; ..."`):

```
ROOT  = ...\scratchpad\staging
DATA  = ...\scratchpad\staging\data
DRAFT = ...\scratchpad\staging\draft
TEMP  = ...\scratchpad\staging\tmp
```

`$env:TMPDIR/TEMP/TMP` are redirected because `build_cumulative` stages each per-run rebuild in
`tempfile.TemporaryDirectory(prefix="press-feed-stage-")` (line 405). Redirecting keeps even the
scratch writes inside STAGING.

## 1. How the code decides what is read and what is written

### 1a. `fec/audit_collection.py` — the intake gate

`--press-delta-root` is honoured; auto-discovery only fires when it is `None`, so the audit does
NOT ignore the flag (lines 1010-1012):

```python
    if args.press_delta_root is None:
        from collect.build_press_engine_feed import discover_run
        args.press_delta_root, _retry_receipt = discover_run(Path(ROOT) / "outputs")
```

No adaptation (per-run outputs dirs) is required. Every other default that could resolve under a
project root is re-based onto `ROOT` = STAGING (lines 1006-1016), and `--output` /
`--accepted-press-receipts-dir` are passed as ABSOLUTE staging paths so the re-basing is moot.

Acceptance is purely "zero errors from `audit_press_delta`" in press scope (lines 1052-1053,
1080):

```python
    if args.scope == "press":
        failed = bool(press_delta_result["errors"])
...
    result["status"] = "REJECTED" if failed else "ACCEPTED"
```

Exit code (line 1101): `return 2 if failed else 0`.

The binding recorded in the receipt (lines 1032-1042) is `press_delta_root` (**resolved**),
`press_retry_receipt_sha256`, and `press_source_sha256` over the three delta CSVs.

Archive + immutability (lines 978-1001):

```python
def archive_accepted_press_receipt(document, receipt_dir):
    if (document.get("schema") != "collection-intake-receipt-v1"
            or document.get("status") != "ACCEPTED"):
        return None
...
    if not re.fullmatch(r"press_refresh_\d{8}", run_name):
        raise RuntimeError("unsafe press run name in accepted receipt: %r" % run_name)
...
    if destination.is_file():
        existing = json.loads(destination.read_text(encoding="utf-8"))
        if _receipt_binding(existing) != _receipt_binding(document):
            raise RuntimeError("accepted press receipt binding changed for %s" % run_name)
        return destination
```

REJECTED receipts are never archived (early `return None`). Re-running with an identical binding
is idempotent (`return destination`, no write).

### 1b. `fec/collect/build_press_engine_feed.py` — the feed builder

**The brief's premise that the builder discovers runs by globbing `outputs/press_refresh_*` is
wrong for the cumulative path.** `discover_run()` (line 146) is dead code inside this module's
`main()`; its only caller is `audit_collection.main` above. `--outputs-root` (line 486) is parsed
and never used. When `--source-root` is omitted, `main()` takes the cumulative branch
(lines 507-510) and the accepted set comes from the **archive dir + the current intake receipt**,
not from a filesystem glob of run dirs.

Run acceptance — `_accepted_intake_receipts` (lines 328-363):

```python
    if receipt_dir.is_dir():
        paths.extend(sorted(receipt_dir.glob("press_refresh_*.json")))
    current_receipt = Path(current_receipt)
    if current_receipt.is_file():
        paths.append(current_receipt)
...
        if (document.get("schema") != "collection-intake-receipt-v1"
                or document.get("status") != "ACCEPTED"):
            if path == current_receipt:
                raise RuntimeError("collection intake receipt is not an accepted gate receipt")
            raise RuntimeError("archived press receipt is not accepted: %s" % path)
        try:
            root = Path(document["inputs"]["press_delta_root"]).resolve()
...
        if prior:
            prior_inputs = prior[1].get("inputs") or {}
            current_inputs = document.get("inputs") or {}
            binding_names = ("press_delta_root", "press_retry_receipt_sha256", "press_source_sha256")
            if any(prior_inputs.get(name) != current_inputs.get(name) for name in binding_names):
                raise RuntimeError("conflicting accepted receipts for %s" % root)
        if prior:
            continue  # prefer the immutable archived path over the rolling current receipt
```

Run ORDER (lines 366-375) — by the run dir's own `press_network_retry_receipt.json`
`completed_at`, tie-broken by the resolved root string:

```python
        retry_path = root / "press_network_retry_receipt.json"
...
            completed = parse_receipt_timestamp(retry.get("completed_at"))
...
    ordered.sort(key=lambda item: (item[0], item[1]))
```

Collision precedence — **earliest accepted run wins**, via `setdefault` (lines 420-429):

```python
            for row in tone_rows:
                tone_by_key.setdefault(turn_key(row), row)
            for row in fulltext_rows:
                key = (canonical_url(row.get("url"), keep_fragment=False),
                       (row.get("bioguide") or "").strip().upper())
                fulltext_by_key.setdefault(key, row)
            for row in mention_rows:
                key = (canonical_url(row.get("article_url"), keep_fragment=False),
                       (row.get("mentioned_bioguide") or "").strip().upper())
                mentions_by_key.setdefault(key, row)
```

Key definitions used by the reconciliation in step 5:
- tone: `turn_key(row)` (line 165) = `(canonical_url(url, keep_fragment=False), bioguide.upper())`
- fulltext: `(canonical_url(url, keep_fragment=False), bioguide.upper())` (lines 423-424)
- mentions: `(canonical_url(article_url, keep_fragment=False), mentioned_bioguide.upper())` (lines 427-428)

`build()` re-verifies the hash binding against the intake receipt before writing (lines 220-235)
and again after reading (lines 289-290).

### 1c. Junction semantics (the one thing that determines where reads land)

`New-Item -ItemType Junction` produces a reparse point that `pathlib.Path.resolve()` follows.
Empirically verified before execution:

```
given   : ...\staging\outputs\press_refresh_20260828
resolve : C:\Users\pgoff\OneDrive\Desktop\Melange Systems\outputs\press_refresh_20260828
name    : press_refresh_20260828
```

Consequences, all benign:
1. `inputs.press_delta_root` in every staged receipt records MAIN's real path — which is exactly
   what a production run would record, so the rehearsal receipts are faithful rather than skewed.
2. `build()`'s `audited_root != root.resolve()` guard (line 224) compares two resolved paths, so
   it matches either way.
3. `root.name` is `press_refresh_YYYYMMDD` on both sides, so the archive filename regex and the
   `source_run` label are unaffected.
4. During the feed build the source CSVs are read from MAIN directly (bypassing the junction).
   Reads only — no code path in `audit_collection.py` or `build_press_engine_feed.py` writes into
   `press_delta_root`.

## 2. Every path each command touches

### Reads (MAIN, read-only)
- `MAIN\outputs\press_refresh_{20260828,20260829,20260830,20260831,20260901}\*` — via the junctions
  for the audit, directly (post-`resolve()`) for the feed build.
- `MAIN\data\stance\press_refresh_tone.csv`, `press_refresh_fulltext.jsonl`,
  `press_refresh_feed_receipt.json`, `MAIN\data\press\official_mentions.jsonl` — read-only, for the
  reconciliation and the consumer negative check.

### Writes (STAGING only)
- `staging\PLAN.md`, `staging\RECONCILIATION.md`, `staging\main_before.csv`, `staging\main_after.csv`
- `staging\outputs\press_refresh_*` (junction reparse points; no file content)
- `staging\receipts\intake_<run>.json` (+ `.tmp` during the atomic replace)
- `staging\data\engine\press_collection_receipts\press_refresh_<run>.json`
- `staging\data\stance\press_refresh_tone.csv`, `press_refresh_fulltext.jsonl`,
  `press_refresh_feed_receipt.json`
- `staging\data\press\official_mentions.jsonl`
- `staging\logs\*.txt`, `staging\recon\*`, `staging\tmp\*` (python tempdir)

### How "no write resolves under MAIN" was confirmed
1. `paths.ROOT/DATA/DRAFT` printed and confirmed to sit under STAGING before any producer ran, so
   every ROOT-relative default (`data/engine/press_collection_receipts`, `data/stance/*`,
   `data/press/*`, `outputs/`) resolves into STAGING.
2. Both writer entry points take explicit ABSOLUTE staging paths for `--output`,
   `--accepted-press-receipts-dir`, `--tone-output`, `--fulltext-output`, `--mentions-output`,
   `--receipt-output`, `--intake-receipt`, `--accepted-receipts-dir`.
3. `tempfile.gettempdir()` redirected into `staging\tmp`.
4. The only MAIN-resolving path in the whole flow is `press_delta_root`, and it is consumed by
   `sha256()`, `read_csv_strict()`, `Path.read_text()`, and `.is_file()` — read calls only.
5. Byte-level proof: a recursive `(RelativePath, Length, LastWriteTimeUtc.Ticks)` snapshot of the
   five run dirs plus `MAIN\data\stance`, `MAIN\data\press`, `MAIN\data\engine` is taken before
   the first run and re-taken after the last, then diffed.

## 3. Exact commands

Each is run with the env prologue from section 0 and `cwd = <WORKTREE>`.

**Snapshot (before):**
```
Get-ChildItem -Recurse -File over the 5 run dirs + MAIN\data\{stance,press,engine}
  -> staging\main_before.csv  (Scope, RelativePath, Length, Ticks)
```

**Per-run audit** (for RUN in 20260828, 20260829, 20260830, 20260831, 20260901):
```
python fec\audit_collection.py --scope press ^
  --press-delta-root  <STAGING>\outputs\press_refresh_<RUN> ^
  --output            <STAGING>\receipts\intake_<RUN>.json ^
  --accepted-press-receipts-dir <STAGING>\data\engine\press_collection_receipts
   > staging\logs\audit_<RUN>.txt  (stdout+stderr+exit code)
```
`--press-date-floor` left at its `2026-06-25` default; `--scope press` means no house/audio/db/
interview path is touched at all (lines 1052-1054 select only `press_delta`).

Expected: 20260828/20260830/20260831/20260901 ACCEPTED (exit 0) if the delta invariants hold.
**Predicted failure mode for 20260829 (negative control):** that dir contains only
`manual_cu_news.csv`, `press_discovery.rds`, `press_refreshed_index.*`, `press_roster.rds`,
`press_url_delta.*` — no `press_delta_*.csv` and no `press_network_retry_receipt.json`. `main()`
hashes the sources at line 1021-1023 **before** calling `audit_press_delta`, so
`sha256(root / "press_delta_scored.csv")` raises an uncaught `FileNotFoundError`. Predicted
result: a Python traceback and exit code 1 — NOT a clean REJECTED receipt and not exit 2. This
will be reported as an observed defect, not smoothed over.

**Negative control (i) — idempotent re-accept:** re-run the 20260828 audit verbatim. Expected:
same ACCEPTED status, `archive_accepted_press_receipt` hits `if destination.is_file()` with an
equal binding and returns without writing.

**Negative control (ii) — binding change:** `audit_collection.py` ends with
`if __name__ == "__main__": raise SystemExit(main())` (lines 1104-1105) and its module level does
nothing but import `collect.press_receipt` and `paths`, so it IS import-safe. A tiny script will
import ONLY `archive_accepted_press_receipt`, load the archived `press_refresh_20260828.json`,
mutate `inputs.press_retry_receipt_sha256`, and call the function against the same staging archive
dir. Expected: `RuntimeError: accepted press receipt binding changed for press_refresh_20260828`.
The archived file must be byte-identical afterwards (the raise happens before any write).

**Feed build (cumulative):**
```
python fec\collect\build_press_engine_feed.py ^
  --intake-receipt          <STAGING>\receipts\intake_<newest accepted>.json ^
  --accepted-receipts-dir   <STAGING>\data\engine\press_collection_receipts ^
  --tone-output      <STAGING>\data\stance\press_refresh_tone.csv ^
  --fulltext-output  <STAGING>\data\stance\press_refresh_fulltext.jsonl ^
  --mentions-output  <STAGING>\data\press\official_mentions.jsonl ^
  --receipt-output   <STAGING>\data\stance\press_refresh_feed_receipt.json
   > staging\logs\feed_build.txt
```
`--source-root` is deliberately OMITTED so `main()` takes the `build_cumulative` branch
(line 508). The outputs are passed explicitly even though the ROOT defaults already point into
STAGING, so the destination does not depend on the env alone.

**Consumer check:** `press_stream.py` has no `__main__` guard but its module level only builds
path constants from `paths` — import-safe. Two calls to `validate_refresh_receipt()` with explicit
path arguments: (a) the four staged files → expect a returned receipt, no exception; (b) MAIN's
four live files → expect `RuntimeError`, predicted message
`press refresh receipt is not a cumulative accepted-run ledger`, because MAIN's receipt (read
above) carries neither `promotion_mode` nor `accepted_runs`. Reads only.

**Reconciliation:** a script importing only `turn_key` and `canonical_url` from the builder,
computing per-run / union / candidate / active sets and their differences. Read-only over
`staging\data\*` and `MAIN\data\*`; writes `staging\RECONCILIATION.md` and `staging\recon\*`.

**Snapshot (after) + diff** against `main_before.csv`, restricted to the five run dirs and
`MAIN\data\{stance,press,engine}` (MAIN's `fec\` code is being edited by another session and is
deliberately out of scope for this comparison).

## 4. Not done, by guardrail
- No fold: `fec\collect\press_baseline_fold.py` is never invoked. `PRESS_BASELINE_FOLD` (User)
  observed as `"0"` and left untouched.
- No dashboard publication, no scheduled-task change, no `git add`/`commit` anywhere.
- `C:\Users\pgoff\OneDrive\Desktop\Draft Systems\all_press_release_index.csv` never opened —
  `MONEYBALL_DRAFT` is redirected to `staging\draft` precisely so `press_stream.BASE_TONE_PATH`
  cannot resolve into the real Draft Systems tree.
