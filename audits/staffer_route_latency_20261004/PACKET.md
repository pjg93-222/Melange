# Staffer route latency: diagnosis, evals, build prompt (2026-10-02)

Read-only diagnosis. Nothing in the repository or the sidecar was changed. Every algorithmic claim is
marked VERIFIED (the line was read) or INFERRED.

## 0. Paul's rulings (2026-10-02)

- Scope: core exact fix, plus responsiveness (cancel abandoned searches, show route 1 while the
  alternatives finish), plus typeahead and lock contention.
- Real-data check: synthetic exactness tests offline, then a live panel after Paul applies the patch
  and restarts 8841.
- Landmark (ALT) A* heuristic: deferred until the bidirectional search is measured.
- Ties: cost and steps must match exactly; equal-score paths may differ and each swap is listed.

Second rulings (2026-10-03, Paul: "b on ties, fix the uuid match, keep identity loop"):
- Ties, option (b). A route counts as tied when its exact cost is within 1e-12 relative of the
  minimum. Among tied routes, fewer steps wins, then lower exact cost. The reported cost is still
  the forward-order float sum. Builder branch: claude/staffer-route-ties-20261003.
- Typeahead no longer matches fragments of machine identifiers such as politico:<uuid>, bare uuids,
  source ids and hashes. A query equal to a full id still finds that node. Builder branch:
  claude/staffer-search-uuid-20261003.
- The identity loop keeps running at its current pace. No change.

Brain drafts for these rulings, for Paul to apply:
- D-082 "Staffer route near-ties resolve to fewer steps". In the work_time search, routes whose exact
  costs are within 1e-12 relative of the minimum are ties; fewer steps wins, then lower exact cost.
  Reversal: Paul asks for bit-identical behaviour with the old one-way search.
- D-083 "Typeahead never matches fragments of machine identifiers". Typeahead matches human-readable
  fields only; an exact full id or uuid still returns its node. Reversal: Paul wants id-fragment
  search back.
- D-084 "The staffer identity loop stays running". Its pace is unchanged; status() runs outside the
  service lock. Reversal: Paul pauses or throttles it.

Build layout: WP-A core search (branch claude/staffer-route-core-20261002, worktree
C:\Users\pgoff\Melange-wt\route-core); WP-B cancellation and progressive results (branch
claude/staffer-route-jobs-20261002, worktree C:\Users\pgoff\Melange-wt\route-jobs); WP-C typeahead and
lock diagnosis (read-only, fix scheduled after WP-B because both touch staffer_live_service.py). One
merged patch is cut against LIVE bytes with fec/tools/live_patch.py and applied only on Paul's APPLY.

## 1. Measured problem

| Surface | Measurement (2026-10-02, live sidecar 8841, PID 10876) |
|---|---|
| Page load, `/staffer-live/` | 11 requests, 110-300 ms total per load, 2.8 MB on the wire (`/api/staffer-live?limit=1800` 0.63/2.25 MB, `/api/staffer-network-index` 2.18/8.37 MB wire/decoded). Not the bottleneck on the server side; browser parse and render time not measured. |
| Default office route (UI defaults) | One request ran about 5.5 min at 0.75-1.0 core. First 49.7 s: 7,190 expansions, 1,371,818 neighbour checks (145 expansions/s). Sidecar working set 7.0 GB to 17.5 GB peak; host available RAM fell to 0.22 GB; the box nearly ran out of memory. After the search the sidecar stayed at about 10.4 GB. |
| Earlier receipts (2026-09-10) | Single 3-step route Gordon to Casca: 6,282 expansions, 985,370 checks, 25.3 s (about 157 checks per expansion, about 26 us per check). Three distinct routes: 6,565 / 9,041 / 14,497 expansions, 136.7 s; the "independent" option 217 s. A 13-person office with 34 expansions still took 2,485 ms (fixed overhead). |
| People typeahead | n=16 uncached: p50 596 ms, p95 8.4 s. |
| Office typeahead | n=26: p50 39 ms, p95 442 ms, max 41.2 s. |
| Idle sidecar | 0.34 core average with no client; the identity loop (57,575 queued) holds the service lock about 0.7 s every 30-35 s. |
| Startup | 146-324 s to Ready (2026-09-10 receipts), including a full SHA-256 of the 1.4 GB activity database. |

