# Full-history member relationships: implemented methodology

This version implements the user's corrections: use observed cosponsorship propensity over available history, count jointly cosponsored bills, hold political/geographic context constant in comparisons, and interpret personal language relative to the speaker. It is an evidence assessment with transparent components, not the previous small fitted classifier.

## 1. Legislative opportunity and propensity

The source contains H.R. and S. bills in Congresses 116–119. The target roster has 532 members with dated service at the September 10, 2026 cutoff. Historical sponsors and cosponsors outside that roster remain in bill records. Only duplicate canonical bill IDs are collapsed, choosing the latest source record. Distinct and reintroduced bills survive even when their titles match.

For member i and bill b:

- E(i,b)=1 if i served in the bill's chamber at any time between introduction and the earlier of Congress end or cutoff, and i was not its sponsor.
- A(i,b)=1 if i joined during dated service, on or after introduction and before the Congress end/cutoff.
- A_active(i,b)=1 if A(i,b)=1 and no subsequent withdrawal is recorded before that boundary.

There is no 30-day gate. A new member can have an opportunity to join an already introduced bill. Same-day cutoff events count; service end is exclusive. A bill's enactment or withdrawal from legislative consideration is not separately modeled as an opportunity-closing date. These are observed service-exposure propensities, not a time-to-joining probability model; recent bills have less observed follow-up. Full and current-Congress counts are reported separately rather than excluding recent bills.

Direct support, opportunities and propensity are:

    D(i,j) = Σ_b A(i,b) 1[sponsor(b)=j]
    N(i,j) = Σ_b E(i,b) 1[sponsor(b)=j]
    P_direct(i,j) = D(i,j) / N(i,j)

This reuses the existing selectivity concept, signatures divided by opportunities. It does not import the production module or its finance-only bill sample, and it does not reuse a precomputed model score. Both directions are retained. No extra shrinkage constant is applied. A zero denominator is unavailable, not zero support.

## 2. Shared cosponsorship

The former prototype omitted this channel. Members must both cosponsor a third member's bill; a sponsor is not treated as their own cosponsor.

    C(i,j) = Σ_b A(i,b) A(j,b)
    T(i,j) = Σ_b E(i,b) A(j,b)
    P_shared(i,j) = C(i,j) / T(i,j)

T asks how often i joined bills j signed when i could have joined them. It excludes bills sponsored by either member. C is symmetric; P_shared can be directional. Counts of joint original cosponsorship, Congresses with shared bills, and distinct policy areas are separate evidence of history and breadth.

To reduce the contribution of a bill with a very large coalition, let k(b) be its full cosponsor count, including historical members outside the target roster, and w(b)=1/max(1,k(b)−1). The comparison feature is weighted Jaccard overlap:

    J(i,j) = Σ_b w(b) A(i,b) A(j,b)
             / Σ_b w(b) [A(i,b) E(j,b) + E(i,b) A(j,b) − A(i,b) A(j,b)]

Raw counts and unweighted Jaccard are also retained. Initial joins and later withdrawals stay separate. 'Shared active' means neither signature was subsequently withdrawn; it does not mean both members currently serve. Historical shared signatures can occur at different times within the same Congress. Reintroduced bills count as persistence, not independent experimental observations.

## 3. Hold context constant

For a fixed actor i, compare target j with other targets with the same:

- same-party versus different-party relationship;
- same-state versus different-state relationship;
- same-chamber versus different-chamber relationship;
- DW-NOMINATE first-dimension distance bin, width 0.2;
- similarity of issue-area selectivity profiles, bin width 0.25.

Issue selectivity is signatures divided by eligible bills within each policy area over available history. Profile similarity is the cosine of those vectors. Comparison percentiles are the share of peers below the focal value plus half of ties. At least five finite peer values are required. Focal j never enters its own comparison pool. There is no subtraction for sharing geography or ideology.

Service/activity enter the opportunity denominators and persistence fields. Leadership status is reported for interpretation of deference and public praise, rather than fragmenting comparison groups further. Geography is state overlap, not district-mile distance. Political context and leadership use the frozen current roster, not reconstructed annual histories. Party membership is used as recorded; shared caucus affiliation of independents is not separately modeled. These are coarse descriptive controls, not proof that every political, geographic, or institutional incentive has been removed.

## 4. Proximity in the full cooperation network

