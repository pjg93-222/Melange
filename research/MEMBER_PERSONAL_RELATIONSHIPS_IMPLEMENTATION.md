# Member personal relationships: implementation framework

This is the archived initial design. The user's later corrections are implemented
in [the full-history methodology](MEMBER_PERSONAL_RELATIONSHIPS_V3_MATH.md).
Current results are in
`outputs/member_personal_relationships/20260910_full_history/REPORT.md`.

Version 1.0 | September 10, 2026 | Complete design rewrite. No relationship model has been fitted or deployed by this document.

## 1. Purpose and governing question

Infer who personally likes, trusts, seeks out, resents, or avoids whom in Congress, **beyond the relationships expected from geography, ideological alignment, party, shared interests, and institutional responsibilities**.

The governing question is:

> Given the colleagues this member could interact with, and the political reasons for doing so, what indicates a particular personal attachment or aversion toward this colleague?

The inference combines five inputs: repeated personal expressions and interactions; personality compatibility; proximity in the personal network; directed positive/negative network patterns; and selective working relationships beyond political expectations.

Geography and ideology explain the baseline. They do not earn friendship points. Ideological or geographic distance does not earn friendship points either: unusual cooperation can have a strategic explanation. Genuine friendships within a delegation or ideological camp remain eligible; they must be distinguished by personal signals rather than assumed from membership in that group.

Direct friendship declarations are not required for every prediction. A model can infer a tie from compatible personalities, social connections, and distinctive behavior. The product must distinguish such an inference from a relationship documented by personal evidence.

## 2. What is being estimated

The primary unit is an ordered pair of members, A -> B, assessed as of date t. Begin with present relationship inference; future friendship formation is a separate task with separate labels and evaluation.

| Construct | Definition and treatment |
|---|---|
| Personal affinity | A's liking, fondness, or enjoyment of B; the main positive target |
| Personal antagonism | A's resentment, dislike, personal distrust, or deliberate interpersonal avoidance of B; the negative target |
| Personal trust | Confidence in B as a confidant or person; a separate facet, potentially supporting affinity |
| Professional respect/reliability | Regard for B's competence or conduct at work; distinguish from liking |
| Mutual friendship | A pair-level interpretation requiring reciprocal evidence or a separately validated pair model |
| Relationship strength | Closeness, durability, or intensity conditional on a tie existing; not the same as confidence that it exists |
| Opportunity/familiarity | Access to, contact with, or knowledge of one another; can precede either affinity or rivalry |

Estimate affinity and antagonism separately. They are not complements and can coexist. Different periods can also show friendship followed by estrangement; distinguish change from simultaneous mixed feelings. Low affinity does not mean hostility. No observed relationship does not mean an observed neutral relationship.

Keep three dimensions separate in every output: predicted relationship, supporting documentary evidence, and uncertainty. A high-confidence prediction does not automatically imply a close friendship or direct corroboration.

Candidate members come from the dated target roster, with all ordered non-self pairs eligible for assessment. Model House, Senate, and cross-chamber opportunities explicitly. Historical members can be retained as dated intermediaries without appearing as current target members. Unknown or nonoverlapping congressional service does not prove that two people never met elsewhere.

## 3. How the model looks beyond geography and ideology

Construct two linked components:

1. **Political and opportunity baseline:** expected interaction, public regard, and cooperation given party, DW-NOMINATE distance, constituency/geography, interests, chamber, leadership, committee roles, shared tenure, and activity.
2. **Personal relationship component:** personality compatibility, selective personal conduct, personal-network proximity and signed patterns, persistent voluntary contact, and cooperation beyond that baseline.

Use geography and ideology to construct comparisons, not to label friends and enemies. Examples include comparing A's treatment of B with A's treatment of similarly situated colleagues, and comparing A/B network overlap with pairs having comparable political alignment and institutional exposure.

For calibrated models, retain the context-only prediction p0 and full prediction p1. Their log-odds difference is an incremental predictive signal, not a probability or a causal estimate of friendship. Show that signal and its contributing features alongside the full prediction. Raw context-only scores do not populate the Personal relationships layer.

