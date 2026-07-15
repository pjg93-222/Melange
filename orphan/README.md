# Orphaned and historical artifacts

Nothing under `orphan/` is read by the production pipeline. Files are retained for provenance, not
deleted. `orphan_manifest.json` records the first root cleanup; later quarantines are grouped by use:

- `snapshots/` — historical rank, database, workbook, and preregistration snapshots.
- `snapshots/congress_scrapes/` — 65 timestamped collection intermediates formerly in `Documents/`.
- `stale_workbooks/` — three look-alike workbooks that are not rank or stance authorities.
- `research_audio/` — unconsumed MFCC/wav2vec diagnostics; populated measurements are not accepted
  profile evidence and must never bypass the strict audio gate.

Do not move a file back into production merely because a historical note names it; restore it only
when a live script explicitly needs that exact snapshot.
