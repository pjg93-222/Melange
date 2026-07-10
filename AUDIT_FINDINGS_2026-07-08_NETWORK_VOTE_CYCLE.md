# Data-Integrity Audit — Co-sponsor Network / Vote DB Collection / New-Cycle Collection & DB Integrity

**Date:** 2026-07-08
**Scope (as requested):** (1) Co-sponsor network computation, (2) Vote database collection methods, (3) New-cycle collection and database integrity.
**Looking for:** irrelevant loops, dead code, dead-ends, redundancy, errors, duplicates.
**Method:** 7 parallel deep-read finders (3 areas × correctness/integrity lenses + cross-cutting) → **adversarial verification of every finding** (each finding independently re-checked against code + live data under DATA ROOT, with a mandate to *refute*) → dedup + synthesis. 49 raw findings → **44 survived verification → 26 after dedup**; **5 refuted**. Several top items were also independently re-confirmed by hand (noted ✔hand).

> Note on roots: code was read from the worktree (`.../worktrees/eager-wright-c73612/fec`); data existence/columns/DB were checked at **DATA ROOT** = `C:\Users\pgoff\OneDrive\Desktop\Melange Systems` (where `paths.py` points at runtime). Some live files (e.g. `b5_behavioral_instrument.py`, `HSall_members.csv`, `voteview_consistency.json`) exist **only** at DATA ROOT and are untracked — see V-5 / C-3.

---

## Executive summary

Two systemic defects dominate:

1. **Kernel divergence (network).** The cascade activation kernel is hand-rolled in three engines (`cosponsor_route`, `lt_priming`, `scenario`) instead of `MBC.build_P`, and every copy silently drops the `edge_mult` receiver-susceptibility factor. 530/533 members have `edge_mult ≠ 1.0`, so activation probabilities diverge up to **~13%/edge**; `lt_priming` runs unattended in the pipeline.
2. **Severed vote path (vote DB).** `vote_by_category.py` is orphaned from every orchestrator **and** crashes because its input CSV is gone, yet its stale Jun-26 output still feeds the rank authority and the say-do gate. The same script also last-write-wins-clobbers 107 multi-category bills, mis-signs Neutral CFPB bills, and silently drops all `J.Res` votes.

Supporting integrity issues: an edge-key convention mismatch double-writes 4 pairs; `press_engagement`/`press_hcoi` layers freeze at Jul-01 while `weekly_refresh` rebakes them into every fresh AUG; AUG files accumulate unbounded and are chosen by fragile mtime; GATE-2 self-completes even when post-rescore steps fail; CREC re-fetches ~1170 non-session dates forever; the `speeches` table has no uniqueness constraint. **Fix the kernel (N-1) and the vote path (V-1) first.**

Severity tally: **HIGH 7 · MEDIUM 12 · LOW 7.**

---

## Fixes applied (2026-07-08/09, branch `claude/magical-booth-f272da`)

All **7 HIGH** findings addressed, plus the vote-scoring MEDIUMs that live in the same loop (V-3/V-4) and a LOW diagnostic (V-6). Verification: all edited files `py_compile` clean; **kernel tests 37/37 pass**; `audit_full` **64/65 pass** (the one failure — `frontier (11) sub-audit` — is the *pre-existing* stale `electoral_plays.json` issue, unrelated to these edits, awaiting a `build_electoral_plays.py` re-run); the new V-1 freshness check reports green.