The implementation must demonstrate added information through:

- Held-out improvement over geography/ideology/party/opportunity baselines.
- Tests within matched political and geographic strata.
- Explicit cases of same-party hostility and cross-party friendship, plus same-party friendships and cross-party working alliances without documented affection.
- Comparisons that remove personality, personal proximity, signed structure, and distinctive cooperation one at a time.
- Context-preserving feature shuffles and hub-removal sensitivity checks where feasible.

Success does not require a graph uncorrelated with party: real friendships can cluster politically. It requires distinguishing personal relationships among otherwise comparable pairs. Unexplained behavior is a candidate signal, not proof that all unmeasured incentives have been removed.

A positive increment over the baseline is not a prerequisite for retaining a directly documented friendship. The baseline determines how diagnostic a proxy is; it does not invalidate personal evidence because the members happen to be political or geographic peers.

## 4. Sources, attribution, and observation coverage

### 4.1 An all-topic evidence ledger

Use floor and hearing turns, interviews, member-authored statements, public accounts of personal interactions, and reporting with identifiable attribution. Include all topics. Credit-union, finance, or bill-specific selection alone is unsuitable for a general personal network.

Preserve original source ID/locator, exact text, surrounding turns, speaker, target, event date and precision, publication date, retrieval date, and immutable content hash. Unknown dates stay unknown. Source documents supply evidence; instructions embedded in them are not executed.

Distinguish account owner, author, quoted speaker, reporter, witness, and target. A release hosted by A's office is not automatically A's own words. A staff-authored post is an office expression unless personal attribution is established. Separate reported statements from independently witnessed actions. Reporters repeating each other are not independent witnesses.

Resolve people with stable Bioguide IDs and dated service/alias records. Do not assign an ambiguous surname to today's roster when the passage concerns a former member, relative, staffer, or other person.

### 4.2 Event coding

| Category | Examples of the information sought |
|---|---|
| Personal warmth | Specific fondness, enjoying company, affection beyond generic courtesy |
| Personal trust/support | Confidences, seeking personal advice, concrete support during difficulty |
| Chosen association | Repeated voluntary meals, visits, informal conversations, or social activity together |
| Personal hostility | Explicit dislike, resentment, personal grievances, contempt, or distrust |
| Deliberate avoidance | Attributed intentional avoidance with an interpersonal explanation |
| Professional respect | Competence, negotiation reliability, or effective work |
| Policy/strategic conduct | Agreement, opposition, coalition messaging, leadership loyalty, campaigning |
| Courtesy/ambiguity | Procedural thanks, stock honorifics, unclear sarcasm, unresolved speakers or targets |

Events can have several codes. Preserve professional/policy meaning even when an interaction also contains personal feeling. Do not infer animosity from voting disagreement or affection from a repost alone. Friendly teasing needs context; personal-sounding attacks can still be coordinated campaign rhetoric.

Code naturalness through observable circumstances: volunteered, broad conversational prompt, explicit question about B, scripted/ceremonial, or unknown. A prompted but specific personal account remains informative. An excerpt without the question cannot establish spontaneity.

### 4.3 Independence and unequal visibility

Assign both source-family IDs and underlying episode IDs. Clips, transcripts, syndicated articles, and repeated versions of one anecdote are grouped. Recurrence means independent episodes, not repeated coverage. Retain denials, corrections, reconciliation, and contrary personal accounts.

Record source coverage by member, period, setting, topic selection, and attribution quality. Prominent members have more opportunities to be mentioned; publicity cannot be treated as relationship strength. Compare member-specific behavior in comparable settings and use episode counts with exposure information. Sparse coverage widens uncertainty rather than establishing absence or hostility.

Use balanced retrieval: search for warmth, conflict, professional-only explanations, and counterevidence. Review randomly sampled raw material as well as model-selected candidates. Freeze search budgets and source criteria for evaluation pairs so promising predictions do not receive uniquely favorable evidence collection.

## 5. Opportunity versus choosing one another

