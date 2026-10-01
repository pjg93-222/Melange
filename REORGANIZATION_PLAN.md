# Repository reorganization — plan and risk assessment

Draft 2026-08-03, revised 2026-08-04 after re-measurement and Phase 0, **EXECUTED 2026-08-04
late: Phases 1 and 2 are DONE.** Phase 3 (code into packages) remains, per this plan's own
one-domain-per-sitting law.

## Execution record (2026-08-04, run-20260804T2021407173543Z-4d7c2d0d27)

**Phase 1 @fa66617** — 118 tests into `fec/tests/{legislation 64, infra 15, members 11,
engine 8, collect 8, lobbying 5, stance 4, district 3}`; 117 `__file__`-depth bumps; both
runners resolve suites through a recursive basename map that raises on duplicates and on any
missing registration. Gate: kernel 149/0 from the new layout, identical count.

**Phase 2 @923e75c/@2c7766d/@ec6e9ab/@caba359/@40cb28c** — five batches, each gated
(kernel 149/0 + content-freshness 0 + `ranks_python.json` byte-identical) and separately
revertible. **Root: 360 files → 164.** 196 artifacts now live in
`data/{stance 78, members 62, engine 15, lobbying 11, legislation 9, money 8, network 7,
district 6, reference 0}` with every code site rewritten in place (style preserved; accessor
consolidation deliberately deferred to a dedicated pass — `paths.py` carries the note).

**~35 artifacts stayed at root deliberately**, each for a stated reason: bound by the frozen
55-file baseline manifest, bound inside re-attested receipts under `audits/legfix5/`,
referenced by deploy scripts, or being Paul's direct access points (the deployed surfaces,
the workbook family, the databases, `ranks_python.json` — rank authority does not move).

What the per-batch gates caught, kept for the record: layout-bound test pins (prerequisite
sets, alphabetical source ordering), fixture trees needing the nested layout, one real missed
consumer (`say_do_gap.py` → `lep_criterion.json`, caught by the say/do fail-closed guard),
and one genuine latent defect — `run_legislation_shadow_recompute` keyed one artifact by
`Path.name` and its sibling by repo-relative string, indistinguishable until the move split
them. Also two operational lessons: codex MCP timeouts ~30 min with the work actually
complete (inspect, don't redo), and a force-staged-gitignored-artifacts incident (403k-line
commit) unwound via parent-commit truth because `git check-ignore` skips tracked files.

## Status: Phase 0 is BUILT; two of four tripwires are green

Four audits now exist and run standalone (`python fec\audit\<name>.py`, `--json`, exit 1 on findings):

| tripwire | file | result |
|---|---|---|
| chain-step | `fec/audit/audit_chain_steps.py` | **0 hard**, 164 informational |
| content-freshness | `fec/audit/audit_content_freshness.py` | **0 findings** — all 5 surfaces carry their builders' markers |
| path-resolution | `fec/audit/audit_path_resolution.py` | 70 hard (≈31 distinct artifacts), 32 informational |
| output-consumption | `fec/audit/audit_output_consumption.py` | 30 hard, 44 informational |

The two failing tripwires report **pre-existing conditions, not regressions**. Their residue is
inventoried under "What Phase 0 found" below, and which entries are defects versus deliberate
is Paul's call — several are known-deliberate (the severed vote path, the cancelled expert
panel).

### The construction count is not a trustworthy number; the distinct-artifact count is

Successive scanners gave 102 → 708 → 1058 → **2515** constructions. That number is an artifact
of what one chooses to count as a "construction," and it moved ~25× without the tree changing.

Across those same scanners the **distinct-artifact count barely moved: 300 → 300 → 301**.

**Phase 2 must therefore be scoped by distinct artifacts (~300), not by call sites.** The
earlier claim that "seven hundred call sites is not a mechanical sweep anyone should do in one
pass" was reasoning from the unstable number. The real shape is ~300 artifacts addressed from
~2500 sites — which makes the `paths.py` accessor consolidation *more* attractive, not less,
because the leverage ratio is roughly 8:1.