## 2. Root cause of slow office routes

1. VERIFIED. The UI default is `objective=work_time`, `route_count=3`, `alternative_strategy=distinct`
   (`fec/surfaces/staffer_live/index.html:20,25-27`; `staffer-route.js:64,186`; confirmed by two
   independent agents).
2. VERIFIED. That path ends in `ClosenessRoutes.search` (`fec/surfaces/staffer_closeness_routes.py:110-138`):
   a ONE-directional Dijkstra from the origin to a virtual SINK. Office staff enter only as arcs
   `p -> SINK` with terminal cost `-log(factor) + uncertainty_weight * anchor_uncertainty` (`:70-81`,
   `:125-126`). A person target has terminal cost 0. There is no heuristic.
3. INFERRED. Office terminal costs are positive (the uncertainty term alone is at least about 0.6), so
   Dijkstra must settle every person closer than the best `staff distance + terminal cost`. The search
   ball for an office is wider than for a person, and in this graph each extra half hop multiplies the
   explored set. This is the effect Paul observed as "the heuristic gets messed up because there are
   multiple people".
4. VERIFIED. If no staff member has an office anchor above 0 (`if anchor > 0:`, `:76`), the SINK is
   unreachable and the search scans the whole connected component before it returns.
5. VERIFIED (code) and measured. Each expansion evaluates every all-time shared-workplace neighbour
   (`index.pair()` + `uncertainty()`, about 70% of them without any time overlap) and stores a full
   evidence dict for every checked pair in a per-call cache (`:82-109`). That is about 1 KB per check,
   which explains the 10 GB spike.
6. Reported with quotes, not re-read. `distinct_routes` runs up to 3 such searches, each from empty caches,
   and later ones grow as people are excluded (`staffer_distinct_routes.py:56-61`).
7. Reported with quotes. Searches are never cancelled: 2-worker pool (`staffer_live_service.py:145`),
   "active jobs always finish" (`:1459`). Cancel and avoid-person in the UI leave the old search
   running and submit a new one.

## 3. Paul's design against the code

- "Every current member of the office heads toward the person trying to reach them" is a backward
  frontier seeded from the whole roster. It already exists, but only in the Ecosystem objective
  (`staffer_routing.py:528-530`, VERIFIED) and in `OverlapRoutes`. The default Staffer (`work_time`)
  path does not have it.
- No route path has a heuristic. Every one runs with heuristic 0 (`staffer_routing.py:381`), so all of
  them are Dijkstra. The snapshot's `'algorithm': 'A*'` label (`staffer_live_service.py:1354`) is a misnomer.
- Applying the design to `work_time` is exact. Seeding each current staff member at its terminal cost is
  the same as expanding the virtual SINK first, so the optimum, coefficients and model versions do not
  change (D-025).
- The A* part: this graph has no geometry, so an admissible heuristic needs precomputed landmark
  distance tables (ALT) per revision and option set. On low-diameter social graphs those bounds are
  usually weak. Recommendation: build bidirectional search now (A* with zero heuristic), measure, and add
  landmarks only if the targets are missed.
- Bidirectional search shrinks suspect 5 (each search's ball). Suspects 6 and 7 (three searches from
  scratch, uncancelled jobs) and the memory per check need their own fixes. They are in the build prompt.

## 4. Eval definition (eval-harness)

Proposed file at build time: `.claude/evals/staffer-office-route-latency.md`.

### Capability evals
- **C1 Exactness, synthetic.** At least 2,000 seeded random graphs and queries with 5-200 nodes, positive
  costs with exact ties, 0-30 targets with terminal costs that include 0, origin inside the target set,
  zero-anchor offices, blocked nodes and edges, and excluded contexts. Compared with the current
  one-directional search, the new search must give the same status, cost (absolute 1e-9) and steps. Every
  returned path must be valid, and its recomputed `path_cost` must equal the reported cost. Target pass^3 = 100%.
