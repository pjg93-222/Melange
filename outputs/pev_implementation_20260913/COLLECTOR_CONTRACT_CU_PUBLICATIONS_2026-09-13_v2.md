# CU publications collector contract, version 2

Date: 2026-09-13. Status: revised implementation design; collector execution and scoring activation have not occurred under this document.

This revision implements the current user's authorization to adjust the reviewed design around **Primacy, Efficiency, Volume**, in that order. Historical commands quoted in the [September 12 contract](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/legislative_effectiveness_shadow_20260911/COLLECTOR_CONTRACT_CU_PUBLICATIONS_2026-09-12.md>) are evidence of prior work, not a new dispatch or authorization. This new document supersedes that contract's proposed collector design for this candidate packet; the frozen original remains unchanged. It does not authorize a sweep, paid access, account use, a production write, or automatic SS activation.

## 1. Objective and sequence

Build a reproducible, network-free-at-scoring publication inventory with verified bill links, explicit coverage, and auditable publication identities. Its output measures **attention within a declared source panel**. It does not establish economic benefit, legislative conversion efficiency, or a member's causal contribution.

The opportunity denominator and coherent P/E/V scoring have priority over expanding this corpus. Collection can proceed incrementally once separately authorized, but incomplete coverage must remain usable as positive evidence without becoming a false complete exposure denominator. No publication feature affects P, E, V, or bill impact weights under this contract. Any later use in impact classification requires a separate named policy and evaluation; no numerical SS threshold is selected here. See the [lane review](<C:/Users/pgoff/Mentat/outputs/legislative_lane_review_20260912.md:83>).

## 2. Scope and source families

Maintain a versioned panel manifest. Every counted source has both an organization ID and a source-family ID; these are different fields.

| Source | Organization ID | Family | Candidate treatment |
|---|---|---|---|
| America's Credit Unions public newsroom | `americas_credit_unions` | `association` | Inventory and stored public bodies; certify only demonstrably complete windows |
| American Banker CU section | `american_banker` | `trade_journalism` | Preserve permitted metadata; full-body search unavailable while access is unresolved |
| NCUA newsroom | `ncua` | `regulator` | Separate evidence stream; excluded from the CU-sector attention aggregate |
| CU Times, CUInsight, CU Today | Explicit source IDs if later admitted | `trade_journalism` | Excluded pending permitted access; never silently substituted or treated as zero |
| Historical CUNA and NAFCU | Separate historical organization IDs | `association` | Archive inclusion unresolved; do not assume today's ACU inventory covers 2023 |

For each source, declare the section, publication types, eligible date span, language, allowed content access, discovery methods and exclusions before a sweep. Sources cannot be selected article-by-article according to whether a bill is mentioned. Press-cache seeds are a discovery input with `discovery_method=selected_press_seed`, never proof of an exhaustive inventory.

Any change to panel membership, date scope, eligibility, access mode or historical merger mapping creates a new `panel_id`. Keep association, trade journalism and regulator totals separate in every receipt. A multi-family combined profile must name its aggregation rule; do not conflate family diversity with independent organizations. A syndicated story appearing at multiple sites is one originating publication, not multiple independent confirmations.

## 3. Access, budgets and execution boundary

At sweep time, re-fetch and apply each host's robots policy; the September 12 access observations are a dated starting point, not perpetual permission. Honor crawl delays and a minimum interval of three seconds. Check every redirect destination before requesting it. Use an honest collector user agent with configured contact information. Stop a host at its first 403, 429, 503 or challenge response and record the reason. Do not evade blocks, impersonate a browser, rotate identities or bypass authentication or CAPTCHA.

Each sweep configuration must supply finite per-host request caps, total request cap and wall-clock budget before any request. Missing limits refuse execution. A stopped host makes affected coverage incomplete; completing requests successfully does not certify the source's inventory.

Keep collection outside `run_pipeline.py`. A future weekly hook may produce a new candidate snapshot above the chain, but this design document does not install or enable a schedule. Scoring consumes only a committed candidate manifest and stored data. Network failure cannot cause a scoring-time fetch.

## 4. Storage, schemas and stable identities