## What we are actually dealing with

| | count | vs first draft |
|---|---|---|
| `fec/*.py` | **395** | +1 |
| `fec/tests/*.py` | 120 | — |
| root-level files | **360** (145 `.json`, 73 `.md`, 51 `.csv`, 35 `.xlsx`, 15 `.jsonl`, 11 `.ndjson`) | — |
| intra-`fec` import edges | **446** | +1 |
| root-relative path constructions | **708** | **was stated as 102 — see below** |

`moneyball_core` is imported by **139** modules; `paths` by **78**.

### Correction: the path count was understated by 7×

The first draft said 102. That number came from a regex matching only `MB_ROOT + literal` and
`B + r'\fec…'`. Counting **all** root-relative constructions — including `B + r'\<artifact>'`,
which is how most of the 360 data artifacts are actually addressed — gives **708**.

This materially raises Phase 2's risk and is the single most important revision in this document.
Seven hundred call sites is not a mechanical sweep anyone should do in one pass. It also
strengthens the argument for the `paths.py` consolidation *on its own merits*: 708 scattered
path literals are a standing hazard whether or not a single file ever moves.

### The lobbying lane is now the largest coherent new domain

Twenty-one modules, most of them built in the last two days:

`assemble_association_items` · `attention_vs_stance` · `build_network_2021_rebuild` ·
`classify_bill_positions` · `client_identity_harvest` · `coalition_pricing` ·
`cosponsor_forecast` · `cosponsor_route` · `cosponsor_selectivity` · `entity_identity` ·
`lobby_champions` · `lobby_forecast` · `lobby_interactions` · `lobby_position_classify` ·
`lobby_position_items` · `lobby_position_join` · `lobby_position_prompt_ab` · `lobby_posture` ·
`make_lobby_interactions_html` · `make_lobby_network_html` · `sector_spend`

It has clean internal cohesion and a narrow interface to the rest of the tree, which makes it
the best Phase 3 candidate — but it is also the most actively changing code in the repository,
which makes it the worst one to move *first*. Move it late, when it has stopped churning.

That coupling is the whole problem. Every module sits in one flat directory and imports its
siblings by bare name (`from moneyball_core import ...`). That works *only* because they share
a directory. The moment a file moves into a subfolder, 445 import statements and 102 path
constructions become candidates for silent breakage — and "silent" is the operative word,
because several of these paths are read at runtime inside try/except blocks that degrade to a
default rather than crash.

## Why this is riskier here than in a normal codebase

1. **Producers are addressed by filename.** `run_pipeline.py` invokes chain steps by script
   name. A rename or move that misses one step does not error — the step is skipped and the
   chain reports success with a stale artifact.
2. **`dashboard_integrity.py` hashes files by path.** Moving a hashed input changes its
   identity, and the audit's response to a missing input is not uniformly fail-loud.
3. **Artifacts and code are addressed from the same root.** `paths.py` resolves `ROOT` from
   `MONEYBALL_ROOT` or the parent of `fec/`. Both code and 360 data artifacts hang off that
   single anchor, so moving either side moves the other's reference frame.
