# Legislative impact and effectiveness: implementation plan

Prepared September 10, 2026. Scope: methodology review, read-only code/data audit, and proposed implementation. Production scores, policy, collectors, and allocation outputs were not changed.

Revised to incorporate the user's subsequent direction: CU/trade-association mention frequency, without sentiment, is the proposed sector-significance signal; later cosponsorship earns progressively less credit. Cosponsor and amendment counts are additional candidate evidence, subject to validation.

## Recommendation

Build one auditable bill-level impact and milestone layer, then use it in both Melange's standard reporting model and tensor-based beneficiary model. Preserve three distinct concepts: **what a member works on, how substantial that work is, and how far it actually advances**. Keep institutional position visible, and count the legislative results obtained through that position.

The legislative substrate largely exists: local official BILLSTATUS archives contain whole-Congress records, including action histories and dated cosponsorship. The small live CU bill repository is a scored subset, not the chamber denominator. Existing CU/trade publications can support the requested sector-significance measure after document deduplication and coverage reconciliation. Independent newspapers remain a separate paper-comparison profile; they are not a prerequisite for Melange's association-frequency profile.

Implement first as a shadow comparison with complete bill-by-bill explanations. The recommended methodological destination is a five-stage results measure, with an impact-weighted advocacy measure alongside it. Retaining the current agenda/results blend is a possible Melange composite, but it must be labeled as an adaptation rather than the paper's formula.

## 1. What the paper actually specifies

Source: Bucchianeri, Volden, and Wiseman, *Legislative Effectiveness in the American States*, American Political Science Review 119(1), 21–39; equation (1), printed p. 23 / PDF p. 3. The construction and scope appear on pp. 22–24. I checked the rendered equation as well as extracted text. [Supplied paper](<C:/Users/pgoff/Downloads/legislative-effectiveness-in-the-american-states.pdf>).

For a fixed originating chamber and legislative term, let:

- \(B_{ht}\) be all eligible measures introduced in chamber \(h\) and term \(t\), including off-topic and commemorative bills.
- \(N_{ht}\) be the corresponding member population, including eligible members absent from today's Melange roster.
- \(w_b\in\{1,5,10\}\) be the bill's commemorative, substantive, or substantive-and-significant weight.
- \(I_{bk}\) indicate whether bill \(b\) reached milestone \(k\).
- \(s_{ib}\) indicate that member \(i\) is its primary sponsor.

\[
D_{htk}=\sum_{b\in B_{ht}}w_b I_{bk}
\]

\[
E_{iht}=\frac{N_{ht}}{5}\sum_{k=1}^{5}
\frac{\sum_{b\in B_{ht}}s_{ib}w_bI_{bk}}{D_{htk}}.
\]

| Milestone | Meaning |
|---|---|
| BILL | Introduced |
| AIC | Received action in committee |
| ABC | Received action beyond committee |
| PASS | Passed its chamber of introduction |
| LAW | Became law |

All five fractions are additive. A bill may contribute at several milestones; repeated actions within the same milestone do not earn repeated credit. There is no separate 1/2/3/4/5 stage multiplier. Later-stage credit becomes larger because its chamber denominator is usually smaller. With complete attribution and five nonzero denominators, the sponsor-only score averages 1 within its chamber-term.

For illustration, suppose a 100-member chamber has weighted totals of 5,000 / 1,000 / 500 / 250 / 100 at the five stages. One weight-5 bill reaching every stage contributes:

\[
20(5/5000+5/1000+5/500+5/250+5/100)=1.72.
\]

The same bill reaching only introduction contributes 0.02. A weight-10 bill would contribute twice as much **within those same fixed denominators**; changing a bill's classification requires rebuilding its denominators too.

Several boundaries matter:

- This measures relative realized effectiveness. It is not elapsed-time speed, a success probability, or a member's own passage rate. Melange can call the feature progressive effectiveness and show time-to-stage separately.
- The paper attributes bills to primary sponsors. Original and later cosponsor credit is a Melange extension.
- The paper includes measures capable of carrying the force of law and excludes single-chamber resolutions. Letters are outside its five-stage lawmaking score.
- Its significance proxy is newspaper coverage, not estimated economic benefits or approval of the bill. The 1/5/10 labels measure substantive importance, not a causal estimate of real-world impact.
- Committee chairs and party leaders receive credit when their proposals advance. The paper does not subtract institutional power from the raw score.
- Federal application preserves this mathematical structure but requires federal stage and measure rules. It is an SLES-style federal measure, not a reproduction of the state dataset.

## 2. Current Melange implementation

The code and active policy artifacts are more current than several README/specification descriptions.

