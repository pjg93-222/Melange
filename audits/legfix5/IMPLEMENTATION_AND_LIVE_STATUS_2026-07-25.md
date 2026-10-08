# Congress.gov legislation audit — implementation and live status

Checkpoint: 2026-07-26 11:53 America/Chicago
Primary discovery instrument: Congress.gov Advanced Search — Legislation
Quorum used: **No**
Production/mainframe sync: **Frozen**

## Executive status

The pre-sync gate is correctly **BLOCKED**. All immutable frozen baseline
copies remain unchanged. A separate scheduled `weekly_refresh.py` /
`run_pipeline.py` process changed live production outputs,
including ranks, the production workbook, behaviors, planning outputs,
dashboards, and member-desk artifacts. The frozen/live comparison therefore
fails closed and no current live output is accepted as the legislation
baseline.

The strict discovery registry contains 62 required Congress.gov Advanced
Search queries for Congresses 116–119 and all ten selected measure types.
Registry SHA-256:
`ba865417a0e722e0103d8a8ff65b657d15f66fde0fd76eeabaa37ba169d20b39`.

Exactly **22/62** queries are complete and page-reconciled, totaling **62,994
query memberships before cross-query deduplication**:

| Search section | Exact results | Pages |
|---|---:|---:|
| Examination & Supervision | 2,024 | 9 |
| Credit Union Capital Requirements | 1,477 | 6 |
| NCUA Budget & Share Insurance Fund | 2,481 | 10 |
| Interchange | 82 | 1 |
| Payments | 5,412 | 22 |
| Technology & Emerging Issues | 2,224 | 9 |
| Fraud Prevention | 3,656 | 15 |
| Data Privacy & Cybersecurity | 6,813 | 28 |
| Charter Modernization & Governance | 1,657 | 7 |
| Defense Credit Union Issues | 9,250 | 37 |
| Field of Membership | 2,923 | 12 |
| Credit Union Tax Status | 8,948 | 36 |
| CDFI Fund | 4,254 | 18 |
| Credit Union-Bank Competitive Dynamics | 1,387 | 6 |
| CFPB Issues & Structural Reform | 1,823 | 8 |
| Credit Card & Consumer-Fee Mandates | 1,679 | 7 |
| Telephone Consumer Protection Act Issues | 1,791 | 8 |
| Member Business Lending | 2,043 | 9 |
| Mortgage Lending & Housing | 2,304 | 10 |
| Headline recall net | 753 | 4 |
| FIRM Act exact-title probe | 5 | 1 |
| TAILOR Act exact-title probe | 8 | 1 |

All 22 query artifacts were independently re-read after the interruption:
22/22 retain exact total, unique-total, and every-page validation, with zero
file/count discrepancies. Congress.gov then returned a legitimate singleton
Advanced Search redirect for the FAIR Exams Act probe. The collector now
accepts that transport only when the exact highlighted query, search-session
rank, disabled Previous/Next controls, Congress/type scope, and official
measure identity all prove a 1-of-1 result; arbitrary detail pages still fail
closed. The focused navigation regression passes 5/5.

The repaired supervisor is alive at PID 5148 and resumes the 22 validated
queries. It does not bypass verification and does not count a query until every
page and record reconcile exactly. Congress.gov is currently serving a
noninteractive Cloudflare automatic-verification interstitial for the FAIR
Exams Act probe. The collector waited passively for 120 seconds, accepted no
result, performed no interaction or bypass, recorded the exact query, Ray ID,
and failure evidence, and activated an exponential 10-minute/20-minute/40-minute
cooldown capped at two hours. The supervised worker holds the collector lock
during cooldown and performs no browser navigation or refresh until the
recorded retry time. The exact Advanced Search/result validation contract is
unchanged. Navigation and verification-backoff regressions pass 12/12.
The first retry after the 10-minute cooldown encountered a second independent
interstitial with a new Ray ID, again accepted no result, and activated the
20-minute cooldown through 2026-07-26 01:36:02 America/Chicago. Its immutable
timeout receipt is hash-valid.
The next retry after that 20-minute cooldown encountered a third independent
Ray ID under the same noninteractive condition and activated the 40-minute
cooldown through 2026-07-26 02:18:07 America/Chicago. The supervisor remains
alive and all 22 exact queries remain preserved.
The scheduled 02:18 retry resumed and revalidated all 22 queries, then waited
passively for the FAIR Exams Act probe for the full 120 seconds. Congress.gov
returned a fourth independent Cloudflare Ray ID and no valid result page.
No interaction, reload, bypass, result acceptance, or artifact replacement
occurred. Attempt 8 entered the 80-minute cooldown through 2026-07-26
03:40:11 America/Chicago. It resumed on schedule, revalidated all 22 completed
queries, and again waited passively for the full 120 seconds. Congress.gov
returned a fifth distinct automatic-verification timeout. No result was
accepted and no verification interaction or bypass occurred. The scheduled
05:42 retry then revalidated all 22 completed queries, waited passively for
the full 120 seconds, and received a sixth distinct automatic-verification
timeout (Ray `a212cc2c39d01d4c`). No result, interaction, reload, or bypass was
accepted. The scheduled 07:44 retry then revalidated the preserved 22-query
checkpoint, waited passively for the full 120 seconds, and received a seventh
distinct automatic-verification timeout (Ray `a2137f014abf1320`). No result,
interaction, reload, or bypass was accepted. The scheduled 09:46 retry again
revalidated all 22 completed queries, waited passively for the full 120
seconds, and received an eighth distinct Cloudflare timeout (Ray
`a21431d8c82902dc`). No result, interaction, reload, bypass, or artifact
replacement was accepted. The eighth immutable timeout receipt is hash-valid
at SHA-256
`e905ac147d5b3bea84a8e9352dee00746170b64223fe378d81f9e337057ed008`.
The scheduled 11:48 retry revalidated the same 22 completed queries and then
received a ninth independent Cloudflare timeout (Ray
`a214e4a2aa352434`). It again accepted no result and performed no verification
interaction, reload, or bypass. The ninth immutable timeout receipt is
hash-valid at SHA-256
`7f24f701949c7ccc5462ae48d1b7e2c53e448703b253744eb872eeff2c51dd51`.
The collector remains in the capped two-hour cooldown through 2026-07-26
13:50:40 America/Chicago, with the new cooldown worker alive at PID 13864.
All 22 validated queries and their artifacts remain intact.

