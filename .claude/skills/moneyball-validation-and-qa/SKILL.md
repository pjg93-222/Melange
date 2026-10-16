---
name: moneyball-validation-and-qa
description: Load this skill when verifying that a Moneyball code change is safe or when building/extending the project's QA machinery. Triggers - "did my change break anything?", "what counts as evidence here?", ranks or artifact hashes drifted after a run, "how do I add a test / an audit check?", a new artifact needs coverage, questions about gold labels / adjudication / stance accuracy / macro-F1 / acceptance thresholds, "is this classifier good enough?", fingerprinting inputs, or a script silently skipping members. Does NOT cover the scientific prereg/look/battery discipline for research claims (moneyball-research-methodology), day-to-day chain/collector operation (moneyball-run-and-operate), statistical analysis recipes like power studies and permutation gates (moneyball-proof-and-analysis-toolkit), the dial catalog (moneyball-config-and-flags), or the change-class rules themselves (moneyball-change-control).
---

# Moneyball validation and QA

This project turns congressional data (press releases, tweets, votes, cosponsorship networks, FEC money) into per-member persuasion rankings. Most defects here are "silent wrong-number": the pipeline keeps printing success while producing subtly wrong ranks. This skill defines what counts as engineering evidence that a code change is safe, documents the user-gold-label machinery that gates every accuracy claim, and shows exactly how to extend the two verification harnesses (`fec/tests/run_tests.py` and `fec/audit/audit_full.py`). The scientific bar for *research* claims (preregistration, one-shot "looks", batteries) is a different, stricter standard — see moneyball-research-methodology; this skill is about code changes.

## When NOT to use this skill

- Deciding whether a change is even allowed, or which verification tier a change class requires → **moneyball-change-control**.
- Running a new statistical test (power study, split-half reliability, permutation gate, byte-match purity proof) → **moneyball-proof-and-analysis-toolkit**.
- Preregistering a hypothesis or consuming a "look" at held-out data → **moneyball-research-methodology**.
- Interpreting an existing diagnostic's output → **moneyball-diagnostics-and-tooling**.
- A test/audit is FAILING and you need triage → **moneyball-debugging-playbook**; check the refuted/do-not-re-flag lists in **moneyball-failure-archaeology** before filing anything.
- Measurement-theory concepts (reliability, validity, halo) → **psychometrics-reference**.

## Quick reference

```powershell
# ALWAYS cd to the repo root first (path contains spaces — quote it):
cd "<repo root>"

# Rung 1 — kernel tests (count grows — trust the run's own tail; exit 1 on failure):
python fec\tests\run_tests.py
#   pass tail: KERNEL TESTS — N passed, 0 FAILED

# Rung 3 — rank-authority parity (read-only audit mode; exit 1 on drift):
python fec\engine\compute_pillars.py
#   pass tail: PARITY: CLEAN

# Rung 5 — full-body audit (count grows — trust the run's own tail; ~2-4 min):
python fec\audit\audit_full.py
#   pass tail: FULL-BODY AUDIT — N passed, 0 FAILED  /  ALL MODULES CLEAN.
#   audit_full exits 1 on failure, 0 when clean; still gate on the tail TEXT as belt-and-braces.

# Rung 6 — score any prediction column against the user's gold labels (read-only):
python fec\stance\stance_eval.py model_stance
```

