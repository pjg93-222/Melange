# Staffer stabilization continuation — September 5, 2026

## Final staffer v5 outcome — 19:34 UTC

Staffer v5 is live and independently verified. The final sidecar is PID 18136,
started at 19:27:39 UTC; API acceptance passed at 19:31:38 UTC and again at
19:33:54 UTC after the final map-control layout fix. Fresh browser checks passed
afterward. The `MelangeStafferLiveSidecar` watchdog is enabled and
Ready. This completes the scoped staffer stabilization and storage objective.
The combined dashboard has a separate unresolved audit, described below.

- The primary and twin builds passed independent numerical verification. Six
  files are byte-identical; the manifest differs only in `generation_id`.
  The served graph receipt SHA-256 is
  `71103ee457a6f20f7a2ad1cc6024ff33be87b5b35397418b8cb0276b96bd3879`.
- The service is Ready with no errors, graph verification PASS and seven served
  interface assets matching the current source files. Ranking remains exploratory.
- All 690,500 records are searchable: 497,738 person records, 190,845 organizations,
  1,833 offices, 36 policy areas and 48 unresolved payroll observations. All held
  Quorum IDs, all 54,073 native LDA organization IDs and all 3,641 verified graph
  institution IDs are conserved. Records are not a deduplicated headcount.
- The sealed full LDA catalog passes its byte hash and source-role checks:
  1,037,547 activities and 5,565,148 relationship assertions, with zero missing
  endpoints. LittleSis retains its three missing endpoints and one invalid date
  as visible source exceptions.
- All 100,256 review assertions survive profile refresh and identity overlays;
  zero are promoted into the model. The two repaired source-profile cases expose
  their exact seven and fifteen assertions, all review-only.
- Collection remains COMPLETE_WITH_EXCEPTIONS: all 18,618 profiles accounted for,
  with 17,127 content-bearing, 1,473 unavailable and 18 accepted source gaps;
  pending, unresolved and failed counts are zero. The completed collection is
  not labeled stale.
- The unchanged coworker statement yields the Gordon-to-Stephanie route at cost
  1. Excluding user assertions yields reported lobbying activity at cost 2.
  Preference changes clear the previous route; standing statement dates and
  Eastern timestamps display correctly. Real coworker pages retain keyboard
  focus and do not change collaborator pagination. No statement was changed.
- The restart launcher now uses file-backed output so a detached server cannot
  keep a captured pipe open indefinitely. The final repin completed normally;
  its integration run passed 111 checks.
- Map controls are positioned inside the map with 44-pixel touch targets. A fresh
  browser check confirms that the confirmed route and Fit map control work after
  this final layout change, with no browser console errors.

Independent evidence: [final API validation](STABILIZATION_V5_LIVE_VALIDATION_20260905.json)
and [final browser and watchdog validation](STABILIZATION_V5_BROWSER_VALIDATION_20260905.json).
The successful pre-profile-fix API run is preserved separately as
`STABILIZATION_V5_LIVE_VALIDATION_20260905_BEFORE_PROFILE_FIX.json`.
The coordinated task owns the full graph, inclusion and interface
[completion report](../staffer_network/sna_review_20260905/COMPLETION_REPORT.md).

Storage cleanup recovered 117,196,132,352 bytes net (117.2 GB) by removing six
inactive worktrees and four fully merged local branches after verifying recovery
archives of every unique local file. After the completed builds, C: still had
109.65 GB free at 19:32:58 UTC. See the
[cleanup report](../disk_cleanup_20260905/CLEANUP_RESULT.md).

### Remaining combined-dashboard audit

The rebuilt combined HTML does **not** have a passing global audit: 570 checks
pass and 13 fail. The failures cover personal-texture propagation, press source
hash/intake parity, an outdated externally prepared vote input, culling promotion
state, scenario tier priorities, seven inventory/sentinel checks and one stale
dashboard-data dependency. Full details are preserved in
[global audit output](../staffer_network/sna_review_20260905/global_audit_details.log).
These checks were not weakened, source dates were not changed to manufacture
freshness, and no culling promotion was invented. Staffer PASS does not certify
the combined dashboard. Repairing those domains is the next separate work item.

The checkpoints below are historical; their storage/build blockers and v4 status
have been superseded by this final v5 result.

## Historical release continuation — 18:29 UTC