4. **This repo has now demonstrated five distinct silent-failure modes in one week.** Each one
   is a specific thing a reorganization could reproduce, so each gets a named defence below:
   - A **raw NUL byte** disabled git's line-ending normalization for one file for an unknown
     period, making its diffs unreadable. *Mechanical file rewrites can have effects nothing
     reports.*
   - `coalition_pricing.py` **existed but was never wired into the chain**, silently degrading
     an entire scoring basis to neutral values. *A producer that is not invoked looks identical
     to one that is.*
   - `sector_spend` wrote to `derived\sector_spend_entity`, a path **nothing consumes**, while
     the canonical path served day-old numbers. *A move that redirects an output to an
     unconsumed path is invisible.*
   - `lobby-network.html` carried a **newer mtime than its builder while missing every feature
     the builder emits**. *Freshness cannot be inferred from timestamps.* This one directly
     invalidates the obvious Phase 2 staleness check.
   - A stale test-harness **slice marker broke 12 tests** with nobody noticing, because the
     suite was not in the kernel runner.

   Two more were found on 2026-08-04 while building Phase 0, bringing the count to seven:

   - **A crashing assertion masked every assertion after it.** `test_lobbyview_network.py`
     died at a stale `build()` call in `main()`, so the header-anchor assertion below it had
     not executed in an unknown number of runs. Fixing the crash *surfaced a second failure*
     that had been invisible the whole time. *A failing test can conceal other failing tests;
     an early hard failure is not one defect, it is an unknown number of them.*
   - **A tripwire that cries wolf is as bad as no tripwire.** The first cut of
     `audit_output_consumption` reported `district_employers/financial/hmda.json` as "written
     by X, read by nothing." All three were false — each has 10–11 readers and exists on disk.
     The readers call a loader helper with a bare filename (`_optional_L('district_hmda.json')`)
     instead of constructing a path, so static reader-detection was blind to them. *An audit
     that produces confident false alarms will be ignored, which reproduces the very omission
     it was built to catch.* Fixed by treating a quoted basename literal in another module as
     reader evidence, and reporting match basis (`exact resolved path` / `basename literal`).

   The common thread: this codebase fails by *omission*, not by exception. Every gate in this
   plan must therefore assert that something is **present and correct**, never merely that
   nothing raised — and every gate must itself be negative-controlled, because a check that
   cannot fail is worthless.

   Both Phase 0 tripwires that pass have been negative-controlled. `audit_content_freshness`
   was run against five deliberately corrupted surfaces (honesty string removed, industry
   cards removed, evidence class removed, cost fix reverted, old guard reintroduced as live
   code) and caught all five, with both surfaces restored byte-exact afterwards.

## Proposed target structure

```
fec/
  core/          moneyball_core, paths, bill_rules, tier_util, config_overlay   (the 6 hubs)
  lobbying/      lobby_*, make_lobby_*, build_network_*, classify_bill_positions,
                 cosponsor_*, sector_spend, coalition_pricing
  legislation/   build_legislation_*, run_legislation_*, audit_legislation_*,
                 *_culling_*, primacy_*
  stance/        *_stance_stack, per_category_stance, stance_rules, say_do
  members/       member_*, historical_member_names, receptivity_layer, big5/b5_*
  district/      demographic and district producers
  surfaces/      make_dashboard_html, make_member_desk, make_combined, templates/
  collect/       collect_*, fetch_*, harvest_*
  audit/         audit_*, verify_*
  tests/         mirrors the above
data/
  network/ stance/ legislation/ members/ district/ money/ reference/
```

Two rules make this survivable:

- **`fec/core/` is the only package anything may import across boundaries.** Cross-domain
  imports go through it or through an explicit re-export. This turns 445 arbitrary edges into
  a hub-and-spoke shape that can be checked mechanically.
- **`paths.py` becomes the single owner of every artifact location.** The 102 inline
  `MB_ROOT + r'\literal.json'` constructions become named accessors (`paths.stance('tweet_stance_final.csv')`).
  After that, moving a data file is a one-line change in one file.

## Phasing — each phase independently revertible

**Phase 0 — instrument before moving anything (no file moves)**
Add a resolver-audit that asserts every artifact `paths.py` can name actually exists, and a
chain-step audit that asserts every script named in `run_pipeline.py` exists and is importable.
These are the tripwires for phases 2 and 3; without them a missed reference is invisible.
*Gate: both audits pass on the current, unmoved tree.*