- **C2 Exactness, real data.** A panel of at least 30 queries: at least 15 office queries, including a
  roster of 150 or more, a zero-anchor office and the 2026-10-02 intelligence-subcommittee case; at least
  15 person queries, including the README case "Gordon to Grace J Ryan = 3 steps". All three distinct
  routes are compared. Status, cost and steps must be identical. Paths may differ only on exact ties,
  and each one is listed.
- **C3 Latency**, live sidecar, UI defaults, sequential, cold cache. Proposed targets: office default first
  route p95 ≤ 3 s and all 3 routes p95 ≤ 10 s; person default p95 ≤ 5 s; cache hit ≤ 200 ms. Report
  p50, p95 and p99 with n.
- **C4 Memory.** Peak sidecar growth ≤ 500 MB per request. After completion it returns to within 200 MB
  of baseline, or any retained cache is bounded and declared.

### Regression evals
- **R1** Every `fec/surfaces/test_staffer_*.py` passes, with the baseline count recorded before the change;
  the kernel stays at its baseline (standing reds only).
- **R2** For an identical path, the hop payloads (evidence, labels, provenance) are byte-identical.
- **R3** The Ecosystem and overlap objectives give identical outputs on the panel.
- **R4** No change to any coefficient, cost formula, terminal cost, roster rule or model version
  (checked by grep on the diff).

### Gates
R1-R4 and C1 at pass^3 = 100%; C2 with zero cost or step mismatches; C3 and C4 at the targets Paul sets.

## 5. Optimized build prompt (prompt-optimizer)

### 5.1 Diagnosis of the original ask
Strengths: it names the slow case (office targets) and a concrete algorithm, and it insists on
identifying the problem before building.

| Issue | Impact | Fix in the prompt |
|---|---|---|
| "The heuristic gets messed up": the code has no heuristic | A builder would tune something that does not exist | Target the one-directional search, the memory per check and the multipliers |
| "Bidirectional A*" without a heuristic source | A* collapses to Dijkstra or needs a landmark precompute | Exact bidirectional search first; ALT gated on measurement |
| The default UI path is not named | A builder might patch the Ecosystem path, which is already bidirectional | Name `ClosenessRoutes.search` (`work_time`) |
| No latency or memory target | No way to tell when it is done | C3 and C4 targets |
| No exactness requirement | Faster but different routes | C1, C2, R2 |
| No scope boundaries | Coefficient or UI drift (D-025) | Explicit do-not list |

### 5.2 Components
- Build: executor agent on Sonnet 5.5 at xhigh effort (standing directive 2026-10-01).
- Verify: architect agent on Opus 5.5 at high effort, adversarial review plus its own test rerun.
- Landing: patch cut with `fec/tools/live_patch.py` against LIVE bytes (D-060), applied only on Paul's
  APPLY; sidecar restart is Paul's call.

### 5.3 Full prompt