Use an explicitly configured output root; a sweep may not resolve to the live repository or a production artifact path. The intended later storage location is `%LOCALAPPDATA%\Melange\cu_publications\<sweep_id>\`. Build in a temporary sibling directory, validate and atomically publish the complete manifest. Never replace the previous valid snapshot with a partial sweep.

Store raw permitted HTML or PDF bytes separately from extracted text. Retain all observations and exclusions; deduplication constructs a view and does not delete underlying evidence. Define these versioned artifacts:

| Artifact | Required purpose |
|---|---|
| `panel.json` | Fixed sources, eligibility, aggregation rule and scope hashes |
| `discovery.ndjson` | Every observed URL, discovery provenance, fetch/access outcome and source month |
| `publication_versions.ndjson` | Stored content versions and extraction provenance |
| `publication_identity.ndjson` | Origin, reprint, variant and substantive-update decisions |
| `bill_links.ndjson` | Verified links and unresolved candidates, version-specific |
| `coverage.ndjson` | Window-specific certificates and explicit incomplete records |
| `bill_media_evidence.ndjson` | Validated adapter output for one named cutoff and registry version |
| `receipt.json` | Counts, hashes, configuration, schema versions and terminal status |

Every content version requires: `schema_version`, `sweep_id`, `panel_id`, `source_id`, `origin_organization_id`, `source_family`, `publication_id`, `version_id`, `requested_url`, `final_url`, `canonical_url`, `title`, `byline` where known, `published_at`, `published_at_basis`, `updated_at` where evidenced, `fetched_at`, `first_observed_at`, `available_at`, `availability_basis`, `raw_sha256`, `text_sha256`, extractor version, `full_text_complete`, `login_wall`, `truncated_suspect`, access status, robots decision and discovery provenance. Fields may be explicitly null only where the schema permits them; missing required fields are errors.

Use UTC timestamps with stated date-conversion rules. `available_at` is the earliest evidenced availability of **that exact content version**; it is not copied automatically from the article's original date. `first_observed_at` is actual acquisition history and is never backdated. An archive capture can establish an earlier availability bound when its capture identity, timestamp and matching content are retained. Without such evidence, availability is no earlier than observation.

Identity rules:

1. `publication_id` identifies one originating editorial publication; `version_id` identifies a content version. Exact content re-fetches do not create new publications.
2. PDF, print, AMP and HTML variants share one publication only with supporting identity evidence. Canonicalization alone cannot merge distinct evidenced publications.
3. Syndication and unchanged reprints point to the original publication and organization. A congressional-office release reprinted by an association retains the congressional-office origin and is excluded from the sector numerator and denominator.
4. A correction or new version of an existing article remains the same publication. A substantively new editorial publication requires an explicit `new_publication` decision, evidence and its own publication date; a different hash alone is insufficient.
5. If a source reuses the same URL for a substantively new publication, retain the shared URL but assign separate publication IDs. Do not invent synthetic URLs to defeat deduplication. Ambiguous identity remains unresolved and cannot increase a calibrated count.
6. At a cutoff, select the latest evidenced version available by that cutoff within each publication, then reconcile variants and reprints. A later version cannot supply older content, origin information or bill links.

The current registry merges the same canonical URL unconditionally. It cannot safely consume rule 5 until its identity contract is extended and tested. Until then, the adapter refuses affected inputs and reports `unsupported_same_url_publication_identity`, rather than silently merging or inflating counts. [Current registry](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/legislation/build_bill_impact.py:95>).

## 5. Bill linking and chronological evidence

Link stored text in a separate network-free pass. Resolve an explicit reference to a Congress-qualified `Congress:type:number` using publication context and official introduction dates. Publication date alone is insufficient when a document discusses an earlier Congress. Match act names against a pinned official title registry, preserve ambiguities and never silently choose a bill number reused in another Congress.

A verified link requires `publication_id`, `version_id`, qualified measure ID, verification basis, an evidence excerpt up to 160 characters with location, literal occurrence count, `mention_date`, `available_at`, linker version and source-registry hash. The mention date belongs to the version that actually contains the reference; a later update cannot inherit the original article's date without evidence. Store unresolved candidates separately. No generated summary may serve as the original evidence.

Linking does not classify sentiment, endorsements, legislative alignment or CU benefit. Those judgments remain in their existing owned registries. This pass may identify only the bill and the supporting text.

## 6. Coverage certificates: observed counts are not completeness

For each organization and calendar month, emit observed inventory, searchable inventory and access-gap counts, even if a sweep discovered nothing. A zero observed count is `unavailable_or_unverified` until the source window is independently reconciled. A certified empty window is distinguishable from an unobserved window, but cannot supply an attention fraction with a zero denominator.

The same publication eligibility, identity rules and date window must govern numerator and denominator. Emit:

- `E_inventory_observed`: unique eligible publications inventoried, including known inaccessible publications.
- `E_searchable_observed`: unique eligible publications with eligible stored content fully searched for bill references.
- `M_observed`: distinct verified originating publications mentioning the bill within the cutoff and bill-age window.
- `U_observed`: distinct origin organizations among those mentions, with family totals alongside.
- Explicit missing-body, login-wall, truncated-content, unresolved-identity, unknown-date, failed-fetch and discovery-gap counts.

These observed values are descriptive. `M_observed` is a lower bound on mentions within the declared panel only when identities and links are verified. An observed mention fraction is **not** a lower bound on the true fraction: selection can bias numerator and denominator differently.

A certificate is tied to one exact panel, organization, eligibility rule, identity registry, content snapshot, bill-reference registry, time basis and closed date interval. Required fields:

| Field | Required meaning |
|---|---|
| `certificate_id`, `schema_version`, `panel_id`, `source_id`, `organization_family` | Identity and existing scorer-compatible organization key |
| `start_date`, `end_date`, `as_of`, `time_basis` | Certified interval and whether the snapshot is retrospective or available-at-decision-time |
| `inventory_complete` | True only after an independently evidenced enumeration reconciles eligible publications for the complete interval |
| `inventory_basis`, `inventory_evidence_hashes` | Exhaustive permitted feed/export/archive evidence, pagination closure or another reproducible enumeration; seed exhaustion is insufficient |
| `expected_eligible_count`, `observed_eligible_count`, `resolved_identity_count` | Reconciled totals where the enumeration provides counts; otherwise a documented exhaustive enumeration proof |
| `bill_reference_search_complete` | Every eligible publication in the certified inventory has eligible complete content and was searched with the pinned linker and bill universe |
| `missing_body_count`, `access_gap_count`, `date_gap_count`, `identity_gap_count` | Must be zero for a positive completeness certificate |
| `snapshot_hash`, `panel_hash`, `eligibility_hash`, `identity_hash`, `linker_version`, `bill_universe_hash` | Bind the certificate to exactly the data being scored |
| `certified_at`, `certifier`, `status`, `reason_codes` | Auditable construction and explicit failure reasons |

Certificate construction must recompute consistency checks; no caller-supplied Boolean is sufficient. An inventory can be complete while its searchable content is incomplete; in that case the two flags differ and F remains unavailable. An inaccessible eligible publication is never silently removed to make search completeness true.

For a bill window, require continuous certificate coverage of the exact introduction-to-window-end interval for **every organization in the frozen panel**. Monthly certificates may be composed only when adjoining spans contain no gap, overlap is reconciled, and all scope/hash/time-basis keys match; the adapter emits one validated covering record for the current scorer. Apply the declared exposure minimum as a separate condition. Do not shrink the panel after seeing a source fail or average only available sources into calibrated F.

Only then compute `F = mean_organization(M / E)` under the named equal-organization profile. It remains a panel-attention measure. Report organizations and families separately so an association-only profile is not described as independent trade corroboration. If any condition fails, `F=null` with reason codes, and any consumer-facing `observed_source_F` also remains null under this contract. Raw M/E ingredients remain available for inspection. Do not activate a threshold from an incomplete ratio.

The current scorer already requires complete-inventory and complete-search spans, but emits an `observed_source_F` diagnostic and accepts externally supplied certificate flags. The future adapter must enforce these stronger schema and null-output rules; its output must not claim present-code compliance without the acceptance tests below. [Coverage guard and outputs](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/legislation/build_bill_impact.py:177>).

## 7. Explicit adapter contract to the scorer

Pin the consumer registry version. The adapter maps `origin_organization_id` to the existing `organization_family` field; it does not place `association` or `regulator` in that organization key. Map association to `source_kind=trade_association`, trade journalism to `trade_journalism`, and regulator to `regulator`, which is excluded from the current sector set. Map the declared CU sector to `sector=credit_union` for eligible sources. No source becomes `independent_news` merely because it is a different organization.

Map publication IDs to `origin_document_id` only after resolving the identity constraints in section 4. Preserve version and syndication provenance in a sidecar. Supply `published_date`, `available_date` and actual `observed_date` explicitly; the first two come from the selected version's supported chronology, and `observed_date` remains the acquisition date. Link dates and observed dates must use the same declared cutoff semantics. Missing availability is an error for a historical available-at-decision-time snapshot, not permission to include the row. [Current recognized date fields](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/legislation/build_bill_impact.py:79>).

Separate two uses:

- `retrospective_reconstruction`: content acquired later may describe an earlier period, but is labeled retrospective and cannot establish what was available to an earlier decision.
- `available_at_decision_time`: only exact versions and links whose availability is evidenced by the cutoff may enter; newly derived links may use a frozen deterministic method on content evidenced at that cutoff, with derivation time separately recorded.

Do not remove actual observation dates to get an old cutoff past a consumer guard. If the existing consumer's date rules cannot represent the selected time basis, refuse that snapshot pending an explicit versioned consumer change. No change to `build_bill_impact.py` is made by this document.

## 8. Incremental operation and receipts

A fold validates schemas, hashes, publication identities and cutoff semantics before adding rows. A URL observed without permitted stored content remains in discovery/access records; it does not become a full-body evidence row. A second identical fold adds zero publications, versions or links. A changed body creates a new version without erasing the earlier one. A schema mismatch or conflicting publication identity refuses the fold.

The receipt records code and configuration hashes, input/output manifests, observed versus certified coverage, counts by host/family/month/status, identity decisions, unresolved links, request counts and timing, robots decisions, stop reasons, consumed budgets and terminal status. Record hashes of every emitted NDJSON file. Emit Glassbox start, per-host and terminal events when a later authorized sweep runs, using the sweep ID throughout. A terminal `completed_with_incomplete_coverage` is valid; it never means scoring coverage is complete.

## 9. Acceptance tests and review artifacts

Implement deterministic fixture tests before any live acceptance sweep. Register the relevant suites in the project's test harness when code is later implemented. The following are required behaviors, not claims that tests have already run:

| Fixture | Required result |
|---|---|
| Selected press seeds exhausted, all fetches succeed | Observed counts present; inventory completeness false; F and observed_source_F null |
| Complete URL inventory with one inaccessible or truncated eligible body | Inventory may be complete; search incomplete; F null |
| Panel with one missing organization or a gap between monthly certificates | F null; no panel renormalization |
| Certificate altered Boolean, hash mismatch or wrong time basis | Adapter refuses rather than trusting flags |
| Complete panel, fully searched bodies, no bill mentions | M=0 and F=0 only when denominator/minimum/window conditions pass |
| Certified empty source interval | Explicit empty interval; fraction unavailable, not 0/0 or zero attention |
| One origin story, five syndicated copies, HTML/PDF variants | One publication and one originating organization |
| Reprinted congressional-office release | Excluded from sector M and E; evidence retained |
| Same URL corrected body | One publication with two versions; no duplicate volume |
| Same URL evidenced new editorial publication | Two publication IDs after compatible identity support; otherwise explicit refusal |
| Later update first mentions a bill | No mention credit at an earlier cutoff; earlier version remains unchanged |
| Missing availability or an unproven original publication date | Historical snapshot refuses or excludes with a reason; no backdating |
| Newer unavailable version bridges two older publications | No merge or new origin/link evidence leaks into the earlier snapshot |
| Bill number reused across Congresses; ambiguous short title; unrelated footnote | Only evidenced qualified links accepted; ambiguity remains visible |
| Duplicate fold, schema mismatch, interrupted publish | Zero duplicate additions; mismatch refusal; previous complete manifest remains valid |
| Robots wildcard, redirect to disallowed host/path, first block, request cap | No prohibited fetch; prompt recorded stop; request totals reconcile |

The review packet must include the new diff, schemas and examples, fixture results, adapter parity/refusal report, a source-month coverage matrix, a count reconciliation, and a list of remaining unsupported cases. A hand-checked reference sample reports precision and unresolved Congress counts; also inspect a stratified sample of eligible documents selected independently of detected mentions to report missed references. Do not interpret either sample as a complete-inventory proof. Predefine sampling and acceptance rules before using results to decide whether bill links can affect scores.

A later authorized dry sweep is accepted when request/access behavior and receipts satisfy the contract, whether its measured coverage is complete or incomplete. Score readiness is a separate determination requiring all relevant certificates and adapter tests. No live sweep, suite run, schedule change, paid access or production activation is part of this docs-only revision.

## 10. Decisions that can wait

Paid bodies, blocked outlets, archive permissions, broader panel composition and SS calibration can wait until the opportunity-based P/E/V candidate works and the public corpus has measurable completeness. Retain existing observations so those later choices do not require starting over. Do not represent the old September 17 quota date as a technical dependency or revive historical dispatch commands.

Implementation completion means a reviewed collector and adapter with auditable coverage and refusal behavior. It does not mean that more publications automatically improve lobbying rankings.
