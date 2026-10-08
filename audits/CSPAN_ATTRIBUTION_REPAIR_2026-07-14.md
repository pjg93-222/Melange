# C-SPAN attribution repair audit — 2026-07-14

## Scope and safety controls

This audit repairs C-SPAN speaker attribution from the raw per-program transcript JSON files through `social_media.db` and the deterministic downstream artifacts. It does not alter hearings, press releases, or press-reader ingestion because inspection showed that they do not produce the faulty C-SPAN flag.

Safety controls:

- Preserve raw `cspan_out/transcripts/*.json` as the source of truth.
- Build and test the new attribution path before changing any database rows.
- Wait for pre-existing pipeline jobs to finish before changing generated artifacts.
- Back up the database and the old flat C-SPAN CSV files before replacement.
- Replace only rows whose package is a C-SPAN URL; do not truncate the broader `INTERVIEW` source.
- Resolve full names conservatively, require the program title to identify the same guest, and verify that the person served in Congress on the program date.
- Record every command, warning, failure, and before/after count below.

## Confirmed baseline

Inspection of `cspan_out/turns*.csv` found:

| Measure | Baseline |
|---|---:|
| Flat turn rows | 30,405 |
| `is_member_role=FALSE` | 30,405 (100%) |
| Blank role values | 30,405 (100%) |
| Rows with a named speaker | 30,208 |

The faulty scraper expression on branch `claude/cspan-video-scraper-528437` inferred membership only from `turn.role`:

```r
is_member_role = grepl("Representative|Senator|Congress|Delegate|Speaker", t$role, ignore.case = TRUE)
```

C-SPAN supplies the member's name in the speaker field but leaves `role` blank in this corpus, so the expression is systematically false even when the label is correct.

The production loader on the same branch did not read that flag. It independently resolved `turn.name`, which limited the immediate damage but silently missed public-name aliases. The existing database baseline is:

| Measure | Baseline |
|---|---:|
| Loaded C-SPAN member turns | 6,693 |
| Loaded members | 180 |
| Loaded program packages | 476 |
| Loaded words | 986,916 |
| Stored source | `INTERVIEW` |

After the existing 8-word threshold and per-video deduplication, the known alias misses are:

| Raw C-SPAN label | Canonical member | Missed turns | Missed words | Programs |
|---|---|---:|---:|---:|
| Buddy Carter | Earl Carter | 143 | 22,825 | 13 |
| Jan Schakowsky | Janice Schakowsky | 80 | 9,393 | 5 |
| Brad Schneider | Bradley Schneider | 63 | 9,785 | 5 |
| Hank Johnson Jr. | Henry Johnson | 36 | 6,860 | 4 |
| Gabriel "Gabe" Vasquez | Gabe Vasquez | 26 | 3,647 | 3 |
| Lou Correa | Luis Correa | 15 | 2,274 | 2 |
| Jen Kiggans | Jennifer Kiggans | 8 | 791 | 1 |
| Dustin "Dusty" Johnson | Dusty Johnson | 4 | 597 | 1 |
| **Total** |  | **375** | **56,172** | **34** |

## Confirmed downstream exposure before repair

- C-SPAN currently supplies 4.4% of interview rows and 8.1% of interview words.
- It supplies 1.8% of words in the default `CREC + INTERVIEW` Big Five speech corpus.
- It is the majority of interview words for 87 members and at least 25% for 130 members.
- The missed alias turns contain 21 candidate member-reference mentions across 13 dyads.
- The missed alias turns contain 7 candidate personal-texture windows across 3 members.
- `member_personal_texture.json` currently contains 147 C-SPAN-supported items across 84 members. Separate semantic false positives were observed; those are a classifier-quality issue, not speaker attribution.
- C-SPAN packages currently fall into the generic `other` program bucket in `interaction_features.py`. Removing C-SPAN in a read-only counterfactual changed the shared `other`-bucket standardization for many non-C-SPAN members, so this repair will give C-SPAN its own program bucket.
- No loaded C-SPAN program currently has turns attributed to more than one member, so no C-SPAN co-appearance episode is presently formed.

Downstream readers exposed to these rows include behavior volume, interaction features, Big Five speech features, member references, personal texture, interview antagonism, and affective-N validation. Member-desk output consumes several of those derived artifacts.

## Execution log