```
ROLE: Builder for the Melange people-network (staffer live sidecar) route-latency fix.
Python 3.12 on Windows. Repo: C:\Users\pgoff\OneDrive\Desktop\Melange Systems. That checkout is the
LIVE tree on main: never edit it. Work in a new git worktree off current main.

GOAL: Make the default office route search fast and memory-bounded without changing any answer.
Paul's design: every person currently listed as staff of the target office searches backward toward
the person trying to reach them, while that person searches forward; the searches meet in the middle.

WHAT RUNS TODAY (verified 2026-10-02):
- UI default: objective=work_time, route_count=3, alternative_strategy=distinct
  (fec/surfaces/staffer_live/index.html:20,25-27; staffer-route.js:64,186).
- Office path: staffer_live_server.py:634 -> staffer_live_service.start_route_search (2-worker pool,
  :145) -> office_route (:1499-1519) -> staffer_routing.route_many -> staffer_distinct_routes.distinct_routes
  (route_many :479-481) -> up to 3 x route_many(route_count=1) -> ClosenessRoutes.route
  (fec/surfaces/staffer_closeness_routes.py).
- ClosenessRoutes.search (:110-138) is a ONE-directional Dijkstra from the origin to a virtual SINK.
  Office staff with anchor > 0 appear only as arcs p -> SINK with terminal cost
  -log(factor) + uncertainty_weight * anchor_uncertainty (:70-81, :125-126). Person targets have
  terminal cost 0. Priority key is (cost, steps); the SINK arc adds no step. No heuristic.
- neighbors() (:86-109) evaluates index.pair() + uncertainty() for every all-time shared-workplace
  neighbour (about 26 us each, about 157 per expansion, about 70% with no overlap) and stores a full
  evidence dict per checked pair in pair_cache (:95-99): about 1 KB per check. One default office
  route on 2026-10-02 grew the sidecar from 7.0 to 17.5 GB and ran about 5.5 minutes.
- distinct_routes recomputes each of its 3 searches from empty caches.
- staffer_routing.route_many (:528-560, Ecosystem objective) already runs a bidirectional search with
  a reverse frontier seeded from all targets. Use it as the style reference; do not modify it.

BUILD:
1. Tests first: fec/surfaces/test_staffer_closeness_bidirectional.py
   a. Keep the current one-directional search as an internal oracle (_search_reference), reachable only
      from tests; it is never selectable from the UI or an HTTP parameter.
   b. Property test: at least 2,000 seeded random graphs and queries (5-200 nodes; positive costs with
      exact ties; 0-30 targets with terminal costs including 0; origin among the targets; zero-anchor
      offices; blocked nodes and edges; excluded contexts). New vs oracle: same status, cost within
      absolute 1e-9, same steps. Every returned path is valid and its recomputed path_cost equals the
      reported cost. Fixed seeds; run the suite 3 times (pass^3).
   c. Unit tests: with no target anchor > 0 the search returns unreachable at once (no component scan);
      the progress callback still reports expanded, neighbor_checks and elapsed_ms summed over both
      sides; for an identical path, hop payloads are byte-identical to the oracle's.
2. Implement bidirectional search in ClosenessRoutes:
   - Forward frontier: the origin at (0.0, 0).
   - Backward frontier: each target p with anchor > 0 at (terminal[p][0], 0). This is expanding the
     SINK first.
   - Person edges are undirected with the same cost formula. Apply the same allowed(), strength > 0,
     excluded_contexts, blocked_nodes and blocked_edges filters when entering a node from either side.
   - On every relaxation, if the node already has a label from the other side, update
     best = d_forward + d_backward (tuple addition).
   - Stop when top_forward + top_backward >= best (lexicographic tuples). Any additional pruning bound
     needs a written proof in a comment and its own test.
   - Expand the side with less accumulated neighbour-check work (or the smaller top key). Document the
     choice; correctness must not depend on it.
   - Return the same shape as search(): ([origin, ..., staff, SINK], cost).
3. Memory: during the search, cache per pair only what the search needs (the cost, plus a compact
   context-id set if needed for exclusions). Build full evidence dicts (index.pair + uncertainty +
   adjusted_strength) only for pairs on returned paths, and make them identical to what the current
   code produces.
4. Reuse: share the neighbour-cost cache across the up-to-3 distinct-route iterations of ONE request.
   Apply exclusions at relaxation time, never baked into cached lists. Optional: a bounded LRU across
   requests keyed by router revision, activity revision, as_of, work_sources, uncertainty_weight and
   every other option that changes a cost, with a hard entry cap and a reported memory figure.
5. Labels: any result field that names the algorithm must state what ran
   (for example "Bidirectional Dijkstra", heuristic 0).

DO NOT:
- change any coefficient, HOP_FACTOR, MEMBER_BETA, uncertainty model, cost formula, terminal cost,
  roster rule or model version (D-025);
- add a wall-clock or work cap that cuts off a route (routes run to proof, staffer_routing.py:519-521);
- touch route_many, the Ecosystem or overlap paths, the UI, the identity loop, startup hashing or
  typeahead;
- start, stop or restart the 8841 sidecar (Paul's call), write to the LIVE tree, or call any POST or
  identity endpoint;
- load a second full copy of the graph on this host while 8841 runs (available RAM is about 1-5 GB).

VERIFY AND REPORT:
- Run every fec/surfaces/test_staffer_*.py before the change (record baseline counts) and after;
  zero new failures.
- Report tests added or changed, the pass^3 result and the diff stat. Cut the patch with
  `python fec/tools/live_patch.py` against LIVE bytes (D-060); do NOT apply it.
- Hand off to an Opus 5.5 (high) verifier for adversarial review of the stopping rule, SINK seeding,
  tie handling, filter symmetry, memory and the oracle comparison; it reruns the tests itself.
- After Paul applies the patch and restarts 8841, run the live panel from eval C2/C3 sequentially:
  GET only, UI default parameters; abort if host available RAM < 400 MB or the sidecar grows by more
  than 1.5 GB. Report p50/p95/p99 wall and server time, expanded, neighbor_checks, peak memory growth
  and agreement with the oracle where the oracle finishes within 120 s.

ACCEPTANCE: evals C1-C4 and R1-R4 (.claude/evals/staffer-office-route-latency.md). Latency targets:
office default first route p95 <= 3 s and all 3 routes p95 <= 10 s; person default p95 <= 5 s;
peak sidecar growth <= 500 MB per request.
```