The follow-up supervisor now polls the validated strict-manifest selector every
30 seconds while the collector is alive and once more immediately before the
normal post-collector pipeline. Receipt-identical polls are zero-network
no-ops; a new capped timeout transition automatically performs the validated
zero-network semantic rollover. The ninth-timeout rollover passed at ID
`1b1a89c8c4ff44131d9121be47118080f765aa3b87e171331e372b0c2381dd02`;
its receipt SHA-256 is
`1e0c482168d5ba6cdb032d0ac0c399b52e7503a0b2382e45e77f1a9c1e4b84e4`.
It performed no candidate exclusion, scoring, network collection, production
write, sync, or promotion.

A live pre-sync check exposed and repaired a reporting defect: a newer empty
cooldown-worker manifest could temporarily hide the stronger 22-query
checkpoint. Strict-manifest selection now rejects wrong-registry, malformed,
duplicate-query, stale-receipt, or non-Congress.gov artifacts, validates every
referenced query file and record hash, and ranks eligible artifacts by exact
validated query count before deterministic freshness. The live gate now
correctly selects the newest eligible maximum-progress artifact,
`manifest.partial.27000.json` (SHA-256
`c21f88817b9ffaf99dc2ebd32421885d4dfdafb950b2384227f7dbf3a944942e`),
and reports 22/62. This independently validates the ninth immutable timeout
receipt while refusing the newer empty cooldown-worker manifest.

A separate resume-continuity audit compared the sixth-timeout
`manifest.partial.13108.json` checkpoint with the seventh-timeout
`manifest.partial.22424.json` checkpoint. All 22 ordered query IDs retain
identical result totals, unique counts, page counts, Congress/type counts,
record hashes, and validation booleans. All 22 current query files and all 264
referenced page entries were independently parsed and rehashed with zero
errors. The only 11 manifest differences are run timestamps, honored cooldown
state, and immutable timeout/failure metadata; semantic record drift is false.
The 62,687-row review ledger and its 55/4/62,628 partitions still match their
recorded hashes. The audit passes with zero blockers; artifact SHA-256:
`bce87676d9875916bdb2aecfc5f33d3c1e7edf6d2fc207f439e2e652d2f7573f`.

Current authoritative gate artifacts:

- `audits/legfix5/shadow_recompute/presync_current/checkpoint.json`
- `audits/legfix5/downstream_readiness/downstream_readiness.json`
- `audits/legfix5/timeout_rollover/current.json`
- `audits/legfix5/final_regression_audit/receipt.json`
- `audits/legfix5/shadow_recompute/consumer_isolation_audit.json`
- `audits/legfix5/shadow_recompute/consumer_plan.json`

The live staged-only pre-sync and downstream-readiness reports were regenerated
after the computation-gate and informational-audit hardening. They now bind
the ninth-timeout worker manifest `manifest.partial.27000.json` (SHA-256
`c21f88817b9ffaf99dc2ebd32421885d4dfdafb950b2384227f7dbf3a944942e`).
The independent 32388-to-27000 continuity audit proves all 22 ordered query
IDs, semantic fields, query/page artifacts, and the 62,687-row review
partition unchanged; semantic record drift is false and blocker count is
zero. Continuity artifact SHA-256:
`c4b2211ec13afa170758f2ba8ce427a70c7f4ff001c33985e36ed7de901e42b3`.
It also validates the ninth immutable timeout receipt at SHA-256
`7f24f701949c7ccc5462ae48d1b7e2c53e448703b253744eb872eeff2c51dd51`.
The current manifest-bound specificity receipt passes at SHA-256
`404fe07ce008e04255c37426a493f281ed629546ffb2d06256fd36ad51d44665`;
the former stale-specificity blocker is cleared. The reports detect the
existing collector as already running, preserve the approved spreadsheet
import and frozen production baseline, and keep `sync_allowed=false`. No
role-weight or workbook-computation approval receipt exists, so the typed
policy contracts remain unavailable rather than being accidentally inferred.

At this checkpoint the staged-only pre-sync checkpoint is **BLOCKED** by 16
blockers, including strict coverage at 22/62, absent final/review/policy
artifacts, and frozen/live drift at 35/55 exact matches. Its exact file SHA-256
at edit time is
`cdc318b7c5e94c5342f97fe48f0cdb2ef54b1da2580197cad31343166783d9e7`.
The current readiness receipt has 6/26 gates true, 20 false,
`hard_freeze=true`, and `sync_allowed=false`; its exact file SHA-256 at edit
time is
`78301acf217a8e6f598d6172d5751fbf69941cba9648fcd78f07de646ef99850`.
Exact input hashes and stage bindings remain the freshness authority.

## Coverage, sorting, and culling contract

Discovery is lossless. Every Advanced Search hit and every query membership is
retained. Discovery never performs semantic exclusion.

Sorting and culling occur per measure/category membership only after discovery:

1. Check the official title, summary, text, and relevant provisions.
2. Use trusted press articles as corroboration or a reverse-coverage lead.
   Article absence is never negative evidence.
3. Do not accept generic “Act” matches or other unlocalized keyword noise.
4. Keep uncertain cases unresolved and visible.
5. Require an exclusion reason, official evidence, reviewer, review time, and
   provenance before a false positive can be ratified.
6. Keep excluded and unresolved records in their audit ledgers forever; they
   contribute zero but are never deleted from coverage.

Decision validation now rejects a generic or ambiguous excerpt such as
`An Act` or `SMART Act` for both inclusion and exclusion even when it is
attached to an otherwise allowed evidence label. Press/ACU article absence is
explicitly neutral and cannot be carried as an exclusion basis. Resolved
relevance must instead localize a specific Congress.gov official title,
summary, text, or operative provision. A Congress-qualified identity-mismatch
exclusion requires distinct expected/observed canonical keys plus an official
Congress.gov URL that parses to exactly the observed Congress/type/number;
same-identity and label-only claims fail closed. All four existing ratified
production membership decisions pass the stricter validator.

