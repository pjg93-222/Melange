# AUDIT FINDINGS — 2026-07-03 (extensive audit + true run-through, run 3)

**State audited:** commit `3ca213d` (worktree `claude/modest-sinoussi-824761` == `main` == live tree; live tree clean).
Since run-2 (merged @d0f1643): Empath+fitted-SMOreg activation (@ac86bca, ranks 0/533), cost controls,
IIT-C approach notes, persona-homophily gate (negative → router OFF), YouTube collector contamination
fix (test rows wiped), gitignore hygiene. big5_traits.py is NOT in the pipeline chain (manual,
corpus-driven), so corpus changes since the last traits build do not move ranks until the user reruns it.

## Phase 1 — Static baselines
| Baseline | Expected | Actual |
|---|---|---|
| `fec/tests/run_tests.py` | 30 passed, 0 FAILED | ✅ **30 passed, 0 FAILED** |
| py_compile sweep fec/ (skip attic) | all clean | ✅ **80 files, 0 errors** |
| `fec/audit_full.py` | 52 passed, ALL MODULES CLEAN | ✅ **52 passed, 0 FAILED** (solo run) |

*Procedure note (not a repo defect):* the first audit_full invocation reported 51/52 with
`integrity (22) sub-audit clean` failing. Two contention sources were live at that moment: (1) my
own parallel baseline processes, and (2) **the user's own full pipeline run finishing ~19:27–19:33**
(engine artifacts stamped 19:27; its sync_stance_g workbook save overlaps my first audit window —
the more likely culprit). Standalone audit.py = 22/22 and a solo audit_full rerun = 52/52 →
transient read contention, not a repo defect. Run baselines serially, and check for a live user
pipeline (artifact mtimes + python process list) before baselining.

## Phase 2 — True run-through gates
| Gate | Expected | Actual |
|---|---|---|
| (a) every chain step OK, exit 0 | OK | ✅ **16/16 steps OK, exit 0, 15.0 min** (sync_stance_g `SAVED.` — Excel was closed) |
| (b) audit tail | ALL MODULES CLEAN | ✅ **`ALL MODULES CLEAN.`** (audit_full inside the chain, 148.9s) |
| (c) rank delta vs pre-state | ZERO / explained | ✅ **0/533 rank deltas, 0 score deltas (>1e-12)** |
| (d) engine artifact hashes | identical / explained | ⚠️→✅ **7 artifacts differ — EXPLAINED & PROVEN benign** (below) |
| Determinism (budget_frontier ×2, TOPIC=Interchange) | identical hashes | ✅ **byte-identical** (md5 4ef9b206… both runs) |

**Gate (d) forensics.** Differing: budget_frontier(.json/_electoral), optimize_result, per_topic_alloc,
per_topic_coalition, salience_advisory, dashboard_data. Identical: ranks_python, per_topic_alloc_bridge.
Context: the **user's own full pipeline finished ~19:27**, and a **user big5_traits.py loop was writing
big5_traits.json live** (observed writes 19:41:08 and a fresh PID 23192 started 19:42:35) — the pre-state
I hashed was 12 minutes old and built from slightly different inputs than my run consumed. Proof the
delta is inputs, not the engines: (1) determinism double-run byte-identical; (2) **input-purity test** —
a full all-topics budget_frontier rerun against current on-disk inputs reproduced the chain's
budget_frontier.json **byte-for-byte (md5 6a27a4ed…)**. A deterministic pure function changing output
⇒ its inputs changed: my receptivity step (19:40:09) read a fresher big5_traits.json than the user's
(~19:12) run did, and my engines read the bipartisan.json the user's run emitted at 19:27 (two-run
convergence, known-benign registry). The purity test doubling as a fixed-point check ⇒ **convergence has
settled**: absent new corpus/traits changes, the next chain run should be zero-delta across all engines.

## Findings

_(appended as discovered; severity S1 corrupts/crashes/unexplained delta, S2 silent wrong-number, S3 hygiene)_

**[S3-01] MATHEMATICAL_SPECIFICATION.md — three rows drifted behind code** (spec untouched since
merge d0f1643; code presumed authoritative; reconcile is the user's call, per protocol NEITHER side
edited here).
- Receptivity row still reads `susc = .40A+.30N−.20C−.10E (Byrne)`; code (receptivity_layer.py:60–88,
  commit 4b116fd) now blends the B&L persona read: `susc = (1−PERSONA_W)·susc_trait + PERSONA_W·persona_susc_z`
  for members with ≥15 classified sentences (persona_susc_z = .60z(communion) − .40z(agency)), plus the
  susc_read cross-comparison field. Coverage is no longer a pilot: 496/533 members.
- Standing-dials list is missing `PERSONA_W=0.30` (new env dial, receptivity_layer.py:61).
- Big Five row says "Ramey-synth closed-vocab on tweets+floor+hearings"; live method string (big5_traits.py:218)
  is "…Empath lexicons + essays-fitted SMOreg weights when fec/liwc/ files present", corpus now includes
  INTERVIEW rows. Impact: none on outputs (doc rot only). Remedy: update the three spec rows.

**[S3-02] fit_smoreg_essays.py / fit_smoreg_rkh.py — raw `json.dump` (non-atomic) writers.** Same
family as run-2's S3-01 registry (manual/one-shot scripts exempted). Noted because their output
`fec/liwc/mairesse_smoreg.json` is a **runtime input to big5_traits.py**; a kill mid-write would leave
a torn weights file. Mitigated: the file is git-tracked (commit 3ca213d) → recoverable. Remedy (inert):
swap to `MC.dump_atomic` next time either fitter is touched.