| Layer | Verified current behavior | Consequence for integration |
|---|---|---|
| Standard agenda | Signed role credit, sponsor/original/cosponsor = 3/2/1; Congress decay \(0.8^{119-t}\); category priority weights | Reuse accepted membership, direction, identity, and routing. Add impact independently. |
| Standard efficiency | Signed, decay-weighted binary advancement rate among sponsors and original cosponsors; unknown outcomes omitted; normalized by category maximum | Replace coarse latest-status inference with official milestone histories. |
| Legislative subscore | 70% agenda percentile + 30% efficiency percentile; the outer model percentiles that blend again | Inserting all five terms into the 30% slot retains an extra introduction/activity reward. Treat that as a named composite, not exact SLES. |
| Reporting rank | 45% legislation, 10% press, 40% influence, 5% demographics | Keep the outer mix for the initial results comparison; avoid changing unrelated calibration simultaneously. |
| Tensor/primacy | Role weights 1/.5/.25; beneficiary-weighted portfolio average, then shrinkage and uncertainty adjustment | It measures beneficiary orientation. Simply weighting its average by bill importance does not measure total delivery. |
| Tensor cells | Effective CU cell = relevance × valence; confidence is validated, not multiplied; substitution is currently scoped to declared ACU SUPPORT/OPPOSE bills | Preserve accepted cell scope initially. Do not silently introduce a confidence multiplier or apply direction twice. |
| Tensor board/engines | Active board uses `factor_ranked`; tier seats influence allocation priority | A new results artifact will not affect tensor rankings unless the board consumer is explicitly updated. |
| Letters and amendments | Tensor letter alignment defaults to .60; amendments count .5 of an act | These are alignment/measure conventions, distinct from substantive impact 5. |

Current published standard legislative artifact: **533 members, 8,073 selected member–measure–category events, and 365 unknown-advancement entries**. These are not unique-bill counts. Agenda has 18 categories; the legacy efficiency configuration has 17 slots and omits **CU Tax Status**. The new builder should use the canonical category registry rather than spreadsheet column ranges.

Key code references:

- [Standard legislative computation](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/live_legislative_pillar.py:41>), [role weights and decay](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/bill_rules.py:190>), [pillar policy](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/pillar_policy.py:12>).
- [Reporting rank authority](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/compute_pillars.py:69>), [tensor computation](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/primacy_factors.py:346>), [active board modes](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/tier_util.py:45>).

## 3. What data we actually have

These are inspected local holdings, not a certification that collection is complete against the current official source. Counts refer to different units and should not be added together.

| Dataset | Verified holdings | Readiness / gap |
|---|---|---|
| Official BILLSTATUS ZIPs | Whole-Congress HR/S archives for 115–119; all eight top-level measure types for 117–119 | Best denominator/history source. Stored outside the repo under `C:/Users/pgoff/AppData/Local/Melange/lda_rebuild/raw/billstatus{congress}`. |
| 117–119 top-level archive records | 17,828 / 19,315 / 18,607 | Includes resolutions that must be screened for force-of-law eligibility. Not the final scoring-universe count. |
| Action histories, 117–119 | Present for 17,828 / 19,315 / 18,602 records; 247,887 action rows, all dated and type-tagged | Five 119th records lack histories. Roughly 24% of actions lack an action code, so a code-only classifier is inadequate. |
| Cosponsorship, 117–119 | 595,522 edges; all inspected edges have Bioguide ID, joining date, original flag; 747 withdrawals | Supports time-aware participation credit. Requires deduplication and sponsor/role reconciliation. |
| Live CU bill repository | 465 bills: 153 / 169 / 143 for Congresses 117 / 118 / 119 | Latest action is available, not a complete history. It is much too narrow for chamber denominators. |
| CU discovery repository | 18,579 records across 116–119, including 3,703 amendments | Query/category-filtered. Useful discovery and accepted-context input, not an all-bill universe. |
| Active press stream | 2,679 member/article turns: 1,793 congressional-site, 883 ACU, 3 other | Congressional communication cannot establish the paper's independent-media significance. |
| ACU coverage | 386 distinct base URLs represented by 883 turns; dated coverage 2024-01-15–2026-08-31 | Many turns are member-specific excerpts. 797 of 816 historical ACU cache turns contain a login marker; inspect actual accessible content before using. |
| Latest press refresh | 291 turns, including 67 ACU turns without that login marker | Receipt generated Sept. 6. No proof that all bodies are complete original articles. |
| Other independent/trade content in active feed | One CU Times story; the other nonstandard URL is a legislator X post | No consistent broad newspaper panel currently established. |
| Potential ACU bill links | Existing parser finds 136 dated turns with explicit citations, corresponding heuristically to 36 Congress-qualified candidate keys | Discovery only. Publication date can misidentify Congress for retrospective coverage. |
| Congressional letter evidence | 296 member/category rows, seven distinct letter IDs | All `DetailLink` values blank; verify original document and signatories. |
| ACU organizational letters | 533 metadata records: 240 comment and 293 policy letters, with asset IDs | Snapshot fetched July 25; no original URLs or document bodies in that snapshot. These are not automatically congressional-member actions. |
| Historical official press index | 257,223 rows, all congressional domains | Large communication corpus, not an independent-news corpus. |

