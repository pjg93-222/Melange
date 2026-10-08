# Relationship evidence and identity boundary adjudication — 2026-09-08

Status: adjudicated, independently reviewed, tested and live. Commit receipt
follows the scoped source commit.

## Decision

Retain the v8 source spine and duration-based graph. Do not claim that a record
match, co-employment interval, PageRank, or shared-background score measures how
well two people know each other. No familiarity labels or outcome data have been
validated, so there is no defensible error rate or closeness probability to publish.

Fix bounded evidence errors in consumers without retuning the graph:

1. Use name standard 1.2's complete surname and suffix as a veto on automatic
   identity candidates. The legacy last-token parser previously accepted
   `Robert de los Santos` versus `Robert Santos` when middle tokens were omitted.
   Preserve existing first-name candidate classes: importing every nickname class
   would also newly equate distinct formal names (for example Patrick/Patricia).
   This veto is a partial consumer migration, not a claim that every parser has
   been standardized. Conflicts remain separate for source review.
   Identical complete normalized token sequences retain punctuation equivalence;
   this preserves Connery-Dawe/Connery Dawe and Jr-Urbieta/Jr.-Urbieta without
   accepting any omitted, reordered, or expanded tokens.
2. Fail closed when an installed spine has lost its payroll configuration or
   bundle, regardless of generation. The old fixture exception recognized only
   v7 and could silently fall back to whole-career last-title evidence on a
   v8-only installation. Empty service fixtures may still omit payroll.
3. Apply the identity overlap rule to routing episodes explicitly marked
   `presence_within_report`. Two uncertain windows and partial coverage cannot
   establish co-employment. Full coverage supports presence somewhere in the
   window, with unknown duration. Do not reclassify the separately adjudicated
   observed-report-core source model as exact daily service or change its rules.
4. Affinity routing obtains employment points only from work evidence. Shared
   lobbying reports remain searchable through activity and evidence-cost routes;
   they no longer receive the fallback past-employment contribution. Shared
   background still supplies exploratory affinity routes and is labelled as such.
5. Expose each hop's evidence class, temporal support, and the absence of measured
   familiarity. Latest-listed common employers alone do not establish current
   co-employment. Display a shared-background score, not connection strength.

## Math and untouched areas

The previous independent graph verifier establishes computational agreement on
the declared model: interval union/intersection, positive edge construction,
attribution conservation, and ranking. It does not validate the source dates or
the relationship interpretation. The baseline selected graph has 144,692 people,
4,546,099 positive co-tenure edges, and 23,699 isolates. Source payroll evidence
has 425,825 episodes and conserves 1,351,415 admitted rows.

The graph's shared-role factor of 0.05 was selected by a diagnostic top-100
composition threshold. It is provisional, not fitted against known closeness.
Do not optimize that threshold further to produce preferred people. The live
affinity weights (128 through 1) and balanced step penalty are also preference
parameters, not probabilities. This change does not alter either set of numeric
coefficients, graph source rows, canonical identity assertions, or member ranks.

Remaining worthwhile work requires additional evidence or a separately reviewed
model migration: row-level shared-role attribution instead of whole-span last
titles; employer size and time-since-service sensitivity; source-window versus
   day-date coverage by stratum; labelled namesake and nickname-class adjudication;
and held-out human assessments of actual relationships. Office co-presence does
not establish direct interaction. Sparse profiles and missing careers can change
route availability. A chain of valid associations does not establish that an
introduction will succeed.

## Verification and ownership

The initial 64 targeted tests passed before edits. New negative controls exercise
compound surnames even with a shared external ID, missing v7/v8/future-generation
bundles, all service-day possibilities in three-day payment windows, shared
activity versus work, latest-employer temporal limits, and assertion filters.
Existing exhaustive routing tests compare all simple paths on 100 independently
generated small graphs for three objectives. Retain those comparisons.

`capture.py` stores exact pre-edit source bytes, pinned input hashes and the live
identity inventory for a before/after census. Only this task's deltas are to be
staged. The dashboard task's newly requested intern exclusion is preserved;
port 8841 and `staffer-route.js` ownership are coordinated with that task.

Independent Astra review rejected the initial draft on two points: report cores
were being labelled like daily service, and changed models were missing from the
service revision. Both were fixed, including mixed uncertain-window/report-core
pairs. Report-core support is now explicitly modeled, actual duration is unknown,
and every affected model version participates in revision/cache invalidation.
Final independent review: PASS, 95 tests, no open blockers, exact-file bindings in
`independent_review.json`. The reviewer examined but did not rerun the full census.

Full immutable-input census: 195,847 nodes, 478,819 identity episodes, six eligible
references; 5,872 to 5,860 automatic aliases. Exactly 12 links were withdrawn and
zero were added. Every changed pair is enumerated in `identity_delta.json`.
Disposition: keep separate source identities pending explicit full-surname or
name-change evidence. This does not establish 12 pairs of distinct humans and is
not a corpus error-rate estimate. The raw 231 payroll record-pair observations
remain retained; the display resolver applies its compatibility gate to them.

199 targeted checks pass, including the 32 new boundary cases, exhaustive route
comparisons, identity consolidation, service/server behavior, intern scope and
graph arithmetic. The proposed committed modules separately pass all 32 boundary
cases. Both live and committed-variant JavaScript pass Node syntax checking.

Live service PID 34020 is ready without errors on port 8841, serving the coordinated
Moneyball_Redesign.html. The complete live alias delta equals the offline delta.
All 24 affected source profiles were checked individually and remain accessible
under separate IDs. Pinned spine/graph receipts and payroll configuration hashes
are unchanged; ordinary startup source-hash gates passed. Visible network rows
increased 127,914 to 127,926; source reconciliation holds. The dashboard's 52,107
intern exclusions and current-staff count of 14,216 are unchanged.

Three live path probes retained their exact paths and costs: Gordon Holzberg to
Stephanie Belk (one step, cost 1), Gordon Holzberg to Gregory Mesack (one step,
cost 1), and Gordon Holzberg to Grace Ryan under fewest-steps affinity (two steps,
cost 7.695239). The last path explicitly identifies its background-only step.
These probes are regression checks, not relationship validation or an exhaustive
census of all possible routes. The served route JavaScript matches the reviewed
file exactly. Detailed before/after inventories and route evidence remain local.

Only six production deltas, the new boundary suite and this audit's supporting
artifacts are committed. Other tasks' source changes remain in the shared tree.
`live_dependencies.patch` records the difference between the committed variants
of these six files and their tested live versions; it includes the dashboard's
pre-existing intern integration. It is not a complete snapshot of other tasks'
untracked modules. `integration_test_delta.patch` records the three wording
assertion edits to the already-untracked integration suite. Original source bytes
remain in `before/`; no canonical data were changed and no remote push was made.

Scope limitation: the earlier repository-wide audit had 554 passes and 15
classified failures. This targeted pass does not close those unrelated failures
or certify the entire personal corpus as correct.
