# ARCHITECTURE REVIEW — Melange Systems / Moneyball — 2026-07-02
*Lead Enterprise Systems Architect pass: code quality, logical integrity, refactoring, maintainability.
Analysis only — no code was changed. Every number below was measured, not estimated.*

> **Historical snapshot, not current state.** This review records the repository as it existed on
> 2026-07-02. Version control, centralized paths, shared kernels, writer locks, and expanded test/audit
> gates were added later; retain the measurements below as provenance rather than a live runbook.

## Executive verdict

This is a **research codebase that has outgrown its skeleton**. The scientific machinery is genuinely
strong — deterministic CRN Monte Carlo, a 50-check self-audit harness, provenance sheets, backup-first
write discipline, neutral-fallback dials — but it is carried by **100 flat scripts (9,647 LOC) with a
copy-paste kernel, 193 hardcoded absolute paths, no version control, and an Excel workbook as the
mid-pipeline system of record**. Every defect class found in this week's audits (the CFPB engagement
drift, the BETA export break, the PERS_NONE comment/code divergence, the 18th-category producer
clobber, the workbook corruption) is a *predictable emission* of these four structural facts. The
system works and is verifiable; it is not yet maintainable by anyone but its authors, and several
failure modes will recur until the structure changes.

**Health score: functionality A− · verification B+ · structure D+ · maintainability C−**

---

## S1 — Systemic risks (the four things that generate everything else)

