# AUDIT FINDINGS — 2026-07-02 (constrained read-only audit)
Scope per mission brief: correctness audit, findings-only. Constants/outputs are user-ratified;
anomalies are reported as questions. No repo file changed except this report and the §5 fix lane
recorded at the bottom.

## Baselines
- `python fec/tests/run_tests.py` : **28 passed, 0 FAILED** ✅ (matches expectation)
- `python fec/audit_full.py`      : **50 passed, 0 FAILED — ALL MODULES CLEAN** ✅
  (mission brief and README both say "29 passed" — the suite has grown to 50; see S3-07 doc rot)
- `py_compile` sweep: **66/66 fec/*.py compile clean** (an initial all-fail was this audit's own
  scanner bug — `cfile=os.devnull` is invalid on Windows; corrected and re-run)

---

## S2 — silent wrong-number risks

### [S2-01] fec/surfaces/build_dashboard_bundle.py:76,91,229 — "bipartisanship" is computed from the AUGMENTED graph and written back over bipartisan.json, creating definition drift + a feedback loop into cascade physics
Evidence: `net=max(glob.glob(MB_ROOT+r'\congress_cosponsor_network_*.xlsx'),key=os.path.getmtime)` (L76 — this
selects the AUG file); comment L91 says "weighted fraction of **cosponsorship** ties crossing party" but the
graph now contains press-engagement, HCoI, and 619 social edges (+117 socially reinforced weights);
L229 `json.dump({name[i]:BP[i] ...}, open(...bipartisan.json','w'))` overwrites the artifact that
`moneyball_core.bpf()` serves to `cpf_diffusion` (cascade cross-party physics), the flip model's
`tgt` bonus (1+0.3·bpf), and the coalition seed boost.
Impact: three coupled effects, all silent: (a) the *meaning* of bipartisanship changed the day the
AUG network went live — cross-party reposts (e.g. Lummis↔Gillibrand) now raise a member's
"bipartisanship" without any cosponsorship; (b) mild self-amplification: social cross-party edges →
higher bpf → higher cpf_diffusion on those same edges next cycle; (c) engines always consume the
PREVIOUS run's bp (bundle sits last in CHAIN). Cascade spreads, winnability targets, and coalition
boosts all move with it — no error is ever raised.
Remedy (text only): compute BP from the newest **non-AUG** cosponsor file (same filter
build_multilayer_network.py uses: `if 'AUG' not in os.path.basename(p)`), or promote bipartisan.json
to its own early-chain producer; either way the definition needs user ratification. **Question for
the user: is social/press-engagement affinity supposed to count toward bipartisanship?**

### [S2-02] fec/members/receptivity_layer.py:41-45 — a completely missing big5_traits.json (or electoral_plays.json) degrades the whole layer to neutral with no failure signal
Evidence: `try: T=json.load(...big5_traits.json...)['traits']` / `except FileNotFoundError: T={}` and
`except FileNotFoundError: EP={}`. With T={}, `sh=min(1,(t.get('tokens',0)/1500)**0.5)`=0 → every
member gets neutral multipliers; with EP={}, PT loss-domain falls back to security-only.
Note: per the brief, the *per-member* neutral fallback is BY DESIGN — this finding is only about the
whole-input-file-missing case, which produces a fully valid-looking member_receptivity.json.
Impact: an accidentally deleted/renamed traits file silently turns the personality layer off while
the pipeline reports success (stdout does print `trait-neutral(lowconf) 533`, but run_pipeline
surfaces only the last line, and audit_full's caps check passes on all-neutral values).
Remedy: keep the fallback, add a loud guard — e.g. `if not T: print('!! big5_traits.json missing —
ALL members trait-neutral')` plus an audit_full check that trait-neutral count < 533.

### [S2-03] pattern (14 sites) — non-atomic artifact writes: `json.dump(..., open(path,'w'))` truncates-then-writes in place
Evidence (full list from scan): budget_frontier.py:120, build_archive_legislative.py:69,
build_dashboard_bundle.py:229+231, build_electoral.py:41, build_electoral_plays.py:42,
build_im_allocation.py:31, lt_priming.py:68, optimize.py:116, per_topic_coalition.py:75,
per_topic_flip.py:83, sna_layout.py:33, tweet_collector.py:314, vote_by_category.py:69.
Impact: a crash/kill mid-dump (the 2026-07-02 recalc force-kills Excel; OneDrive contention is
real here) leaves a truncated artifact; every artifact is gitignored → unrecoverable except by
re-running the producer. Downstream json.load then crashes loudly (good) — but for
electoral.json / electoral_plays.json / bipartisan.json the producers are NOT in run_pipeline's
CHAIN, so recovery requires knowing which off-chain script to re-run.
Remedy: write-to-temp + `os.replace(tmp, path)` (atomic on NTFS) — a 2-line pattern change per site.

### [S2-04] pattern (14 files) — workbook row ranges `range(3,536)`/`range(2,535)` and the 533-member roster are assumed, never asserted, at every workbook read
Evidence: per_category_stance.py (3 sites), budget_frontier.py, flip_model.py, per_topic_flip.py,
per_topic_coalition.py, build_media_blend.py, build_dashboard_bundle.py, money_response.py, audit.py (7), etc.
`fec/tests/run_tests.py` asserts len(members)==533 from congestion.json — but nothing asserts the
WORKBOOK row count matches. If a member row is ever added/removed from the workbook (special
election, resignation), every reader silently truncates or NULs the tail.
Impact: silent partial reads of stances/scores → wrong ranks with no error.
Remedy: one shared assertion after each sheet read (`assert len(rows_with_names)==len(MC.members())`),
or a single audit_full check comparing workbook row count to the roster.

### [S2-05] press_raw_original.json — the media-blend idempotence cache has NO producer script and no in-repo rebuild path
Evidence: scan shows `W[-NO LIVE PRODUCER-] R[build_media_blend.py]`; build_media_blend.py:89 hard-fails
without it (good — loud), but the file was created once, ad hoc, from a pre-blend backup and is gitignored.
Impact: if lost/corrupted, the blend cannot separate press from social in the raw cells; recovery
requires manually extracting press columns from a backups/ workbook — a procedure documented nowhere in the repo.
Remedy: add a `rebuild_press_cache.py` (reads a named backup, writes the cache) or at minimum a
recovery note in MATHEMATICAL_SPECIFICATION.md's workbook contract.

## S3 — hygiene / report-only

### [S3-01] Unused imports across 29 files (post-refactor residue; AST-verified whole-tree)
Notables: `import moneyball_core as MC` unused in apply_leg_stance.py:3, build_dashboard_bundle.py:2,
corrected_signals.py:3, sync_stance_g.py:3 (the from-import is what's used); flip_model.py:13 `_os`;
budget_frontier/per_topic_flip/per_topic_coalition: math/collections/glob/csv now dead after kernel
adoption; scenario.py/lt_priming.py/cosponsor_route.py: openpyxl now dead. Full list in scan output.
moneyball_core.py's `ROOT,DRAFT,WORKBOOK` re-exports are *intentional API surface* — not defects.
(§5 fix lane below removed the five safest; the rest left for a verified pass with the pipeline available.)

### [S3-02] fec/build_electoral_history.py:67 — bare `except: continue` in the importer loop
Can swallow real parse errors; recommend narrowing to (ValueError, KeyError).

### [S3-03] fec/surfaces/build_dashboard_bundle.py:213 — `except Exception: pass` empties the advisory panel on ANY advisory-file defect
A malformed salience_advisory.json renders as a blank System-shocks panel with no message.

### [S3-04] fec/build_tweet_gold_queue.py:33 — reads dashboard_data.json (previous cycle's bundle) for play codes
One-cycle staleness in a sampling tool — same class as the fixed salience-VULN issue, lower stakes.

### [S3-05] Write-only artifacts (no live reader found in ANY channel checked)
stance_dynamics.json, social_stance_signals.json, tweet_influence.json, imviz.json,
corrected_signals.json, social_member_summary.json, cu_golden_labels_stats.json.
Channels checked per brief §HARD-7: run_pipeline CHAIN (absent), Python readers (grep, none),
fec/surfaces/templates/*.tpl + *.html JS fetches (grep, none — dashboards embed data inline; sna_compact.json
IS fetched by the network app, so it is NOT on this list). These are candidates for the user to
confirm as diagnostics-only; NOT flagged as dead code.

### [S3-06] fec/sync_stance_clean.py — residual local IMP copy behind the sys.exit guard
Unreachable while guarded; only relevant if the guard is ever lifted. Kernel-drift scan is otherwise
CLEAN: no stray cpf/_sm/PERS/BLOCKCAT/SGATE copies outside moneyball_core; no MC-alias confusion.

### [S3-07] Doc rot: README.md is one refactor behind
Says 17 issues (now 18 incl. CU Tax Status), audits "22/11/29" (audit_full is now 50), references
atticked modules (sheet_sync.py, make_baseline.py, scenario_diff.py) as live, and omits paths.py /
moneyball_core.py / run_pipeline.py entirely. The mission brief's "expect 29 passed" inherited this.
Also: receptivity_layer.py's docstring L32 and its json 'provenance' string both still say lowconf
traits are "shrunk to 0/neutral" while the code applies graded sqrt(tokens/1500) shrinkage; spec's
dial registry omits SOC_VOLFLOOR / SOC_MEN_W.

### [S3-08] fec/method_audit.py:36 — unused `_m` import mid-file (second-wave adoption artifact); left untouched pending a pipeline-verified pass

## P4 — spec-vs-code (code presumed authoritative; neither side edited)
- Spec's "Media blend" row matches build_media_blend.py exactly (incl. SHRINK f=nz/15, RT×0.5). ✓
- Spec's receptivity row says "shrinkage √(tokens/1500)" — matches CODE; the file's own docstring
  disagrees (S3-07). Spec wins here; docstring is the rotten copy.
- Spec workbook-contract row could not be verified against the live workbook (workbook access is
  out of scope by rule 3); verified instead against audit_full's W1 guard output (passes).
- README (not spec) is the materially stale document — S3-07.

## Coverage notes (what was checked and found CLEAN)
- Artifact producer↔consumer key contracts for: category_stance.json (13 consumers), archive_leg,
  electoral, electoral_plays, big5_traits→receptivity, social_interactions→network builder,
  press_engagement/press_hcoi→network builder, salience_advisory→bundle (recomputes verdict from
  'value'; keys align), per_topic_alloc/coalition→build_im_allocation/write_im_sheet (shapes align),
  member_receptivity→core/audits. No schema mismatches found beyond S2-01's semantic drift.
- Apparent "-NO LIVE PRODUCER-" rows for budget_frontier/per_topic_*/optimize_result/dashboard_data
  are scanner regex artifacts (`%s`-templated filenames / env-var outputs / variable paths) — all
  four have live producers; verified by eye. congestion.json genuinely has no live producer
  (Draft-era base data) — expected, documented in README.