| Time (America/Chicago) | Stage | Result | Error or warning |
|---|---|---|---|
| 2026-07-14 | Baseline diagnosis | PASS | The flat CSV flag is completely wrong; the database loader bypassed it but missed 375 valid turns. |
| 2026-07-14 | Concurrency check | WAITING | A pre-existing `fec/run_pipeline.py --from per_category_stance` process (PID 35736) is still running. Database/artifact mutation is deferred until it finishes. |
| 2026-07-14 | First unit-test run | 11 PASS, 1 FAIL | The inserted-clip case was safely rejected as `unresolved_label`; the test had over-specified `title_label_mismatch`. The assertion was corrected to require rejection through either safe branch. |
| 2026-07-14 | Second unit-test run | PASS (12/12) | Includes the real Don Bacon fixture, all eight known public-name aliases, tenure, title/label agreement, inserted-clip rejection, and a separate C-SPAN interaction bucket. |
| 2026-07-14 | Scraper repair | PASS | The R scraper now writes raw JSON only. The bad role-based membership expression and sharded flat-file appends were removed; canonical CSV generation is delegated to the Python identity gate. `Rscript` is not installed in this environment, so an R parser check could not be run. |
| 2026-07-14 | Canonical builder dry run | PASS | 858 raw files, 30,405 turns, stable source digest `eff1152bb11dcc479827150d5bd28ab69711f4b0c0ada84453ea054378be5384`. |
| 2026-07-14 | Database loader dry run | PASS | Prepared 7,076 turns, 1,044,472 words, 189 members, and 512 programs at the existing 8-word threshold. Database remains unchanged at 6,693 turns, 986,916 words, 180 members, and 476 programs. |
| 2026-07-14 | Concurrency re-check | PASS | The pre-existing pipeline process has finished; no conflicting pipeline mutation remains. |
| 2026-07-14 | First flat-file replacement attempt | PARTIAL / ERROR | The old CSVs were backed up and canonical `turns.csv` plus `attribution_audit.json` were written, but Windows returned `WinError 32` while removing stale `turns_0.csv` because another process had the file open. Database mutation remained blocked pending verification. |
| 2026-07-14 | Flat-file verification | PASS with one cleanup warning | Canonical CSV has 30,405 rows, 7,773 member rows, 190 resolved members, 30,405 blank roles, and zero role-derived positives. Audit counts and raw-source digest agree. Stale shards 1–3 were removed; locked `turns_0.csv` remains, preserved in the backup and ignored by all repaired code. |
| 2026-07-14 | Downstream artifact snapshot | PASS | Ten existing downstream artifacts were copied to `backups/cspan_downstream_pre_repair_20260714_162957` with SHA-256 hashes before rebuilding. |
| 2026-07-14 | Transactional database replacement | PASS | Full backup: `backups/social_media_pre_cspan_repair_20260714_163027.db`. Only packages matching `c-span.org` were replaced. SQLite `integrity_check` returned `ok`. |
| 2026-07-14 | Deterministic core rebuild | PASS | `interaction_features.py`, `behavior_panel.py`, `big5_traits.py`, and `behavioral_dispositions.py` completed without errors. |
| 2026-07-14 | Cache-only media rebuild | PASS with coverage warning | References rebuilt with 19,753 capped contexts: 17,872 cached and 1,881 uncached (`n_raw` only). Personal texture rebuilt to 3,739 retained details across 477 members. Co-appearance remained 2,510 pairs. No API calls were made. |
| 2026-07-14 | Interview antagonism eligibility check | STALE SOURCE WARNING | Fresh corpus eligibility is 325 members, while the promoted artifact contains 322 frozen members. Existing scores were not silently reused as fresh. |
| 2026-07-14 | Multimethod package-cache rebuild | PARTIAL / ERROR | The fresh 1,142 member-venue / 172,298-package cache completed with zero package overlap, then reliability failed because `interview_antagonism_halves.json.candidate` is missing. The promoted artifact cites this missing file as its source. No promotion was attempted. |
| 2026-07-14 | Missing antagonism source recovery | PASS with provenance warning | The exact 322-member half-score content was recovered from repository history and agrees with the promoted artifact for every member. The recovered file's serialization hash does not equal the emitter-recorded source hash, so it is retained as a candidate rather than treated as newly verified provenance. |
| 2026-07-14 | Free multimethod validation | PASS (5/5) | Reliability and validation completed against the recovered frozen 322-member source. `big5_blue_validated.json` was not promoted because fresh corpus eligibility is now 325 members and a paid rescore was outside this repair. |
| 2026-07-14 | Reference cache-cap regression | FOUND / FIXED | In cache-only mode, newer uncached contexts could displace older cached contexts before the per-member cap. Rebuild mode now uses the newest cached fallback while preserving the newest contexts as the future paid-scoring target. Corrected artifact: 7,972 edges (5,949 positive, 1,187 negative); 1,881 contexts remain unscored. |
| 2026-07-14 | Full artifact audit before main merge | PASS (97/97) | The deterministic and cache-only downstream rebuild passed the repository's full audit with zero failures. |
| 2026-07-14 | Merge current `main` | PASS | Merged `main` commit `cb739ce` into this branch as merge commit `0a3b5ac`. The only content conflict, `fec/make_member_desk.py`, was resolved by retaining both the tier feature and the newer atomic-output / integrity checks. Existing worktree changes were preserved. |
| 2026-07-14 | Tier and production-output verification | PASS | Redirected dashboard and member-desk builds both produced 533 members with 12 Tier 1, 24 Tier 2, 48 Tier 3, and 449 untiered. Verified outputs were copied into production and both HTML entry points rebuilt. `ranks_python.json` remained byte-for-byte stable (`3634c9e516af35cce6dc82abbecac7e8097e329ac99d6e4df2da0ecd4edad525`). |
| 2026-07-14 | Final regression checks | PASS | Targeted C-SPAN tests: 13/13. Core repository kernel: 64/64. `git diff --check`: clean. No unresolved merge markers. |
| 2026-07-14 | Stale flat-file cleanup retry | PASS | The process holding `cspan_out/turns_0.csv` released it; the stale shard was removed. `turns.csv` is now the sole canonical flat output. |

