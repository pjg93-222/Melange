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
- (a) chain steps: **17/17 OK, exit 0, 5.9 min** ✓
- (b) audit tail: **ALL MODULES CLEAN** ✓
- (c) rank delta vs pre-state: **0/533 moved** ✓
- (d) artifact hashes vs pre-state: **7/7 byte-identical** (budget_frontier, electoral,
  optimize_result, per_topic_coalition, salience_advisory, dashboard_data incl. refs+coap,
  lt_priming fresh-regenerated) ✓ — pipeline idempotent at current inputs
- determinism: budget_frontier double-run (TOPIC=Interchange, scratchpad FRONTIER_OUT) —
  **identical hashes** ✓

## Phase 2.5 — P5 UI smoke (port 8802; 8801 is the user's server)
- cu-member-desk.html: 537 rows render; member view opens; 8 SVG charts; green overlap markup
  present with the new all-axes rule + Consc legend note; staff content present; **zero console
  errors/warnings** ✓
- Moneyball Dashboard.html: renders; `ly_r` + `ly_a` toggles present; DATA.refs=1,641,
  DATA.coap=111; co-appearance layer toggled + drawn live; **zero console errors/warnings** ✓
- No test state written to localStorage.

## S2-01 remediation verification (same session)
- run_hewitt: full sitemap-index enumeration → date map 19,099 posts / 20 sitemaps (was 4
  hardcoded). run_fox: JSON-LD datePublished fallback.
- Backfill: hewitt 48 packages dated → **0 rows dateless**; fox 192/192 packages dated (every
  page carried datePublished) → **0 rows dateless**.
- Kernel 30/30 after the fixes; both collectors relaunched (resume log = free interruption).
- Fix commit: @962959d on main.

## Known-benign additions
- make_combined "id collisions: ['backbtn']" — deliberate merge-warning print, display-only.
- Fox transcript pages that 404 during the archive walk (dead URLs in old sitemaps) print FAIL
  and are retried next run by design — not data loss.

## Verdict (run-5a)
ALL GATES GREEN at @1a9ee41→@962959d. One S2 caught-and-remedied in the collector layer
(never reached any chain artifact); two S3 hygiene notes report-only. The chain remains
idempotent, deterministic, and rank-stable while three collectors crawl concurrently.

---

# RUN-5B — EXTENSIVE PASS (same night, user: "Extense audit")

## Baselines re-confirmed
kernel 30/30 ✓; audit 56/56 → **59/59 after the new guards** (below) ✓.

## New-corpus forensics (~8k rows landed tonight)
- Exact duplicates: **tonight's four legs are clean** (fox/hewitt/npr 0; cbs 2 prefix-collisions,
  not exact dups). The 27 INTERVIEW dup rows are LEGACY ABC/CNN packages from the older ingest era
  → they join the standing user-gated D2 dedup ledger (CREC 299 + INTERVIEW 27). No action without
  the user's gate.
- Attribution eyeball (2 random turns/leg): all read as genuine first-person member speech,
  era-consistent (Sanders–Brennan 2019 CBS; Jeffries Oct-2025 shutdown; Graham 2009 Afghanistan).
  Observed-and-benign: NPR pieces sometimes quote members' clips from other networks — still the
  member's words; the co-appearance substantial-appearance floor absorbs clip-level noise.
- **[S2-02] run_hewitt enumeration walked ONLY the historical archive page** — every stored post
  dated 2011–2014 and the smoke-tested 2026 Thune post had 0 rows (the smoke test fetched pages
  directly, masking the gap). The paginated /transcripts listing (360 pages ≈ 8.3k posts,
  2005→today) is the live index. **FIXED same pass:** enumeration = archive page ∪ /transcripts
  pagination, with a slug-level member prefilter (full name or rank+known-surname) so the walk
  fetches ~hundreds of member posts instead of 8.3k blind; strict slug+title resolution + body-
  label gate unchanged after fetch. Collector relaunched.
- [S3-04] Old Hewitt pages emit U+FFFD mojibake for smart quotes (utf-8 replace on likely
  cp1252 pages) — cosmetic in desk quotes, words intact for scoring. Report-only (a latin-1
  fallback in get() would touch every leg; not worth the risk unratified).
- Fox date range 2004→2022 at check time reflects the alphabetical walk position, not a defect;
  the JSON-LD fallback dates every page from here on.

## Coverage & documentation
- **[S3-05→FIXED] audit_full had ZERO guards on the psychology/media artifacts** — three schema/
  sanity checks added (big5_llm_opus traits+n_chunks+coverage floor; member_references edge keys
  + scored-count consistency + floor; co_appearance edge keys + n>=1 + floor). Audit is now
  **59 checks**; all pass on live artifacts.
- **[S3-06→FIXED] README documented none of the media/psychology layer** — module table gains
  section 6 (collectors → dispositions → LLM Big-5 → reference layer → co-appearances) and the
  audit count is corrected 52→59.
- Tree-wide: **zero true bare excepts**; direct json.dump users are legacy/non-chain writers
  (noted, no new ones tonight); spec constants spot-verified in the kernel (PERS_NONE=0.45
  user-ratified line, SGATE ladder incl. '—'=0.85); DTHRESH/LOSSFRAME covered by kernel tests.

## Deep UI (French Hill — a non-pilot member)
Member view renders 8 SVG charts; all-axes green legend + Consc→Diligence note visible; External
measures row (follow-through) present; LLM overlay markup present; refs panel markup present;
In-contact clean; **zero console errors across the entire click-through**.

## Verdict (run-5b)
ALL CLEAN after remediation: one S2 enumeration hole (Hewitt live stream) fixed + collector
relaunched; audit coverage extended to the new layer (56→59); README brought current; legacy
dup ledger updated (user-gated as before). Kernel 30/30 and audit 59/59 at close.

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

**[S2-01] fec/members/fetch_interviews.py (run_hewitt dates / run_fox dates) — 100% of tonight's new-leg
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