Use J as the weighted observed work network. The network component is cosine similarity between i's and j's connection profiles, excluding both focal endpoints:

    Q(i,j) = Σ_{k≠i,j} J(i,k) J(j,k)
             / sqrt[Σ_{k≠i,j} J(i,k)^2 × Σ_{k≠i,j} J(j,k)^2]

Compare Q within the same context groups. An i–j edge alone creates no common neighbor. This uses the full work network, not only the handful of documented friendships. It is correlated with shared cosponsorship and is not counted as an independent statistical experiment. No enemy-of-an-enemy rule produces a friendship or dislike.

## 5. Personality and personal treatment

The local public-text Big Five estimates are retained. For each observed trait t:

    S_t(i,j) = exp(−|z(i,t)−z(j,t)|)
    S_EAO(i,j) = mean of available S_E, S_A, S_O

All five similarities are displayed. E/A/O supplies the primary compatibility indicator because that is the similarity pattern supported in the supplied Selfhout study. Compatibility supplies positive support when at least two of E/A/O are observed and S_EAO is at or above the median across eligible roster pairs. Missing or dissimilar traits do not supply negative relationship evidence. The formula and median rule are design choices, not coefficients estimated in the paper.

Speech retrieval uses full names or a unique surname with a congressional title. A nearby positive/hostile cue is assigned to the nearest uniquely resolved target within 160 normalized characters. Common words such as 'young', 'strong', 'case', and 'justice' alone cannot identify a member. Exact same-day duplicate attributed turns are removed. Detected appended speaker labels in interview rows are trimmed. Full source context is still required before a retrieved passage becomes a relationship observation.

The speech ledger reports, separately by source, a member's warm/hostile cue rate when mentioning j versus that member's rate when mentioning everybody else. These are lexical retrieval statistics, not automatic judgments of intent. Negation, quotations, irony and unresolved attribution are handled in source review. The current multiplier uses overall attributed-turn usage; source-specific and target-specific rates are shown alongside it for interpretation.

To implement the user's personality hypothesis, let q(i) be the share of the speaker's deduplicated turns with a warmth cue and F_E,F_A the roster percentiles of their trait estimates:

    reserved(i) = 1 − mean of available [F_E(i), F_A(i)]
    M(i) = 1 + [1 − q(i)] reserved(i)
    reviewed_warmth_strength(i,j) = distinct reviewed positive episodes × M(i)

M ranges from 1 to 2. Rare warmth from a lower-E/A speaker receives more weight. Missing usage or both traits gives M=1. This is explicitly a proposed distinctiveness weight; it does not establish sincerity. Public-text trait scores and statements may share source material, so their agreement is not independent validation. The supplied research does not validate this multiplier.

## 6. Decisions and testing

Documented personal friendship requires a context-reviewed personal statement/account. Contextual warmth can support **inferred personal affinity** when at least two positive supports exist: selective sustained cooperation; above-median personality compatibility; network proximity at/above the 75th comparison percentile; repeated reviewed positive episodes; or M≥1.5. Directional evidence is never copied to the reverse edge. Episode dates remain visible.

The legislative review flag requires shared Jaccard at/above the 90th comparison percentile, either direct propensity at/above the 75th or network proximity at/above the 90th, at least five shared bills, and shared bills in at least two Congresses. Those cutoffs are transparent review settings, not validated friendship boundaries. A work-only flag remains a cooperation-supported candidate. The report also shows a reciprocal work shortlist; it is not automatically labeled friendship.

Reviewed person-directed hostility is recorded separately. Selective personal refusal or a severe targeted personal action can support an event-dated dislike inference. Neither personality mismatch, low cooperation, ideology, nor geographical distance creates dislike. High collaboration does not erase a hostile episode. A historical episode alone is not asserted to describe the present relationship.

Testing uses meaningful regression cases, full-panel invariants, independent bill-list recounts and the original documented pairs with their personal statements hidden from work/network calculation. No personal labels enter those calculations or the comparison groups. The result is a retrospective check against known ties, not a new calibrated accuracy claim. Sensitivity at 85th/90th/95th shared/network percentiles is reported. Additional source-reviewed examples discovered in this run are disclosed separately and not folded into the original benchmark.

The executable code is under `fec/research/member_personal_relationships`. The new outputs are under `outputs/member_personal_relationships/20260910_full_history`. Production relationship files and the two earlier prototype outputs are not overwritten.
