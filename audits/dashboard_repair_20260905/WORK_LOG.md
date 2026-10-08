# Dashboard audit repair — September 5, 2026

The user authorized resolving the 13 failures left by the staffer publication.
Work is in progress; this file is not a completion receipt.

## Findings and repairs

- **Personal texture:** all 480 raw source payloads were intact. The obsolete
  equality check rejected the new `display_dedupe` metadata. The replacement
  checks exact source preservation and the display suppression partition.
- **Press:** the current feed combines three accepted runs. The obsolete audit
  expected one top-level source. It now verifies every run's four source hashes,
  immutable acceptance receipt, complete accepted-run coverage and the rolling
  intake binding. Output hashes and non-scoring mention boundaries remain checked.
- **Votes:** the missing cleaned export was found in Draft Systems but dates to
  June. Fresh, separately archived Voteview files cover House votes through
  September 3 and Senate votes through August 8. The new network-free producer
  retains existing categories/sign rules and previous exclusions/holds, uses
  exact measure types/Congresses and refuses unresolved member identities.
  It publishes 38 accepted final-passage events, 15,046 member-vote records,
  705 historical members and 6,261 category cells. One direction lacks a unique
  Congress and is withheld rather than guessed. The audit independently checks
  source coverage dates and every required input/output hash.
- **Culling:** the original promotion receipt is unchanged. All 11 installed
  culling decision/evidence files match it. A subsequent rank refresh no longer
  erases that history: status records the current and original rank hashes and
  verifies the complete culling continuity set. Current rank correctness remains
  the separate `compute_pillars` audit's responsibility.
- **Dashboard priorities and freshness:** rebuild the downstream stance, engine
  and surface artifacts from the accepted inputs. A first resumed run passed the
  vote, stance, rank, primacy and allocation stages, then exposed an additional
  obsolete speech-profile basis hash. The pipeline now builds profile basis,
  evidence ledger and validated descriptive profiles before the dashboard.
  Existing profile inputs and active prose were backed up; these producers make
  no API calls and perform no new audio reviews.
  The ledger then caught an obsolete whole-turn measurement producer hash.
  Recomputed the nine existing turns from unchanged audio (13.438167 minutes,
  four members): all remain candidate-only, with zero qualified or baseline-eligible
  turns. Rebuilt the ledger and all 533 profiles against the actual current basis;
  all word-count and evidence-template checks passed. Future reuse of the audio
  measurement requires unchanged producer, source and artifact hashes.
- **Inventory:** the original manifest is preserved. Changed generated files
  will be remeasured after publication. Glassbox's installed retention function
  keeps 5,000 events and retires older files every five minutes; its event store
  is now correctly measured as a rolling window rather than immutable files.
  Existing event files and retention code were not manually altered. See
  `glassbox_retention_review.json`. The first census rejected a proposed
  `presence_only` policy because it is reserved for secrets; that failed run
  wrote no manifest. The corrected `hash_never` policy retains A1/A2 store
  presence, size-class and file-count checks while allowing old filenames to retire.

## Verification so far

- 24 targeted source, vote, culling and producer-scope tests passed.
- 42 system-manifest checker controls passed, including corruption and missing-store failures.
- 42 profile-generation, publication and pipeline-order tests passed.
- The seven source-contract tests passed again after strengthening the vote check
  to recompute coverage dates directly from the downloaded roll-call CSV.
- 82 speech measurement, ledger and pipeline-order tests passed, including
  negative controls for changed source bytes, changed measurement output and
  missing producer provenance.
- Independent staffer acceptance passed at 20:59:55 UTC: the same v5 generation,
  source counts, review-only assertions, user assertions and live routes remain
  valid. The sidecar is still PID 18136 and its watchdog is enabled.
- The complete targeted repair suite passed 182 tests. After publication, the
  pipeline audit passed all functional checks (575 passed, eight inventory
  mismatches). The additional network mismatch is `lt_priming.json`, regenerated
  from current inputs by the successful `lt_priming.py` stage.
- The user separately resumed **Review and complete markdown** to change routing,
  office targeting and the standalone interface. Those edits are preserved and
  owned by that task. After its restart, the independent staffer acceptance passed
  again at 21:12:17 UTC on PID 45620 with the same verified v5 graph, counts and
  original user assertions. `staffer_release_lineage.json` distinguishes 35
  unchanged prior-receipt files, five dashboard-repair changes and nine concurrent
  standalone changes. This report does not certify the new routing implementation.
- A broad primacy test run passed 85 tests and seven subtests but exposed an
  existing live-data/frozen-board-order fixture mismatch before vote publication.
  The isolated culling tests passed. No board fixture was changed to force a pass.

## Evidence and pending work

`rebuild.log` preserves the first dashboard stop. The resumed profile/surface run
is in `rebuild_profiles_and_surfaces.log`. `vote_candidate`, `voteview_source`,
`vote_change_summary.json` and `before` retain the examined evidence.
`rebuild_final_surfaces.log` records the successful measurement/profile stages
and the final surface rebuild. The copy of `fec/run_pipeline.py` in `before` was captured after the initial
vote-step wiring; it is not represented as a byte-exact pre-edit backup.
The previous staffer completion receipt remains a historical record. This repair
supersedes its pipeline and generated dashboard hashes; it does not rewrite that
receipt. The original combined HTML, staffer section and staffer HTML were copied
to `before` only after matching their original receipt hashes.

After the rebuild: remeasure the system manifest, run the independent full audit,
verify the current surfaces and protected staffer state, and issue a final report
with actual receipts. Do not change source timestamps or fabricate promotion facts.

Vote source documentation: [Voteview member-vote data](https://voteview.com/articles/data_help_votes).