America's Credit Unions is an additional positive-only corroboration channel.
For each candidate, the review plan searches the exact official title together
with Congress-qualified bill-number variants against the current America's
Credit Unions domain and applicable legacy CUNA/NAFCU news domains. A positive
result may corroborate identity, category, industry direction, or a reported
legislative action. A missing result is neutral and can never justify inclusion
or exclusion. These searches never assign Sponsor, Original Cosponsor,
Cosponsor, or withdrawn status; those roles remain Congress.gov-only. The
deterministic query-plan contract is era-scoped, retains malformed or
generic-title candidates in an unresolved ledger, emits four bill-number
variants, and passes 9/9 focused tests. It is now wired into the resumable
coverage pipeline with complete input/output hash validation; stale or
tampered query plans fail closed.

Once final coverage exists, the pre-sync and downstream-readiness gates require
this ACU title-query plan to be hash-current, exhaustive, and resolved. Every
candidate must appear in exactly one of the covered or unresolved partitions.
Unresolved rows remain visible and block acceptance; a missing ACU result
remains neutral; and neither ACU evidence nor any press article can assign
sponsorship roles or override Congress.gov relevance evidence. The integrated
ACU/presync/readiness focused suite passes 25/25. Pre-sync and readiness now
share the same selector and both report the same hash-bound 22/62 checkpoint;
there is no independent newest-file fallback.

The final output must separately expose:

- all discovered candidates and query memberships;
- included category memberships;
- proposed and ratified false-positive exclusions;
- unresolved memberships;
- recall-only and historical-only recoveries;
- missing named/identifier probes and zero-yield searches;
- boundary-extension records from the 116th Congress;
- records with unavailable official text or unresolved dates;
- sponsorship/cosponsorship mismatches; and
- every remaining acceptance blocker.

The current 22-query review checkpoint now has an independent streamed
partition audit. Its 62,687 unique `(canonical_key, query_id)` memberships
partition exactly into 55 included, 4 officially verified category-only
exclusions, and 62,628 unresolved rows. There are zero duplicate keys,
omissions, extras, wrong buckets, raw-line mismatches, or parse errors. Every
excluded candidate remains in the discovery corpus and has complete
hash-verified Congress.gov decision provenance; article absence was used
negatively zero times. Four apparent text-availability mismatches are
specifically classified as harmless automated-enrichment lag because the
independent official decision evidence is complete. Actual provenance
inconsistencies: zero. The audit artifact SHA-256 is
`1edc05b3bb437eed557e6e269519f76684c6acd5264eb2ef727650575a2c5523`
and its focused regression passes 4/4.

No final sorting/culling run can begin until all 62 searches and the historical
merge are complete. Machine proposals never become human decisions.

## Query specificity and generic-Act control

The current manifest-bound specificity audit covers the entire 62-query registry:
19 category searches, 43 coverage probes, and 42 exact-title probes. All 16
ambiguous short-Act aliases are isolated as non-scoring, non-dispositive
probes. There are **zero** ambiguous aliases and **zero** bare/generic `Act`
terms in category scoring queries. Audit SHA-256:
`404fe07ce008e04255c37426a493f281ed629546ffb2d06256fd36ad51d44665`.

Official-evidence review is also hardened against citation boilerplate.
Phrases such as “This Act may be cited as …”, “This bill may be cited as …”,
and “An Act to amend the law …” cannot resolve a membership. A specific
official title, summary, or operative provision is required. The specificity
receipt is mandatory for membership stages, shadow closure, downstream
readiness, and any future sync.

## Sponsorship and relationship coverage

The accepted relationship schema captures:

- Sponsor;
- Original Cosponsor;
- later Cosponsor;
- withdrawn Cosponsor, including withdrawal status and date when available;
- Bioguide ID, chamber, party, state, district, and official links; and
- reported-versus-recovered count reconciliation.

Original cosponsorship is stored as a Cosponsor relationship with
`original_cosponsor=true` and is materialized as its own role. It is never
double-scored as an ordinary cosponsorship. Withdrawn and excluded
relationships remain audit-visible and contribute zero to scores and networks.
Within a measure/category/member identity, the strongest active role wins.
Accepted-generation validation now requires `original_cosponsor` to be an
explicit Boolean on every Cosponsor edge, requires the flag to be null on a
Sponsor edge, and requires exactly one current Sponsor for every measure.
Missing or malformed role flags can no longer silently become later
cosponsorship.

The expanded cross-producer contract now generates Sponsor, duplicate
Original/Later input for the same member, a distinct later Cosponsor,
withdrawn, and category-excluded copies. It proves strongest Original wins
exactly once, the distinct later Cosponsor remains separate, and
withdrawn/excluded rows remain visible with zero contribution through accepted
ledger, workbook/archive routing, base network, scenarios, numeric planning,
direction edges, and roll-call measure/category collapse. The focused contract
passes 1/1; the selected role-consumer regression set passes 45/45.

## Official BILLSTATUS enrichment and roll-call source automation

Congress.gov Advanced Search remains the sole discovery instrument.
Official GPO/Congress.gov BILLSTATUS bulk XML is staged only as a downstream
enrichment source and cannot create candidates or make semantic exclusions.
The initial no-network plan accounted for all **18,557** current candidates:
**14,854** bills/resolutions had top-level official XML tasks across the
32-source Congress/type matrix, while all **3,703** amendments remained
visible as `unsupported_nested_amendment`. An adversarial audit then proved
that the plan was not sufficiently bound to the selected collector manifest,
so that artifact is **not accepted as current evidence**.

The strengthened snapshot contract now reconstructs every referenced query
artifact from the selected strict manifest, validates query identity, registry,
exact reconciliation, record hashes/counts, and then requires exact ordered
row closure against the aggregate candidate corpus. The cumulative contract
also validates the earlier completed-manifest aggregate and membership
receipts. The current gate is **CURRENT** against
`manifest.partial.27000.json`: **18,287/18,557** candidates have current-query
artifact proof, and all remaining **270** have exact historical completed
aggregate and membership proof. There are zero candidates without an official
Advanced Search generation receipt.