### 5.4 Quick prompt

```
Worktree off main. Tests first: closeness bidirectional vs one-directional oracle, >=2,000 seeded
property cases, pass^3. Make ClosenessRoutes.search bidirectional with the backward frontier seeded
from office staff at their terminal costs; store costs only during the search; share the neighbour
cache across the 3 distinct routes. No coefficient, cap or UI change. Opus verifier. Patch via
live_patch.py, not applied.
```

### 5.5 Rationale
| Added | Why |
|---|---|
| Names the real default path and its file:line | The Ecosystem path is already bidirectional; patching it would change nothing Paul uses |
| Backward seeding at terminal costs | That is Paul's design written in exact form; it keeps every answer |
| Oracle plus property tests | Proves "faster, same routes" before anything goes live |
| Memory clause | The 10 GB spike endangers the whole host, not just the page |
| Cache sharing across the 3 alternatives | Removes most of the 3x multiplier without changing the strategy |
| Do-not list | D-025 (coefficients and evidence boundaries fixed); routes run to proof |

## 6. Brain update drafts (for Paul to apply and commit)

STATE.md, add under "Current position":

```
- STAFFER ROUTE LATENCY (2026-10-02, people-network latency lane; read-only diagnosis, NOTHING applied): the UI default route (objective work_time, route_count 3, distinct; index.html:20,25-27, staffer-route.js:64,186) runs ClosenessRoutes.search (staffer_closeness_routes.py:110-138), a ONE-directional Dijkstra to a virtual sink. Office staff enter only as sink arcs with a positive terminal cost (:70-81, :125-126). No route path has a heuristic; the snapshot's 'A*' label (staffer_live_service.py:1354) runs with heuristic 0. A backward frontier seeded from every target exists only in route_many (Ecosystem, staffer_routing.py:528-530) and OverlapRoutes. Measured on 8841 (PID 10876): one default office route ran about 5.5 min at about 1 core, with 7,190 expansions and 1,371,818 neighbour checks in the first 49.7 s; the sidecar went from 7.0 to 17.5 GB, and host available RAM fell to 0.22 GB. The per-call pair_cache keeps a full evidence dict per checked pair (about 1 KB per check). Page load is not the bottleneck: 11 requests, 110-300 ms, 2.8 MB on the wire. People typeahead p95 is 8.4 s; office typeahead max is 41 s. Proposed fix, awaiting Paul: bidirectional work_time search seeded from current office staff at their terminal costs, compact search caches, and cache reuse across the 3 distinct routes.
```

DECISIONS.md, append to D-080's Outcome:

```
Observed 2026-10-02: 8841 is served by PID 10876 (server.json started_at 2026-10-02T14:25:41Z), Ready, verification_status PASS; the MelangeStafferLiveSidecar task is Disabled.
```

DEADENDS.md: none yet. No approach has failed; the heuristic premise was checked and found absent, which
is a finding, not a dead end.

## 6b. Typeahead and lock diagnosis (WP-C, 2026-10-02)

Both typeahead handlers are read-only. Their slow tail is mostly time spent waiting on the
service-wide `self.lock`, not search work. 40 sequential GETs measured: people full names p50 40 ms,
p95 1.59 s; people 2-character queries p50 300 ms; offices p50 26 ms, max 5.96 s (zero CPU, all waiting).

