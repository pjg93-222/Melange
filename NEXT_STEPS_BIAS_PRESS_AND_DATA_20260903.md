# Melange Dashboard: Recommended Next Steps

Date: 2026-09-03

## Current baseline

- The dashboard and workbook use the following overall scoring weights:
  - Legislative action: 45%
  - Press sentiment: 10%
  - Influence: 40%
  - Demographic potential: 5%
- Press may affect issue and overall labels. Its nominal label-evidence weight is 10%, compared with 55% for legislation and 10% or 20% for recorded votes.
- Press does not currently affect primacy-tier placement.
- There are no active member-specific tier placements in `tier_overrides.json`.
- The regenerated dashboard passes the calibration guard, dashboard-integrity audit, 31 rendered-dashboard checks, and the focused scoring tests.
- The complete repository audit is not yet clean because some narrative, receipt, and manifest artifacts are stale.

## Priority 1: Remove outcome-targeted tier calibration

The current uncertainty penalty uses `K=0.25`. The source documentation says that value was selected partly so Juan Vargas would remain in Tier 1. Although this is not a direct member pin, it is an outcome-targeted calibration and should be replaced with a member-neutral rule.

### Work

1. Define an outcome-independent objective for the uncertainty penalty, such as out-of-sample stability, measurement reliability, or error minimization.
2. Run a sensitivity analysis across a reasonable range, including `K=0`, and publish:
   - tier entry and exit counts;
   - changes at each tier boundary;
   - party, chamber, tenure, and evidence-volume distributions;
   - members most affected by each candidate value.
3. Select the value using the published objective without considering whether any named member remains in a preferred tier.
4. Remove named-member rationales from parameter documentation.
5. Add an audit that rejects active scoring-policy comments or configuration fields that describe a parameter as preserving a named member's outcome.

### Acceptance criteria

- The selected value is reproducible from a documented, member-neutral procedure.
- No member-specific placement is active.
- Current and counterfactual tier assignments are exported for review.
- Changing a member's name while holding all evidence constant cannot change the outcome.

## Priority 2: Prevent press-only evidence from dominating labels

The label combiner currently normalizes over sources that are present. Consequently, a category with press evidence but no legislative or voting evidence can still be determined entirely by press, despite the nominal 10% media weight.

### Work

1. Replace present-source normalization with a bias-aware confidence rule for media evidence.
2. Recommended approach: keep legislation as the neutral anchor when only press is present, so press can move a label but cannot independently create an extreme label.
3. Require stronger corroboration for Champion, Defender, Highly Skeptical, and Opponent labels.
4. Preserve the raw press signal, source list, and pre-cap label for auditability.
5. Compare current and proposed labels before publishing the change.

### Acceptance criteria

- A press-only category cannot become Champion, Defender, or Opponent without corroborating action or vote evidence.
- Press can still move middle-band labels.
- Every changed label has an explainable evidence decomposition.
- The dashboard distinguishes reported speech from demonstrated legislative action.

## Priority 3: Audit all structural tier and label rules

Several universal rules can create sticky outcomes even without explicit member pins.

### Rules to review

- Fixed tier capacities: 13 / 24 / 48.
- Minimum `cu_primary` evidence floor: 0.75.
- Uncertainty penalty applied to thin evidence.
- Conduct ceilings at net severities 3, 6, and 9.
- Automatic Champion label for every Tier-1 member.
- Say/do corroboration gate that caps uncorroborated top issue labels at Ally.
- Fixed overall-label thresholds.

### Work

1. Produce a rule-by-rule counterfactual report showing the outcome with each rule disabled individually.
2. Separate direct effects from replacement effects. For example, Andy Barr is directly constrained by the conduct ceiling, while another member can move because a seat becomes available.
3. Decide whether tiers should remain fixed-size buckets or become score/evidence thresholds with variable membership.
4. Decide whether Tier 1 should automatically imply Champion or whether the overall label should remain evidence-derived.
5. Reconcile stale tier-policy documentation with the current live effects.

### Acceptance criteria

- The dashboard can explain why each tiered member qualified and which constraints applied.
- Every structural rule has a stated purpose and an empirical validation.
- No replacement effect is presented as a direct penalty or promotion.

## Priority 4: Measure and correct media-source coverage bias

The press system should include all qualified material while preventing high-volume outlets or syndicated copies from overwhelming the evidence.

### Work

1. Publish source-level coverage counts for Fox News, MSNBC/MS NOW, CNN, CBS, ABC, PBS, NPR, Wall Street Journal transcripts, local outlets, podcasts, hearings, and member-owned channels.
2. Report per-member and per-party source coverage, missingness, date range, transcript availability, and graded-stance yield.
3. Cluster duplicates, syndicated copies, excerpts, and repeated airings before scoring.
4. Retain every qualified item in the evidence archive, but summarize related coverage as one concise story or appearance cluster in the dashboard.
5. Separate:
   - volume of coverage;
   - outlet/source diversity;
   - issue stance;
   - sentiment or tone;
   - direct member statements versus third-party discussion.