Those 270 are preserved historical coverage from deliberately narrowed query
definitions, not corruption: removed ambiguous aliases account for CDFI Fund
101, Mortgage 80, Technology 46, Examination 38, and Fraud 5. They are not
silently treated as current scoring memberships. Of them, 268 remain visibly
unresolved and 2 SMART Act collisions retain official-evidence false-positive
exclusions (`117:hr:3664` and `118:hr:1707`). No candidate was deleted or
newly excluded. The FIRM/TAILOR probe labels are also explicitly flagged as
absent from the older aggregate membership arrays so the eventual cumulative
rebuild cannot lose them.

The dedicated historical-membership acceptance ledger closes all 270 rows:
268 unresolved/non-scoring, 2 official exclusions/non-scoring, and 0 scoring.
Every row binds historical/current registry, manifest, query-version, raw
membership, and review receipts. Accepted generation rejects lossy partitions,
review rows absent from raw memberships, and forged historical scoring
authority. Ledger SHA-256:
`7d8cb4256d04d966b8cc9d2479cd4d36c7ea52705887ad3798b179b3b390642f`.

The content-addressed snapshot bundle
`c71214090c9d401d56393d65bf8b3294043d251b7fb7950fcd6c6e6d7139cb74`
automatically rolls forward with the selected strict manifest and producer
receipts while preserving every older immutable bundle. It covers all
**18,557** candidates: **14,854** top-level official XML tasks plus **3,703**
retained amendments. Plan SHA-256:
`bcc15c9dda2e21307ba6dd689f54f944fa696094d99d6b314ff2e1a1b72dba67`.
The bundle divergence audit SHA-256 is
`8ac6ae976eb607acdebfe185ef078d775ab95fc2bcd025e45d9b2594bcb2483e`.
The completed official worker is reused without network only through an exact
semantic-rollover receipt. It proves query, candidate, record-task, and
unsupported-amendment logical identity between the current plan and completed
plan `f07587795d753cfcdeae6c554e0c20e57161d6afb1d8ae37590958150fe81fd2`;
semantic SHA-256:
`85aec08da8cd5930dadc7ae6934720ff2021a8f2219022f6ec809b7794849538`.

The official GovInfo worker validated all 32 Congress/type sitemaps and
completed **14,854/14,854** top-level records with zero failures. Raw and
parsed receipts preserve official titles, summaries, Sponsor, Original
Cosponsor, later Cosponsor, withdrawn roles, actions, recorded votes, and text
links. All **3,703** nested amendments remain explicitly visible as unresolved
rather than being dropped. A complete second invocation reused all 32 sitemap
receipts and all 14,854 record receipts with `network_executed=false`. Run
manifest SHA-256:
`0911c95f49d0f315a6bccacea211756b5134fd2fae99dfb67aa168a0e1ad69a9`.

The post-fetch completeness gate is **CURRENT** and independently rehashes the
plan, worker manifest, raw XML, parsed records, and exact bill identities. It
closes all 18,557 candidates and inventories 54,831 titles, 12,827 summaries,
79,736 actions, 1,887 recorded votes, and 18,440 text links. Role provenance
contains 14,854 Sponsor, 96,603 Original Cosponsor, 107,418 later Cosponsor,
and 98 withdrawn rows; all 218,875 relationship rows have Bioguide and full
name, with zero unresolved roles. Three hash-bound ledgers retain every
defined absence as neutral evidence: 81,159 candidate-visibility gaps, 34,059
field-completeness gaps, and 5 role-provenance gaps, for 115,223 visible rows.
The hardened pass exposed 32 URL-less individual text versions, 31,369
missing action-classification fields, 56,439 unstructured official relevance
sections, 2 unstructured `introduced on behalf of` relationships, and 3
repeated-member withdrawal/re-addition histories. These remain visible and
cannot exclude, score, or silently double-count a member. Completeness audit
SHA-256:
`b2acd1ff3c0ff7a39406196d268e24e97eacc828de6445982d37f45da6a45739`.

A content-addressed review-only adapter now makes this official evidence usable
for accelerated sorting without granting decision authority. The current
producer-bound sidecar
`e56bef4afd790ec1b66b4f3d63562067591851cf54aaf4e9cb28bc0490ea0034`
contains 14,854 review-compatible metadata rows, all 218,875 role edges, all
3,703 unresolved amendments, and all 115,223 gap rows. Its manifest SHA-256 is
`355925e07f61703fb5ff40ec1856289d6cbc4f6f73ecfc305c9e288d17709a7e`.
Candidate creation, exclusion, ratification, scoring, sync, and production
authority are all explicitly false.

A rollover audit found that the old top-level
`current_snapshot_plan.json` compatibility artifact still binds a superseded
collector manifest. It is preserved as provenance and was not overwritten or
deleted. The adapter's default resolver no longer trusts it when the pre-sync
checkpoint exists: it validates the checkpoint's current c712 bundle and 27000
strict-manifest receipts, recomputes the immutable bundle content address,
fully validates the bundle, and then selects the one completed official worker
with exact semantic task closure. Any path, size, hash, authority, or safety
drift fails closed. The legacy artifact is only a pre-checkpoint fallback.
Eight focused adversarial tests and compilation pass. A live run produced the
sidecar above and a second run returned `created=false`.

A second immutable prefill layer applies that evidence to the exact selected
22-query checkpoint without pretending the stale 20-query review manifest is
current. It validates 18,287 records and all 62,994 memberships, then emits
62,994 non-ratified review proposals: 28 ambiguous short-Act collisions, 13
collisions with an independent official nexus, 134 named-Act-reference-only
rows, 299 official-title/summary nexus rows, 9 probe/parent-category
confirmation collisions, zero actual parent-category recall misses, and
62,511 context/text-unavailable rows. The adversarial pass moved 20 apparent
official-nexus false positives into the reference-only bucket and found zero
authority violations. All 3,703
unsupported amendments remain visible, including 3,695 current and 8
historical-only measures; 22,734 amendment-membership proposals remain
non-authoritative. The ratified review ledger is untouched. Prefill manifest
SHA-256:
`30f6c7139793980b7573336bef297c63382ea770ac68e367578db9ed841fc085`.