**Phase 1 — tests (120 files, near-zero risk)**
Nothing imports a test module. Move `fec/tests/*.py` into `fec/tests/{lobbying,legislation,stance,...}/`
mirroring the target layout. Update the two runners' discovery globs.
*Gate: `run_tests.py` 89/0 and `test_lda_rebuild.py` unchanged; test count identical.*

**Phase 2 — data artifacts (360 files, medium risk)**
Introduce `data/` and move root artifacts by domain. Every move is paired with a named accessor
in `paths.py`; the 102 inline constructions are rewritten to call it. Leave a compatibility
shim resolving old root paths for one release so any missed reference resolves rather than
silently defaulting.
*Gate: full chain run; `ranks_python.json` **byte-identical**; audit count unchanged; the
Phase 0 resolver audit green.*

**Phase 3 — code into packages (394 files, highest risk)**
One domain at a time, smallest first (`collect/`, then `audit/`, then `district/`, then
`stance/`, `members/`, `legislation/`, `lobbying/`, `surfaces/`, `core/` last). Each domain:
move, add `__init__.py`, rewrite that domain's imports, run the gate. Nine separate commits,
each revertible alone.
*Gate per domain: kernel tests, `test_lda_rebuild.py`, full chain, byte-identical ranks.*

## The verification gate, stated once

No phase is complete until all four hold:

1. `fec/tests/run_tests.py` — 89 passed, 0 failed
2. `fec/tests/test_lda_rebuild.py` — full count, unchanged
3. Full `run_pipeline.py` reaching `audit_full` with **no new failures** (the culling-promotion
   stale-artifact failures are known and separately tracked)
4. **`ranks_python.json` byte-identical before and after** — this is the one that matters. Rank
   authority is the product; if a reorganization moves a single rank, it changed behaviour and
   is wrong by definition.

## Honest assessment

**Is it worth doing?** Phases 0, 1 and 2 — yes. 394 files in one directory is genuinely hard to
navigate, the tests are cheap to organize, and pulling artifact paths into `paths.py` is
independently valuable regardless of any reorganization: it removes 102 scattered literals that
are already a latent hazard.

**Phase 3 is the one to think hard about.** It touches 445 import edges to buy navigability.
The honest trade is that it makes the codebase easier to reason about and carries a real chance
of a silent regression in a repo that has already demonstrated silent regressions this week.
If we do it, it should be one domain per sitting with a full gate between, never in a batch.

**What would make me stop:** any phase where the rank artifact moves and the cause is not
immediately explicable. That is not a merge conflict to resolve — it means the reorganization
changed behaviour, and the correct response is revert, not patch forward.

## Sequencing against current state — REVISED 2026-08-04

The first draft said "do not start while multiple sessions hold live work." **That window has
reopened: the three background sessions are done.** All three had exited *without landing their
work* — a notification of completion turned out to be no evidence of it. Verified and finished
in-session on 2026-08-04:

- `task_0e7a1f0a` — stale `build()` in `test_lobbyview_network.py`. The call carried an
  obsolete 3-positional-arg contract (`build(data_root, out, …)` now) *and* obsolete
  expectations (`"Coverage 2021–2023"`; the corpus is 2021–2026). Rather than synthesise a
  22-file fixture to satisfy the ingest validators, the end-to-end emission check was
  **relocated** to `audit_content_freshness`, where it validates the *deployed* surface
  instead of synthetic data. Removing it surfaced a second, previously-masked failure (see
  failure mode 6). **Now 21 passed / 0 failed.**
- `task_48dc0270` — `lt_priming` JS mirror. The template fix was committed; the dashboard had
  never been rebuilt from it. Now deployed and verified *in executable code*: live form is
  `rcost(u,i)/add<avg` with sort key `rcost(a[0],i)/a[1]-…`, matching Python's fixed
  `c < avg_rate` where `c = recruit_cost(u)/add`.