Add an explicit opportunity table: overlapping service, prior workplaces, freshman cohort, committees, caucuses, shared events, and other documented settings where members could meet. These explain access and familiarity.

Within those opportunities, seek **selective choice**: whom A repeatedly approaches, spends discretionary time with, seeks advice from, or continues seeing after the common assignment ends. A shared hobby is context; documented recurring choice of each other as companions adds relational evidence. A group event does not imply every attendee likes every other attendee.

This addition is motivated by Feld's account of social settings organizing interaction. Applying it here means representing the setting separately from the specific relationship that may develop within it; the congressional implementation is our design choice. [Feld, 1981](https://www.journals.uchicago.edu/doi/10.1086/227352).

Persistence across disagreement, leadership loss, changed committees, or reduced professional utility can be informative. Record documented circumstances rather than inventing political costs or motives. These transitions are useful comparisons, not automatic natural experiments.

## 6. Personality as an active friendship prior

**Working assumption:** among members with comparable opportunities to know one another, similarity in extraversion, agreeableness, and openness increases initial friendship propensity. Similarity can mean two introverts as well as two extraverts.

Selfhout et al. studied 205 Dutch university freshmen across five monthly waves in 10 groups. Their Table 2 distinguishes:

| Feature | Starting hypothesis |
|---|---|
| Extraversion similarity | Positive contribution to friendship selection |
| Agreeableness similarity | Positive contribution to friendship selection |
| Openness similarity | Positive contribution to friendship selection |
| A's extraversion | Greater outgoing nomination propensity |
| B's agreeableness | Greater incoming nomination propensity |
| Conscientiousness/neuroticism similarity | Exploratory; this study supplies no corresponding positive formation finding |

These are differentiated hypotheses, not an equal-weight Big Five compatibility score. The study's population, friendship-formation outcome, and self-ratings differ from congressional adults and public-behavior estimates. Do not import its coefficients or infer a friendship probability above 50% merely from similarity.

Use separate trait estimates, measurement basis, source lineage, dates, and uncertainty. Public speaking style or a narrative profile is not automatically a validated personality measurement. Missing traits remain missing. Freeze instrument scaling and training-reference standardization before evaluation.

Audit political content leaking into trait estimates: identical party talking points are not personality similarity, praise of allies is not by itself agreeableness, and media volume is not by itself extraversion. Compare recurrent behavioral style across settings while retaining topic and role context. Test whether the trait contribution survives political/geographic matching, especially where openness overlaps with interests or ideology.

An initial similarity measure is `S_k(A,B) = exp(-abs(z_Ak - z_Bk))`. This is a design choice, not Selfhout's fitted function. Use weak positive-centered priors for the supported similarity/actor terms, and compare with zero-centered priors. Congressional data may weaken or reverse them. C/N coefficients begin near zero but are not declared permanently irrelevant.

Account for uncertainty rather than treating two imprecise matching estimates as certain compatibility. Exclude focal-pair personal episodes from trait estimation in independent-prediction tests. Where exclusion or uncertainty estimation is unavailable, qualify or omit the affected feature. Do not count identical evidence once as agreeableness and again as proof of a friendship.

Behavioral similarity may precede a tie, follow it, or reflect shared surroundings. That does not prevent prediction, but it prevents claiming that compatibility caused the friendship from association alone. This separation is consistent with the identification problem discussed by [Shalizi and Thomas, 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3328971/).

## 7. Personal-network proximity and signed structure

### 7.1 Three typed graphs

Maintain separate graphs for personal relationships, public references, and legislative cooperation. Preserve direction, sign, dates, evidence status, and source lineage. A legislative path is not automatically a chain of friends, and an office endorsement is not automatically personal warmth.

Bootstrap the personal graph from source-reviewed personal episodes. Preserve provisional seeds and their reliability separately from independently corroborated ties. Personality-generated or model-predicted ties do not become observations used to generate the next batch of predictions. If seed coverage is thin, use the other predictors and report limited network support.