The lossless review queue bound to that hardened prefill contains all 62,994
memberships exactly once, with 175 exclusion-like visibility signals, 50
ambiguity signals, and 299 official title/summary nexus rows. The queue also
retains 22,731 missing-evidence rows after precedence and 39,780
unresolved-context rows. Its overlapping visibility ledgers expose all 22,734
memberships
missing official title/summary evidence. Every row remains unresolved,
retained, zero-weight, and proposal-only. Queue manifest SHA-256:
`3cd128598758cb4e9679342529f14ddc595cb75c4f11ab81e7105de351cabd51`.

An additional official-XML relevance sidecar now structures the evidence
sections that were previously only raw/hash-preserved. It closes 18,557
candidates exactly: 14,854 top-level measures and 3,703 unresolved amendments.
It extracts 14,795 policy areas, 156,006 legislative-subject items, 22,980
committee items, 22,320 related-bill items, 21,022 amendment items, 207 laws,
1,234 committee reports, and 1,525 CBO estimates. Missing-section (62,393),
empty-section (6,068), and unresolved-amendment (3,703) ledgers remain neutral
and visible. Sidecar manifest SHA-256:
`3a7517068ba529b15b605f4d472594563fcf8309c36cf7b5a67daa8f9f91d8f1`.

The current structured-evidence augmentation is content-addressed at
`3e4748571ff18779d840ba8914d2c8e903f26e23d1ccf0e31912f7b4bba010c9`
with manifest SHA-256
`a7f72c080ac7c5c9389121704b2dc800d8d40ef47a4e8393a83a69eb6cc8bb0b`.
Its validated zero-network semantic rollover preserves exactly **62,994**
membership proposals, **18,287** selected records, **18,557** total
candidates, **3,703** unresolved amendments, **115,223** visible gap rows,
and **218,875** role rows. It adds 428 section-local official-evidence entries
to 157 memberships and leaves 62,837 memberships neutral/unmatched. All 186
short-Act matches remain context-only and non-dispositive. Candidate and
exclusion provenance remain hash-bound, including the one explicit exclusion
provenance receipt and all **62,994** membership-evidence rows; exclusion,
ratification, scoring, downstream, sync, and production authority are false.

The roll-call source gate is now **READY** without requiring a Congress API
key. For `hr`, `s`, `hres`, `sres`, `hjres`, `sjres`, `hconres`, and
`sconres`, exact BILLSTATUS XML identity binding supplies the complete action
and recorded-vote references; the existing collector then derives and
independently validates the official House Clerk or Senate XML. A latest
action alone is explicitly insufficient. Top-level `hamdt` and `samdt`
roll-call enumeration remains fail-closed unless an official exhaustive API
or fixture/action snapshot is supplied.

The former mandatory supplemental Bioguide-map requirement was also removed.
Official chamber XML identity resolution is primary; an optional map is
hash-bound when present. Missing, ambiguous, or unmatched members in any
accepted event still block, fuzzy matching is forbidden, and all resolution
counts must close exactly. BILLSTATUS parsing now also rejects oversized XML,
DOCTYPE/ENTITY input, wrong wrapper/version, and recorded-vote Congress
mismatches; relationship enrichment emits explicit Sponsor, Original
Cosponsor, later Cosponsor, withdrawn, and unresolved-role provenance. The
combined snapshot, divergence, parser, collector, pre-sync, readiness, and
materializer suite passes 133/133. No official roll-call event generation has
been accepted yet, and production remains untouched.

## Staged pre-sync scoring decay (not yet approved or cut over)

| Congress | Staged weight | Prior live comparison |
|---|---:|---:|
| 119 | 1.00 | 1.00 |
| 118 | 0.66 | 0.80 |
| 117 | 0.33 | 0.64 |
| 116 | 0.16 | 0.512 |

Decay affects computation only. It cannot affect discovery, inclusion,
exclusion, relationship visibility, or review priority.
The 1.00/.66/.33/.16 schedule is implemented in the staged producers for
scenario and gate verification, but the required hash-bound computation-policy
approval is still absent. Production continues to use the frozen baseline;
these staged values cannot change ranks until that approval and the two-run
shadow acceptance pass.

The old workbook’s manual sign-on-letter rows also carried the prior decay.
Therefore `Legislative Score - Raw!CU` and `CW` must be recomputed from the
hash-bound manual evidence ledger under 1/.66/.33/.16. They cannot be copied
from the frozen workbook.

The independent decay-propagation audit still proves 9/9 staged source
contracts use or validate 1/.66/.33/.16, zero staged consumers use the frozen schedule,
and all 16 downstream stages are classified (2 direct, 6 mixed, 6 inherited,
2 intentionally absent). Manual LTR rows retain their old stored weights as
provenance, while the staged numeric plan rejects/canonicalizes them. Official
roll-call canonical lean/count and both say/do passes remain intentionally
undecayed under the preserved method; only the declared roll-call diagnostic
uses decay. The current overall receipt is **FAIL**, however, because the live
weekly pipeline changed downstream production outputs. The stable post-refresh
decay audit observes 35/55 exact frozen/live matches. Frozen `bill_rules.py`
plus archive rows independently retain
1/.8/.64/.512, and no legislation cutover was accepted. Last completed audit
SHA-256:
`0da7d4b63031975e7e6df1a5afcffc7a2cbb40af33c52b8e7cc1472a66ce09fc`.

Pre-sync and downstream readiness now require this full receipt rather than
the former two-producer literal check. They fail closed on a missing, malformed,
tampered, or stale receipt/source; independently rehash all embedded inputs;
require 9/9 staged contracts, 16/16 consumer classifications, zero old-schedule
staged consumers, and a 55/55 frozen baseline with no cutover; and bind the
receipt into the future shadow fingerprint. The receipt's current
approval/shadow/sync values are explicitly snapshot-only and non-authoritative,
so a later explicit decision cannot be contradicted by stale workflow metadata.
The dependency-free shadow consumer-plan harness still passes 6/6.
Live pre-sync/readiness now correctly reject the decay/freeze receipt at 35/55
while remaining blocked at 22/62 with `sync_allowed=false`.

## Full legislation-dependent recomputation scope

