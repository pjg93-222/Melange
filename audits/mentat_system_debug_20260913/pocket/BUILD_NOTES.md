# Mentat Pocket — build notes

Built 2026-09-13 / 2026-09-14 UTC in worktree `mentat-system-debug-1f368e`.
Nothing in `C:\Users\pgoff\Mentat` was edited. No git operations.

## Files

| File | Bytes | What it is |
|---|---:|---|
| `mentat-pocket.html` | 165,751 | The app. One self-contained file, data inlined. No DOCTYPE/html/head/body — the publisher wraps it. |
| `pocket-data.json` | 119,605 | The snapshot, also inlined into the page. Under the ~600 KB budget by 4.9x. |
| `pocket-integrity.json` | 23,644 | Extractor receipt: request count, per-industry reconciliation, spot checks, provenance. |
| `icon-180.png` | 2,030 | 180x180, ivory ground, plum serif M. Written with `zlib`+`struct`, no Pillow. |
| `manifest.webmanifest` | 276 | name / short_name / display / colors / start_url / one icon. |
| `extract_pocket_data.py` | 16,305 | The snapshot extractor (stdlib only: `urllib`, `json`). |
| `make_icon.py` | 4,054 | Icon renderer (4x supersampled convex polygons). |
| `build_page.py` | 1,298 | Inlines `pocket-data.json` between the page's data markers. Idempotent. |
| `selfcheck.py` | 13,290 | Static checks: HTML structure, tokens, `node --check`, data integrity, icon, manifest. |
| `render_harness.js` | 14,041 | Executes the page's script against a DOM stub over every scope. |
| `negative_control.py` | 3,871 | Proves the harness can fail, on seven injected defects. |
| `dump_default_view.js` | 2,166 | Prints every string the page shows on a first open, for reading the copy without a browser. |
| `extract.log` | 6,760 | The extraction run's console output. |

## What the read-only run touched in the Mentat tree

Audited by mtime over the whole tree for the session window. **No source file and no application file changed.** 269 path hits, all of them caches or SQLite sidecars:

| What | Count | Why it is not a mutation |
|---|---:|---|
| `mentat/state/contribution-query-cache/responses/results/*` | 259 | The query-result cache the console writes on every read (`contribution_query_store`). Content-addressed, keyed by source stamp + query. |
| `mentat/state/contribution-analytics/*.sqlite` | (excluded from the count) | The materialised per-dataset index. Content-addressed by source token; reused by Paul's consoles. |
| `mentat/.cache/**/mentat.db-shm` | 8 | SQLite shared-memory files. `contribution_data.py:261-262` says it outright: "SHM is a lock/index file: ordinary read-only connections change it," and the source token excludes `-shm` for that reason. |
| `mentat/state/cross-reference/evidence.sqlite-shm` and `-wal` | 2 | Both **created at 21:41:11**, when my first query opened the evidence store read-only. The `-wal` is **0 bytes**; `contribution_data.py:262-264` treats a zero-size WAL as absent — "An empty WAL is likewise equivalent to absence, not new evidence" — so neither file enters the pinned token. Left in place: deleting SQLite sidecars under a database other processes may have open would be the actual hazard. |

The database itself, `mentat/state/cross-reference/evidence.sqlite` (534,528,000 bytes), still carries **LastWriteTime 2026-09-12 17:06:51** — unchanged across the entire run.

## Data snapshot

- Source: a **read-only** console instance I started myself, `python C:\Users\pgoff\Mentat\mentat\app\server.py --port 8814 --read-only`, **PID 38164**, started 21:40 local, **stopped 22:05 local**. Verified stopped; Paul's consoles on 8802 / 8803 / 8804 / 8805 / 8808 / 8813 were listening on the same PIDs before and after (43404, 22228, 67100, 75920, 51268, 9920) and were never contacted.
- Endpoints used: `GET /api/contributions/session`, `GET /api/contributions/catalog`, `POST /api/contributions/query`. Request shape is the studio's own compiled shape (`chart-studio-contributions.js:71-132`): `{dataset, basis, dimensions, measures, filters, sort, limit, offset}`.
- Basis `receipt`, the studio default. Amounts are **integer cents** (`catalog.amount_unit == 'cents'`), rounded nowhere — stored and compared to the cent.
- Field ids verified against the live catalog before use: `cycle`, `recipient_category`, `party`, `recipient`, `company`, `amount`, `records`. `records` is the count measure; its catalog label is **"Observation count"** (`contribution_data.py:59-62`).
- Async `retry_after_ms` / `status: preparing` polling handled exactly as the studio does.