### A. No version control — measured proxy: 26 manual workbook backups (126 MB) in the project root
9,647 lines of Python evolved over 6 days with zero git history. Recovery from the 2026-07-02
workbook corruption worked only because of the manual backup convention; code archaeology ("which
script wrote col G?") requires memory files instead of `git log`. **One `git init` + a `.gitignore`
excluding data artifacts is the single highest-leverage 15 minutes available.** It also unlocks
`/code-review`, diff-based change review, and honest rollbacks (no more `.PRE-*` filename taxonomy).

### B. Absolute-path welding — 193 occurrences of the root path across 95 of 100 scripts
The codebase runs only as `pgoff` on this machine inside OneDrive — and OneDrive sync already
truncated the workbook mid-save once this week. Fix: one `paths.py` (root from env var with the
current default), mechanical find-replace. Then relocating data out of OneDrive's blast radius
becomes a one-line change instead of a 95-file edit.

### C. The copy-paste kernel — the measured drift factory
| Duplicated block | Copies | Drift incidents already caused |
|---|---|---|
| Cosponsor-network loader (+ mean-symmetrize) | **17 files** | 41-dup-pair wart re-fixed in 4 places |
| Party loader (HS117–119 rosters) | **11 files** | — |
| `cpf()` partisan factor | **8 files, 2 different physics** | undocumented divergence (audit-II M5) |
| Receptivity loader | 9 files | — |
| IMP importance dict | **6 files** | ABB26 re-tier had to be applied 6× (missed once) |
| PERS persuadability dict | 5 files | PERS_NONE comment/code contradiction (H1) |
| splitmix64 CRN kernel | 4 files | — |
| BLOCKCAT block map | 4 files | **H2: CFPB block merge fixed in flip_model, missed in frontier** |
Roughly **800 lines of load-bearing duplication**. A single `moneyball_core.py` (paths, rosters,
network loader, cpf variants as *named* physics, CRN kernel, PERS/IMP/BLOCKCAT, receptivity accessor)
removes the entire drift class. This is the one refactor that pays for itself immediately — three of
this week's five code bugs were duplication drift.

### D. Excel as mid-pipeline database
The rank formula chain lives in a 5 MB workbook that Python writes, Excel-COM recalculates (killing
stray Excel processes), and Python re-reads — inside OneDrive. This produced the truncation incident;
the zip-validate + retry + backup mitigations now contain it, but the architecture is still
*write → out-of-process recalc → re-read* with a user-editable file as the pivot. Long-term: compute
the pillar math in Python (it's already been reverse-engineered and verified exactly — the audit
recomputes it), and demote the workbook to a rendered *view* for editing dials. The user-facing dial
sheets (Topic Weights, Category Stance) stay in Excel; the compute leaves it.

## S2 — Structural findings

### E. Dead and dangerous scripts (fleet hygiene)
The 06-26 mtime cluster (32 files: `makeup/makeup2`, `recheck/recheck2`, `im_allocate/im_allocate2`,
`final*`, `*_congestion`, `write_*`, one-shot `apply_*` already applied) is finished work parked in
the live namespace. Worse, two **deprecated-but-loaded-gun** scripts remain executable:
- `sync_stance_clean.py` — starts by restoring a pristine backup over the live workbook (documented
  as destructive in memory, still one `python` invocation from disaster);
- `apply_stance_guard.py` — overwrites col G with a superseded formula.
Recommendation: `fec/attic/` for the one-shots (provenance preserved), and a hard `sys.exit("SUPERSEDED
— see sync_stance_g.py")` guard at the top of the two dangerous ones.

### F. Import-time side effects
41 scripts open workbooks at module import; `flip_model` does ~10s of IO+compute on `import`
(optimize/salience/scenario all pay it, and its failures surface as import errors in *other* tools);
`build_social_master` **imports `process_quorum` and thereby reruns the entire Quorum pipeline** as a
side effect (documented trap, still armed). Convention fix: module-level constants only; loaders as
functions with lazy caches.

### G. Configuration sprawl
80 `os.environ.get` dials across 22 files, with defaults duplicated per file (PERS_NONE's default
lives in 2 files; HALFF in 3; IMPUTE_IND0 in 4). The dial *culture* is right (user-ratified,
default-visible); the *storage* is wrong. One `config.py` with every dial, default, ratification
date, and consuming modules — the current comment-based documentation becomes queryable.

### H. Data-plane sprawl — 134 files in the project root
Inputs (Quorum exports, census), derived artifacts (54 JSONs), reports (8 MDs), backups (26 xlsx),
temp files (`_audit_tmp_*`, `_leg_before`) and the production workbook share one namespace. Proposed
scheme (staged, since paths.py must land first): `data/source/`, `data/derived/`, `reports/`,
`backups/` (already exists — unused by convention), with INDEX.md regenerated. Nothing here is
urgent; everything here compounds confusion.

### I. Identity by display string
"Richard Durbin" is the primary join key across the entire system; bioguide IDs exist in every
roster but are second-class. This has already forced accent-folding, NICK maps ('buddy carter'),
ambiguous-surname guards, and state-disambiguation logic — all symptoms of joining on a rendering.
Migration is invasive (every JSON keyed by name), so: **new artifacts carry both keys** from now on,
and joins prefer bioguide where present. Full migration only if a name collision ever bites in prod.

## S3 — Code-quality findings

- **J. Exception hygiene:** 19 bare `except:` in 14 files and 30 `except Exception` in 17. The
  collector retry loops are legitimate; the ones wrapping JSON loads and workbook reads can silence
  real data corruption (the class of bug the audits keep catching late). Rule: bare except only
  around retries; data-load failures should crash loudly (the pipeline runner already reports them).
- **K. Deprecated syntax:** genuinely clean. Zero deprecated openpyxl idioms, zero removed-pandas
  patterns (`applymap`, `DataFrame.append`) in live code; Python 3.12-compatible throughout. The
  modernization debt is *structural*, not syntactic. (One process note: audit_full has twice been
  patched via heredoc scripts that broke on escaping — with git + normal edits, that practice dies.)
- **L. Monoliths:** `make_member_desk.py` (89 KB) and `make_dashboard_html.py` (53 KB) are Python
  files that are mostly embedded JS/HTML template strings. Extract templates to `templates/*.html`
  with a placeholder substitution — Python shrinks ~80%, and the JS becomes editable/lintable.
- **M. Test posture:** audit_full (50 checks) + audit_frontier (12) is a real integration harness —
  better than most research code. What's missing is the unit layer under the math kernels
  (`pflip`, `shaped_cut`, `cascade`, `defection`, `issue_params`): each has documented invariants
  (monotonicity, bounds, p+q+b≡1, CRN order-independence) that would take ~150 lines of pytest and
  make refactor C safe to execute mechanically (refactor → pytest → pipeline → expect zero rank delta).

## Logical-coherence register (documented, not necessarily wrong)

1. **Two partisan-influence physics** on the same edges: diffusion `cpf = 0.4+0.6·√(bpf·bpf)` vs
   pressure `cpf = 1.7/0.5`. Defensible (different mechanisms), but they share a name across 8 files.
   Rename (`cpf_diffusion` / `cpf_pressure`) in the shared module; run the still-pending sensitivity test.
2. **Three normalization philosophies** (workbook pos/neg-max, blend p80, pillar PERCENTRANK vs
   value/MAX) — each chosen deliberately at its layer, nowhere documented as a system.
   MATHEMATICAL_SPECIFICATION.md is confirmed stale (memory: "spec was behind the code all session")
   — either refresh it from code or delete it; a wrong spec is worse than none.
3. **'—' (no position) ontology** varies: PERS 0.45 (Ally parity), SGATE 0.85, TORD-excluded,
   psi-numerator. Each is individually reasoned; collectively they're an undocumented convention.
   One paragraph in the spec fixes it.
4. **Env-dial interaction surface**: SHRINK × RT_W × SGATE × pressure_mult × LOSSFRAME all touch the
   same social→influence path; no single place states the composed formula. The audit verifies each
   in isolation; a composed "one post's journey" doc section would catch interaction bugs the
   per-dial checks can't.

## Prioritized roadmap (effort → payoff)

| # | Action | Effort | Kills |
|---|---|---|---|
| 1 | `git init` + .gitignore (artifacts/backups/db out) + first commit | 15 min | backup taxonomy, unreviewable changes, heredoc patching |
| 2 | `paths.py` + mechanical replace of 193 path literals | 1–2 h | machine-welding; enables data relocation off OneDrive |
| 3 | `moneyball_core.py` (loaders, cpf×2 named, CRN, PERS/IMP/BLOCKCAT, config dials) + mechanical adoption in the 15 live engines | 0.5–1 day | the drift factory (source of 3 of 5 recent bugs) |
| 4 | Attic the 06-26 cluster + hard-guard the 2 dangerous scripts | 30 min | the loaded guns |
| 5 | pytest unit layer on math kernels (~150 lines) | half day | makes #3 verifiable; guards future calibration changes |
| 6 | Template-extract the 2 HTML monoliths | half day | 140 KB of string-in-python |
| 7 | Data-plane directories + INDEX refresh | 1 h (after #2) | root swamp |
| 8 | Spec refresh or deletion; '—' ontology + composed-dial section | 2 h | doc drift |
| 9 | (Long-term) Python-native pillar compute; workbook demoted to view | multi-day | the Excel/OneDrive failure class at its root |

Safety protocol for #2/#3 (the invasive ones): refactor → pytest → `run_pipeline.py` → assert
**zero rank delta** vs `orphan/snapshots/ranks_AFTER_fixes.json` → audit 50/50. The harness you already built is
exactly what makes this refactor low-risk; most codebases have to earn that first.