All **16/16** downstream consumer stages pass path-isolation and exact
output-ownership checks. An adversarial audit subsequently found that this was
not sufficient to call the emitted plan runnable: several immutable auxiliary
inputs were not yet materialized, and two first-pass prerequisite receipts had
no producer. The 16/16 result is therefore **structural only** until the input
closure and prerequisite-production gates pass. The intended chain covers:

1. accepted archive/workbook materialization;
2. official roll-call aggregation;
3. base cosponsor network, Centrality, and pre-behavior bipartisanship;
4. behavior panel;
5. behavioral dispositions;
6. cooperation;
7. receptivity;
8. augmented network;
9. category stance;
10. say/do first pass;
11. legislative raw, normalized, sublayer, and pillar inputs;
12. pillars and ranks;
13. coalitions, flips, budget frontiers, optimizer, and allocation;
14. dashboard and member desk;
15. say/do second pass; and
16. all second-pass dependents and final receipts.

The accepted-workbook producer completed a fresh exact-source
`@oai/artifact-tool` smoke test:

- capability status: PASS;
- current producer and helper hashes matched;
- frozen workbook import hash matched;
- all required sheets were present;
- targeted formula-error count was zero;
- six rendered previews were inspected;
- production written: false; and
- its adjacent regression suite passed 20/20 plus CommonJS syntax validation.

Capability receipt:
`audits/legfix5/spreadsheet_engine_verification/accepted_workbook_producer_capability.json`.

The audited-layout fallback now uses the accepted full artifact inspection plus
a bounded read-only OOXML comparison and has produced a factual `PASS` layout:

- layout SHA-256:
  `f772257658b3600da54e59dd30db587f8bc027de2f164af9a7eb30887a7d3437`;
- 533 members and 533 unique Bioguide IDs;
- all six audited baseline/calibration sheets are semantically identical when
  only formula cached values are ignored;
- all 9,594 category Sub Layer formulas match exactly;
- all 10,660 Press Normalized LET formulas match exactly;
- nonlegislative vectors are reconstructed from Press Raw under the literal
  formula-row references;
- AG:AW identify 17 distinct categories and omit CU Tax Status; no shared slot
  or merge is inferred; and
- the five-member press-order discrepancy is retained as an explicit
  legacy-preserve versus Bioguide-join decision.

There are 44,804 formula-cache error diagnostics in the old calculated
workbook surfaces, but zero blocking errors in the six factual source/layout
tables. Those old cache errors are diagnostic only and are not treated as
layout evidence. The new artifact remains deliberately
`numeric_plan_ready=false` until the CU Tax efficiency treatment and five-member
press-row policy are approved. Pre-sync is now bound to this stronger layout,
so the old extraction failure is removed without inferring either decision.

## Computation methods preserved or repaired

Base network edge weights remain:

- later cosponsor: `0.5 × decay / sqrt(current cosponsor count)`;
- original cosponsor: `1.0 × decay / sqrt(current cosponsor count)`.

Centrality remains:

```text
W = WeightedOutDegree / max(WeightedOutDegree)
B = Betweenness / max(Betweenness)
E = Eigenvector / max(Eigenvector)
raw = 0.60W + 0.25B + 0.15E
InfluenceScore = round(100 × raw / max(raw), 1)
```

The current rank authority uses workbook committee score E as its influence
pillar. Base/AUG Centrality currently has zero effective rank weight. This
treatment is preserved; no unapproved centrality-to-rank method change was
made.

The workbook numeric-plan producer now:

- recomputes all 18 raw and normalized category blocks;
- recomputes all 18 category sublayers;
- recalculates CU/CW from hash-bound manual sign-on letters;
- materializes CV/CX as explicit zero;
- recomputes AV/DX from the current accepted bills with declared one-decimal
  percentage-point precision;
- retains a machine-readable mapping for all 18 categories; and
- fails closed if any range, category, member, role, direction, decay, or
  source hash is missing.

The pre-sync supervisor now automatically runs the numeric-plan producer and
the approved-generation assembler as explicit hash-checkpointed stages once
coverage, directions, the audited layout, and human approvals exist. The
assembler preserves the accepted ledger byte-for-byte, packages every required
artifact adjacent to its manifest, and refuses existing output directories.
This removes the prior manual handoff between policy approval and shadow
execution without inferring any approval.

### Adversarial execution audit

The following defects were found after the structural 16/16 result and are
promotion blockers:

- raw auxiliary inputs such as congestion, social/press layers, votes, and
  LEP criteria were not all hash-staged; some legacy consumers silently omit
  missing optional layers;
- `pillars_ranks_prerequisites.json` and
  `network_dependents_prerequisites.json` were required but had no producing
  stage;
- neutral-direction included/current actions could disappear from activity
  evidence even though they correctly contribute zero to signed scoring;
- a truncated artifact-tool table inspection could be mistaken for zero
  nonnumeric cells;
- manual letter evidence was not guaranteed at the run-root path used by
  category-action corroboration;
- the final say/do pass lacked a fixed-point proof against the final member
  desk; and
- manual role matching used a substring that could treat later cosponsorship
  as authored evidence.

Remediation is in progress. Neutral actions are being retained in the
13-column activity surfaces with zero signed contribution; workbook inspection
must prove exact row/column/cell counts; manual roles now use exact normalized
semantics; the final say/do chain now requires an isolated fixed-point proof;
and input-closure/prerequisite producers are being added. The consumer plan
will be regenerated and must pass these stronger gates before execution.

The sealed shadow-runner regression fixture now exercises those stronger
contracts end to end: deterministic valid workbook materialization, exactly 31
declared outputs, generation-bound workbook and say/do receipts, and pillar and
network prerequisites emitted at their actual producer steps. The standalone
shadow runner passes 6/6, immutable input closure passes 8/8, and the consumer
plan passes 6/6. This proves the strengthened gates are executable; it does not
substitute for the still-blocked real accepted generation or the required two
real shadow runs.

The current combined focused regression across coverage selection, readiness,
layout, accepted roles, conservative culling, numeric/workbook contracts,
official roll calls, input closure, network dependents, say/do, and second-pass
dependents passes 125/125. The Congress.gov singleton/backoff Node suite passes
12/12.