**Cost: 216 requests, 118 of them polls, 244.0 seconds wall.** Seven of the eight dataset indexes had to be materialised by the server during the run (Telecom alone reported 808,066 records and wrote a ~3.5 GB `.pending` before collapsing to its final cache). Those caches live in the shared `state/contribution-analytics` store and are reused by Paul's consoles. Free space on C: was 34.9 GB before and 39 GB after — the run did not consume disk net.

### Why 216 requests and not ~630

Per-company result sets are obtained by **grouping on `company`** (e.g. `dimensions: [company, cycle, recipient]`) rather than issuing one company-filtered request each. That is the same SQL `GROUP BY` the filtered form produces, and it is only used because the server reported the **complete** group set (`has_more` false after paging) for every one of those queries — so no ranking is derived from a truncated page. Eleven requests per industry:

1. `[cycle]`, 2. `[cycle, recipient_category]`, 3. `[cycle, party]`, 4. `[cycle, recipient]`, 5. `[recipient]` limit 8 — the industry scope, each its own request;
6. `[company]` (the facet), 7. `[company, cycle]`, 8. `[company, cycle, recipient_category]`, 9. `[company, cycle, party]`, 10. `[company, cycle, recipient]`, 11. `[company, recipient]` — the company scopes.

Per-cycle top-8 lists are cut from the **complete** `[.., cycle, recipient]` group set, so they are honest per cycle; the all-cycles top-8 comes from its own cycle-free query, never from a union of per-cycle lists.

### Integrity

The reconciliation compares two **different queries**: the industry total from `dimensions: [cycle]`, and the sum of the per-company totals from `dimensions: [company, cycle]`. This follows DE-012 — a check whose two sides come from the same producer is a vacuous pass.

**All 8 industries, all 3 cycles, zero delta in cents and in record counts. All 8 spot checks matched** (one company per industry re-fetched with an explicit `company eq` filter and compared against its grouped rows). All group sets complete.

| Industry | Companies | 2021-22 | 2023-24 | 2025-26 | Delta |
|---|---:|---:|---:|---:|---:|
| Banking | 10 | $16,652,458.77 | $26,107,204.16 | $12,003,181.12 | 0 |
| Community Banks | 10 | $228,755.22 | $379,455.03 | $255,295.73 | 0 |
| Credit Arms | 10 | $8,778,979.26 | $9,677,525.39 | $5,475,940.60 | 0 |
| Credit Union | 10 | $369,423.16 | $779,088.35 | $273,494.14 | 0 |
| Crypto | 10 | $1,756,273.34 | $145,462,078.45 | $102,731,131.38 | 0 |
| Fintech | 10 | $1,891,559.66 | $3,859,524.56 | $4,052,807.09 | 0 |
| Property & Casualty Insurance | 10 | $5,240,339.66 | $7,857,445.42 | $3,589,580.51 | 0 |
| Telecom | 10 | $12,463,873.75 | $17,978,153.89 | $7,256,093.45 | 0 |

`selfcheck.py` re-derives all of the above **from the raw per-scope result sets in `pocket-data.json`**, never from the extractor's own integrity block, and additionally proves — for all 88 scopes — that `recipient_category` and `party` each **partition** the same receipts (their rows sum to the cycle total exactly, in both cents and records). That is what licenses the page's "% of the party-recorded total" wording.

## Palette validation

`node validate_palette.js "#2f5fa8,#b8322e,#9a9297" --mode light --surface "#fcf7f4" --pairs all`

```
[PASS] Lightness band         all 3 inside L 0.43–0.77
[FAIL] Chroma floor           below floor (reads gray): [["#9a9297",0.012]]
[PASS] CVD separation         worst all-pairs #9a9297<->#b8322e dE 16.2 (deutan) · tritan 19.5
[PASS] Normal-vision floor    worst all-pairs #9a9297<->#2f5fa8 dE 21.8 (normal)
[WARN] Contrast vs surface    below 3:1 — relief required: [["#9a9297",2.85]]
```

`node validate_palette.js "#4a80d0,#c9564f,#9a9297" --mode dark --surface "#221a30" --pairs all`