Represent group events and their members explicitly before projecting pair features. Co-attendance or one shared story cannot manufacture an independently supported clique. Multiple paths originating from the same article/event share provenance and must not be counted as independent evidence.

### 7.2 Proximity measures

| Feature | Interpretation and control |
|---|---|
| Shortest positive path | Directed A -> B and B -> A distances, excluding the focal pair |
| Shared personal neighbors | Incoming, outgoing, and reciprocated neighborhood overlap separately |
| Normalized overlap | Shared neighbors relative to neighborhood union, with degrees/coverage reported |
| Selective intermediaries | Compare inverse-degree or Adamic-Adar weighting so prominent hubs do not dominate |
| Distinct short routes | Separate intermediaries and source-independent connecting evidence |
| Persistence | Recurring overlap and durable connecting ties across dated windows |
| Excess overlap | Overlap beyond matched political/opportunity pairs or a documented constrained network baseline |

Personal proximity is pair-specific; it is not overall centrality or the distance between dots in a graph drawing. In a dense all-bill cosponsorship graph, nearly every pair can be one or two steps apart. Diagnose distance saturation and compare weighted/selective overlap rather than assuming shortest path remains informative. Choose any graph threshold on training data, disclose it, and test sensitivity.

Retain degree and coverage because normalization can otherwise make a single shared contact look decisive. Where fewer than two distinct neighbors exist, intermediary weights that require a logarithm need a defined convention. Missing paths in an incomplete graph do not establish social separation.

Test personality-proximity interactions such as `S_E * normalized_positive_overlap`, with analogous A/O terms. The hypothesis is that compatibility is more informative about an existing relationship when social worlds overlap. It remains an estimated interaction, not a mandatory multiplier or a rule suppressing isolated members.

### 7.3 Signed relationships and status

Use directed positive/negative degrees, reciprocity, and the 16 signed two-step patterns from Leskovec et al. Fit their contributions rather than imposing balance as a law.

- A likes C and C likes B can support predicted affinity A -> B.
- A likes C and C dislikes B can support predicted antagonism A -> B.
- Shared enemies do not automatically imply friendship.
- Shared social circles can contain rivals as well as friends.

Tang reports that 82.64% of negative pairs in Epinions and 87.86% in Slashdot were within three hops in the positive graph. This is the proportion of negative pairs that were close, not the probability that close pairs are enemies. Proximity alone cannot determine sign.

Measure formal leadership, committee authority, seniority, and informal esteem separately. Use Leskovec's convention that A -> B positive can express A viewing B as higher status when testing status features; do not equate rank with affection. Tang's Section 3.2 uses the opposite verbal higher/lower orientation, so check definitions before combining implementations.

Test soft balance/status features with shrinkage and a zero-penalty comparison. Never delete observed personal evidence because it violates the theory. Do not force a two-camp global partition. Confidence-weighted provisional negative seeds are an optional later experiment, with their noise retained and results compared against observed-seed-only models.

## 8. Selective working history and cooperation

Build a dated member-bill opportunity panel across subjects. Distinguish A supporting B's bills from both appearing on a long cosponsor list. Include reciprocal support, original/early cosponsorship, bill families, substantive joint work, and cooperation across issues or role changes. Joint letters and amendments can add distinct work evidence when adequately sourced; an office press release is not proof of personal coauthorship.

Fit expected support using party, ideology, geography/constituency interests, issue focus, chamber, committee/leadership roles, shared tenure, sponsor activity, and A's general cosponsorship propensity. Use features available before the opportunity. Current friendship predictions do not enter this baseline.

Start with a 30-day joining window to reuse existing dated methods, retain seven-day early support, and add longer-window sensitivity. Handle member entry/departure and censored observation periods. Leadership norms, low bill activity, and cross-chamber differences can explain missing cosponsorship.

```text
distinctive cooperation(A -> B) = observed eligible support
                                  - expected support under political/opportunity conditions
```

Report observed/expected counts, the opportunity denominator, period, and uncertainty. Group reintroductions and related bills. Add early/reciprocal/cross-issue dimensions rather than equating a large residual with friendship. Estimate this baseline within training folds, not using held-out outcomes.

