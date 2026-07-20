# INDEX — Melange Systems / Moneyball
*Regenerated 2026-07-02 (architecture refactor). Git repo: `git log` for history.*

## Layout
- `fec/` — the engine (~60 live scripts). Start points: `run_pipeline.py` (canonical chain),
  `moneyball_core.py` (shared kernel), `paths.py` (roots; MONEYBALL_ROOT env override).
- `fec/tests/run_tests.py` — 84 kernel checks as of 2026-07-19 (count only grows — trust the run output); run before any pipeline after code changes.
- `fec/attic/` — retired one-shot/diagnostic scripts (history preserved via git mv).
- `backups/` — workbook backups (auto-created before every write).
- `votes/` — HS117-119 rosters. `research/` — papers. `Moneyball Main Version - Blended.xlsx` — the rank workbook (system of record for ranks; dial sheets: Topic Weights, Category Stance).
- Root `*.json` — derived pipeline artifacts (regenerable). `social_media.db` — posts + speeches + interactions.

## Canonical docs
- `MATHEMATICAL_SPECIFICATION.md` — law of the system (authoritative-code table, conventions, dials).
- `ARCHITECTURE_REVIEW_2026-07-02.md` — the review that drove the refactor (+ remaining roadmap).
- `DEEP_AUDIT_REPORT_2026-07-02.md` / `DEEP_AUDIT_MATH_LOGIC_2026-07-02.md` — audit findings record.
- `PERSONALITY_RECEPTIVITY_LAYER_2026-07-02.md` — Big5/receptivity/contingency design + validation.

## Verification protocol
code change -> `python fec/tests/run_tests.py` -> `python fec/run_pipeline.py [--recalc]`
-> rank delta vs last ranks_*.json (zero unless intended) -> audit 136/136 clean as of 2026-07-19 (count only grows).