Root causes, by share of the latency beyond each request's own CPU time:
1. **79%.** The identity loop runs `status()` inside the lock (`staffer_live_service.py:683-686`). It
   takes 0.7-2.0 s and 5.6 s under contention, every 25-30 s. Its cost grows with the 684,348-row
   `reference_outcomes` table.
2. **19%.** The 30-second server refresh loop recomputes about 10 CPU-s per cycle from inputs frozen
   since 2026-09-05: `graph()` 4-5 s, one `json.dumps` call of 0.30 s that blocks every other thread,
   and contacts written under the lock at `:966-984`.
3. Short-query compute runs while the lock is held, and the client does not cancel overlapping
   typeahead requests (`staffer-route.js:88`).
4. Incidental bug: the full-network cache is dropped on every poll, because `:982` compares a string
   with the tuple set at `:1172` and `:1258`.

Planned fixes, all inside the approved scope and none changing an answer:
- F1: `status()` outside the lock.
- F2: memoize the refresh's derived results, keyed by their exact inputs; every integrity check still runs.
- F3: lock-free typeahead on one immutable view.
- F4: `snapshot`/`_graph` on the same view.
- F5: pre-tokenised short-query index, behind a differential test proving identical answers.
- F6: the `status()` count in SQL.
- F7: build `router.nodes` and contacts outside the lock.
- Abort superseded typeahead fetches in the client, and fix the `:982` cache bug.

These are built after WP-B, because both touch `staffer_live_service.py`.

Paul's calls:
- (a) Profile search matches substrings of `politico:<uuid>`, so "co", "po" and "li" match every
  profile. Fixing that changes answers.
- (b) The identity loop has yielded 11 accepted outcomes from 684,348 checks. Whether to keep it
  running is Paul's call; after F1 and F6 it no longer blocks requests.

## 6c. WP-A result and Opus verification (2026-10-02)

Commit 629da986 on claude/staffer-route-core-20261002.
- **Exactness:** 2,400 property cases with 0 mismatches and 13 equal-score tie swaps (listed in the
  commit report). 1,440 real-index queries and 415 payload comparisons were identical to HEAD.
- **Speed:** synthetic benchmark, 20,000 people and 1,000 offices. Person routes went from a median
  24.2 s to 0.92 s (26x); office routes from 12.9 s to 0.77 s (17x).
- **Memory:** about 28 MB of cache against about 2.7 GB for the old per-search pair cache. The caps
  allow about 300 MB.

Verifier verdict: PASS-WITH-FIXES. Concurrency, caps, cancellation, filter symmetry and payload
identity all pass; 115 tests passed in the 8 route suites.

Fixes queued for integration:
- (1) `install_staffer_live.py` FILES must list `staffer_route_cancel.py`. This is a deployment
  blocker: every work_time route would return search_error.
- (3) The LRU key uses id/len of `router.nodes`, which the service replaces every 30 s poll, so the
  cache resets. Key it on a nodes revision that the service bumps instead; that also closes (4).
- (5) Put the frozenset itself in the key, not (len, hash).

Open ruling (2): floating-point near-ties. When two paths tie in real arithmetic, the
forward-plus-backward sums can round differently from the old forward-only sum. In 40,000 tie-heavy
synthetic graphs there were 102 step mismatches and 30 cost mismatches of 1-2 ULP, with 0 status
mismatches. Real-data incidence is expected to be low.
- (a) Accept it and document it.
- (b) Choose among candidates by forward-order cost; costs within 1e-12 relative count as equal,
  and fewer steps wins.
- Recommendation: (b). It enforces the documented "equal cost, fewer steps" rule deterministically,
  where the old choice was a rounding artifact.

## 7. Evidence
- Live measurement: `scratchpad/latency/` (`all_raw_rows.csv`, `load_timing_rows.csv`, `route_raw/001_office_default_c1.json`, `typeahead_search_rows.csv`, `passive_watch_log.txt`).
- Brain boot output: `scratchpad/boot.txt`.
- Receipts cited by the analysis: `audits/staffer_governing_audit_20260910/live-gordon-casca.json`, `audits/staffer_payroll_promotion_20260910/promoted.json`, `after_work_office.json`.