**[S3-03] fetch_interviews.py:169–171 (CNN; same pattern PBS :319–322, NBC :357–360) — a day/show is
marked `ok` in iv_fetch_log even when individual segments inside it failed silently** (`except
Exception: continue` per segment, then unconditional `INSERT … 'ok'`). Resumable-log semantics make
those segments permanently skipped on every future resume — silent partial harvest, no retry path.
Impact: corpus completeness only (collector layer; no rank/engine effect). Remedy: write `'partial'`
instead of `'ok'` when the inner loop swallowed ≥1 exception, so a re-run revisits the day.

**[S3-05] budget_frontier.py:121 — completion print names the wrong file in two of three modes.**
Evidence: `print('\nwrote budget_frontier.json (mode %s, …)'…)` — the string is hard-coded while the
actual dump path (line 120) is `budget_frontier_electoral.json` under `--electoral`, or `FRONTIER_OUT`
when overridden. The chain log therefore shows "wrote budget_frontier.json (mode ELECTORAL…)".
Impact: log-forensics confusion only (artifact itself is written correctly). Remedy: print the actual
path chosen at line 120.

**[S3-06] make_member_desk_00.tpl:544 — percentile ordinal hard-codes "th"** (`${Math.round(v*100)}th pct`),
rendering "91th pct" / "21th pct" / "1th pct" on the psychometrics bars (observed live: Tim Scott
"Dominance — agency persona 91th pct"). Impact: cosmetic. Remedy: ordinal helper (st/nd/rd/th) or the
neutral form "pct 91".

**[S3-04] No concurrency interlock between the pipeline chain and manual corpus jobs.** Observed live:
user's big5_traits.py (PID 23192, started 19:42:35) rewrote big5_traits.json *between* my chain's
receptivity step (reads big5 at 19:40:09) and make_member_desk (reads big5 directly, minutes later) —
desk radar percentiles can reflect a newer trait snapshot than the engines' receptivity did for one
run. Self-heals on the next chain run; known modus operandi (big5 is deliberately manual/out-of-chain).
Remedy (report-only): make_member_desk could print a one-line notice when big5_traits.json mtime >
member_receptivity.json mtime.

## Phase 3 — Deep-sweep coverage
- **P1 artifact contracts:** run-2 verified the full producer→consumer table at d0f1643; only 13 files
  changed since (diff-stat driven). New contracts verified by hand: big5_traits.json {O,C,E,A,ES,**N**,
  tokens,lowconf} satisfies BOTH consumers (receptivity reads N, desk radar reads ES; zero-text members
  get full-key rows); agency_communion.json {members:{m:{agency,communion,n}}} matches receptivity's
  read incl. the n≥15 gate; desk bundle's new `psy` key is consumed by the template (psychHTML, line 542)
  with a graceful empty state. Two writers CONVERTED to dump_atomic since run-2 (assemble_viz,
  social_interaction_layer) — S3-01-run-2 shrank. No new non-atomic writer in the chain.
- **P2 silent failures:** zero bare `except:` outside attic. All `except FileNotFoundError` fallbacks
  print loudly (incl. the two new ones: persona channel OFF, desk psychometrics empty). Collector
  swallows assessed — one real gap = S3-03.
- **P3 kernel drift:** cpf/sm64/PERS/IMP/BLOCKCAT/SGATE/TORD single-sourced in moneyball_core; only
  copies = hard-guarded sync_stance_clean.py (guard intact, sys.exit line 4) + attic (excluded). MBC
  alias convention inherited unchanged.
- **P4 spec-vs-code:** ratified dials confirmed in code (MAXSHIFT 18, HALF/HALFF 0.10, DTHRESH 11.25,
  LOSSFRAME 1.10, PERS '—' 0.45, SGATE ladder, IMP 18-cat, two cpf physics distinct). Drift = S3-01 only.
- **P5 UI smoke (port 8802, preview browser, no localStorage writes):** cu-member-desk.html — 533 ranked
  rows; #1 member (Tim Scott) opens; staff sections (staff-view/file-staff/staff-edit) + gold/star/notes
  markup present; NEW computed psychometrics section renders live (Big5 radar, B&L warmth/dominance
  percentiles, pressure multiplier 1.171×, susceptibility cross-read); In-contact panel switches;
  **zero console errors/warnings**. Moneyball Dashboard.html — all engine sections render; **zero
  console errors/warnings**.

## Fix lane
Branch **`audit/fixes-2026-07-03`** @ `4527b8f` — one provably-inert fix: S3-05 (frontier completion
print now names the actual file written; zero consumers of the old string, kernel tests 30/30 after).
All other findings are behavior-affecting or user-domain → **report-only**: S3-01 spec rows (user
reconciles), S3-02 fitter atomic writes, S3-03 `'partial'` fetch-log status, S3-04 interlock/notice,
S3-06 ordinal suffix (regenerates desk HTML — needs the full verification protocol when applied).

## Tally
**S1: 0 · S2: 0 · S3: 6** (S3-05 fixed on the fix branch; 5 report-only). All baselines green, all
run-through gates green (gate d deltas proven benign: moving corpus + two-run convergence, now settled).

## Known-benign (NOT re-flagged; registry in the mission brief)
View-stale workbook / snapshot fallback print; two-run col-G↔bipartisan convergence; 4 territorial-
delegate staffer offices; Big-Five O-trait reversed party validation; `--recalc` retired-notice;
per-topic $2M budgets are diagnostics; README §Diagnostics-only write-only artifacts.