## Validation results

- Targeted C-SPAN regression tests: 13 passed, 0 failed.
- Core repository kernel tests: 64 passed, 0 failed.
- Python syntax compilation: passed for identity, CSV builder, and loader.
- Dry-run source file count and SHA-256 digest agree between the CSV builder and loader.
- The loader refuses mutation unless `--replace` is explicit.
- Transactional loader test: creates a backup, replaces only C-SPAN, and preserves unrelated interview rows.
- Production database before/after: 6,693 → 7,076 turns; 986,916 → 1,044,472 words; 180 → 189 members; 476 → 512 programs.

## Before/after downstream delta

- Database change is purely additive: 383 turns and 57,556 words were restored; no previously loaded C-SPAN rows were removed.
- C-SPAN coverage increased from 180 to 189 members and from 476 to 512 program packages.
- The eight known public-name aliases were restored. Title-confirmed conservative matching also recovered four Mike Rounds turns and one additional turn each for Jamie Raskin, Don Bacon, and John Larson.
- Deterministic consumers were rebuilt: interaction features, behavior panel, Big Five speech features, behavioral dispositions, receptivity, dashboard bundle, and member desk.
- Media-reference and personal-texture consumers were rebuilt cache-only. No paid model calls were made. The corrected reference layer contains 7,972 edges; personal texture contains 3,739 retained details across 477 members.
- C-SPAN now has its own `cspan:washington-journal` interaction bucket, preventing these restored turns from changing the shared generic `other` standardization bucket.
- Co-appearance remains unchanged because no loaded C-SPAN package contains multiple resolved members.
- Personality implications are concentrated among the 12 members receiving restored text and can propagate through speech volume, interaction features, Big Five traits, behavioral dispositions, receptivity, and member-desk prose. The deterministic layers were regenerated; frozen LLM-scored validation layers were not silently promoted.

## Remaining risks and decisions

- 1,881 reference contexts and 57 personal-texture candidates lack cached model classifications. They remain visible as raw counts or excluded from semantic output as appropriate; no paid calls were made.
- Fresh interview-antagonism eligibility is 325 members versus the frozen 322-member scored source. A fresh paid rescore is required before promoting a new multimethod validation artifact.
- The recovered antagonism half-score candidate has exact semantic agreement but a serialization fingerprint mismatch; provenance should be repaired at the emitter before it is treated as a fully reproducible source.
- `make_combined.py` reports an existing duplicate HTML id, `backbtn`. The output is generated successfully, but this is a separate UI defect worth cleaning up.
- The merge safety stash `stash@{0}` is intentionally retained until the user confirms the merged worktree; it duplicates the preserved pre-merge tracked changes and is not applied twice.
