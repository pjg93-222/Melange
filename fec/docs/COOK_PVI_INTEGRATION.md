# Cook PVI historical district context

Implemented in the isolated Cook PVI worktree on 2026-10-05. This adds the supplied
Cook PVI snapshot to the Member Desk District section and Sources & method.
It does not change scoring, receptivity, allocation, ranking, or efficiency.

## Source and interpretation

The byte-preserved source packet lives in `source_data/cook_pvi/2026/`. Its CSV
SHA-256 is `3bf2786d391323b48f4d87e9b5c5e82802bbf7749a1c83e7c6da600fa353cb71`,
matching the supplied research CSV. Publication date is 2026-07-29; retrieval
date is 2026-10-05. The packet retains the raw Datawrapper table, original
normalizer, JSON, source manifest, and research notes. Original notes describe
the extraction session; this document describes the subsequent integration.
The archived normalizer is evidence, not a refresh command.

Cook describes the 2026 edition as presidential partisan lean based on the 2020
and 2024 elections. [Publisher methodology](https://www.cookpolitical.com/cook-pvi).
The supplied labels are rounded. Signed values use D negative, R positive and
EVEN zero; missing observations never become zero. EVEN does not claim an exact
unrounded zero. Source rank and incumbent text remain source metadata and do not
become priority scores or member identity keys.

All 435 source districts retain `UNVERIFIED-HERE` boundary currency. A matching
district code does not certify identical current boundaries or current incumbency.
The District display explicitly calls this a **2026 source snapshot**, with both
dates and the historical code-match limitation next to each available value.

## Runtime contract

`fec/district/cook_pvi.py` is import-safe and uses only the standard library.
`load_reference()` checks all six manifest hashes, the exact 435-district roster,
uniqueness, label/sign agreement, raw source cells, source ranks and CSV/JSON/raw
parity before returning a keyed reference. Source `.gitattributes` disables
newline conversion so fresh checkouts preserve the hashes.

The desk loads the tracked source packet directly from its code checkout. It
does not depend on a research-worktree path, a network fetch, or a generated JSON
cache. The optional standalone export command is:

```powershell
python fec/district/cook_pvi.py
```

This validates the packet and atomically writes `data/district/cook_pvi_2026.json`.
`--source-dir` and `--output` support isolated verification. An absent packet
produces an unavailable display; a partial or corrupt packet raises an error.
The loader is deliberately bound to this edition and its source dates. A future
edition needs a separate reviewed snapshot and a matching loader update.

After existing desk calculations, `attach_reference()` adds only:

- `members[].cook_pvi`: explicit status, historical district label and PVI label,
  signed points, identity source and boundary limitation.
- `cook_pvi_meta`: source provenance, display-only flag, CSV/manifest hashes and
  coverage counts.

Member identity uses the desk bioguide-to-legislators roster where available,
with an explicit House district-text fallback. Conflicting identities and
ambiguous district text fail closed. At-large keys normalize to `SS-00`.
Senate, DC and territories remain outside this 435-district snapshot. Original
publisher incumbent names are never used for matching. `cook_pvi` travels with
the existing deferred profile payload; ranked/efficiency renderers do not use it.

## Verification and deployment status

Checks on 2026-10-05:

- 435/435 source rows, all six source hashes and original source fields verified.
- Read-only replay against the saved live 533-member desk and legislators roster:
  431 historical district-code matches; 100 senators and two delegates outside
  scope; zero unmatched records. These are roster counts, not 435-seat coverage.
- Every pre-existing bundle field matched before/after the candidate renderer's
  canonical non-Cook SHA-256
  `ae117b5cbf4ecea0477ec0a3e72179f29461b2bf734b9215f42d23172375c45c`.
- 49 importer/join tests, 14 existing efficiency regressions, and 20 JavaScript
  surface tests passed. The latter include eight new PVI tests.
- Browser preview visibly showed AK-AL R+6, AZ-06 EVEN, and Senate outside-scope
  text, including dates, source link and boundary caveat.

Commands:

```powershell
python -m pytest fec/tests/district/test_cook_pvi.py fec/tests/surfaces/test_desk_efficiency_metrics.py -q
node --test fec/tests/surfaces/test_desk_cook_pvi.cjs fec/tests/surfaces/test_member_desk_honors.cjs
```

`fec/surfaces/refresh_cook_pvi_context.py` stages an enriched copy of a saved
generation without importing producers or running models. It checks the saved
bundle against both published light data and deferred profiles, retains the
existing efficiency payload and honors generation, and adds only Cook fields
and three HTML insertions. It refuses changed inputs and reused output paths.

```powershell
python fec/surfaces/refresh_cook_pvi_context.py --root "C:\Users\pgoff\OneDrive\Desktop\Melange Systems" --out-dir outputs/cook_pvi_candidate_new
```

The local live desk received a **descriptive context overlay** on its served
`original-desk.html`, `advanced-desk.html` and 533 individual profile records.
All pre-existing profile fields and page behavior are preserved. Canonical
`member_desk_bundle.json`, desk/profile exports, combined/offline/email files,
the shell, its generation receipt and other served assets remain unchanged.
The integration is also wired into the normal producer for its next guarded
generation. A future full clean rebuild must consume that enriched generation
to retain the overlay.

The broader analytical-source audit already failed before this publication
(112 bill/FEC generation errors). This overlay does not repair or certify that
generation. Its separate `live_context_overlay_receipt.json` records the
baseline failure, source hashes, unchanged non-Cook values, page proofs,
published hashes and backups. The existing canonical alias receipt still binds
its unchanged generation. Evidence is under
`outputs/cook_pvi_integration_20261005/`; the verified candidate is under
`outputs/cook_pvi_refresh_overlay_verified_20261005/`.

[COOK_PVI_DESCRIPTIVE_FORMULA.md](COOK_PVI_DESCRIPTIVE_FORMULA.md) gives the signed
encoding and an equivalent direction/magnitude representation. Neither alters
the existing scoring or allocation formulas.