- MC-alias (module vs Monte-Carlo dial) confusion: none found.
- Secrets grep over *.py: no literal key strings; govinfo key correctly lives in gitignored file. ✓

---

## APPLIED STATUS (2026-07-02, post-report — user: "Continue and apply these changes")
ALL S2 remedies applied and verified (commit bf4a703): S2-01 cosponsor-only BP (BP_SRC dial;
19 optimizer allocations shifted, 17/17 frontier paths adjusted, ranks untouched), S2-02 loud
missing-input guards, S2-03 dump_atomic at all 14 sites (+2 kernel tests -> 30), S2-04 row-drift
audit check, S2-05 rebuild_press_cache.py. S3: 58 unused imports pruned across 28 files.
Verification: kernel 30/30 twice, full pipeline twice, audit ALL CLEAN twice, rank delta ZERO.
Still report-only: S3-04 (gold-queue staleness — one-shot tool), S3-05 (write-only artifacts —
awaiting user confirmation as diagnostics), S3-07 README refresh (doc-rot; low priority).

## §5 Fix lane (executed after report completion)
Branch: `audit/fixes-2026-07-02`. Scope: five provably-inert unused-import removals (name appears
nowhere else in file text; AST + grep verified): the four unused `import moneyball_core as MC`
lines (apply_leg_stance, build_dashboard_bundle, corrected_signals, sync_stance_g) and
flip_model's dead `import os as _os`. One commit per file. Kernel tests re-run after: must match
28-OK baseline. Everything else in S3-01 deliberately left for a pipeline-verified session.