For the main candidate measure types, the direct counts are:

| Congress | HR | S | HJRES | SJRES |
|---|---:|---:|---:|---:|
| 117 | 9,709 | 5,357 | 106 | 70 |
| 118 | 10,564 | 5,649 | 230 | 122 |
| 119 | 10,297 | 5,367 | 214 | 212 |

These counts still precede the joint-resolution eligibility screen. The 115/116 holdings contain 11,199 and 14,148 HR/S records respectively, without the full measure-type coverage of 117–119.

Impact classification has a separate content constraint: summaries are present for **17,809 / 12,067 / 5,564** records in 117/118/119. Text-version metadata exists for **17,817 / 19,306 / 18,576**, but those are pointers, not proof of downloaded operative text. The local historical BICAM snapshot includes a 6.59 GB full-text CSV; its bill metadata is stale and contains parsing irregularities, so it is supplemental pending validation. Recover authoritative text for ambiguous impact cases rather than pretending every current bill already has usable full text.

All 55,750 archive records have originating chamber and introduction date. Eleven 117th records lack a sponsor container and need reconciliation before sponsor normalization. Voteview roster row counts are **455/102, 451/105, and 450/103 House/Senate** for 117/118/119, with replacements and duplicates; never use those raw row counts as N. Historical committee research retains 53 usable 2021–2024 snapshot states, but exact service and leadership dates remain incomplete. These holdings support institutional context after normalization, not an immediately complete opportunity-adjusted model.

The 119th archive refresh completed September 6 at 10:06:51 UTC; archive introductions run through September 4 and record updates through September 6. Historical raw storage and the existing receipts should be ingested through configured paths rather than hard-coded user directories. Do not refresh or duplicate these large archives merely to draft the plan.

Important media caveat: the existing collector extracts surname-adjacent sentences and omits third-party stories naming no tracked member. Consequently, absence of a bill mention in the scored member feed is **not evidence of no coverage**. Significance ingestion must occur at the original document/bill level before member attribution.

Evidence anchors: [bulk refresh receipt](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/data/engine/billstatus_bulk_refresh_receipt.json>), [existing full-action parser](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/legislation/stage_billstatus_bulk_enrichment.py:571>), [CU discovery manifest](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/data/legislation/congress_advanced_current/manifest.json:130>), [canonical press readers](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/press_stream.py:98>), [bill/article linkage](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/legislation/cross_reference_legislation_press_articles.py:203>), [ACU letter snapshot](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/source_data/acu_letters_snapshot_20260725.json>), [member-excerpt collector](<C:/Users/pgoff/OneDrive/Desktop/Draft Systems/cu_press_release_scraper.R:3733>).

## 4. Canonical evidence layer

Create the following versioned, hash-bound artifacts; these are proposed files, not existing outputs:

| Proposed artifact | Required contents |
|---|---|
| `data/legislation/effectiveness_universe_manifest.json` | Congress, chamber, measure scope, source archives/hashes, as-of dates, expected/observed counts, exclusions, coverage exceptions, historical member population |
| `data/legislation/bill_milestones.ndjson` | Canonical measure ID, originating chamber, each milestone's first date, observed/inferred/not-applicable/unknown state, official action evidence, mapper version |
| `data/legislation/bill_impact.ndjson` | C/S/SS class, weight, global/sector significance basis, raw and normalized mention frequency, distinct organizations, source/window exposure, candidate cosponsor/amendment features, operative-text evidence, coverage status, review history, coding version |
| `data/legislation/bill_media_evidence.ndjson` | Original document ID/URL, originating publisher and organization family, source kind, dates, full-text completeness, content hash, verified bill links, excerpts, syndication group, count eligibility and exclusion reason |
| `data/legislation/member_measure_roles.ndjson` | Bioguide ID, canonical measure, role, joining/withdrawal dates, days from introduction to joining, timing multiplier/policy, official evidence, accepted overrides |
| `data/engine/legislative_effectiveness_v1.json` | Five denominators and member numerators, sponsor reference, Melange role results, positive/negative/net results, advocacy output, coverage and reproducibility receipt |

