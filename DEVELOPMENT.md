# About this branch

`release/melange` is a filtered, history-free publication of the local Melange `main` branch (source commit recorded in `SOURCE_PROVENANCE.json`). It is not a development branch.

- Local `main` is never pushed to this repository as it is. Everything here passed the export filter (`ops/release_lib/export.py`: roots `fec/`, `requirements.txt`, `ops/`; extension allowlist; 5 MB blob cap; path excludes) and a secret scan.
- `FILTER_REPORT.txt` lists what was left out and why, including the ADDENDUM that classifies every exclusion. Private and runtime data (FEC bulk files, per-member measurement data, press-derived records, licensed datasets) never ships here; supply it locally.
- Do not commit work directly on this branch. Changes made here are overwritten the next time it is republished.

## Making a change

1. Make the change on local Melange `main`, with its normal tests and review.
2. Republish: export the new `main` commit through the same filter, compare it with this branch, and add one fast-forward commit. Verify that every published blob id equals its source blob id at the new commit.
3. Update `SOURCE_PROVENANCE.json` (source commit, generated time) and `FILTER_REPORT.txt` (counts and any new exclusions), then push `release/melange` without force and confirm with `git ls-remote origin refs/heads/release/melange`.

A new file type that the filter drops needs an explicit decision (add to the allowlist, or record it as kept-excluded in the report); never widen the filter to ship data.

Mentat is published separately, from its own repository, and has its own `DEVELOPMENT.md`.
