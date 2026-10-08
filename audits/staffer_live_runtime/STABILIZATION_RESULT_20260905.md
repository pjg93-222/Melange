# Staffer stabilization result — September 5, 2026

## Verified outcome

The live sidecar is healthy on the existing v4 generation. Its current PID is
58816, started at 2026-09-05T17:41:42Z. Final API validation passed at
2026-09-05T17:42:50Z, followed by browser verification.

The acquisition receipt is now PASS / COMPLETE_WITH_EXCEPTIONS with zero integrity
failures. Its partition is 17,127 profiles with the required content, 1,473 verified
unavailable profiles, and 18 evidence-bound source omissions, totaling 18,618.
The omissions are not reported as populated content. All 18 were checked through
the authenticated rendered browser: 17 displayed the scoped page-not-found message;
Grace Molson rendered a current position with no employment-history section. Saved
HTTP-200 API evidence independently binds the missing collections to each UUID.
Existing API history remains intact even when the rendered page is unavailable.

The bridge primary and twin at `politico_payroll_direct_links_20260905_v4_*` are
byte-identical and their independent verification passed. The full v5 primary
build failed during a NumPy membership allocation; it was not repinned or published.
The failure receipt and partial output directory remain preserved.

## Implemented changes

- Added an explicit source-exception contract and propagated it through the crawl
  verifier, completion report, finishing chain, bridge and graph gates. Missing,
  mismatched, loading, login and failed browser observations do not qualify.
- Rewrote migration tests around a SQLite backup and a synthetic old schema,
  checking schema, retained state and idempotence rather than changing live values.
- Made robots.txt 408/429 transient; bumped identity evidence version for its
  changed provenance shape; prioritized route endpoints in the durable queue.
- Preserved search timing on cache hits, exposed cache timing separately, fixed
  disabled-cost bounds and coworker response metadata, and removed wall-clock
  sleeps from the timing regression.
- Moved the original coworker statement into the persistent assertion store with
  effective dates, retained history, and replace/retract controls. The original
  statement remains active: the user's “co-worker” clarification concerned another
  session, not the people relationship. Identity assertions were preserved.
- Separated completed collection status from inactivity, retained source and
  verification ages, and displayed those timestamps in America/New_York. Routing
  effective dates now use the same timezone.
- Wired source filtering, map zoom and people-list pagination; retained route
  participants; added the statement-panel asset to installation and HTTP serving.

## Validation

- Fourteen-file service suite: 228 passed, 15 subtests passed.
- Completion/API/chain/bridge contract suite: 58 passed.
- After the browser caught the missing statement-script asset mapping, the mapping
  and HTTP regression were added: 18 targeted tests and 15 subtests passed.
- JavaScript syntax checks passed.
- Live API: ready=true, errors=[]; completion=COMPLETE_WITH_EXCEPTIONS; stale=false.
- Gordon Holzberg → Stephanie Belk: cost 1 current_coworker with user assertions;
  cost 2 co_reported_lobbying_activity without them. Cache hits preserve search time.
- Browser: statement record and controls render, both route endpoints are labeled,
  Eastern freshness timestamps render, and no console errors were recorded.
- The unrelated legacy-v3 full-corpus test scan was stopped after it became clear
  it repeated large artifact scans; it is not represented as a completed test suite.

## Coordinated remaining work

The active network-repair task `01a07298-aff6-7320-aac5-8a6208e033ab` owns the broader
graph repairs, independent centrality/component checks, new graph generation,
whole-inventory explorer integration, dashboard rebuild and eventual repin.
This task handed over stable `staffer-live.js` and `index.html` edits and reported
the final healthy sidecar PID and validation receipt. No repin runner is running
from this task. V4 remains available meanwhile.

Before the failed build, C: had about 4.8 GB free and system virtual-memory headroom
was limited. Those observations were handed to the network-repair task. No unrelated
process was stopped. The exact origin of the earlier 16:32:57Z restart was not proven;
the watchdog log does not show it launching that restart. Both restarts in this task
were restricted to the PID whose command and listener matched this sidecar.

The wider UX task was also told that the footer snapshot timestamp still displays
raw UTC and the expanded statement editor can cause horizontal scrolling in the
left pane. These are outside the completed freshness display checks.

## Evidence and recovery

- `STABILIZATION_DECISIONS_20260905.md`
- `STABILIZATION_LIVE_VALIDATION_20260905.json`
- `STABILIZATION_CHANGES_20260905.json`
- `stabilization_full_tests.log`, `stabilization_contract_tests.log`
- `stabilization_chain.stdout.log`, `stabilization_chain.stderr.log`
- `../staffer_network/FINISH_CHAIN_HALT_20260905T173405Z.json`
- `../staffer_network/politico_profile_crawl_20260903_raw/browser_source_exceptions_20260905.ndjson`

Byte-exact pre-edit copies are under `backups/stabilization_20260905/`, retaining
repository-relative paths. Pre-restart process/log records are in its two
`pre_restart*` folders. Changes remain uncommitted. Restore only the relevant hunks
after checking for subsequent work by the coordinated task; whole-file restores
could overwrite its later changes. The original supplied Downloads markdown remains
a historical handoff.