Use `Congress:type:number` identity, not a naked “H.R. 123.” Keep bill, amendment, resolution, and letter types distinct. Join members by Bioguide; retain display names for existing consumers. Historical chamber membership must include departures and replacements, with a documented member/seat convention; the contemporary 533-person display roster cannot define historical denominators or normalization.

### Milestone mapping

Build and validate an originating-chamber-aware mapping of action source, action code, action type, and text. Initial referral alone does not count as AIC. Distinguish committee consideration/hearings/markup, reporting or discharge/beyond-committee movement, actual originating-chamber passage, and enactment. A procedural motion is not final passage; presentation to the President is not law; a veto without successful override is not law.

Store milestones separately instead of deriving every flag from a single maximum status. A bill may bypass committee; do not invent a hearing merely because it passed. Document any logically inferred stage and its basis. Preserve early milestones after later failure or veto. Each bill earns one contribution per qualifying stage regardless of repeated votes or referrals.

For initial federal scope, include HR/S and joint resolutions eligible for enactment; screen constitutional-amendment proposals separately. Exclude simple/concurrent resolutions, amendments, and letters from the five-stage bill denominator. Retain those activities in the appropriate advocacy/measure track. A related or companion bill's enactment does not automatically make this bill law; verified text incorporation/vehicle transfer is a later explicit extension.

Official API documentation supports dated actions, source-system-specific action codes, and dated original/withdrawn cosponsorship. It also warns that action-code availability varies by source system. Use the fields together and retain text fallbacks. [Library of Congress bill API documentation](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/BillEndpoint.md).

### Impact and significance coding

Use the user's weights exactly: **C = 1, S = 5, SS = 10; congressional letters = substantive 5**. Keep importance, CU relevance, CU direction, and evidence confidence in separate fields.

1. Classify commemorative measures from title, summary, and operative provisions, with review of ambiguous naming bills or mixed measures. Everything policy-substantive begins at 5, with separate significance-coverage status.
2. Record independent-news significance using a stable, documented panel and archive window appropriate to federal legislation. One verified qualifying mention can meet the paper-style criterion; extra mentions do not create an unbounded multiplier. Check content origin so syndicated office press releases do not become independent journalism.
3. Use **sector mention frequency** as an explicit Melange adaptation, as requested by the user. Count verified bill mentions in CU, association, and separately identified trade-journalism publications. Positive, negative, and neutral mentions count equally. Endorsement, opposition, adjectives, sentiment, and rhetorical intensity do not change the significance score. Language is used only to resolve bill identity, document origin, and duplicate/boilerplate content; operative text still distinguishes commemorative from substantive measures. No favorable-language or formal-advocacy gate is required for a verified mention.
4. Retain `global_significance` and `sector_significance` separately. The paper-style profile uses independent-news evidence; the requested Melange profile uses the frequency rule below. Do not silently combine newspaper presence and association frequency under an undocumented OR rule. If a combined profile is evaluated, name and version it. Each profile uses its own consistent weights in numerator and full-chamber denominator, capped at 10. Do not add weights or apply a second significance multiplier.
5. Keep missing, paywalled, incomplete, and unsearched sources visible. A provisional substantive-5 weight is not a finding that the bill lacks significance. Mark a C/S-only baseline as such until SS coverage is adequate.

No legislator speech, press release, social post, or general media visibility earns direct credit in this new effectiveness measure. The existing 10% press pillar remains a separately defined product feature. CU organizational correspondence is evidence about a bill; it becomes a member's letter action only with verified member authorship/signature evidence.

### Frequency-based sector significance

Treat this as measured **sector attention**, used as a proxy for significance. It does not establish the magnitude or desirability of the bill's eventual economic effects. CU associations are relevant sources for the CU profile even though they advocate positions; other trade-association families can support the corresponding industry tensor profiles. Keep those sector panels distinct instead of letting a large unrelated industry's communications determine CU significance.

Define a mention event as one verified bill appearing in one distinct originating publication. Ten repetitions of a bill number inside the same article count as one event. Ten genuinely different articles over time count as ten. Preserve literal occurrence counts as an audit field, but do not reward repetition within a document. Remove member-specific URL fragments, duplicate scrape rows, article/PDF/HTML variants, syndicated copies, recurring navigation links and mechanically repeated newsletter boilerplate. Substantively new updates can be new publications; unchanged reprints cannot. A trade association's own original discussion is eligible; a reproduced congressional-office release stays excluded under the legislator-communication rule.

Track three observable values for each bill at cutoff T:

- **M:** distinct qualifying originating publications mentioning the bill, with raw publisher-level counts.
- **U:** distinct originating organizations discussing the bill. Treat affiliate and predecessor/merger relationships explicitly; copied alerts are not independent publications. Breadth is reported separately and need not be a hard requirement, since one specialized association may repeatedly cover an important bill.
- **Exposure:** which panel archives, publication dates and bill-age windows were actually observed, including the total eligible documents collected per organization.

Report cumulative counts and matched bill-age windows (initial candidates: first 30/90/180 days), using only information available by the stated cutoff. Distinguish zero observed mentions from unavailable coverage. A visible, unambiguous bill reference in an accessible title or excerpt can establish a positive mention even if the full article is unavailable; an incomplete excerpt cannot establish that an unmentioned bill was absent. Counting frequency therefore needs less text than sentiment analysis, but still needs a reconciled publication inventory.

For a candidate source-volume adjustment, let m_bo be bill b's mention documents at organization o and E_bo all eligible publications observed at o in the same window. For a fixed, sufficiently covered panel P:

\[
F_b=\frac{1}{|P|}\sum_{o\in P}\frac{m_{bo}}{E_{bo}},\qquad E_{bo}>0.
\]

This is each organization's share of published attention to the bill, averaged across the panel. Keep M and U visible alongside F: raw frequency, organizational breadth, and normalized attention answer different questions. Compare raw-count and source-normalized variants in shadow, within chamber/Congress and matched bill-age cohorts. Require adequate publication exposure before interpreting a very small denominator. Missing archives or zero-publication windows make the standard panel score unavailable; do not silently shrink P or substitute zero. A narrower observed-source profile can be reported under a different coverage label.

Preserve the requested **1/5/10** weights: commemorative remains 1; substantive remains 5; substantive bills exceeding a frozen, coverage-qualified frequency threshold become sector-SS at 10. Frequency does not multiply the stage score continuously or make commemorative bills substantive. Select minimum distinct-publication counts and frequency cutoffs using blinded historical review and rank sensitivity; these numeric thresholds are not yet calibrated. Report continuous M/U/F during that work. Repeated discussion at one organization can qualify when the declared threshold permits; no sentiment or endorsement requirement is introduced.

Freeze mention counts, source panel, thresholds and impact weights for each score generation. Rebuild all affected chamber denominators after a classification change. Historical as-of evaluations may not use later publications, eventual cosponsors, or amendments filed after their cutoff. A final-term classification applied to earlier milestones is explicitly retrospective, distinct from a real-time estimate.

### Cosponsor and amendment counts as additional evidence

| Candidate signal | What it can help establish | Initial scoring treatment |
|---|---|---|
| Unique cosponsor count | Breadth of recorded legislative support | Collect total, original, current-active and withdrawn counts; compare chamber share and matched bill ages. Use as corroboration/review evidence initially. |
| Cosponsor breadth | Whether support spans parties and constituencies | Report composition separately from volume; do not make bipartisan support necessary for an important bill. |
| Unique amendment count | Attention to changing the proposal | Separate submitted, actually offered/proposed, agreed-to, and failed/withdrawn amendments, amendment sponsors, and chamber/procedure. Initial diagnostic, not an automatic importance multiplier. |