```
[PASS] Lightness band         all 3 inside L 0.48–0.67
[FAIL] Chroma floor           below floor (reads gray): [["#9a9297",0.012]]
[PASS] CVD separation         worst all-pairs #9a9297<->#c9564f dE 9.9 (deutan) · tritan 13.1
[PASS] Normal-vision floor    worst all-pairs #9a9297<->#4a80d0 dE 15.0 (normal)
[PASS] Contrast vs surface    all 3 >= 3:1
```

**Final values: light `#2f5fa8 / #b8322e / #9a9297`, dark `#4a80d0 / #c9564f / #9a9297`.** Two judgement calls, both deliberate:

1. **The chroma-floor FAIL on `#9a9297` was not snapped.** That check exists to catch a hue that *accidentally* reads as gray. Here gray is the semantic: "Other / Unclassified" must not read as a party. Raising its chroma would give the unclassified bucket a hue. Every **pair** check — the thing the brief said to snap for — passes in both modes. The contrast WARN that comes with it (2.85:1 in light) is legal under the validator's own rule only with mandatory secondary encoding, which the card has: a legend giving every segment a name, a value and a percent, plus a Table toggle.
2. **Dark blue and red were stepped up** from `#2f5fa8`/`#b8322e` to `#4a80d0`/`#c9564f`. On the `#221a30` ground the originals measured 2.64:1 and 2.81:1; the stepped values clear 3:1 while every pair check still passes. Lightening the gray as well was tried and rejected — it pushed the neutral out of the dark lightness band and dropped the normal-vision floor to 13.6.

## Verification (Step 4)

Browser tools are barred in this lane, so nothing here is an eyeball claim.

- **`selfcheck.py` — ALL CHECKS PASSED.** No `<!DOCTYPE>`, no `<html>`/`<head>`/`<body>` wrapper (regex uses `\b` so `<header>` is not a false hit); every tag closed (an `html.parser` stack walk found no mismatched end tag and no unclosed element); exactly one `<title>Mentat Pocket</title>`; every required iOS meta and link; safe-area insets on all four sides; `-webkit-text-size-adjust:100%`; `prefers-reduced-motion`; `tabular-nums`; the ten console tokens present with their exact hexes; the dark block guarded exactly once as `:root:not([data-theme="light"])` and once as `:root[data-theme="dark"]`; `body` backgrounded from a token; **every external URL is a Google Fonts host and there is no external `<script src>`**; exactly one script block; no emoji; the data is an object literal, not `JSON.parse`.
- **`node --check`** on the extracted script block (written to a temp `.js`): passes. The inlined data literal re-parses to 8 industries and carries no raw `</script>`.
- **`render_harness.js`** executes the page's real script against a DOM stub and drives **1,056 scope combinations** (8 industries x 11 company choices x 4 cycle choices x 3 measures), clicking **21,114 marks**, toggling all four Table views on and off in each. It asserts: no exception; the headline tile **parsed back** and checked against the raw cents within the tolerance its unit allows (it does not re-implement the formatter — that would only prove two copies agree); the receipt count and company count in the tile; every subline non-trivial; every empty card says so in words; and **58,575 geometry assertions** that no bar and no text label leaves the 340-unit viewBox, using the page's own character-width model plus 6% slack. **PASSED.**
- **`negative_control.py`** injects seven specific defects and requires the harness to reject each: total measure returning the count; a wrong money divisor; an empty card drawing a blank box; an off-by-one company count; names wrapped to the full box with no font-error margin; a too-narrow value gutter; an average abbreviated like a large total. **All seven caught, unmutated page passes.** The checks are not vacuous.

### Defects the verification actually found and fixed

1. **Money-unit boundary.** `$999,999` rendered as `$1,000K` because the K/M thresholds were tested before rounding. Thresholds moved to 999,500 / 99,950.
2. **Long recipient names could clip.** Names wrapped to the full box width using an approximate character-width model, so any model error ran off the right edge — 692 geometry failures. Names now wrap inside 90% of the box and the value gutter went 78 -> 84.
3. **Stacked bar overflowed by 1 unit** when a party segment was exactly zero, because zero-width segments were forced to a 1-unit minimum and still consumed a gap. Zero segments now draw nothing, keep a clamped tap target, and take no gap, so the bar still spans the full width.
4. **An empty Recipient categories card drew a blank box.** It now states "No included receipts for <scope> in <cycle>."
5. **The Party split card said "no recipient party"** even when the real reason was that the scope had no receipts at all. Those are different facts about the source and the card now distinguishes them.
6. **The party denominator was misnamed.** The card said segments were shares of "the total giving *carrying a recipient party*". They are not: `party` partitions **every** included receipt — "Other / Unclassified" is the source's own bucket for a recipient with no party — so the denominator is the whole scope total. `selfcheck.py` proves that partition for all 88 scopes, and the card now checks the arithmetic at render time and only claims "all giving for <scope> <window>" when the three segments actually add back to the scope total; otherwise it says "the three segments shown". This was caught by dumping the default view and reading the sentence, not by a test.