The main baseline excludes pair-specific prior cooperation so it does not automatically absorb a longstanding personal partnership. A second sensitivity model includes earlier pair history to distinguish persistent collaboration from newly unusual behavior. Neither residual is a causal measure of affection. Low support is not automatically hostility.

## 9. Time, reciprocity, and relationship change

Keep an episode timeline and versioned as-of assessments. Track first observed evidence, recurring evidence, disagreement, rupture, reconciliation, and last supported status. First observed is not necessarily when the relationship began.

Separate formation, persistence, and dissolution. An isolated dispute should not erase years of friendship mechanically; an explicit later rupture should not be averaged away by old praise. Counterevidence must be interpreted in its period. Sparse recent coverage produces stale or uncertain current status, not automatic relationship decay into neutrality or hostility.

Start with 24 months of current evidence and a longer historical record, comparing 12/24/36-month windows. These are design conventions. Preserve described event dates so a newly published old anecdote does not become a new encounter.

Maintain A -> B and B -> A separately. In ordinary evidence-based assessment, use available reciprocal observations. In a hidden-pair evaluation, remove both directions so the answer cannot leak through reciprocity. Do not multiply directional marginal probabilities to manufacture a mutual-friendship probability; use a separately validated pair model or explicitly reciprocal evidence.

## 10. Initial inference model and output rules

### 10.1 Proposed model

Begin with regularized directed models for affinity and antagonism. Use an interpretable specification before more complex graph models. For each polarity s:

```text
logit P_s(A -> B at t) = g_s(political context and opportunity)
                       + h_s(personal expressions and voluntary choice,
                             trait similarity and actor traits,
                             personal proximity and signed patterns,
                             distinctive cooperation,
                             time and personality-proximity interactions)
```

Fit the baseline and additions with nested development folds; any standardization, expected-count model, graph threshold, and calibration also belongs inside that process. Use member-level partial pooling where data permit, without letting publicity alone become popularity. Coverage informs missingness, uncertainty, and validation strata; low visibility is not itself evidence of low true affinity.

Do not multiply independently fitted channel probabilities: statements, traits, work, and networks share information. Estimate jointly with shrinkage and feature-group ablations. Missing features trigger qualified estimates or abstention rather than invented values. Preserve contradictory observations as inputs.

The context-only model is a benchmark. The model's non-context contribution, inspected alongside observed/expected comparisons, is what establishes additional personal information. No arbitrary percentage allocation among the five inputs is set before validation.

### 10.2 Prediction and evidence remain separate

| Situation | Output |
|---|---|
| Geography/ideology/party/opportunity only | Context expectation; no personal relationship claim |
| Personality similarity only | Compatibility and initial relative propensity |
| Combined personality, selective work, and/or personal-network support | Eligible for inferred affinity without a friendship quote |
| Personal negative events and/or informative signed structure | Eligible for inferred antagonism; proximity/dissimilarity alone do not assign it |
| Attributed personal episode | Direct evidence, with source and context |
| Independent supporting accounts/episodes | Corroborated evidence, with independence explained |
| Conflicting accounts or different periods | Contested, mixed, or changing relationship, as appropriate |
| Too little information | Unknown or exploratory; missing is not a neutral label |

Evidence status can be `none`, `direct`, `corroborated`, or `contested`. Independent corroboration is not defined by a raw article count. Record recurrence, source diversity, attribution, and directness separately. A single particularly explicit account can be strong direct evidence without being independently corroborated.

Prediction status is `unfitted`, `exploratory`, or `validated`. Until fitting/calibration, output feature profiles and evidence assessments; exploratory ranks follow fitting. Numerical probabilities and high-confidence inferred labels require held-out calibration for the stated population. Probability of existence, assessed closeness, documentary quality, and prediction uncertainty have separate fields.

## 11. Data contracts and repository integration

### 11.1 Proposed artifacts

Place versioned generations under `outputs/member_personal_relationships/<run_id>/`.