The consolidated final regression audit compiled **110/110** Python modules
and passed **477/482** Python tests, **13/13** Node contract tests, and
**9/9** official-text matcher checks. There are zero implementation
regressions. All five Python failures are the same explicit fail-closed
production-freeze blocker: only **35/55** frozen/live sources match. The
content-addressed final regression receipt SHA-256 is
`a34cfbd85eeec08409824fa68b61bc42d86ab857b840564e6b75e4232e4199cb`.

Focused numeric-plan tests pass 8/8; the combined numeric-plan,
accepted-workbook, and recompute-wrapper regression passed 22/22. The
recompute adapter’s own current suite passes 8/8, including rejection of old
frozen CU/CW/AV/DX policy and rejection of a hidden eighteenth category.

## Computation decisions still blocking ranks

The user requested the same computation method. The audit found that the
existing method is consumer-specific:

- archive: Sponsor/Original/Later = 3/2/1;
- workbook grid: exactly proportional 4/2/1;
- stance: 1/1/1;
- say/do: 1/.5/.25; and
- base network: Original 1, Later .5, divided by square root of current
  cosponsor count.

Forcing one global role-weight policy would change the method. The recommended
resolution is an explicit `consumer_specific_legacy_preservation` profile,
with each consumer retaining its audited formula.

Decay is also a separate pending decision. Production remains on
1/.8/.64/.512, while 1/.66/.33/.16 is only a staged scenario. The user's
question about making decay more aggressive did not itself select or approve
the scenario, so no cutover or rank claim is permitted.

The more serious unresolved issue is legislative efficiency. The legacy Sub
Layer surface has **17 physical efficiency columns (AG:AW)**, maps 17 distinct
categories, omits CU Tax Status, and provides no evidence for a shared slot.
The former numeric gate nevertheless required all 18 categories in those 17
slots with exactly one approved mean-pair. That contradiction is now removed.
The numeric and assembly gates require a typed CU Tax treatment that preserves
the 17 audited singleton slots and represents either legacy AG:AW omission
with the separately recomputed FB generic-success metric, or a specifically
named audited-slot merge with explicit workbook-fact and rank-effect
acknowledgements. No treatment is selected or inferred. This remains a pending
computation decision and may change ranks.

CFPB also needs an explicit policy for accepted bill Sponsor/Original rows
outside the CU/CW letter-only columns. Those rows currently fail closed rather
than being silently misrouted. The former contradictory approval placeholder
is now a typed route contract. `UNSELECTED` is accepted only when a generation
has no matching CFPB Sponsor/Original relationships; named routes require
explicit user approval and a registered implementation. The implementation
registry is intentionally empty, so invented and unimplemented routes fail
closed.

The audited five-member press row-alignment choice is now consumed by both
numeric and assembly gates through a typed policy bound to the exact layout SHA
and normalized mismatch facts. Preserve-literal validates only the current
literal-row reconstruction; repair requires a different audited sidecar
proving a Bioguide join was actually applied. No treatment is selected. The
required decision template is bound to the audited layout and
production-workbook hashes and contains no approval. The hardened
numeric/assembly focused suite passes 30/30; the wider accepted-workbook,
recompute, and shadow suite passes 26/26; the decision-template suite passes
2/2.

Pending-decision artifacts:

- `audits/legfix5/manual_inputs/LEGISLATION_COMPUTATION_DECISIONS_REQUIRED.md`
- `audits/legfix5/manual_inputs/legislation_computation_decisions.required.json`

## Production freeze and rank status

The immutable full downstream baseline contains 55 files totaling
111,359,124 bytes, and all 55 frozen copies remain intact. The separate
scheduled weekly pipeline has finished. The stable post-refresh rehash finds
35/55 exact matches and 20 live changes, including the workbook, ranks,
behaviors, planning outputs, dashboards, and member-desk artifacts. The
baseline was not rewritten or re-approved, and the gate treats every change
as blocking drift.

- Frozen baseline workbook SHA-256:
  `5c61cab60f4831fb5842fa8c20c2703c05a986b2a7e32e39f61fe3a08cc19c31`
- Current live workbook SHA-256 after the weekly refresh:
  `915aa3b4958a86128391bba701df80988d7b5aa4499ee273c07b67deeed74fab`
- Frozen baseline `ranks_python.json` SHA-256:
  `8ef63e5734581f041820ddc8514a930a436af8bd9f44c40e996357313c027bc7`
- Current live `ranks_python.json` SHA-256 after the weekly refresh:
  `08778adabe55b12eadb03a4b152c409fff2cefaf46a6fbc5ebfe6cfb0e3e4862`
- Rank and score populations: 533 members each.

A direct frozen-versus-live rank comparison finds 238/533 ranks and 441/533
scores changed. Maximum movement is 11 places, mean absolute movement is
0.7317, and rank correlation remains 0.99995728. The largest upward movements
are Brad Sherman, Elizabeth Warren, Peter Welch, and Sean Casten (7 places);
the largest downward movement is Seth Magaziner (11 places). These are
external weekly-refresh deltas, not an accepted legislation recomputation,
and cannot be used as the requested new legislation ranks.

The entire 55-file frozen/live surface is now also sealed in an immutable
observational receipt. Audit
`0542e3c220d16b8de170e878605751eed4793b279b1b9fb456acae98a5af977d`
proves exact closure of 20 changed and 35 byte-identical files. The changed
set comprises 16 JSON files, 3 HTML files, and 1 workbook. Recursive JSON
comparison exposes 63,513 changed paths: 3,890 added, 3,881 removed, zero type
changes, and 55,742 scalar-value changes. All three HTML files differ after
line-ending and whitespace normalization. The workbook receipt binds the
audited layout, model, and rank receipts but explicitly leaves cell-level
semantics unresolved. All 20 changed consumers remain potentially
legislation-bearing and zero are accepted as legislation recomputations.
Manifest SHA-256:
`754edc4d234f25c15da94df2fc8f07815cabfd63ebfb4fa87eb428ddfbf0912e`;
current-pointer SHA-256:
`40657bf1dab35547e773db94a60cf4965d60104ea855b70d85d524f2990fc549`.
The hardened producer binds every source/copy path, size, live/frozen hash,
pass/fail state, mismatch row, and the exact 55-row decay receipt; later file
drift fails closed. Three identical reruns reused the same audit ID, and the
current pointer retained identical bytes and mtime. Producer adversarial tests
pass 8/8; the independent pre-sync/readiness informational-binding tests pass
4/4; and compilation passes. Both gates now expose the receipt as
`CURRENT_INFORMATIONAL` with `affects_gate_decisions=false` and
`can_satisfy_blocked_gate=false`; no gate, blocker, or passing condition was
added. All legislation, scoring, sync, promotion, and production-write
authority flags are false.