- `task_a5776fa0` — industry surface wiring. `make_lobby_network_html.py` now sits in the
  CHAIN between `make_member_desk.py` and `make_combined.py`, so the combine step can no
  longer merge a stale industry surface.

A methodological note worth keeping: verifying these three produced **three false positives in
a row** from plain substring search, because `Math.max(0.1,add)` and `NOT rcost/add**2` both
appear in the *rationale comment that documents the fix*. Any check for a code-level defect in
a generated surface must strip `//` comments first. `audit_content_freshness` now does.

**Consequence for this plan, and it follows the plan's own rule rather than overriding it:**

- **Phase 0 proceeds now.** It adds audits and moves nothing, so it cannot collide with a
  concurrent edit and cannot be invalidated by one. Starting it during churn is not just safe,
  it is the *right* time — the tripwires it installs are exactly what the other three sessions'
  changes should be landing against.
- **Phase 1 waits** for the three sessions to finish and their work to be committed. It is
  near-zero risk in isolation but it moves 120 files, and moving files under three concurrent
  editors is how you get a merge that silently drops someone's work.
- **Phase 2 additionally waits** for a re-count. The 708 figure is seven times the original
  estimate; before committing to a single-pass sweep, Phase 0's resolver audit should report
  how many of those 708 sites actually resolve to distinct artifacts versus repeated references
  to the same few. That ratio decides whether Phase 2 is one change or ten.
- **Phase 3 stays a per-domain decision**, and the lobbying lane — the obvious candidate on
  cohesion — should go **last**, not first, because it is the most actively changing code in
  the repository.

### Phase 0's brief, sharpened by what we now know

The two audits in the original Phase 0 are necessary but insufficient. Given the five failure
modes above, Phase 0 must install four tripwires, not two:

1. **Resolver audit** — every artifact `paths.py` can name exists, and every one of the 708
   root-relative constructions resolves to a real file. Report the distinct-artifact count.
2. **Chain-step audit** — every script named in `run_pipeline.py` exists, is importable, and is
   actually invoked. Catches the `coalition_pricing` failure mode.
3. **Output-consumption audit** — every path a producer writes is read by something. Catches the
   `sector_spend_entity` failure mode, where output went somewhere nothing consumes.
4. **Content-freshness audit** — for each generated surface, assert that identifying strings its
   builder emits are present in the deployed artifact. Catches the `lobby-network.html` failure
   mode, where mtime lied. `make_lobby_network_html` already implements exactly this check
   against its own honesty strings; generalise that pattern rather than inventing a new one.

*Gate: all four pass on the current, unmoved tree — and any that does not pass is reporting a
real defect that exists today, which should be fixed before anything moves.*

## What Phase 0 found — the residue, for adjudication

Two tripwires are green. The other two report pre-existing conditions that predate this work.
**None of these were caused by the reorganization or by the three landed tasks.** They need
Paul's judgement, because several are deliberate:

**Missing artifacts that code reads (~31 distinct).** Grouped by likely disposition:

- *Believed deliberate, confirm only:* `votes\cu_rollcall_votes_clean.csv` (the vote path was
  deliberately severed); `expert_panel_rater.html` / `panel_manifest.json` (the expert gold
  panel was built then cancelled).
- *Research one-offs not in the chain, probably fine to leave:* `b5_emb_cache*.npz`,
  `big5_latent.json`, `outputs\research\*`, `b5eval`, `hearing_substance\substance_labels.json`.
- *Genuinely worth a look:* `source_data\big5_composite.json` (read by three modules),
  `source_data\committee_membership.json`, `source_data\cu_stance_label_set_AUGMENTED.xlsx`
  (read by two; note the label template of record is `cu_stance_label_set.csv` in Draft
  Systems, so the AUGMENTED xlsx may simply be gone), `source_data\electoral`,
  `source_data\staff`, `member_narratives_v2.json` (read by `audit_full.py`).