Storage is resolved: six inactive worktrees and four fully merged local branches
were removed after all unique files were archived and verified. Net recovery was
117.20 GB; C: had 119.06 GB free at the final 18:27:14 UTC measurement. The live
service and protected file checks passed before build maintenance began. See
`../disk_cleanup_20260905/CLEANUP_RESULT.md` and its JSON evidence.

The authorized v5 primary build is running under the coordinated task. The named
watchdog is held and the verified old sidecar was stopped for build memory
headroom. Primary/twin generation, independent verification, publication and
service/watchdog restoration remain with that task. This task owns the separate
final live route, assertion and browser checks after v5 begins serving.

No v5 completion is claimed at this checkpoint. The following 18:08 service
receipt records the last verified v4 state before maintenance.

## Historical verified outcome — 18:08 UTC

The service is restored on verified v4, PID 70288, started at 18:06:17 UTC.
Final API validation passed at 18:07:44 UTC and browser checks passed afterward.
The named `MelangeStafferLiveSidecar` watchdog is enabled again.

- Ready is true, errors are empty, and six served interface assets match the
  current files byte for byte.
- Completion remains COMPLETE_WITH_EXCEPTIONS: 18,618 records accounted for,
  including 17,127 content-bearing profiles, 1,473 unavailable profiles and 18
  evidence-bound source omissions. Completed collection is not labeled stale.
- The original coworker statement remains active. Gordon to Stephanie has cost 1
  through the confirmed statement and cost 2 through reported lobbying activity
  when user assertions are excluded. Cached responses retain search timing.
- Changing route preferences clears old hop text. Successful statement changes
  now emit an event that immediately invalidates pending and displayed routes.
  No actual statement was changed during verification.
- The full-inventory worker retains searches entered while loading; its failing
  reproduction now passes. The coordinated owner also rejects stale load results.
- Browser checks confirm Eastern timestamps for identity checks, source and
  verification times, and the footer. Standing statements display their active
  as-of date without presenting the calculation cutoff as an expiry.
- The source catalog passed: 306,368 LittleSis person records, 136,772 organizations,
  5,773 Quorum records and 1,880,491 relationship assertions. One malformed date
  and three missing endpoints were retained and flagged. These source assertions
  do not add new route weights.

Evidence: `STABILIZATION_POST_INTEGRATION_VALIDATION_20260905.json`,
`STABILIZATION_BROWSER_VALIDATION_20260905.json`, and the coordinated task's
`../staffer_network/sna_review_20260905/live_acceptance.json`.

The scored v5 primary/twin build and publication remain blocked by storage. C:
has about 1.9 GiB free; the build requires at least 8 GiB free. The user has been
asked to free space or provide another build location. V5 has not been repinned,
and the broader explorer/mobile review remains with the coordinating task.

## Publication runner checks

The continued review repaired `fec/surfaces/repin_staffer_live.py`:

- Backups and rollback retain exact UTF-8 bytes and mixed Windows/Unix line endings.
  Repinning changes only the two selected constant values.
- Before rewriting anything, the selected generation receipt must match exactly
  one verification entry with identical primary/twin SHA-256 hashes.
- Live acceptance requires no reported errors, PASS verification, and the exact
  verified graph-receipt filename under the selected generation. A generation
  name appearing merely as a substring no longer qualifies.

Validation: 19 unit tests and 11 subtests passed, using small fixtures and mocked
live responses. The real pinned `staffer_social_network_20260903_v4_primary`
receipt also passed the strengthened gate in a read-only check. Its SHA-256 is
`36b08a581f98229d35c50620a8d212ea7834abde96f817dcdaab724e8403fb73`.
No repin or process restart was performed by this continuation.

Byte-exact pre-edit copies of the runner and its tests are under
`backups/stabilization_20260905/fec/surfaces/`.

## Historical maintenance checkpoint — 17:57 UTC

The healthy live validation at 17:42 UTC in the earlier stabilization result is
historical. The coordinating network-repair task subsequently stopped the sidecar
to reduce memory pressure after disk exhaustion. It disabled the named
`MelangeStafferLiveSidecar` scheduled watchdog for maintenance and owns restoring
the service and watchdog. The last free-space check was approximately 2 GiB;
the coordinated full graph build requires more headroom.

That task owns the new full-inventory interface, Quorum/LittleSis source catalog,
primary/twin graph generation, independent verifier, dashboard and repin. This
task remains responsible for the final API/browser regression after it signals
readiness. The source catalog retry encountered a malformed native date
`2018-05-o5`; the finding was sent to its owner for evidence-preserving handling.
The new v5 generation is not verified or published at this checkpoint.