| Artifact | Required information |
|---|---|
| `sources.ndjson` | Original locator/hash, publisher/author/speaker, source family, dates, corpus selection |
| `events.ndjson` | Actor/target/witness IDs, episode/group IDs, exact excerpts/offsets, context, codes, elicitation, choice, corrections, review provenance |
| `coverage.ndjson` | Member/period/source availability, topic/setting coverage, attribution and extraction quality |
| `opportunities.ndjson` | Dated service, roles, settings, participation, possible contact, and source lineage |
| `pair_features.ndjson` | Political baseline inputs; trait estimates/similarities; observed/expected cooperation; graph proximity/motifs; uncertainty; contributing event/edge IDs |
| `relationships.ndjson` | Direction/date, separate polarity predictions, baseline/incremental signal, evidence status, facets, reciprocity, temporal state, optional strength, confidence/calibration |
| `review_queue.ndjson` | Ambiguous identities, contested meaning, uncovered pairs, conflicting evidence, and informative cases |
| `manifest.json` | Input hashes, schema/code/model/prompt/graph versions, training/cutoff rules, coverage, exclusions, validation status |

All future modules should be import-safe, use read-only source access, and write new generations atomically. Keep raw evidence and correction history. Machine classification, assistant review, and human adjudication have distinct provenance; a model cannot assign itself independent human approval.

### 11.2 Reuse with explicit boundaries

| Existing component | Role in the new implementation |
|---|---|
| `social_media.db` speeches/posts/interactions/members | Source adapters; recover original context and audit selection. Do not invent missing historical retrieval dates. |
| `fec/members/member_reference_layer.py` and `member_references.json` | Candidate discovery. Reclassify personal versus policy meaning; aggregated signs, short snippets, and scoring caps are insufficient for recurrence. |
| `fec/members/member_identity.py` | Conservative joins supplemented by historical service/identity records |
| `fec/network/social_interaction_layer.py` | Raw mention/repost discovery; recover direction and meaning before personal inference |
| `fec/network/co_appearance_layer.py` | Episode discovery; verify actual interaction instead of assuming separate guests on one broadcast chose each other |
| `fec/network/build_multilayer_network.py` | Audit existing layer provenance and density; do not treat the blended influence graph as the observed personal seed graph |
| `fec/research/cosponsor_refinement/` | Dated joining, exposure, censoring, and evaluation patterns; finance/agriculture scope does not automatically generalize to all-topic friendship |
| `fec/speech/assess_member_behavior_evidence.py` | Evidence identity, independent episodes, and contradiction patterns adapted to dyads |
| Big Five inputs used by `fec/surfaces/make_member_desk.py` | Trace accepted measurement lineage and uncertainty; prose portraits are not new trait measurements |
| Member desk/dashboard builders | Later rendering of inference, documentary evidence, timelines, and explanation paths |

Earlier code inspection identified broad networks augmented with issue-selected media inputs and scripts that execute on import. Audit actual input scope rather than inferring coverage from a filename such as "holistic". Do not import these producers simply to reuse a helper.

Proposed module sequence under `fec/research/member_personal_relationships/`:

```text
inventory_sources.py -> extract_events.py -> reconcile_episodes.py
build_opportunities.py -> build_personality_features.py
build_cooperation_baseline.py -> build_signed_features.py
fit_relationships.py -> assess_evidence.py -> evaluate_relationships.py
export_relationships.py
```

The personal layer has its own contract. Friendship probability is not a persuasion probability and hostility is not a negative diffusion weight. Any influence-engine use requires its own validated interpretation.

## 12. Validation that tests the actual objective

### 12.1 Labels and evaluation populations

Assess affinity and antagonism presence/absence separately. Known friends versus known enemies tests sign conditional on a relationship; it does not test whether an unknown pair has a tie. Random unseen pairs are not verified nonfriends or nonenemies. Unknowns remain unlabeled.