- *Looks like a bug:* `B+r'\_capX'` in `b5_audio_verify.py:37` — a stray path fragment.
- *Zero-match globs:* `Ballotpedia_119th_CU_Influence_*.xlsx`,
  `Moneyball Main Version - Blended.PRE-STANCEGUARD-*.xlsx`, `panel_ratings*`.

**Outputs nothing reads (30).** Mostly collector and research one-offs
(`social_stance_signals.json`, `tweet_influence.json`, `sna_compact.json`, `imviz.json`,
`corrected_signals.json`). One is a genuine smell: **`fec\tests\test_primacy_tier.py` writes
`source.json` into the repo root** — a test should write to a temp directory.

**A second orphan surface — CHAINED 2026-08-04 on Paul's instruction, and it was worse than
reported.** `lobby-interactions.html` was not merely stale: it was **unbuildable**. The
interactions builder reaches into `make_lobby_network_html`'s private helpers, and bank-tier
segregation had grown `_load_sector_roster`'s return from 3 values to 5. The builder raised on
every invocation. Nothing reported it because nothing invoked it.

This is the sharpest available demonstration of the difference between *coverage* and *wiring*:
`audit_content_freshness` passed on this surface the whole time, because the deployed page did
contain its builder's honesty strings. **Content-freshness cannot detect a builder that no
longer runs** — it compares a deployed artifact against declared strings, and the chain-step
audit deliberately only parses producers rather than importing them (importing a producer here
executes work). The only thing that catches "builder raises at runtime" is *being in the chain*.

Fixed and chained. An AST sweep of all 17 `industry.*` cross-module call sites confirmed one
real break; a second apparent hit (`PostureTable`) was a false positive of the sweep, which
scanned `FunctionDef` but not `ClassDef`.

**Dead duplicated constants.** `POSITION_NOTE` and `INTERACTION_NOTE` are defined in *both*
`make_lobby_network_html.py` and `make_lobby_interactions_html.py`; only the latter emits
them. They are exempted-with-reason in the freshness audit rather than silently dropped.

### The tests outside the kernel runner are where drift accumulates

`test_lda_rebuild.py` was broken in **two** places, both by the bank-tier / industry work, and
neither had been noticed:

1. its fixture `sector_roster.csv` header omitted `bank_tiers`, which
   `_load_sector_roster` had made **required** — `IngestError: sector roster lacks required
   columns: bank_tiers`;
2. it bound `_load_spend(...)` to a single name after that function's return changed to a
   3-tuple `(spend, tier_meta, entity_receipt)` — `TypeError: tuple indices must be integers`.

Both are fixed. But note the shape: **`run_tests.py` was 89/0 green the entire time.**
`test_lda_rebuild.py` is not in the kernel runner, so nothing reported its breakage — the
same mechanism as the earlier slice-marker incident that broke 12 tests silently.

Rather than discovering these one crash at a time, an AST sweep comparing every `MLN.<fn>(...)`
call in the test against the producer's live signatures (positional arity, unknown kwargs,
unpack arity vs return arity) found the complete set in one pass and confirmed there were
exactly two. **That sweep is worth keeping as a fifth tripwire** — signature drift between
producers and their tests is precisely the kind of breakage a reorganization would mass-produce.

**Done 2026-08-04 on Paul's instruction — and the census behind it is the real finding.**
`run_tests.py` already had a subprocess registration mechanism. It was pointed at **14 of 118**
suites. `test_lda_rebuild`, `test_lobbyview_network` and `test_lobby_interactions` are now
registered: **92 passed / 0 failed in 56 s**.

Registering them exposed a third instance of the same stale-fixture defect:
`test_lobby_interactions` had **11 of its 31 tests erroring** for an unknown period — its
sector-roster fixture omitted the required `bank_tiers` column and wrote `""` for
`first/last_year_seen`, which no longer parse as integers. A sweep confirmed only two test
files build a sector roster at all; both are now correct.