6. Add outlet-family and format diagnostics so one network, transcript vendor, or repeated segment cannot dominate by volume alone.
7. Treat sentiment as a deactivatable component rather than deleting its underlying measures or evidence.

### Acceptance criteria

- No supported outlet is excluded merely because of its political orientation.
- Every included item has source, date, URL or transcript provenance, speaker role, and deduplication identity.
- Coverage comparisons are available both with and without sentiment.
- A source-removal sensitivity report shows how Fox, MSNBC/MS NOW, and other major sources affect ranks and labels.

## Priority 5: Finish press and coverage completeness

### Work

1. Confirm that the old 50-item display or ingestion cap is removed from interviews and Press & Coverage.
2. Verify that the uncapped archive is used for analysis and not merely stored for display.
3. Add pagination, lazy loading, clustering, and concise summaries so completeness does not make member pages unusable.
4. Publish per-source counts and beyond-cap counts on every member record.
5. Add regression fixtures for members with more than 50 interviews or articles.

### Acceptance criteria

- No qualifying press item is silently discarded at item 50.
- Display totals match the underlying archive after deduplication and eligibility filtering.
- Large member histories remain fast and readable.

## Priority 6: Verify sentinel-to-workbook ingestion

New bills, legislative actions, and media statements collected by sentinels need an explicit, same-cycle path into the workbook and dashboard.

### Work

1. Trace each sentinel output through validation, accepted ledger, normalized feature, workbook/view, rank authority, and dashboard surface.
2. Add an ingestion receipt containing:
   - source sentinel;
   - collected count;
   - accepted count;
   - rejected or quarantined count and reason;
   - newest event timestamp;
   - destination artifact hashes.
3. Add canary records for a new bill, action, and media statement and verify each reaches its intended workbook and dashboard fields.
4. Fail the pipeline if an accepted sentinel record is absent from the expected downstream artifact.
5. Clearly distinguish same-cycle inputs from previous-cycle bundle dependencies.

### Acceptance criteria

- Every accepted sentinel item is traceable to its downstream representation.
- Rejected items remain visible in a quarantine report with reasons.
- The workbook, rank authority, and dashboard report the same data vintage.

## Priority 7: Complete and deduplicate biographies

### Work

1. Verify all 533 members have a Wikipedia lookup result or an explicit no-page/error status.
2. Recheck sparse-profile cases such as Steve Scalise across Wikipedia, official biography, Congress/Bioguide, and verified social accounts.
3. Produce concise sections for career, family, formative experiences, education, military/public service, and major life events only when sourced.
4. Deduplicate facts appearing in biography, personal experiences, behavioral interpretation, and speech sections.
5. Keep source facts separate from inferred behavioral conclusions.
6. Enforce per-section length and repetition limits.

### Acceptance criteria

- No member page is blank without an explicit source-status explanation.
- A biographical fact appears once in the primary narrative and is referenced, not repeated, elsewhere.
- Every displayed personal claim has source provenance and confidence.
- Unsupported or stale narrative artifacts are withheld rather than silently reused.

## Priority 8: Clear outstanding audit and provenance debt

### Work

1. Rebuild the stale member narrative basis and narrative artifacts.
2. Refresh stale collection receipts and system manifests.
3. Reconcile repository size-class and source-hash drift.
4. Run the complete canonical pipeline twice to test idempotence.
5. Run the full audit after the second build and resolve every failure or document an explicit, time-bounded waiver.

### Acceptance criteria

- The full audit exits successfully.
- Two consecutive builds from unchanged inputs produce identical rank, tier, label, and dashboard artifacts.
- No stale narrative is displayed.
- All published artifacts carry matching provenance and source hashes.

## Recommended execution order

1. Replace the outcome-targeted uncertainty calibration.
2. Fix press-only label normalization and run label counterfactuals.
3. Complete the source-coverage and outlet-bias audit.
4. Verify sentinel-to-workbook lineage with canaries.
5. Finish biography completeness and cross-section deduplication.
6. Rebuild stale narrative and manifest artifacts.
7. Run two clean canonical builds and the full audit.
8. Publish the final rank, tier, label, and source-coverage deltas for approval.

## Decisions requiring approval before methodology changes

- Whether fixed-size tiers should remain or be replaced with variable score thresholds.
- Whether Tier 1 should automatically confer the Champion label.
- Which member-neutral objective should select the uncertainty penalty.
- Whether press-only evidence should be limited to middle-band labels or merely confidence-discounted.
- Whether press sentiment should remain active at 10% after the source-removal and outlet-balance sensitivity tests.