Use independent human reviews and adjudication for evaluation labels, retaining disagreement. A direct self-description is evidence to assess, not unquestionable private truth. If weak labels or positive-unlabeled methods are needed, document assumptions and prevalence sensitivity. Do not claim population-calibrated probabilities without a defensible label-observation model.

Evaluate both:

1. **Evidence interpretation:** classify and summarize personal meaning from independently adjudicated source material.
2. **Hidden relationships:** remove all focal-pair personal evidence from prediction inputs and test whether personality, earlier work, and surrounding relationships identify independently documented ties.

Separately test later-time performance and new/low-coverage members. Do not present a current hidden-tie task as a forecast of future friendship formation.

### 12.2 Leakage and dependence

Keep both directions of a pair, source families, underlying episodes, and related bills together across splits. Rebuild training graphs, signed degrees, paths, overlap, baseline residuals, and trait standardization without evaluation information. Exclude the hidden pair from trait evidence and graph inputs, not just the displayed edge list. Future material cannot enter historical features.

Use event/publication/retrieval dates to distinguish retrospective reconstruction from an actual historical information snapshot. Broader contemporary graph observations can be used only when they match the declared inference setting and do not contain hidden evaluation labels.

Account for shared members, intermediaries, sources, and bills when estimating uncertainty. De-duplicated URLs alone do not resolve dependence. Display where a result rests on one episode or one influential intermediary.

### 12.3 Comparisons, stress cases, and metrics

Compare context-only; context plus personality; plus personal behavior; plus distinctive cooperation; plus proximity; plus signed motifs; and the full model. Test personality-proximity interactions separately. Compare weak positive-centered personality priors with zero-centered priors and signed graphs with positive-only graphs.

Stress cases include politically similar nonfriends/rivals, politically distant professional partners, close-network enemies, similar-personality rivals, dissimilar-personality friends, leaders with many superficial links, newcomers, and low-publicity members. Test within political/geographic strata and after downweighting hubs. Perform source-family removal and prior/threshold sensitivity checks.

Report precision-recall, calibration, abstention, usable coverage, evaluated positive/negative counts, and uncertainty by polarity and stratum. Correct population estimates for stratified sampling/class balancing. Report extraction recall from randomly sampled raw material separately from pair-model performance.

A provisional target for the high-confidence inferred category is at least 90% precision for each polarity, with the lower 95% confidence bound above 80%. These are product targets, not demonstrated results. Freeze targets before evaluation, report coverage, and retain lower-confidence exploratory cases without relabeling them as validated. If evaluated cases are insufficient, report the target as unproven rather than inferring success.

## 13. Delivery plan and product presentation

| Milestone | Deliverable | Completion condition |
|---|---|---|
| 1. Inventory and codebook | All-topic source/coverage map, identity rules, event taxonomy, opportunities | Missing inputs and attribution limits explicit; source-backed examples for every code |
| 2. Development pilot | 160 pairs across eight discovery strata; episode and contradiction dossiers | Source/episode independence checked; no machine labels represented as independent gold |
| 3. Feature/model prototype | Personality priors, personal graph, proximity, signed patterns, cooperation baseline, directed models | All feature lineage available; actual training sufficiency assessed; indirect inference works without mandatory quotes |
| 4. Frozen evaluation | Separate fresh labels, hidden-pair and later-time tests, baseline comparisons | Report whether information beyond politics/geography is demonstrated, with uncertainty and coverage |
| 5. Member/network surface | Inferred and corroborated relationship cards, paths, timeline, filters | Every displayed claim traces to its evidence/features and calibration status |

The eight pilot strata are political/geographic peers, distant collaborators, same-party conflict candidates, leadership/deference pairs, personal-story candidates, high-personality-similarity pairs, informative signed-network pairs, and randomly sampled low-coverage pairs. Start with 20 per stratum, de-duplicate through recorded precedence, include both chambers and cross-chamber pairs, and retain both directions. This is a development sample; it is not automatically sufficient to train or validate every feature.

Each relationship card shows the inferred polarity, documentary status, strongest personal signals, the political/opportunity explanation already considered, contributing intermediaries, counterevidence, dates, and uncertainty. Explain why the relationship stands out beyond shared geography and ideology.

