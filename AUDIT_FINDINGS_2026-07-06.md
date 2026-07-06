# AUDIT FINDINGS — 2026-07-06 (mid-crawl audit, run-5a)

**Context:** audit executed WHILE three collectors intentionally run (Hewitt final pass, Fox
36.5k-page archive walk, NPR) — sanctioned by design: the run_pipeline chain reads no
social_media.db (run-4 memory), so collector writes cannot race chain reads. Corpus is
MID-GROWTH; anything downstream of the interview corpus is expected to change at the armed
post-collector top-up, NOT during this audit (the chain consumes none of it directly).

**State under audit:** main @1a9ee41 (run-4z5), working tree clean at audit start except
regenerated display artifacts. Audit scope emphasis = tonight's changed surface:
big5_llm fast-mode block, fetch_interviews (fox/hewitt legs, rank pools, Accept headers),
co_appearance_layer.py (NEW), build_dashboard_bundle COAP, desk tpl green-region-all-axes +
dashboard tpl coap toggle, weekly_refresh two new steps, member_references re-score.

## Phase 0 — orientation
- git: 12 most recent commits reviewed (4w→4z5); chain order in run_pipeline.py unchanged
  (16 steps + audit_full; lt_priming in-chain; salience advisory before bundle). OK.
- Live jobs: 3 python.exe = the three collectors. Expected.
- Label hygiene note: commit subjects reuse run labels (two "Run-4x", "Run-4y", "Run-4z"
  pairs from tonight) — cosmetic, immutable history, noted only.

## Phase 1 — static baselines
- kernel tests: **30 passed, 0 FAILED** ✓
- py_compile sweep: **105 files, 0 failures** ✓ (scratchpad .pyc target)
- audit_full: **56 passed, 0 FAILED — ALL MODULES CLEAN** ✓ (56 is current; the skill text's
  "52" predates the run-4k/4l/4m additions)

## Phase 2 — true run-through gates
(to be appended)

## Phase 3 — deep sweeps (tonight's changed surface prioritized)
- P2 silent-failure: big5_llm broad excepts are the two by-design patterns (cache-line parse
  tolerance :243; work() error capture :298 — surfaces as a counted error, never silent).
  co_appearance_layer writes via MC.dump_atomic ✓. fetch_interviews FAIL paths print and do
  NOT mark iv_fetch_log for fox (auto-retry next run ✓).
- P1 contracts: bundle reads co_appearance.json keys a/b/n/bipartisan — exactly what the layer
  dumps ✓; desk tpl agree/axcol consume 5-length big5_pct/llm_pct arrays (verified live: 469
  members, 154 Consc-agree) ✓; member_references.json schema unchanged by the re-score
  (signed_coalitions + bundle + desk all consumed it clean in tonight's 22:45 chain) ✓.
- P3 kernel drift: zero cpf/_sm copies outside moneyball_core (sync_stance_clean's guarded copy
  excepted, as always) ✓.
- weekly_refresh's two new steps run under step() = tolerant, correct placement pre-chain ✓.
- P4 spec-vs-code: tonight's changes are collectors/diagnostics/display — no spec'd math touched;
  no reconciliation items.
- make_combined "id collisions: ['backbtn']" — deliberate warning print (make_combined.py:39),
  pre-existing, display-only merge artifact. Known-benign (added to registry below).

## Findings

**[S2-01] fec/fetch_interviews.py (run_hewitt dates / run_fox dates) — 100% of tonight's new-leg
rows stored DATELESS (hewitt 559/559, fox 488/488).** Evidence: `select ... where date=''` at
audit time; hewitt root cause = the date map hardcoded post-sitemaps 1–4, which cover 2005-era
posts — every recent interview post missed the map (sitemap regex itself verified correct: 1,000
pairs matched on page 1); fox root cause = the alphabetical walk hadn't reached month-named
slugs AND most Fox slugs never carry dates (slug-regex was the only source). Impact: dateless
rows are invisible to co_appearance_layer (episode key requires date), lose recency ordering in
the reference-layer dyad cap, and blank the desk date columns. Chain/ranks unaffected (chain
reads no social_media.db). **REMEDIED during audit (user present, collector-layer scope):**
(1) run_hewitt now enumerates ALL post-sitemaps from wp-sitemap.xml; (2) run_fox falls back to
the page's JSON-LD datePublished when the slug has no date; (3) scratchpad backfill_dates.py
UPDATEs tonight's stored rows from the same authoritative sources (scoped to empty dates on the
two legs' rows only). Both collectors stopped for the fix and relaunched after backfill;
iv_fetch_log resume makes the interruption free.

**[S3-01] fetch_interviews iv_fetch_log status semantics** — 'ok' conflates fetched-and-stored
with fetched-and-dropped (hewitt marks 0-guest posts 'ok' deliberately so re-runs skip them).
Consequence: improving the attribution rule requires the manual zero-yield marker-clear dance
(done twice tonight). Remedy (report-only): a distinct status value ('ok-empty') would make
revisits self-serve. No wrong numbers; hygiene.

**[S3-02] commit-subject label reuse** — tonight's history contains two "Run-4x", "Run-4y",
"Run-4z" pairs (label collisions across sessions). Immutable; cosmetic; noted so future greps
of "Run-4x" expect two hits.