The hardened behavior/stance comparison now closes the four changed behavior
artifacts across the exact 533-member and 18-category identities. Audit ID
`3834b042aba16171e40d2507e2c609899563035d3772f5e38b71f5ec4063e7f5`
records 49,938 numeric pairs, 6,794 numeric changes across 103 field groups,
eight nonnumeric changes, five added paths, and zero removals, type drift, or
null transitions. Its manifest SHA-256 is
`d8500ac49d686c848fc9d5a219e6533efaa900bef3b1c80533af0f3357810577`.
It remains `PASS_OBSERVATIONAL_NONAUTHORITATIVE`: no changed value is accepted
as legislation causation, scoring authority, sync authority, or promotion
authority.

The workbook now has an exact OOXML semantic comparison, audit ID
`2321921e38ee65a9c6546299273568ea46d848e3411eec3802c3568bad8cc626`
(manifest SHA-256
`c8a968c4e41c2b081cf6d3d5f5e50e1993c63e29a7caf6703496366229afeb56`).
It finds exactly **372 nonformula raw-value differences** and exactly
**98,726 formulas** in each workbook, with zero formula text, attribute,
addition, removal, or stored-cache mismatches. Both workbooks remain in manual
calculation mode; the raw values changed while all stored formula caches stayed
unchanged. The isolated formula-cache audit
`04161aab4c18e872eb0c070005f8889c7c7521d16ebd6d5579260dd625452042`
is now final: two independent guarded Excel runs close all **98,726** formulas
with identical caches, **98,724** substantive values, two explained blank
formula results, and zero formula errors. Both calculations bound the unchanged
live source hash
`915aa3b4958a86128391bba701df80988d7b5aa4499ee273c07b67deeed74fab`;
no live, production, or mainframe workbook was written. Excel rewrote OOXML
encoding, style catalogs, relationships, and sheet metadata in the calculated
copies, so they are nonpromotable and live stored-cache freshness remains
unproven. Pre-sync and readiness therefore bind this receipt as
`CURRENT_INFORMATIONAL` only: it has no gate authority, satisfies no blocker,
and grants no legislation, scoring, sync, promotion, or production-write
authority.

The planning/dashboard comparison is content-addressed across all 11 changed
JSON and three changed HTML targets. Audit ID
`678b365fcc860a93cd5d01b2ea473fc1301a5c4671317b0411e3d71d889196b9`
(manifest SHA-256
`9d48a6b138f416bdd38bcddc3828eb3403c7036c645e7c91e9d7dc36af124a93`)
has exact frozen/live hash closure for all 14 targets and retains both
legislation causation and domain/policy correctness as unresolved for all 14.
Its focused regression passes 5/5.

Pre-sync and readiness bind the behavior, workbook, and planning/dashboard
receipts as `CURRENT_INFORMATIONAL` only. For each,
`affects_gate_decisions=false` and `can_satisfy_blocked_gate=false`; they add no
gate or pass condition and grant no legislation, scoring, sync, promotion, or
production-write authority.

The comparison is now sealed as a content-addressed, non-authoritative
533-row sidecar. A second identical run reused the same snapshot
(`created=false`), member-set closure is exact, and its focused regression
passes 2/2. Audit ID:
`c0a9e68c8cfceed2e881fe4bd07e5106a41af931da4bf6b7e6d577a77f24b140`.
Manifest SHA-256:
`dffc2798ecf93f40c571a4e24eecd87dfc1f3b7de511947d5c690e67f27a096a`;
rows SHA-256:
`c6e6e1e7d6ea704f74211cab777da4e07e8eca58ca11f05231a72725ab2b748b`;
pointer SHA-256:
`3585e8b43fc172f3d0dc84256320ce89e1eb75e0dd5329c96857e754ce662127`;
producer SHA-256:
`5b58245f05cab92fe43c555216517bc5f4c0b0babdeee03ae1443f6ba936a7b7`.
The artifact explicitly sets legislation-rank, scoring, sync, and promotion
authority to false and does not infer why the external weekly refresh moved
the live ranks. The writer now creates same-volume staging directories with
inherited audit-tree permissions instead of Windows `mkdtemp()` owner-only
ACLs. The current immutable identity also binds the producer source, the new
snapshot inherits the audit tree without manual repair, and the second live
run returned `created=false`.

There is no valid “new rank” yet. Any rank comparison before complete
coverage, ratified review, official roll calls, approved computation policy,
and the two-run shadow receipt would be incomplete and misleading.

## Remaining hard blockers

1. Complete and exactly reconcile the remaining 40 Congress.gov searches.
2. Build the distinct historical-merged final coverage generation.
3. Run official-text/article-assisted sorting and ratified culling with all
   exclusions and unresolved cases visible.
4. Complete Sponsor/Original/Later/withdrawn relationship reconciliation.
5. Run the official House/Senate roll-call stage; resolve any unmatched
   identities with the optional hash-bound Bioguide map, and supply an
   exhaustive official source for any accepted amendment.
6. Approve the consumer-specific role profile and Congress decay schedule.
7. Resolve the CU Tax efficiency treatment, CFPB bill-row routing, and
   five-member press alignment policy.
8. Implement the explicitly selected CFPB physical route and, if repair is
   selected, produce the corresponding audited Bioguide-joined sidecar; do not
   accept an invented or stale approval.
9. Assemble the approved generation and run the complete shadow chain twice.
10. Attribute every old/new delta and verify semantic/byte idempotence.
11. Obtain explicit final user approval before any mainframe sync.

Until all eleven are satisfied, `sync_allowed` remains false.