Use separate line styles for inferred and corroborated ties, arrows for direction, and clear markers for mixed evidence. Personality-only results appear as compatibility candidates. Keep professional collaboration available as a separate comparison. Sort personal relationships using the personal assessment and adjusted signal; do not repurpose raw cosponsorship weight or political proximity as the friendship ranking.

## 14. Required checks and failure conditions

- Context-only, geography-only, ideology-only, and courtesy-only fixtures cannot create personal relationship claims.
- Personality similarity actively raises the literature-prior model's expected propensity; learned reversals are reported rather than suppressed.
- Indirect combined evidence can produce an inference without a direct friendship quote; inference never changes documentary status automatically.
- Personality dissimilarity, missing mentions, no cosponsorship, and sparse/no graph paths do not automatically become antagonism.
- Direct personal hostility can outweigh compatibility; mixed evidence is not canceled into neutrality.
- Office ownership, quote nesting, historical names, sarcasm, and interviewer questions are handled explicitly.
- Repeated copies/anecdotes and group events cannot manufacture independent episodes, cliques, or intermediaries.
- Focal/held-out edges cannot shorten their own paths or leak through degrees, traits, reciprocal edges, or co-training labels.
- Predicted ties do not reenter the observed seed graph in the initial implementation.
- Graph density, hub effects, low-degree instability, topic filters, and missingness are reported rather than hidden by normalization.
- Time cutoffs apply to roles, ideology versions, sources, bills, graphs, traits, and calibration inputs.
- A sign-classification result is not reported as unknown-tie discovery accuracy; friendship likelihood is not reported as closeness or causal influence.
- Every run is reproducible from versioned sources/features and retains exclusions, counterevidence, and uncertainty.

## 15. Research basis and scope of the evidence

| Source | Finding used | Limit on the inference |
|---|---|---|
| [Selfhout et al., 2010](https://doi.org/10.1111/j.1467-6494.2010.00625.x), Table 2 and discussion | E/A/O similarity, extraversion ego, agreeableness alter, and network structure relate to friendship selection | 205 university freshmen; no congressional calibration or universal Big Five similarity effect |
| [Leskovec et al., 2010](https://doi.org/10.1145/1772690.1772756), Sections 3-5 | Directed signed degrees/triads, status distinctions, and value of negative edges | Sign prediction and missing-link prediction are different tasks; shared enemies do not reliably imply friendship |
| [Tang et al., 2015](https://doi.org/10.1145/2684822.2685295), Sections 3-5 | Repeated negative interactions, nearby negative ties, unreliable provisional labels, soft balance | Online trust/foe networks; precision and base rates matter; overstrong balance worsens performance |
| [Voteview documentation](https://www.voteview.com/articles/data_help_members) | Dated ideology fields and measure definitions | Ideology is an alignment variable, not affection or status |
| [Feld, 1981](https://www.journals.uchicago.edu/doi/10.1086/227352), publisher abstract reviewed | Shared settings organize social interaction | Our choice-versus-opportunity coding is an application, not a directly validated congressional measure |
| [Shalizi and Thomas, 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3328971/) | Selection, influence, and shared causes can be confounded in observational networks | Predictive association does not by itself identify what caused friendship or influence |

The supplied network articles do not demonstrate congressional friendship accuracy. In Leskovec Table 9, adding negative edges raises positive-link existence accuracy to 0.5911 on Epinions, 0.5953 on Slashdot, and 0.7114 on Wikipedia. Tang Table 3 reports NeLP negative-link precision of 0.2861 and 0.2139, with F1 of 0.3242 and 0.2441. These results support testing the methods, not importing their strongest sign-prediction claims as assurances about hidden friendships.

Tang's datasets contain 14,765 and 7,275 users; Leskovec's contain 119,217, 82,144, and 7,118 nodes. Link meanings include trust/distrust, friend/foe reactions to content, and promotion votes. The congressional target must be established through its own personal-relationship labels and the beyond-geography/ideology evaluations above.