CRS describes cosponsor recruitment as a way to demonstrate support and improve passage prospects; this is not a substantive-impact classification. Research on bipartisan lawmaking finds associations between attracting opposing-party cosponsors and effectiveness, but does not establish raw cosponsor totals as an impact measure. [CRS sponsorship report](https://www.congress.gov/crs-product/RS22477), [Center for Effective Lawmaking research](https://thelawmakers.org/wp-content/uploads/2020/10/Working-Paper-Bipartisan-Lawmakers-and-Effectiveness.pdf).

My methodological assessment: popular commemorations can attract support, and consequential bills can have few cosponsors. Amendment counts may reflect negotiation, controversy, procedure or the size of a legislative vehicle. Neither count alone justifies class SS. Avoid adding automatic weight for an author's own cosponsorship/amendment activity and then using the same activity to inflate the bill's significance; that creates a feedback reward. Milestone advancement and amendment activity also overlap. Validate the counts' incremental value against independent substantive-importance review, rather than against a score that already includes them.

The official amendment API distinguishes submission from floor proposal, identifies the amended bill/amendment, and has chamber-specific field availability. Reconstruct parent-bill links and count unique amendment IDs; text versions, actions, and provisions amending existing statutes are not additional amendments to the pending bill. The prior audit's 3,703 amendments belong to the CU discovery subset and do not certify all-bill amendment coverage. Audit full bill-to-amendment linkage and outcomes before using these features. [Library of Congress amendment API](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/AmendmentEndpoint.md).

## 5. Scoring in the two models

### Shared progressive credit

Compute the common positive bill-stage unit once:

\[
g_{bk}=\frac{N_{ht}}5\frac{w_b I_{bk}}{D_{htk}}.
\]

The sponsor reference is \(\sum_{b,k}s_{ib}g_{bk}\). It is unsigned: it measures legislative accomplishment regardless of whether CU interests benefit.

For Melange, compute:

\[
R^{(m)}_{i,j,t}=\sum_{b,k}r^{(m)}_{ibk}\,q^{(m)}_{bj}\,g_{bk}.
\]

Here \(j\) denotes the policy category (distinct from chamber \(h\)); \(r^{(m)}\) is the model's role credit at the milestone, and \(q^{(m)}\) is the accepted CU/category direction or tensor relevance × valence. Keep standard roles 3/2/1 and tensor roles 1/.5/.25 explicit initially; harmonizing them is a separate calibration decision. Denominators remain positive, unique-bill totals; no CU sign, member role multiplicity, or current-roster filter enters them.

These role-based outputs are **Melange participation-attributed results**, not proof that a cosponsor caused passage, and not sponsor-only SLES. They do not inherit its chamber-mean-one property. Keep sponsor/original/later-cosponsor contributions separately inspectable. Do not silently divide a sponsor's bill credit among all cosponsors or repeat the bill in the official denominator.

For contemporaneous follow-through, a later cosponsor earns only milestones attained on or after joining and while their sponsorship is active. Do not retroactively award earlier stages. Date-only same-day participation needs a documented convention; missing chronology is unknown rather than assumed. Historical membership credit is retained as of each milestone even if the member later withdraws, with the withdrawal visible.

In addition, implement the user's requirement that **later cosponsorship receives less credit even when the same subsequent milestones remain available**. For an additional cosponsor, let d_ib be calendar days from bill introduction to their verified joining date:

\[
f_{ib}=2^{-d_{ib}/H},\qquad
r^{(m)}_{ibk}=r^{(m)}_{\mathrm{base},ib}\,f_{ib}\,
\mathbf{1}\{\text{joined by milestone k and active then}\}.
\]

Use f=1 for the sponsor and official original cosponsors; they retain their distinct existing base role credits. Additional cosponsors receive the declining multiplier on their own base credit. H is a versioned half-life to calibrate: **180 days is an illustrative shadow candidate, not an adopted parameter**. At H=180, a later cosponsor receives 70.7% of their base credit after 90 days, 50% after 180 days, and 25% after 360 days. These percentages apply to the later-cosponsor role, not to the sponsor or original-cosponsor weight.

Apply the timing multiplier once in new bill-action agenda and participation-attributed results. It never enters the unique-bill chamber denominator or discounts the sponsor-only reference. It is fixed by introduction-to-join delay, so an early cosponsor's credit does not erode simply because scoring runs later or the bill waits in committee. Do not normalize delay by eventual passage date, bill age today, or final cosponsor count: those introduce hindsight or unstable early-credit values. Quarantine negative delays or inconsistent original-cosponsor records for reconciliation rather than giving them enhanced credit. Current membership eligibility and missing dates remain explicit; flag members who entered Congress after introduction and test this opportunity constraint rather than silently overriding the user's calendar-delay rule. Rejoining and withdrawals require dated episodes; they must not reset a late participant's clock or duplicate earned stages.

Preserve category-specific views. When combining them, apply existing topic priorities once and declare how multi-category allocation works; never multiply the whole bill once per category and present the result as a unique-bill effectiveness score. A chamber-wide tensor CU result should use the bill's single CU cell once.

Show beneficial advancement, harmful advancement, and net CU results separately. An important anti-CU bill can give its sponsor high unsigned lawmaking effectiveness and negative CU results. This distinction is essential.

### Standard reporting model

During shadow operation, publish the new results beside the existing 70/30 legislative score. The recommended eventual result-based version replaces the **entire** 70/30 legislative subformula with the within-chamber percentile of new signed results, retaining the outer 45/10/40/5 policy and existing final rank machinery. Implement this as an explicit results-mode `Leg%` input to `compute_pillars.py`: bypass its current pooled percentile transformation of `O` for that mode. Otherwise a within-chamber percentile would be ranked again across the mixed House/Senate roster. Keep the legacy transformation only in legacy mode and test both interfaces. Cross-chamber display then compares relative chamber standings, not absolute lawmaking output.

Also publish impact-weighted agenda/advocacy, including letters. Use `impact_weight / 5` when expressing it in legacy substantive-act units: commemorative .2, substantive 1, significant 2. This is merely a common rescaling of 1/5/10, not different relative weights. Preserve role credit, approved direction, and any separately declared measure discount.

There is a real product choice here: the exact five-stage score cannot directly credit letters. If all activities must remain in one headline number, retain a clearly named **Melange composite** in the shadow comparison using the existing 70% impact-agenda / 30% five-stage-results blend. That keeps letter credit and minimizes interface change, but deliberately gives agenda/introduction additional weight. Compare this candidate against the results-only candidate before choosing the production basis. Do not claim that either adding letters to BILL or changing five equal terms is required by the paper.

### Tensor/primacy model

Keep current `factor_ranked` as beneficiary orientation and add a separate `realized_results` computed from the same bill-stage evidence with tensor role weights and accepted cells. Add `advocacy_impact` for letters/non-law measures. A member with one highly CU-aligned introduced bill should no longer look equivalent on results to a member who advances many such bills.

For a results-centered tensor board, add an explicit versioned board mode ordered by the CU signed-results measure, retaining applicable evidence and conduct rules and exposing the existing orientation value alongside it. Shadow tier movement and resulting allocation changes before activation. Joining new fields alone is not integration: `tier_util.py`, industry views, and the allocation-priority consumer must read the chosen new board mode.

Do not multiply the new standard score by the existing primacy factor to create this measure. Compute contributions per bill so impact, stages, and CU direction each enter once. If evidence shrinkage is used, count distinct underlying measures/role evidence, not impact-weighted milestone mass; one significant enacted bill is not fifteen independent observations. Existing confidence and minimum-evidence policies need their own versioned treatment rather than automatic reuse with new units.

### Terms, zeros, and comparisons

Compute denominators separately for each Congress and originating chamber, then display or aggregate complete term scores. For a multi-term Melange view, reuse the current decay convention only **after** term-level normalization and label the result as the historical product aggregate. Do not pool old introductions and current laws into one denominator. Show the current term separately for new members.

If a stage has no chamber activity, its fraction is undefined. Report the full reference as unavailable/provisional with observed components; do not silently use epsilon denominators, a four-stage divisor, or fabricated zeros. Missing bill histories are a different issue and require a coverage exception or repair. Current-Congress results need a visible as-of date and comparison to similar points in prior terms, rather than a completed-term interpretation.

## 6. Institutional power

Count actual advancement by chairs, leaders, majority members, and senior legislators fully. Do not apply an automatic discount for their ability to obtain results. At the same time, office possession alone earns no bill milestone.

Display current and, where supported, historically effective majority status, committee role/jurisdiction, leadership, tenure, and time in office beside results. Begin with descriptive peer comparisons; defer any observed-versus-expected residual until role histories and multiple terms are verified. A residual should be a contextual companion, never a replacement for observed accomplishment or a causal claim about personal skill.

The standard model already gives influence 40% of its total. Review whether the new results signal creates excessive repeated reward for position, but treat that as a measured sensitivity analysis, not a reason to remove genuine outcomes. The existing coalition-pricing “majority-neutral capability” metric intentionally excludes LES/follow-through; retain it as a separate construct. [Existing capability exclusions](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/lobbying/coalition_pricing.py:28>), [contextual residual pattern](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/engine/responsiveness_layers.py:341>).

## 7. Implementation sequence and release gates

| Phase | Work and proposed integration | Completion evidence |
|---|---|---|
| 1. Freeze and reconcile scope | Inventory existing official archives; reconcile eligible measure counts, action coverage, rosters, and dates. Start with completed 118th; run 119th separately as provisional. | A reproducible universe manifest; explicit exclusions and missing records; no CU-only denominator. |
| 2. Build milestones and roles | Add `fec/legislation/build_bill_milestones.py`; reuse official identity/ingestion helpers; capture full histories, dated roles and withdrawals. | Reviewed five-stage records, evidence links, duplicate checks, repaired or explicit unknowns. |
| 3. Build impact evidence | Add `build_bill_impact.py` and bill-centered media registry; classify C/S across the full eligible corpus; reconcile CU/trade publication inventories and frequency counts; recover letter evidence; retain a separate independent-news comparison panel. Audit candidate cosponsor/amendment features. | Versioned frequency policy, deduplicated M/U/F and exposure, sentiment-invariance check, source-completeness metrics, global/sector distinction, hand-review audit. No newspaper requirement blocks the CU-frequency profile. |
| 4. Implement math | Add pure `fec/engine/legislative_effectiveness.py`; emit sponsor reference, timing-discounted role outputs, tensor results and advocacy components. | Hand-computed fixture agreement, denominator receipts, correct signs/roles/timing, monotonically decreasing delay credit, repeatable runs. |
| 5. Integrate shadow consumers | Extend `live_legislative_pillar.py`, `primacy_factors.py`, `tier_util.py`, and industry-board consumers under versioned policy. Build current, results-only, and legacy-composite comparisons. | Separate reporting-rank, tier, and allocation deltas; every material change traceable to measures and stages; live authorities unchanged. |
| 6. Add product explanations | Extend member desk/dashboard bundles and templates; include impact class, stage timeline, role date, source evidence, numerator/denominator and institutional context. | A user can explain why two members differ and distinguish missing data from no advancement. |
| 7. Select and promote a generation | Record the chosen results-only or advocacy-composite basis and tensor board mode. Use the existing locked pipeline, calibration/version checks and atomic-generation pattern. | Acceptance report, generation hashes, synchronized surfaces/engines, retained prior generation and tested rollback. |

Pipeline ordering: verified official repository and role membership → universe/milestones/media/impact → effectiveness artifact → standard rank computation → tensor/primacy build → allocation engines → display builds and audits. Place local transformation steps before consumers in [the canonical pipeline](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/run_pipeline.py:84>). Keep network collection in refresh/intake work; scoring should reproduce from frozen local inputs.

New evidence producers should not rely on importing command-line modules that perform work at import time. Use pure readers/math modules and atomic writers. Update source manifests and calibration hashes for every dependency, including impact policy and stage dictionary.

### Validation that matters

- Verify the example above and a tiny complete chamber: sponsor scores average 1 only under the reference's stated conditions.
- Test an introduced-only bill, committee hearing, report/discharge, home-chamber passage, failed procedural motion, veto, enactment, and committee-bypass path.
- Confirm event duplication earns no extra stage credit, companions do not share law credit automatically, and letters/resolutions/amendments never enter an ineligible denominator.
- Confirm later cosponsors do not receive earlier milestones; exercise withdrawals and date ambiguity.
- With the same base role and eligible milestones, increasing introduction-to-join delay strictly lowers credit; moving the scoring date alone does not change that multiplier. Original-cosponsor status retains its base role credit.
- Rewriting a qualifying association article from supportive to critical without changing its bill references leaves significance unchanged. Repeated strings, member fragments, HTML/PDF copies and syndicated duplicates do not add mention events; a genuinely new publication does.
- Raw cosponsor and amendment counts cannot automatically change C to S or SS. No future mention, signature or amendment can enter an earlier as-of generation; unavailable publication coverage remains unknown.
- Confirm a new eligible chamber bill changes every relevant member's denominator, even when the bill is outside Melange's CU selection.
- Confirm SS reassignment changes numerator and denominator consistently, source syndication adds no extra weight, self-publication cannot establish independent SS, and negative CU direction cannot cancel denominators.
- Confirm bill impact and relevance appear once, multi-category aggregation is explicit, all 18 canonical categories are available, and historical scores use historical populations.
- Hand-code a stratified sample across chambers, stages, impact classes and exceptional measure types. Independently adjudicate disagreements; report class-specific accuracy and error patterns before setting release thresholds.
- Compare standard ranks, tensor factors/tiers, allocation outputs, majority/minority and chair/rank-and-file results, thin portfolios and heavy cosigners. Examine outliers rather than tuning toward named preferred members.
- Run the appropriate existing engine/legislation tests and generation audits after implementation; verify shadow mode preserves current production artifact hashes. No production pipeline run is needed for this plan.

## 8. Decisions to record before production activation

These do not prevent building the evidence layer and shadow scores.

| Decision | Recommended starting position |
|---|---|
| Core results formula | Five additive stage shares with full-chamber positive weighted denominators and N/5 normalization for the sponsor reference |
| Headline standard legislative basis | Prefer results-only for fidelity; compare the explicit existing-ratio advocacy composite if retaining letter credit in the single headline is required |
| Tensor board basis | Add explicit results mode; retain orientation and advocacy as visible dimensions; do not silently change `factor_ranked` semantics |
| Role weights | Preserve each model's current base ratios; additional cosponsors receive a monotonic introduction-to-join discount and only eligible future milestones. Calibrate H in shadow. |
| Significance | CU/trade publication frequency without sentiment for the requested sector profile; separately retain independent-news comparison. Freeze count unit, panel, exposure and 5-to-10 threshold. |
| Cosponsor/amendment counts | Collect normalized counts and procedural distinctions as corroboration; no automatic impact multiplier before independent validation |
| Letters | Substantive 5 in advocacy, legislative milestones not applicable; verify documents/signatories |
| Institutional power | Full realized credit with explanatory context; no default neutralization |
| Initial scope | 118th completed-term validation plus separately labeled 119th live view; extend backward once universe and roster completeness are certified |

The first useful deliverable should be a complete 118th-Congress milestone/impact audit and a shadow member comparison. That will establish how much the rankings change because of substantive importance and actual advancement, before any production ranking or allocation policy changes.