Three standing safety rules before running ANY of the above (details in moneyball-change-control):
1. **Check for Paul's live jobs first** (running python processes, artifact mtimes in the last few minutes). Run baselines serially, never concurrently with his work.
2. **Git worktrees isolate DATA — which makes them the WRONG place to run data-dependent work.** `fec/paths.py:7-8` defaults ROOT to the parent of the imported paths.py; code run in a worktree targets that worktree's EMPTY data plane, where reads die on missing inputs and writes land as throwaway artifacts. Run data-dependent work from the live tree, or set `MONEYBALL_ROOT` to it — and then writes DO hit live. (Corrected 2026-07-19; the previous version asserted the opposite. Verified against `fec/paths.py:7-8`.)
3. **Import == execution** for nearly every `fec/*.py`; most write artifacts at module load. Only `fec/tests/run_tests.py` and `fec/audit/audit_full.py` are on the standing casually-runnable allowlist (and even `audit_full.py` drops `_audit_tmp_optimize.json` / `_audit_tmp_frontier.json` into `data\system\audit_scratch\` — by design, gitignored; location corrected 2026-09-30, verified against `fec/audit/audit_full.py:173-176,212`). Read any other script before running it.

---

## 1. The evidence hierarchy for code changes

The documented protocol (`fec/tests/run_tests.py:5-6`, `README.md:63-64`): **change → kernel tests → run pipeline → zero rank delta → audit clean.** The full ladder, weakest to strongest:

| Rung | Question it answers | Tool | Pass signal |
|---|---|---|---|
| 1. Kernel tests | Do the math invariants still hold? | `python fec\tests\run_tests.py` | `... 0 FAILED`, exit 0 |
| 2. Chain runs | Does the full pipeline chain still execute? (size: see Provenance) | `python fec\run_pipeline.py` (MUTATES live tree) | every step prints OK |
| 3. Zero rank delta | Did member rankings move? | diff `ranks_python.json` pre/post; `compute_pillars.py` audit mode | 0/533 deltas; `PARITY: CLEAN` |
| 4. Byte-identical artifacts | Any hidden nondeterminism or feedback loop? | hash engine artifacts pre/post; double-run | identical hashes, or delta explained by a real input change |
| 5. Audit clean | Do all module/artifact invariants hold? | `python fec\audit\audit_full.py` | tail `ALL MODULES CLEAN.` |
| 6. External benchmarks | Do outputs still track human ground truth? | `stance_eval.py` vs gold labels; thresholds in §3 | at/above the documented numbers |

**Which rungs for which change:** any code change needs rungs 1 and 5 at minimum. Anything that touches a chain script or a consumed artifact needs 1–5. Anything that touches a classifier, label pipeline, or stance logic additionally needs 6. Changes that are *supposed* to move ranks get the delta explained member-by-member instead of asserted zero (see moneyball-change-control for who ratifies that).

### Rung 3: zero-rank-delta, precisely

"Rank" = a member's position 1–533 in `ranks_python.json`, the rank authority written by `compute_pillars.py --write` (the Excel workbook is only a *view* of it). Before a pipeline run, copy `ranks_python.json` to your scratchpad; after, compare `rank` and `score` per member. `python fec\engine\compute_pillars.py` (no flags = audit mode) independently recomputes and prints `PARITY: CLEAN`, exiting 1 on drift, stale authority, or missing authority (`fec/engine/compute_pillars.py:106-124`). The audit itself requires that string (`fec/audit/audit_full.py:261-263`).

### Rung 4: byte-identical artifacts and idempotency

**Idempotency** = running the pipeline twice on unchanged inputs produces byte-for-byte identical outputs. This was NOT always true: the S2-04 incident (a column-G feedback loop) had ~39 stance cells flipping on every consecutive run. The fix was proven with a double full-pipeline run: **12/12 tracked artifacts byte-identical — that is the ratified bar** (`AUDIT_FINDINGS_2026-07-02_RUN2.md:84-87`, commit f17dc2c). Consequence: **any artifact hash drift with no input change is now a real regression (severity S1)**, never "convergence noise".

Two legitimate explanations exist for a hash delta, and you must PROVE one before dismissing it:
- **Real input change** — prove it with the *input-purity test*: re-run the one deterministic engine against current on-disk inputs with output redirected to a temp path (e.g. `FRONTIER_OUT=<scratch>` for `budget_frontier.py`), then byte-compare. A deterministic pure function reproducing the new artifact byte-for-byte means the delta came from inputs, not your code (`AUDIT_FINDINGS_2026-07-03.md:33-44`; recipe in moneyball-proof-and-analysis-toolkit).
- **Two-run convergence** — `bipartisan.json` (the ONLY remaining feedback edge; written late in the chain and read by earlier steps) makes the run *after* a stance/network change legitimately shift engine outputs exactly once more. Col G is NOT part of this — it has been a pure output since the S2-04 fix @f17dc2c (`fec/stance/per_category_stance.py:9-13`); a "col-G convergence" story is the superseded excuse that masked the limit cycle.

Four determinism gates also live inside the audit (same seed/scenario → byte-identical stdout: `fec/audit/audit_full.py:144,160,186,268`; (corrected 2026-10-15; verified against `fec/audit/audit_full.py:144,160,186,268`)). If you add a randomized engine, it must use the CRN kernel (`moneyball_core.sm64`) so it gets the same property.

### Rung 5: the audit — gate on the tail text

`audit_full.py` exits 1 when any check fails and 0 when clean (`fec/audit/audit_full.py:2795-2799`). `legacy_workbook_audit.py` also exits 1 when any of its checks fails and 0 when clean (`main()` returns `1 if F else 0` at `fec/audit/legacy_workbook_audit.py:167`; `sys.exit(main())` at `:171`); only `audit_frontier.py` has no `sys.exit` call and still always exits 0. The chain therefore registers a failed `audit_full.py` step and aborts. Any script or gate you write around the audit must still parse the tail line `ALL MODULES CLEAN.` as belt-and-braces because older automation may assume exit 0. (Corrected 2026-07-19; verified against `fec/audit/audit_full.py:1198-1202` and zero `sys.exit` hits in both sub-audits. Sub-audit exit codes corrected 2026-09-30; verified against `fec/audit/legacy_workbook_audit.py:167,171`, `fec/audit/audit_frontier.py:91` and `fec/audit/audit_full.py:2795-2799`.)

Documented check counts go stale by design — the suite grows nearly every session (count grows — trust the run's own tail). The convention: **any FAILED is the finding; a higher count than documented is not** (`.claude/commands/fable-audit.md:35-36`).

---

## 2. The gold-label machinery

**Core law: machine labels are NEVER the label.** Model predictions (the fine-tuned DEBATE classifier, Claude-API prelabels) appear in gold files only as *context columns for the user to correct*. The label of record is always Paul's own adjudication. And per standing rule: **stance/press classification is Paul's domain — never relabel an item by model judgment; build override mechanisms instead** (`fec/stance/build_golden_labels.py:4-5` docstring; the Velázquez CFPB=Opponent / CCM=True-Neutral review is user-ratified CLOSED 2026-07-08 — do not re-flag).

Jargon: a **gold label** is a human-adjudicated ground-truth answer; **adjudication** is the user filling the `gold_*` columns; a **queue** is a stratified sample built for him to adjudicate; a **split** assigns each row to `train` (model may learn from it), `test` (held-out scoring only), or `goldeval` (a balanced eval set firewalled from training entirely).

### The flow

```
build_gold_queue.py ──────► gold_label_queue.csv      (press; balanced 312-row queue)
build_tweet_gold_queue.py ► tweet_gold_queue.csv      (social; 400-row queue)
        │                        │
        │        Paul fills the gold_* columns (his domain, in place)
        │                        │
        │        conflicts_review_*.csv  ◄─ conflicts exported for him;
        │                        │          he fills `your_decision`; latest file wins
        ▼                        ▼
build_golden_labels.py ───► cu_golden_labels.csv  +  cu_golden_labels_stats.json
                                 │
stance_eval.py ◄─────────────────┘   scores ANY prediction column vs gold
```

- `fec/stance/build_gold_queue.py` — stratified press queue: per-category quota (`PER_CATEGORY=32` across 19 press labels), member cap ≤3, rare class (`oppose`) first, known-confusion articles force-included as a permanent regression suite, `random.seed(7)` (`fec/stance/build_gold_queue.py:15,21-22,63-65`). Output columns: `model_*` (production prediction), `api_*` (Claude prelabel pass via `fec/stance/api_prelabel.py`), `gold_*` (**the user's**, pre-seeded from the API pass for correction-in-place).
- `fec/stance/build_tweet_gold_queue.py` — same design for social: 400 rows, member cap ≤2, platform quotas, forced hard slices `antibank`/`lowmargin`/`disagree`, tweet-form attribution classes (`member-own | rt-endorsement | third-party-voice`) (`fec/stance/build_tweet_gold_queue.py:3-19,25-29`).
- `fec/stance/build_golden_labels.py` — consolidates every user-labeled artifact into `cu_golden_labels.csv`, the authoritative set. Merge key = URL. Conflict policy: `unrelated` from the queue wins over any 3-class label; otherwise the curated AUGMENTED label wins for split-carrying rows; **every conflict is flagged in the `conflict` column — nothing is silently resolved** (`fec/stance/build_golden_labels.py:15-19`). User decisions from the newest `conflicts_review_*.csv` are AUTHORITATIVE and stamp `user-resolved: <label> (was aug=X queue=Y)` (`:57-67,75-78`). Queue-only rows get `split='goldeval'` so the balanced eval set can never contaminate training (`:19-20`).
- `fec/stance/stance_eval.py` — scores **any** prediction column against `gold_cu_alignment` in the queue: per-class precision/recall/F1, **macro-F1** as the headline (the unweighted mean of per-class F1 — used because classes are imbalanced, so raw accuracy over-rewards the majority class), per-channel and per-slice breakdowns, confusion matrix. Usage: `python fec\stance\stance_eval.py [pred_column]`, default `model_stance` (`fec/stance/stance_eval.py:3-8,12`). Verified read-only by inspection as of 2026-07-09 (no file writes anywhere in the script), but it is outside the standing two-script allowlist — read before running remains the rule.

### CRITICAL trap: the queue builders clobber adjudications

`build_gold_queue.py` and `build_tweet_gold_queue.py` write their output CSV **with empty `gold_*` columns** (`fec/stance/build_gold_queue.py:93-106`, `fec/stance/build_tweet_gold_queue.py:93-98`). Re-running either one overwrites the queue file in place and would **destroy every adjudication Paul has made** (312 press + 400 tweet rows as of 2026-07-09). Never re-run them casually; a new sampling round is a user decision, and the old queue must be archived first. These CSVs are the one place in the repo where hand-editing a generated file is by-design — but ONLY the `gold_*` / `your_decision` columns, and only by Paul.

### Gold inventory (as of 2026-07-09, counted on the live tree)

All files live at the data root `<repo root>\` (gitignored — they are NOT in git; losing them loses user labor):

| File | Rows | Adjudicated | Notes |
|---|---|---|---|
| `cu_golden_labels.csv` | 760 | all (user-labeled by construction) | splits train 456 / test 87 / goldeval 217; labels support 377 / neutral 240 / oppose 133 / unrelated 10; 94 conflict-flagged of which 92 `user-resolved:` |
| `gold_label_queue.csv` | 312 | 312 (100%) | press queue; carries the Burnham factorization (`gold_target` / `gold_stance_toward_target` / `gold_target_cu_valence` / `gold_attribution`) |
| `tweet_gold_queue.csv` | 400 | 400 (100%) | social queue; fully adjudicated (was 0/400 on 2026-07-02) |
| `cu_golden_labels_stats.json` | — | — | machine summary written by `build_golden_labels.py` |
| `CU_Confusion_Articles.xlsx` | — | — | known-confusion regression set, force-included in every press queue |

Upstream user instrument (NOT in either tree): `<local data dir>\cu_stance_label_set_AUGMENTED.xlsx` — hardcoded input of `build_golden_labels.py:32`. It is machine-local and irreplaceable; if it disappears, the golden set cannot be regenerated (the existing `cu_golden_labels.csv` becomes the artifact of record). See §5.

### The audit's GOLD checks (what "gold hygiene" means mechanically)

`fec/audit/audit_full.py:152-168` enforces, on every audit run:
- every label is in the vocabulary `{support, oppose, neutral, unrelated}` and the set has ≥700 rows;
- the user's split is preserved EXACTLY: `train==456` and `test==87`, with `goldeval>0` (these literals are pinned — a regenerated golden set that moves them is a finding, not a reason to edit the check);
- no duplicate URLs;
- **every conflict is flagged, not silently resolved** — a compliant `conflict` value either contains `->` (unresolved, awaiting the user) or starts with `user-resolved:` (his decision, with the trail inline). Any other format fails.

Plus the train/test text-hash leak check: MD5 of text/title/stance-span must not collide across splits beyond the known bound of 4 same-article collisions (`fec/audit/audit_full.py:265-276`). Rule when refreshing labels: same text ⇒ same split.

---

## 3. Acceptance thresholds that exist (do not invent new ones silently)

These are the documented, reproduced numbers. A change that degrades one of these is a regression even if all other rungs pass. New thresholds require the change-control process.

| What | Threshold / recorded value | Where documented |
|---|---|---|
| Press stance classifier (production, fine-tuned DEBATE) | acc **0.839** / macro-F1 0.835 / κ 0.742 on the held-out human-gold test (n=87, 36 never-seen members) | `AUDIT_FINDINGS_2026-07-02_RUN2.md:118` |
| Same, leak-free re-test (after the 4-collision split leak was removed) | **84.7%** / 0.816 macro-F1 — headline IMPROVES leak-free | `DEEP_AUDIT_REPORT_2026-07-02.md:28` |
| Classical baseline any new press model must beat | LinearSVM macro-F1 0.792 on the untouched test | `AUDIT_FINDINGS_2026-07-02_RUN2.md:121` |
| Tweet stance stack (production social labels) | 0.855 acc / 0.819 macro-F1, honest 5-fold out-of-fold vs the 400 user golds (oracle ceiling 0.872) | `fec/stance/tweet_stance_stack.py:4,11` |
| Stance-dynamics imputation gate | sign agreement on masked cells **> 0.55** (else audit FAIL) | `fec/audit/audit_full.py:140-143` |
| Train/test split leak | ≤ 4 known same-article collisions | `fec/audit/audit_full.py:275-276` |
| Golden-set integrity | vocabulary, 456/87 splits, goldeval firewall, no dup URLs, conflicts flagged (`->` or `user-resolved:`) | `fec/audit/audit_full.py:152-168` |
| Voice-ES display artifact | must match the recorded look exactly, `heldout_r == +0.208` | `fec/audit/audit_full.py:342-347` |

"κ" = Cohen's kappa, agreement corrected for chance; "out-of-fold" (OOF) = each row scored by a model that never trained on it. Numbers like the +0.208 voice-ES correlation are **frozen history from consumed looks** — the audit pins them so nobody silently recomputes and overwrites a recorded result (see moneyball-research-methodology for why, and moneyball-docs-and-claims for the exact caveats each claim must carry — e.g. ES's mandatory gender-confound caveat).

---

## 4. How to add a kernel test and how to add an audit check

### Adding a kernel test (`fec/tests/run_tests.py`)

There is no test framework. The whole suite is inline `ok(name, cond, detail)` calls that tally pass/fail and print one line each; the file exits 1 on any failure (`fec/tests/run_tests.py:11-14,1187`; (corrected 2026-10-15; verified against `fec/tests/run_tests.py:11-14,1187`)). To add a test, append `ok()` calls in the right `print('[section]')` block, before the final tail line. Real existing test to copy (the say-do cap-law block, `fec/tests/run_tests.py:225-283`; (corrected 2026-10-15; verified against `fec/tests/run_tests.py:225-283`)):

```python
print('[say-do gate + delivery discount]')
# cap law invariants on a synthetic member (no workbook/file dependency: inject all three caches).
MC._CORR={'__test__':{'sponsored':{'CFPB'},'advanced':{'CFPB'}}}
MC._VOTECORR={'__test__':{'Payments'}}
MC._JURISCORR={'__test__':{'finance (full)'}}
_cm={'CFPB':'Champion','Payments':'Champion','Interchange':'Defender', ...}
_g,_cap,_prov,_cor=MC.cap_uncorroborated('__test__',_cm)
ok('authored Champion survives + earns proven (Path A)', _g['CFPB']=='Champion' and ...)
...
MC._CORR=None; MC._VOTECORR=None; MC._JURISCORR=None   # restore lazy loaders
```

Rules distilled from that template:
1. **`ok(name, cond, detail)`** — `detail` prints only on failure; put the observed value in it.
2. **Prefer synthetic, file-independent fixtures.** The say-do tests monkey-patch the kernel's lazy caches (`MC._CORR` etc.) and **must restore them to `None`** afterward so later tests reload real data. Follow this pattern exactly when testing anything cache-backed.
3. Test the **invariant/rung, not a named member** — [example values withheld pending disclosure review] legitimately changed rungs once and broke a name-pinned check (comment at `fec/audit/audit_full.py:32-33`).
4. Verify by running the suite: the tail count should increment and stay `0 FAILED`. Documented expected-counts are dated snapshots (count grows — trust the run's own tail) — do not "fix" your test to match an old count.
5. The suite reads its resolved data plane (roster, network) via `paths.py` — run it from the live tree and check for live user jobs first.

### Adding an audit check (`fec/audit/audit_full.py`)

Same non-framework: `ck(name, cond, detail)` appends to pass/fail lists (`fec/audit/audit_full.py:30-32`; (corrected 2026-10-15; verified against `fec/audit/audit_full.py:30-32`)). There is no registration step — adding a `ck()` call anywhere before the tail *is* the registration. Adding checks is free; the only count floors are on the two sub-audits (`audit_full.py:44-46` requires `legacy_workbook_audit.py` ≥22 and `audit_frontier.py` ≥15 passed with 0 FAILED — so a silently-vanished check fails loudly).

**Template A — a look-consequence / regression guard** (the round-3 N-slot guard, `fec/audit/audit_full.py:239-244`):

```python
# ROUND-3 N-slot guard (2026-07-09): the susceptibility N-slot must be the behavioral reactivity
# read (n_slot='behavioral'); a silent RECEPT_N=text revert or a reactivity-coverage collapse
# would sail through the basis gate above. Coverage floor 150 (currently 207/533).
_nsl=_rc.get('n_slot'); _nsrc=sum(1 for v in _rc.get('members',{}).values() if v.get('n_source')=='reactivity')
ck('receptivity N-slot = behavioral reactivity (round-3; no silent text revert)',
   _nsl=='behavioral' and _nsrc>=150,'n_slot=%s reactivity_members=%d'%(_nsl,_nsrc))
```

**Template B — a schema guard for an artifact** (the run-5b big5 guard, `fec/audit/audit_full.py:281-285`):

```python
if os.path.exists(B+r'\big5_llm_opus.json'):
    _b5=json.load(open(B+r'\big5_llm_opus.json',encoding='utf-8')).get('traits',{})
    _bad=sum(1 for d in _b5.values() if not all(k in d for k in ('O','C','E','A','ES')) or not d.get('n_chunks'))
    ck('big5_llm artifact schema (5 traits + n_chunks per member, coverage >=400)',
       len(_b5)>=400 and _bad==0, '%d members, %d malformed'%(len(_b5),_bad))
```

Rules distilled:
1. **Every NEW artifact REQUIRES a schema guard.** The run-5b lesson: the psych/media artifacts shipped with ZERO audit coverage — a truncated or malformed file would have sailed through (`fec/audit/audit_full.py:278-280`). Minimum content: required keys per record, a coverage floor (member/edge count), and a malformed-record count, with the observed numbers in `detail`.
2. **Comment every check with its date and incident rationale** — that is the house style throughout the file, and it is what stops a future maintainer from deleting a guard whose reason is invisible.
3. **Skip-if-absent vs mandatory:** artifacts built out-of-chain get `if os.path.exists(...)` gating (freshness is meaningless mid-crawl). Artifacts a chain step MUST produce get an explicit `else: ck(..., False, 'missing — ...')` branch — see `fec/audit/audit_full.py:249-251`, which also records the lesson that the else-branch's check NAME must match what it actually tests (a mislabeled else fired the wrong finding for months).
4. **Check what production actually produces.** The 07-04 S2-01 incident: the audit read a stale on-disk `lt_priming.json` and passed while the feature was stranded on an unmerged branch. Where feasible, regenerate in-run (redirect output with the `*_OUT` env dials so you never clobber production — the `_audit_tmp_*.json` pattern at `audit_full.py:181,266`; (corrected 2026-10-15; verified against `fec/audit/audit_full.py:181,266`)) or assert freshness against the input's mtime (the media-blend pattern, `audit_full.py:427-431`; (corrected 2026-10-15; verified against `fec/audit/audit_full.py:427-431`)).
5. **Never tune a floor to pass your own change.** The 07-07 H-3 incident: a headcount floor was nudged 40→35 to green-light the auditor's own edit. Prefer tuning-free properties (monotonicity, coherence, reconstruction) over magic numbers; when a number is unavoidable, derive it and write the derivation in the comment.
6. **Argument-order trap:** `run_tests.py`/`audit_full.py`/`audit_frontier.py` use `ok/ck(name, cond, detail)` but `fec/audit/legacy_workbook_audit.py:45` (`ok()` nested in `main()`) uses `ok(cond, msg)`. Copy-pasting a check between files silently inverts it.
7. Some thresholds are **deliberately tolerant after false alarms** (e.g. the frontier defend-skew at 0.92, split-leak ≤4). Check moneyball-failure-archaeology's refuted lists before "tightening" one.
8. Verify by running `python fec\audit\audit_full.py` and confirming the new check prints `OK` and the tail stays `ALL MODULES CLEAN.` — the exit code now catches `audit_full.py` failures, but the tail remains the belt-and-braces gate (§1, rung 5).

---

## 5. Validation data hygiene

Standards for any evaluation you build, all with live exemplars in the repo:

- **Fingerprint your inputs (SHA-256).** A **fingerprint** is a cryptographic hash of a file's bytes — if the hash matches, the file is byte-identical to what was recorded. The pattern of record is `fec/members/b5_n_matrix.py:28-31,43-55`: a `PIN` dict recording each input's SHA-256 plus row counts (`speeches: 234827, posts: 29098`), a streaming `sha()` helper, and a `fingerprints()` function the run compares against `PIN` — **the evaluation ABORTS without consuming its look if any mismatch** (docstring `:9-11`; the pinned values are also written into the locked prereg, `big5_n_matrix_prereg.md:66-71`). For engineering QA the same idea applies at lower ceremony: record the hash/mtime/row-count of every input your eval reads, print them in the output, and refuse to compare numbers computed from different vintages.
- **Pin your roster.** Every comparison must run on an explicitly recorded member set, never "whoever has data today" (which drifts as collectors run). Exemplar: `MEM = 456 (exact)`, `MEM_N = 201 (exact)` recorded pre-lock with the rule that all comparison bars share the single roster (`big5_n_matrix_prereg.md:58-65`).
- **Party and gender as standard controls.** Members' text and behavior differ systematically by party and gender, so any member-level correlation can be secretly measuring "is a Republican" or "is a woman" instead of the construct. Standard practice is to load both covariates and residualize them out (subtract what party/gender alone predict) before claiming an effect. Exemplar: `fec/members/b5_n_matrix.py:68-79` — gender from `fec/legislators.csv` keyed by bioguide ID via `congestion.json`, party from the roster, both fed into the Frisch–Waugh partial (`:84-90`). This is a standing requirement because the ES instrument was found gender-confounded after the fact (its validity claim now carries a mandatory caveat — see moneyball-docs-and-claims). Theory in psychometrics-reference.
- **Pin your seeds.** Sampling and folds are seeded constants, never wall-clock: `random.seed(7)` in both queue builders; the locked OOF seed lists `SEEDS17=[7,17,29,43,61]` and permutation seed `20260710` in `b5_n_matrix.py:24-25,84`.
- **Know which inputs are irreplaceable.** Gold CSVs live in the gitignored data root — they are user labor, not regenerable code. The AUGMENTED label workbook is hardcoded at `<local data dir>\cu_stance_label_set_AUGMENTED.xlsx` (`fec/stance/build_golden_labels.py:32`) — machine-local, outside both trees, no producer. Treat all of these like `Draft Systems`: back up before any operation that touches them, and never let a script rewrite one non-atomically (the S2-01 run-2 fix exists because a crash mid-write could have destroyed the user's override registry).
- **Same text ⇒ same split.** When labels are refreshed, identical article text must never straddle train/test (the SEV1-2 leak; audit bound §3).

---

## 6. The no-silent-caps norm

Any coverage bound, cap, fallback, or skip must be VISIBLE — printed at run time and, where load-bearing, floored in the audit. The failure mode this kills: `except FileNotFoundError: T={}` once silently turned the whole personality layer off while everything printed success (S2-02, 2026-07-02).

How the norm is embodied (copy these patterns):

- **Loud `!!` guards on missing inputs, never bare except.** `fec/members/receptivity_layer.py:48,72,78,103`: every optional input that is absent prints a `!!` line naming the file, the consequence, and the command to fix it (`'!! big5_traits.json MISSING/EMPTY — every member falls to trait-neutral (personality layer OFF). Run big5_traits.py.'`). Per-member neutral fallback is by design; whole-file-missing must scream.
- **Print coverage counts in the final summary line.** `receptivity_layer.py:167` prints `RECEPTIVITY: %d members | ... | trait-neutral(lowconf) %d`; the persona channel prints its member coverage and weight (`:104`). This matters doubly because `run_pipeline.py` shows only each step's LAST stdout line — the summary line is the entire runtime visibility of a chain step.
- **Named, printed caps.** Cost/volume caps are named dials that announce themselves: `NARR_MAX` (narrative bill cap, `fec/weekly_refresh.py:98-103`), `REF_DYAD_CAP` (LLM-scored mention windows per dyad), `MEMBER_CAP` printed in every gold-queue summary (`build_tweet_gold_queue.py:107`). New dials go through the add-a-dial checklist in moneyball-config-and-flags.
- **Audit floors mirror the printed coverage.** Receptivity must cover 533 members with multipliers inside documented caps (`fec/audit/audit_full.py:186-191` — the section comment is literally "coverage + documented caps"); reactivity coverage ≥150; big5 ≥400; reference edges ≥1000. When you add a coverage print, add the matching floor.

**Checklist when you introduce any bound:** (1) name it (constant or env dial); (2) print the bound AND the achieved coverage in the script's summary line; (3) add an audit floor with the incident-comment; (4) decide and document the failure direction — evidence gates fail OPEN (missing say-do evidence must never wrongly cap a member, `moneyball_core.py:222-224`), spend gates fail CLOSED (an unparseable cost estimate must never spend money). Know which one yours is.

---

## Provenance and maintenance

Written 2026-07-09 against the live tree and a local working branch (HEAD 88a7048). Volatile facts and how to re-verify each (run from the repo root, path quoted):

```powershell
cd "<repo root>"

# Kernel test count + pass state — read the tail line (count grows — trust the run's own tail):
python fec\tests\run_tests.py

# Audit check count + pass state — read the tail line (count grows — trust the run's own tail; audit_full exits 1 on failure):
python fec\audit\audit_full.py

# Protocol wording still documented:
Select-String -Path fec\tests\run_tests.py -Pattern 'zero rank delta'
Select-String -Path README.md -Pattern 'zero rank delta'

# Idempotency bar + input-purity method still on record:
Select-String -Path 'AUDIT_FINDINGS_2026-07-02_RUN2.md' -Pattern '12/12'
Select-String -Path 'AUDIT_FINDINGS_2026-07-03.md' -Pattern 'input-purity'

# GOLD checks incl. the 'user-resolved:' conflict format and 456/87 split pins:
Select-String -Path fec\audit\audit_full.py -Pattern "user-resolved|_sp.get\('train'\)"

# Gold inventory counts (760 / 312 / 400 as of 2026-07-09):
(Import-Csv 'cu_golden_labels.csv').Count
(Import-Csv 'gold_label_queue.csv'  | Where-Object { $_.gold_cu_alignment -ne '' }).Count
(Import-Csv 'tweet_gold_queue.csv'  | Where-Object { $_.gold_cu_alignment -ne '' }).Count

# Thresholds: press .839 headline, leak-free 84.7, tweet stack .855/.819, imputation .55 gate:
Select-String -Path 'AUDIT_FINDINGS_2026-07-02_RUN2.md' -Pattern '0\.839'
Select-String -Path 'DEEP_AUDIT_REPORT_2026-07-02.md' -Pattern '84\.7'
Select-String -Path fec\stance\tweet_stance_stack.py -Pattern '0\.855'
Select-String -Path fec\audit\audit_full.py -Pattern 'sign_agreement'

# Templates still at cited locations (N-slot guard, run-5b schema guards, say-do kernel block):
Select-String -Path fec\audit\audit_full.py -Pattern 'ROUND-3 N-slot guard|run-5b guards'
Select-String -Path fec\tests\run_tests.py -Pattern 'say-do gate'

# Fingerprint/roster-pinning exemplar:
Select-String -Path fec\members\b5_n_matrix.py -Pattern 'PIN =|def sha|def fingerprints'
Select-String -Path big5_n_matrix_prereg.md -Pattern 'SHA-256'

# Downloads-hardcoded gold instrument (machine-local input):
Select-String -Path fec\stance\build_golden_labels.py -Pattern 'Downloads'

# Queue builders still write blank gold_* columns (the clobber trap):
Select-String -Path fec\stance\build_gold_queue.py -Pattern "gold_label_queue.csv"

# No-silent-caps exemplars:
Select-String -Path fec\members\receptivity_layer.py -Pattern '!!'
Select-String -Path fec\audit\audit_full.py -Pattern 'coverage \+ documented caps'
```

Facts most likely to drift: the two check counts (grow with every guard); the gold inventory (grows with each adjudication round — tweet queue went 0/400 → 400/400 between 2026-07-02 and 2026-07-09); the split pins 456/87 (change ONLY via a user-directed label refresh, at which point the audit literals move with it in the same commit); the threshold table (any new number arrives via moneyball-change-control and a documented eval, never silently).

Last measured (dated — counts drift, so trust each run's own tail): `fec/tests/run_tests.py` 247 passed / 2 FAILED in LIVE on 2026-09-20 (standing reds `test_bill_collision_guards`, `test_make_staffer_network_html`); `fec/audit/audit_full.py` 559 passed / 9 FAILED in LIVE on 2026-09-19 (after that day's membership refresh) (both recorded in the Project Brain STATE (local Project Brain decisions repo; not published)); the chain has 80 `CHAIN` entries, 79 run by default (`fec/run_pipeline.py:45-302`), counted 2026-09-30 at main 25eefa3fc.