| Finding | Change | Verified |
|---|---|---|
| **N-1** | `cosponsor_route.py`, `lt_priming.py`, `scenario.py` now delegate to `P=MBC.build_P(adj)` (adds `em(v)` susceptibility); removed dead `BETA/bpf/prt/bio2name`/`cpf` loads | build_P smoke-test: em applied (P 0.1429→0.1387, asymmetric by receiver); kernel tests 37/37 |
| **N-2** | `build_multilayer_network.py:61,73` engagement/HCoI edges now keyed by sorted `k` (matches social lookup) | logic + verifier simulation (eliminates the 4 dup pairs) |
| **V-1** | `vote_by_category.py` now guards the missing external CSV with an actionable `sys.exit`; `audit_full.py` gains a `vote_category_lean.json` freshness check | new audit check runs green |
| **V-2** | `bill2cat` → `defaultdict(set)`; vote loop aggregates into **every** category a bill maps to | unit test: (118,H,7036)→{1,3,9,17} |
| **V-3** | `rc_bill` regex aligned to `billkey` grammar → J.Res/H.J.Res parse instead of dropping | unit test: S.J.Res.32→('S',32) (was None) |
| **V-4** | CFPB sign: `+1 if '1' else -1 if '-1' else 0(skip)` — Neutral(0)/unknown no longer mis-signed | verified vs `cfpb_bill_directions.csv` (Directions 1/0/-1 = 49/6/5) |
| **C-1** | GATE-2 writes `gate2.done` / self-unregisters **only** when co_appearance+desk+combined+audit all `ok`; else returns to retry | compiles; logic reviewed |
| **C-2** | `weekly_refresh.py` runs `press_engagement_layer.py`+`press_hcoi.py` before `build_multilayer_network` | compiles; inputs confirmed order-independent (external R CSV) |
| **C-3** | Tracked the untracked consumer `fec/b5_behavioral_instrument.py` into the repo (verbatim; prereg method-locked) | copied + compiles |

**Regeneration required for the data-side fixes to take effect** (code lands on the branch; artifacts are rebuilt by the live pipeline — your domain): N-1/N-2 change `lt_priming.json`, `cosponsor`/`scenario` outputs and the next `AUG` network on the next `run_pipeline`/`weekly_refresh`; V-2/V-3/V-4 only take effect once the roll-call CSV is restored and `vote_by_category.py` is re-run.

### N-1 follow-up — dashboard JS↔Python mirror (needs your call)
The dashboard recomputes the kernel in JS (`make_dashboard_html_00.tpl:279`, `PE[u][v]=wc/(wc+6)`) **without** `edge_mult`, and the bundle ships no per-member `edge_mult`. Before N-1, the JS mirrored the (un-em) Python engines; now the Python authority is em-aware, so the interactive `prime()`/cascade/route JS lags it by up to ~13%/edge (the same gap the cascade JS already had vs `build_P` consumers). **Fully closing N-1's Python↔JS parity** means shipping `edge_mult` into the bundle and applying it at tpl:279 — a dashboard change with its own preview verification, deliberately **not** done in this pass. Recommend doing it as the immediate follow-up.