## Confusion hazard worth naming

On the default view (Banking, all companies, all cycles) the Party split card reads **Other / Unclassified $37,286,833**. That is close to, but is **not**, the **$37,940,955.71** unresolved-review figure from the 2026-09-13 Mentat system-debug lane. Different universes: this page's number is included receipts to committees with **no recorded party**, inside the published totals; the system-debug number is the cross-reference `company attribution unresolved` bucket, which `exclude()` zeroes and which sits **outside** every total. They differ by about $654K and share nothing but an order of magnitude. If Paul sees "$37M" on his phone the day after that investigation, this is the note that stops a false alarm.

## Deliberate deviations from the brief — for the coordinator to rule on

1. **"Receipts" / "Average receipt", not "Gifts" / "Average gift".** The measure is `records`, whose catalog label is "Observation count", and the console's own model note says the grain is "One preserved source observation … **not necessarily one unique economic gift**". Labelling it "gifts" on a page read by working lobbyists would contradict the system's own stated grain and the CONSTRAINTS rule that a figure names its denominator. Three brief-specified strings changed: the measure control reads *Total giving · Receipts · Average receipt*, the tile reads "n receipts · k companies", and the tap readout reads "name · $value · n receipts · share". **This is a find-and-replace away from the brief's wording if Paul prefers "gifts".**
2. **Third party segment is labelled "Other / Unclassified", not "Other/Unknown"** — that is the source's own literal third value. The snapshot contains exactly three party values across all 8 industries (`D`, `R`, `Other / Unclassified`), so the segment is a passthrough, not a fold; the card's note only mentions folding if a future snapshot adds a fourth value.
3. **Basis label "Published included receipts"** is the studio's string (`chart-studio-contributions.js:6`). The server's data-layer label for the same basis is "Published included receipt view" (`contribution_data.py:66`). The studio string is what the console shows, so it is what the page shows.
4. **Per-company data via `GROUP BY company`** rather than N filtered requests — see "Why 216 requests" above. Proven equivalent by the complete-group-set guard plus eight direct filtered spot checks.
5. **"Giving by election cycle" ignores the cycle control** — it is the cycle comparison, so narrowing it to one cycle would leave a single bar. The card says so in its subline.

## Known limits

- **No browser was used.** Fonts, real glyph metrics, iOS Home Screen behaviour, `env(safe-area-inset-*)` on a notched device, and the actual rendered colour have not been seen. The geometry checks use a character-width model with a 6% margin, not real Albert Sans metrics; if the real font is more than ~10% wider than the model, a long committee name could still wrap one line short.
- **Negative amounts are handled but untested by data.** This snapshot contains no negative cycle total and no negative party row, so the negative-value paths (red bar, "net negative after refunds" note, clamped stacked segment) have never run against real data.
- **The snapshot is frozen.** Regenerating means re-running a read-only console and `extract_pocket_data.py`, then `build_page.py`. The page states its snapshot timestamp in the footer; nothing in it self-refreshes.
- **`icon-180.png` has opaque corners outside the rounded square** (filled with `--paper` #fcf7f4) so that iOS's own squircle mask never reveals transparency. On a non-masking host a faint square edge is visible.
- **10 companies per industry** — that is the tracked-company roster in the pinned report source, not a cap I imposed. The company facet returned exactly 10 for every industry, and `group_count` confirmed the facet was complete.
- **`localStorage` only.** The scope is remembered per-device in a try/catch; a private window or blocked site data silently falls back to the default opening scope (Banking · All companies · All cycles · Total giving).
- **Materialising the dataset indexes wrote multi-GB cache files** into the shared `state/contribution-analytics` store. This is the console's designed behaviour on the read-only analytical endpoints, not a mutation of source data, and the files are content-addressed and reused. Free space on C: was 34.9 GB during the run — worth watching if all eight datasets are ever rebuilt from cold.

## Nothing unfinished

Every deliverable named in the brief exists, every static check passes, and the two dynamic suites pass with a proven-non-vacuous negative control. The open items are the five deviations above, which are wording and method calls for the coordinator, not gaps.