**102 suites remain orphaned.** They are NOT pytest suites — there is no pytest config in the
tree and pytest is not installed; they are standalone scripts with `__main__` blocks that run
and assert. So all 102 genuinely run nothing. By lane:

| lane | orphans |
|---|---|
| legislation / culling | 59 |
| other | 17 |
| audit / postrefresh | 12 |
| workbook / dashboard | 5 |
| district / demographic | 3 |
| big5 / audio, stance / channel, lobbying / network | 2 each |

**Zero of the 102 can be registered as-is**: 95 print no summary line at all, and the rest use
a shape the runner's regex cannot consume. Folding them in is therefore a real project — each
needs a summary line in the runner's format (or a unittest `__main__` block like the one added
to `test_lobby_interactions`) — not a one-line change. It is also a genuine risk surface: three
of the four suites examined this week turned out to be broken, so the expected yield of
registering the rest is a substantial backlog of real, currently-invisible failures.

*Recommendation: do this lane by lane, starting with `legislation / culling` (59 of the 102,
and the lane with active work). Treat each lane as its own commit with its own gate.*

**Closed 2026-08-04, second pass — all 20 formerly-held legislation / culling suites are now
resolved.** Eighteen are registered in the kernel runner: **149 passed / 0 failed**. The final
two — the presync pair — now **PASS** (**readiness 27/0; presync 37/0**) after their drifted
receipts were re-attested. Downstream closure legitimately grew **20 → 36**, with every addition
named to an authorized workstream; the workbook was re-bound at SHA `5001e7df`; decay has
**9/9 staged contracts**; and the formula cache was proven by twin isolated Excel recalculations
with identical ledgers.

The presync pair stays **OUT of the kernel runner BY DESIGN**. These are operational sync-time
gates bound to live mutable receipts: the workbook drifts on every user edit. Registering them
would manufacture a cries-wolf gate.

`pytest 9.1.1` is now part of the environment (Paul-authorized 2026-08-04). The kernel runner
reads five native verdict shapes and never skips an unreadable suite.

The `claude/cfpb-sentiment-recorrection` branch merged to `main` at `9499cef`.

## PHASE 3 COMPLETE (2026-08-05, merged @91bf44a)

The library is done. Final shape:

| shelf | contents |
|---|---|
| `fec/` root | 9 hubs (moneyball_core, paths, bill_rules, tier_util, config_overlay, audio_rules, legislation_measure_key, lane_file_io, calibration_guard) + 2 chain entrances (run_pipeline, weekly_refresh) + 3 attic candidates awaiting Paul |
| `fec/{collect 17, audit 36, district 7, stance 47, members 120, engine 30, legislation 87, lobbying 28, network 10, surfaces 11+templates}` | every producer, by domain |
| `fec/tests/{8 domains}` | 118 suites |
| `data/{9 domains}` | 196 artifacts |

The chain never broke: run_pipeline/weekly_refresh resolve every step by
basename recursively, and the full chain ran end-to-end from the new layout
(audit_full 199/1, pre-existing crown-law only). ranks_python.json
BYTE-IDENTICAL through every one of ~18 gates across Phases 1-3.

The receipt family survived the move by separating IDENTITY from LOCATION:
fec/audit/live_relocations.py (27 entries) resolves live reads for the
immutable baseline manifest; drift closure re-attested 36->47 with per-file
provenance; presync 37/0 and readiness 27/0 green.

New permanent tripwire: fec/audit/audit_stale_imports.py (kernel check #150)
- dynamic ledger of 389 packaged modules, four stale-import forms, justified
pragmas, negative-controlled 5/5. legacy_workbook_audit is now import-inert.

The core/ directory migration (moving the 9 hubs) remains AVAILABLE but was
deliberately not done: paths has 273 importers, moneyball_core 156 - ~500
rewrites for zero navigational gain. Paul's call if the hub-and-spoke import
rule is ever enforced mechanically.