### Provenance investigation (the untracked/missing data files)
- **`cu_rollcall_votes_clean.csv` (V-1):** gitignored data; **no producer anywhere** (only `vote_by_category.py` reads it; the `git -S` hits are that script's own history). Not in `backups/`. `vote_category_lean.json` (628 members incl. former members, mixed name formats) was built from an externally-cleaned roll-call export since removed. **Not restorable from the repo — it is your external data-collection input** (likely a Quorum/congress.gov/ProPublica export you clean externally). The code is now correct-when-restored and fails loudly meanwhile.
- **`HSall_members.csv` + `voteview_consistency.json` (C-3/V-5):** **no writer exists** (tracked or untracked) — produced by an ephemeral/manual step during the ES-instrument prereg (`d630fe3`). `HSall` = the raw all-119-congress Voteview download; `voteview_consistency.json` = HS117-119 vote-weighted gmp+dim1 keyed by bioguide (documented in its own `note`; internally consistent — see refuted R-3). The **consumer** `b5_behavioral_instrument.py` is now tracked; the **producer** still needs to be created/committed (a small derivation `HSall → voteview_consistency.json`). I did **not** fabricate it — the exact pooling recipe is yours to confirm, and per your "investigate" instruction this is flagged, not built. Several other untracked `fec/` scripts exist alongside it (`b5_emb_build.py`, `b5_round4_eval.py`, `b5_textc_confirm.py`, `big5_ctcm2.py`, `c_prereg_test.py`) — a separate tracking decision.

---

## Area 1 — Co-sponsor network computation

### N-1 · HIGH · redundancy → wrong activation probs · CONFIRMED ✔hand
**Cascade kernel re-implemented in 3 engines, dropping the `edge_mult` susceptibility factor.**
Sites: `fec/cosponsor_route.py:26`, `fec/lt_priming.py:30`, `fec/scenario.py:37` vs canonical `fec/moneyball_core.py:136`.
All three compute `P = (w*cpf)/(w*cpf+6.0)` inline, omitting the `em(v)=rc(v,'edge_mult')` term that `MBC.build_P` applies (and that `budget_frontier`, `per_topic_coalition`, `salience_shock`, `kb_benchmark` all use). `member_receptivity.json` has `edge_mult ≠ 1.0` for **530/533** members (range 0.873–1.134) → these copies diverge from the cascade kernel by up to ~13% per edge. `lt_priming` runs unattended (`run_pipeline.py:25`), silently feeding a divergent kernel into `lt_priming.json` despite its own "one diffusion law everywhere" comment.
**Fix:** replace each inline P-dict with `P = MBC.build_P(adj, physics=MBC.cpf_diffusion)` (make the `edge_mult` choice explicit and identical to the cascade).

### N-2 · HIGH · duplicate → corrupted ties · CONFIRMED
**Engagement/HCoI edges stored under the unsorted key while the social lookup uses the sorted key → pairs written twice.**
Sites: `fec/build_multilayer_network.py:61,73,91`; folded by `fec/moneyball_core.py:114`.
Engagement (line 61) and HCoI (line 73) are stored under raw `(a,b)`; cosponsor and the social branch (line 91, `k=(min,max)`) use the sorted key. When a reverse-sorted engagement/HCoI pair also appears in `social_interactions.json`, line 91 misses and inserts a **second** row. Reproduced on live data: **4 reverse-dup pairs** (e.g. `P000617/M000133` engagement 0.2402 + social 0.1056). `load_network` then mean-averages the two weights — corrupting the tie **and** skipping the intended social-reinforcement multiplier (line 93).
**Fix:** change lines 61 and 73 to `edges[k]=...` so every layer keys by the canonical sorted `k`.

### N-3 · MEDIUM · duplicate/dead-end · PLAUSIBLE
**AUG artifacts accumulate unbounded and are selected by fragile filesystem mtime.**
Sites: `fec/build_multilayer_network.py:31,32,100`; `fec/moneyball_core.py:107`.
A date-stamped AUG xlsx is written every Sunday with no cleanup; DATA ROOT already holds 4 AUG + 7 obsolete base files, all in the `max(glob, key=getmtime)` pool. The 7 base files carry OneDrive-rewritten mtimes ~11µs apart (no real chronology), so any sync/backup touch that bumps an older file promotes the wrong base or serves a stale AUG **with no error**. Idempotency rests on a single `'AUG' not in basename` substring test.
**Fix:** prune to a rolling window after each write; select the source by embedded filename date / manifest pointer (not mtime); assert the base has no Provenance sheet.

### N-4 · MEDIUM · silent degradation · CONFIRMED
**A missing layer JSON silently degrades the network with no signal in artifact or audit.**
Sites: `fec/build_multilayer_network.py:62`; `fec/moneyball_core.py:107`; `fec/audit_full.py:131`; `fec/weekly_refresh.py:32`.
Each optional layer is skipped on `FileNotFoundError` with only a `print`, then the AUG workbook is written unconditionally; `load_network` picks the newest AUG with no completeness check. `audit_full` never references the AUG/Provenance artifact, and the weekly log keeps only stdout's last line — so a failed producer ships a network missing an entire edge layer while the pipeline stays green.
**Fix:** record per-layer edge counts into the Provenance sheet and add an `audit_full` check that each expected layer has a non-zero count.

### N-5 · LOW · redundancy · CONFIRMED
**`sna_layout` SUMS reverse-dup edge weights instead of mean-symmetrizing like the shared loaders.** `fec/sna_layout.py:16` (`G[a][b]['weight']+=wt`) gives the 41 documented reverse-dup pairs ~2× weight vs the mean-symmetrizing peer loaders. Impact confined to `sna_compact.json` layout geometry (cosmetic), but it's a 4th drifted copy of reverse-dup handling. **Fix:** reuse `MBC.load_network()` for the adjacency.

### N-6 · LOW · error (latent) · PLAUSIBLE
**Reverse-dup mean-symmetrization is order-dependent for 3+ duplicate rows.** `moneyball_core.py:114` folds dup rows with a pairwise running mean (`w=(adj[a][b]+w)/2`), so a pair appearing 3+ times yields `w1/4+w2/4+w3/2`, not the true mean. Non-triggering today (all dup pairs are multiplicity-2). **Fix:** accumulate `(sum,count)` and divide once, or assert ≤2 rows/pair.

### N-7 · LOW · dead_code/efficiency · CONFIRMED ✔hand
**`cosponsor_route`: recomputed `cpf`, O(n²) Pareto, dead loads.** `cpf(u,v)` evaluated twice per edge (line 26); O(n²) pairwise Pareto (harmless at K=5, line 79); `BETA=1.5` (24), `bio2name` (14), `bpf` (22), `prt` (23) assigned once and never read; header comment (19) cites `+4` while code uses `+6.0`. No numeric effect, but leftover `BETA/bpf` dials falsely imply a bridge-amplification knob. **Fix:** delegate P to `MBC.build_P`, delete the dead loads, correct the comment.

---

## Area 2 — Vote database collection methods

### V-1 · HIGH · dead_end → frozen live input · CONFIRMED ✔hand
**Vote-category refresh path fully severed: producer orphaned + crashes, stale output still feeds the rank authority and say-do gate.**
Sites: `fec/vote_by_category.py:42`; `fec/per_category_stance.py:15`; `fec/moneyball_core.py:240`; `fec/run_pipeline.py:19`.
`vote_by_category.py:42` reads `votes/cu_rollcall_votes_clean.csv`, which **exists nowhere under DATA ROOT and is written by no script** → `FileNotFoundError` before any output. It is also absent from `run_pipeline.py`'s CHAIN and from `weekly_refresh.py`, so its sole output `vote_category_lean.json` is **frozen at Jun-26** yet remains a live input to `per_category_stance` (rank authority) and `moneyball_core` say-do gate "Path V". New roll-call votes cannot enter the model via the intended path. (Path V fails open — no fail-cap corruption — but the vote signal ages indefinitely. `AUDIT_ROADMAP.md:92` already lists this script as legacy/not-in-pipeline; the gap is that its *output* is still consumed.)
**Fix:** restore/repoint the upstream roll-call cleaner that writes the CSV, wire a working `vote_by_category.py` into the CHAIN before `per_category_stance`, and add an `audit_full` freshness check on `vote_category_lean.json`.

### V-2 · HIGH · duplicate → wrong category attribution · CONFIRMED
**`bill2cat` last-write-wins clobber: 107 multi-category bills credited to one arbitrary category.**
Sites: `fec/vote_by_category.py:24,60`.
`bill2cat[bk]=sn` (line 24) is a last-write-wins assignment inside the archive iteration. On the live archive, **107 of 468** bill keys span multiple Section categories (e.g. `(118,H,7036)→{1,3,9,17}`); only the last-in-row-order category survives, corrupting the per-category coverage counter and the signed per-member lean in `vote_category_lean.json`. (None of the 107 involve an ANTI category `{4,14}`, so lean *sign* is unaffected — the defect is category attribution.)
**Fix:** make `bill2cat` a `defaultdict(set)`, `bill2cat[bk].add(sn)`, and aggregate each vote into every category the bill belongs to.

### V-3 · MEDIUM · redundancy → dropped votes · CONFIRMED
**Bill-id regex triplicated with a drifted variant that silently drops all `J.Res` roll-call votes.**
Sites: `fec/vote_by_category.py:9,30,38`.
Lines 9 and 30 are byte-identical (include the resolution group); line 38 (`rc_bill`) drops the `(?:Res\.?)?` group and returns `None` for `S.J.Res.32`/`H.J.Res.66` — the majority of `cfpb_bill_directions.csv` and 388 archive rows. `rc_bill` feeds the roll-call match (lines 46/47 skip on `None`), so **every `J.Res` final-passage vote is silently skipped** even though the bill is in `bill2cat`/`cfpb`, under-counting resolution votes per `(member,category)`. Both parsers also discard the bill-TYPE group (H.R.N / H.J.Res.N collision risk).
**Fix:** extract one shared bill-key helper that includes the normalized bill TYPE and call it from all three sites.

### V-4 · MEDIUM · error · PLAUSIBLE (live impact blocked by V-1's missing CSV)
**CFPB direction signing: Neutral bills scored anti-CU, unknown bills defaulted pro-CU.**
Sites: `fec/vote_by_category.py:56`; consumed at `fec/moneyball_core.py:246`.
`sign = +1 if d=='1' else -1 if d is not None else +1` collapses Direction `'0'` (Neutral) into the same `-1`/anti sign as `'-1'` (Expand): 6 Neutral CFPB bills (e.g. H.R.1215, S.3529) map to cat-13 and would score a Yea as anti-CU. Separately, a cat-13 bill **absent** from `cfpb_bill_directions.csv` defaults to `+1` pro-CU unverified — scoring an actually-anti bill backwards and possibly granting a false Path-V corroboration.
**Fix:** `sign = +1 if d=='1' else -1 if d=='-1' else 0` and skip when `sign==0`; treat an unmapped cat-13 bill as skip-with-warning, not pro-CU.

### V-5 · MEDIUM · dead_end → orphaned data · CONFIRMED ✔hand
**`HSall_members.csv` (6.2MB, all 119 congresses) written each cycle but consumed by no committed code.**
Sites: `fec/moneyball_core.py:33` and 9 other roster consumers; freshly written `votes/HSall_members.csv`.
51,061 rows, congresses 1–119, **8,914/12,584 bioguides appear in >1 congress**. All roster consumers read only per-congress `HS{119,118,117}_members.csv`; `grep HSall` = 0 python matches; no committed writer. Regenerated each cycle by an untracked process → ambiguous which Voteview artifact is authoritative, and a future reader opening it directly would pull duplicate old-congress rows (wrong party/NOMINATE for returning members). Header columns *do* match `HS119` (no column drift — see refuted R-3).
**Fix:** point `party()`/`behavior_panel` at `HSall` if it supersedes the slices, **or** delete/gitignore it and document it as a transient intermediate that per-congress consumers must never read.

### V-6 · LOW · diagnostics · CONFIRMED
**`vote_by_category` diagnostic gaps.** The `else:continue` vote-token branch (line 53) drops Present/Not-Voting/blank rows **without** incrementing `skip`, so the "votes skipped" diagnostic undercounts (aggregate lean unaffected — excluding non-yea/nay is correct). The `covered` Counter (line 41) is read only by an informational print, absent from the dumped artifact. **Fix:** route the else branch through an `unmapped_vote` counter and print it.

---

## Area 3 — New-cycle collection & database integrity

### C-1 · HIGH · error → stale dashboard shipped · CONFIRMED
**GATE-2 writes `gate2.done` even when post-rescore steps fail, then self-unregisters the task.**
Sites: `fec/collector_supervisor.py:184,185,265`.
After the big5 freshness abort, the post-rescore steps (`validate_big5`, C retest, `reference --score`, `co_appearance`, `make_member_desk`, `make_combined`, `audit_full`) all run via `gate_step`, which by design never raises; **none of their `ok` flags are checked**, so `gate2.done` is written unconditionally at line 185. If `make_combined`/`make_member_desk`/`co_appearance` crashes or times out, GATE-2 is still "complete" and `_tick` runs `schtasks /Delete` to self-unregister — a half-regenerated/stale dashboard ships and is never retried; even a failing `audit_full` doesn't block completion.
**Fix:** capture the `ok` flags of the required desk/combined/co_appearance/audit steps; only write `gate2.done` (and self-unregister) when all returned ok, else `return` so the next tick retries.

### C-2 · HIGH · dead_end → frozen layer baked into fresh artifact · CONFIRMED ✔hand
**`press_engagement`/`press_hcoi` layers are never regenerated by `weekly_refresh` yet are baked into every fresh AUG.**
Sites: `fec/weekly_refresh.py:67`; `fec/build_multilayer_network.py:53,66`.
`weekly_refresh` rebuilds the AUG network (line 67) but never runs `press_engagement_layer.py` or `press_hcoi.py`, while `build_multilayer` unconditionally consumes both JSONs. On disk `press_engagement.json` (Jul-01 21:23) and `press_hcoi.json` (Jul-01 21:16) are 6 days stale vs `social_interactions.json` and `AUG20260707.xlsx` (both Jul-07 13:33) — so every weekly AUG folds a frozen Jul-01 press snapshot (incl. the D4 leadership-reconnection edges for isolated members) into an otherwise-fresh artifact, silently mixing provenance.
**Fix:** add `press_engagement_layer.py` and `press_hcoi.py` steps before the multilayer-network step in `weekly_refresh.py`, **or** intentionally freeze and document these layers as static.

### C-3 · HIGH · provenance → untracked producer & consumer · CONFIRMED ✔hand
**`voteview_consistency.json` and its sole consumer `b5_behavioral_instrument.py` are untracked, with no committed producer.**
Sites: `fec/b5_behavioral_instrument.py:17`; related `HSall_members.csv`.
`voteview_consistency.json` (gmp/dim1/extremity, Jul-08) and `HSall_members.csv` have **no producer committed on any branch** (`git log -S` = 0). The JSON's only consumer, `b5_behavioral_instrument.py`, is itself untracked (`git status ??`, absent from the worktree, lives only at DATA ROOT). On the next `git checkout`/reset the consumer is discarded with no history, and the ES-trait instrument referenced by prereg commit `d630fe3` can't be reproduced from the committed tree. *(This is why one verifier "couldn't find" the file — it searched the worktree/git; the file is real but untracked at DATA ROOT. The separate claim that it "mixes congress scopes" was **refuted** — see R-3: the artifact is internally consistent.)*
**Fix:** commit `b5_behavioral_instrument.py` **and** the Voteview downloader/derivation script into `fec/`, wiring them as documented (gitignored-output) pipeline steps.

### C-4 · MEDIUM · duplicate → desyncable dedup · CONFIRMED
**`speeches` table has no uniqueness constraint; dedup relies on desyncable application skip sets.**
Sites: `fec/fetch_congressional_record.py:37`; `fec/fetch_interviews.py:210`; asserted retroactively at `fec/audit_full.py:307`.
The 234,827-row `speeches` table has no PRIMARY KEY/UNIQUE (only a non-unique `ix_sp_m` index); all writers use bare `INSERT`. Dedup rests on two independent best-effort skip sets (`cr_fetch_log 'ok'` + per-package `have_pkg`) with no row-level fallback, despite CREC emitting multiple rows per `(member,package)`. The only backstop is the audit assertion (exact-dup surplus ≤ 50). **Precedent:** the 4-year backfill re-inserted 922 exact-dup rows. DB currently clean.
**Fix:** add a UNIQUE index (or hash column) on `member+package+text` and switch to `INSERT OR IGNORE`.

### C-5 · MEDIUM · duplicate → positional-insert hazard · CONFIRMED
**`speeches` CREATE TABLE DDL triplicated across live fetchers, with `IF NOT EXISTS` masking future drift.**
Sites: `fec/fetch_interviews.py:41`; `fec/fetch_congressional_record.py:37`; `fec/attic/fetch_youtube_interviews.py:29`.
The 7-column DDL is triplicated and each writes via a **positional** `VALUES(?,?,?,?,?,?,?)`. Column order matches today, but whichever fetcher runs first defines the schema under `IF NOT EXISTS` — so editing one copy's DDL to add/reorder a column leaves the others issuing unchanged positional inserts against the first-created schema, writing into the wrong columns **with no error**.
**Fix:** move the `speeches` DDL into one shared init function all fetchers call.

### C-6 · MEDIUM · efficiency → permanent re-fetch loop · PLAUSIBLE
**CREC recent-date ingest is stuck re-fetching ~1170 non-session dates forever (no terminal state).**
Sites: `fec/fetch_congressional_record.py:150,166,167`.
`run_crec`'s done set excludes status `'err'`, so every date that logged `err:File is not a zip file` re-enters `todo` and is re-downloaded/re-parsed every run (**1170 such rows**, re-timestamped 07-02→07-05→07-07). These are overwhelmingly weekend/non-session days (838/1170) for which govinfo returns a 200 HTML page instead of a 404, so the `'404' in str(e)` check never marks them `nosession`.
**Fix:** treat a non-zip 200 body like a 404 (mark `nosession` → add to done), excepting dates within the last N days (retry-without-terminal so the latest still-publishing package retries once). *(Contrast with refuted R-5: the analogous CHRG `err` set is genuinely transient — 503/500/IncompleteRead — and must keep retrying.)*

### C-7 · MEDIUM · error (latent) → wedge false-positive · CONFIRMED ✔hand
**Supervisor progress metric uses the wrong key prefix for hewitt/npr/pbs legs (assumes prefix == arg).**
Sites: `fec/collector_supervisor.py:76,77`; `fec/fetch_interviews.py:596`.
`leg_db_metric` counts `iv_fetch_log WHERE key LIKE (args[0]+':%')`, but hewitt writes `hh:` keys (882 rows vs 0 for `hewitt:%`) and npr/pbs progress lives in sub-keys `nprtx:`/`pbsseg:` (only cnn's `cnnseg:` is special-cased at line 77). For those legs the DB-progress branch of wedge detection is dead/coarse, degrading the detector to CPU-only; a leg legitimately quiet in resume-skip mode (exactly what the DB metric exists to catch) could be misjudged as wedged and killed+relaunched. **Latent today** (live targets are `fox` + `cnn-deep`, whose tokens match their prefixes).
**Fix:** map each leg tag to its real log-prefix/sub-keys via a table (`hewitt→hh, cnn→cnnseg, npr→nprtx, pbs→pbsseg`) instead of assuming the prefix equals `args[0]`.

### C-8 · LOW · efficiency · CONFIRMED
**CHRG re-walks the full 400-day GovInfo listing every weekly run; `co_appearance` regenerated twice per cycle.** `run_chrg` calls `list_packages('CHRG', today-400d)` before the dedup guards (line 188), re-enumerating the whole 400-day collection via throttled paginated API calls each week. Separately, `co_appearance_layer` runs twice per supervised cycle (GATE-1 `weekly_refresh:68` and GATE-2 `collector_supervisor:181`) on identical inputs → byte-identical second output. **Fix:** cap the CHRG listing to the incremental tail (max stored `dateIssued` − lag), and drop the redundant GATE-2 `co_appearance` step.

### C-9 · LOW · dead_end · CONFIRMED
**`yt_fetch_log` table orphaned in the DB.** Its only reader/writer is retired `attic/fetch_youtube_interviews.py:31`; the live collector uses `iv_fetch_log`. Harmless stale schema clutter. **Fix:** drop the table or add a migration note marking it reserved.

---

## Cross-cutting (duplication / dead code spanning areas)

### X-1 · MEDIUM · redundancy · CONFIRMED
**Kernel denominator `6.0` and the inverse `w=6p/(1-p)` are hard-coded in multiple sites with no shared helper.** `fec/build_multilayer_network.py:59,95` vs `fec/moneyball_core.py:136`. Recalibrating the kernel denominator in `build_P` without editing both inversion sites would map augmentation edges against the stale 6 while the cascade uses the new constant. **Fix:** add one `weight_from_prob(p,cap)` helper next to `build_P` and call it from both branches.

### X-2 · MEDIUM · redundancy · CONFIRMED
**`bio2name` rebuilt inline in ~18 live modules despite `MBC.bio2name()`, with drifted guards.** Bare `m['bioguide']` in `scenario`/`cosponsor_route`/`lt_priming` vs `.get('bioguide')` in `build_dashboard_bundle:76`/`member_reference_layer:135`. Harmless today (all 533 records have truthy bioguide), but a future record lacking one would `KeyError` in the bare-access variants while `.get`/kernel variants silently skip it — and any mapping change must be replicated 18×. **Fix:** replace inline comprehensions with `MBC.bio2name()` (start with scenario, cosponsor_route, lt_priming, flip_model).

### X-3 · MEDIUM · redundancy · PLAUSIBLE
**`CU_TERMS` relevance vocabulary duplicated and already drifted between `process_quorum` and `tweet_collector`.** `tweet_collector.py:178` is a ~20-term narrowed copy of `process_quorum.py:20`'s ~50-term regex (missing ncusif, section 1071/1033, tcpa, MLA, fednow, mbl, …), even though `build_social_master.py:18` imports `process_quorum.CU_TERMS` as the single vocabulary. Harmless now (posts holds only bluesky rows, no tweets; `fetch_x` skipped without a paid token; consumed corpus re-applies the full regex), but enabling X collection or adopting `social_stance_signals.json` would silently drop CU-relevant tweets. **Fix:** import `CU_TERMS` from `process_quorum` in `tweet_collector.py`.

### X-4 · LOW · redundancy · CONFIRMED
**Per-congress party lookup duplicated in 5 modules, with a drifted 119-only variant in `validate_nomological`.** `build_dashboard_bundle:68` and `build_electoral_plays:9` copy `moneyball_core.party()` verbatim; `validate_nomological:14` drifted to read HS119 **only** (dropping 118/117) and defaults unknown party to `''` instead of `'I'` — so a member in HS118/117 but not HS119 gets a party everywhere except there. **Fix:** have all callers use `moneyball_core.party()`.

---

## Refuted (checked and cleared — false positives caught by verification)

- **R-1 — `mc_spread` "dead code" / bad CRN** (`cosponsor_route.py:29`): *not* dead — exercised by `audit_full.py:60-64` with `MCMODE=1`; the "CRN-deterministic" docstring only claims run-to-run determinism (which `random.seed(1009*it)` delivers), not order-independence. At most a low variance-reduction nit.
- **R-2 — `load_network` re-symmetrization is a redundant no-op** (`moneyball_core.py:114`): *false* — on the live AUG it fires exactly 4× and load-bearingly corrects the N-2 duplicate rows. (The real defect is the N-2 writer bug, not this pass.)
- **R-3 — `voteview_consistency.json` "mixes two congress scopes"** (`b5_behavioral_instrument.py`): *refuted* by reconstructing values from raw Voteview files — `gmp` and `dim1/extremity` are **both** HS117-119 vote-weighted (same scope), documented in the JSON's own `note`. The artifact is internally consistent; the real issue is provenance (C-3), not scope-mixing. Also: **no Voteview column drift** — `HSall` headers are byte-identical to `HS119`.
- **R-4 — `launch_detached` hardcodes `fetch_interviews.py` for every target**: *refuted* — non-interview collectors (CREC/CHRG/tweets) have a separate path; the live `collector_targets.json` only holds interview legs, and there's no launcher that could emit a non-interview target. Minor missing-validation gap at most.
- **R-5 — CHRG `done` set omits terminal states like CREC**: *refuted* — the CHRG `err` population is genuinely transient (503/500/IncompleteRead, 77 rows) and must keep retrying; the proposed "mark done" fix would silently drop ingestable hearings. The permanent-loop problem is CREC-specific (see C-6), and the "1,170 errors" cited were CREC's, not CHRG's.

---

## Completeness gaps (what this audit did *not* close)

1. **Live numeric impact of the vote bugs (V-2/V-3/V-4) is unquantified** because the input CSV is absent. *Probe:* find the roll-call file the model was last built from (search DATA ROOT `votes/*rollcall*` by mtime, or reconstruct from `vote_category_lean.json`'s Jun-26 provenance), run the logic offline, count affected `(member,category)` cells.
2. **No end-to-end rank delta measured** for the kernel mismatch (N-1) or stale votes (V-1). *Probe:* diff a `build_P`-vs-inline-P activation table for the top-20 recruitment targets to bound rank movement.
3. **Supervisor lock/heartbeat double-spend race** was asserted sound but not independently re-verified under concurrent scheduled-task launches. *Probe:* read lock-acquire / heartbeat / batch-submit spend guard end-to-end, plus the self-unregister→reregister window.
4. **Bluesky posts ingest (29,098 rows) integrity** was checked for current state, not for the insert-path race that produced it. *Probe:* read `tweet_collector`/`process_quorum` posts INSERT paths for uniqueness enforcement; re-run orphan/dup counts.
5. **The untracked Voteview scripts' own correctness** (scope/pooling in the gmp derivation) wasn't audited (the scripts aren't in the tree). *Probe:* read `b5_behavioral_instrument.py` + the derivation script at DATA ROOT and validate `voteview_consistency.json` against raw `HSall` rows for a member sample.

---

## Recommended fix order

1. **N-1** kernel unification (`build_P` everywhere) — silent numeric divergence in an unattended pipeline module.
2. **V-1** vote path — restore the CSV producer + wire/freshness-check `vote_category_lean.json`.
3. **N-2** edge-key convention (one-line fix, corrupts real ties).
4. **C-1** GATE-2 done-on-failure; **C-2** press-layer staleness in `weekly_refresh`.
5. **V-2 / V-3 / V-4** vote-scoring correctness (clobber, J.Res drop, CFPB signing).
6. **C-3** commit the untracked Voteview producer + consumer.
7. **C-4 / C-5** `speeches` uniqueness + shared DDL; then the MEDIUM/LOW hygiene items (N-3/N-4, C-6/C-7, X-1..X-4).
