# Staffer closeness: workplace capacity and member context

Date: 2026-09-10. Status: authorized for implementation after mathematical review. The coefficients remain exploratory and uncalibrated. See the implementation receipt for release and verification status.

## What the pre-change code explains

The historical co-tenure formula in `fec/staffer_network/ranking_math.py` is

\[
w_{ij}=\kappa_{\max}\min(S_i,S_j)
(1-e^{-D_{ij}/365.2425})A_{ij}.
\]

Here A is a duration-weighted attenuation, using 0.05 for an exact shared-role title. There is no workplace-size denominator. The builder uses the strongest workplace kappa across the pair, rather than applying each workplace's kappa only to its own time contribution.

The member lists in `fec/surfaces/build_staffer_network_section.py` sort by global PageRank first and member connection strength second. The outreach comparator also uses origin/target distances only to break PageRank ties. Separately, `fec/surfaces/staffer_overlap_routes.py` has an exact-workplace model with proximity 1 and logarithmic duration, and a feature model with large shared-employment weights. Fixing the sealed graph alone therefore would not fix every recommendation surface. The precise screen producing the user's examples has not been identified in this draft.

The September 8 audit already found that simply dividing weights by container size did not fix the old global PageRank rankings. That finding argues against a denominator-only patch, not against modeling concurrent workplace size. Its historical results must not be presented as tests of this proposal.

Three changes belong together: model finite workplace exposure, distinguish operational assignments from payroll affiliations, and rank connections relative to the requested member/person.

## 1. Define the workplace before projecting people into a graph

Let i,j identify people; c identify an actual workplace or documented team; t identify a day.

- A payroll charge to a member office is not automatically a working assignment to that member.
- A committee employee is not automatically a personal staff contact for every committee member.
- A documented committee team, side, or subcommittee can supply a smaller workplace. A parent committee and its nested team cannot each supply a full duplicate day.
- Administrative and intern-compensation pools remain excluded as workplaces. Real people and source records remain available.
- Headcount N_c(t) means distinct concurrently employed people, including the pair. It is not the number ever recorded in that workplace, number of payroll rows, or today's count applied to historical employment.
- Missing headcount is unknown, not N=2. Use documented roster coverage and a disclosed conservative estimate or range. If assignments are too incomplete, withhold a precise closeness estimate.

Real team membership and shared-role dates may require better source data. Mathematics cannot infer them from a payroll label alone.

## 2. Give each person a finite daily exposure budget

Let f_ic(t) be the fraction of a person's working day assigned to workplace c, with

\[
0\le f_{ic}(t)\le1,\qquad \sum_c f_{ic}(t)\le1.
\]

Use documented allocation when available. In its absence, equal division across K simultaneous distinct assignments, f=1/K, is an explicit sensitivity scenario, not observed FTE. Deduplicate payment lines and nested workplaces before counting K. Compensation dollars alone do not establish time allocation.

Let q_ic(t) in [0,1] discount weak evidence of actual workplace exposure, and define

\[
a_{ic}(t)=f_{ic}(t)q_{ic}(t).
\]

For dedicated, documented work use q=1. For shared-payroll-only support use chamber-specific q_H and q_S, with 0<q_H<=q_S<1. A reasonable experimental comparison is q_H=0.02 versus q_S=0.05, alongside equal-chamber controls. These values are proposed dials, not measured contact rates. Actual dedicated committee work can receive q=1 in its real committee team even if the person's payment entries elsewhere are shared. Do not penalize their entire career because one cell says SHARED EMPLOYEE.

Apply q after allocating f. Renormalizing a back to sum to one would undo the shared-role discount.

## 3. Accumulate size-adjusted exposure, then apply diminishing returns

Let kappa_ijc(t) in [0,1] represent the specificity of the documented common workplace. Preserve explicit uncertainty about committee side or team; do not treat a broad committee label as proof of a small team. Use each workplace's own kappa on its own days.

Define daily pair exposure as

\[
z_{ij}(t)=\sum_{c:\ i,j\text{ concurrently in }c}
\frac{\kappa_{ijc}(t)a_{ic}(t)a_{jc}(t)}
{\max(1,N_c(t)-1)^{\gamma}}.
\]

Start with gamma=1. It divides a person's workplace exposure across the available coworkers. A square-root denominator (gamma=0.5) still lets aggregate exposure grow approximately as sqrt(N), leaving a large-workplace advantage. Gamma>1 can be tested if even constant total exposure overstates large workplaces.

Review correction: the minimum is an upper bound on overlapping schedules, not a conservative estimate. The implemented product is an explicit independent-mixing model for co-presence, not measured shared hours. Actual observed schedules should replace this assumption when available. With two shared-only endpoints, both allocation factors apply.

With guaranteed dated overlap only,

\[
E_{ij}=\sum_t z_{ij}(t),\qquad
W_{ij}=\min(S_i,S_j)(1-e^{-E_{ij}/\tau}).
\]

E has units of effective peer-exposure days. S retains the existing identity-strength convention and is not a probability. No new time-since-service decay is included in this first comparison.

For calibration continuity, tau=365.2425/19 makes one year in a 20-person dedicated workplace have the previous one-year duration factor, with kappa=S=1. This is a reference scale, not a claim that 20 employees is the correct universal office size.

For gamma>=1, complete consistent headcounts and nonduplicated allocations,

\[
\sum_{j\ne i}z_{ij}(t)\le\sum_c a_{ic}(t)\le1.
\]

Proof: within a workplace, each of its N-1 other people contributes at most a_ic/(N-1)^gamma. Summing over workplaces gives the bound. Therefore listing a person across more offices cannot create extra daily exposure. This is a bound on exposure, not a lifetime cap on legitimate relationships. Longer careers can still accumulate connections. Saturation also gives sum_j W_ij <= sum_j E_ij/tau.

Attribute final edge mass to workplaces using their effective exposure: E_ijc=sum_t z_ijc(t), W_ijc=W_ij E_ijc/E_ij. These contributions sum to W_ij and do not credit a three-day high-specificity posting with another workplace's entire tenure.

### Equal-duration illustration

One year; one assignment; identity strength and kappa both 1; gamma=1; tau=365.2425/19:

| Evidence | Daily pair exposure | W |
|---|---:|---:|
| Dedicated coworkers, N=20 | 1/19 | 0.6321 |
| Dedicated coworkers, N=100 | 1/99 | 0.1746 |
| Shared-payroll-only House support, N=100, q=0.02 | 0.02/99 | 0.0038 |

These are model outputs, not empirical probabilities. If the person is a documented full-time committee worker, their real committee-team ties use the dedicated rule; only weak shared-payroll affiliations use the shared rule.

## 4. Do not let PageRank erase the repair

For ordinary weighted PageRank,

\[
P_{ij}=W_{ij}/\sum_kW_{ik}.
\]

Multiplying all outgoing weights in a row by the same positive constant leaves that row of P unchanged. Uniformly scaling an isolated component leaves its transition probabilities unchanged. Shared-role damping is not globally inert, because mixed rows change, but this cancellation explains why merely weakening an entire workplace need not repair its PageRank ranking.

Global staff PageRank and eigenvector centrality remain descriptive diagnostics. They should not be the primary key for a question about a particular target. Do not introduce another normalized walk as the sole closeness score and assume the absolute-exposure problem has disappeared.

## 5. Construct target-specific staff access

Create an explicit staff-to-member anchor H_jm in [0,1], backed by employment in that member's actual personal office or another documented direct working relationship. Committee membership by itself never creates H_jm for every committee member.

A provisional employment anchor can use the same exposure logic with the member as the recipient of a limited office-contact budget:

\[
U_{jm}=\sum_t\sum_{c\in\operatorname{personalOffice}(m)}
\frac{\kappa^{M}_{jmc}(t)a_{jc}(t)}{\max(1,N_c(t))^{\gamma}},
\quad H_{jm}=S_j(1-e^{-U_{jm}/\tau_M}).
\]

Here N excludes the member and counts staff. tau_M=365.2425/20 is an illustrative reference for one year in a 20-person personal office. A documented direct reporting relationship can have a separately specified evidence rule; job-title guesses must not silently set it. Multiple records for one office are deduplicated. q, kappa and source uncertainty remain explicit.

For a route P of staff edges ending at j, define

\[
Q(P,m)=H_{jm}\eta^{|P|}\prod_{(u,v)\in P}W_{uv},\qquad 0<\eta<1.
\]

Use eta=0.8 as an initial hop-penalty scenario. A zero-edge route from i to its own member anchor has score H_im. Products are model strengths, not independent-event probabilities.

For a member-only recommendation, L(i,m) is the maximum Q over simple paths starting at i. When outreach origin o is supplied, L(o,i,m) is the maximum over complete simple paths starting at o, passing through candidate i, and ending at a valid member anchor. An absent route gives no supported route score; incomplete search must remain unknown. A finite hop limit must be declared.

Require the full path to avoid loops: two independently shortest legs can retrace people and exaggerate the usefulness of an intermediary. Use the best supported path rather than summing thousands of correlated paths through one committee. Independent alternate routes can be reported separately.

This addresses useful introduction paths. It does not establish friendship or willingness to introduce someone.

## 6. Bring in members' overall network and eigenvector centrality

Eigenvector centrality is a node's structural importance through its neighbors. Equal centralities do not establish that two members are close. Its definition and connectedness assumptions are documented in the [NetworkX reference](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.eigenvector_centrality.html).

Use an independently constructed member graph A, not this staff-employment projection fed back into itself. Record the exact overall-network generation and whether committee affiliation is already one of its layers. Remove or separately test any duplicated staff/committee signal. For an undirected nonnegative member graph,

\[
Ac=\lambda_{\max}c.
\]

Scale c to [0,1] within a valid comparable population. Independently normalized House, Senate or component eigenvectors are not directly comparable. Missing or incomparable centrality receives a neutral modifier and an explicit missing flag; do not pretend it is an observed zero.

A concrete separate measure of member-pair proximity uses S=D^(-1/2) A D^(-1/2), with zero rows for isolates, and

\[
K_{nm}=0.7S_{nm}+0.2(S^2)_{nm}+0.1(S^3)_{nm}\quad(n\ne m),
\qquad K_{mm}=1.
\]

The coefficients are exploratory. For this undirected nonnegative construction, entries are in [0,1]. Disconnected members have zero pair proximity. Direct ties receive most weight; broad, weak paths do not turn equal prestige into closeness. Preserve direction explicitly if the selected overall graph is directed rather than silently applying this symmetric formula.

For each candidate, normalize their observed direct member anchors only for this contextual modifier:

\[
b_{in}=H_{in}/\sum_rH_{ir},\qquad
I(i,m)=\sum_n b_{in}K_{nm}\tilde c_n.
\]

Set I=0 if no comparable member context exists, with coverage flags. Normalizing b prevents accumulating unlimited prestige merely by listing many bosses. It does not alter H or the staff-edge exposure budget.

The proposed recommendation score is

\[
\boxed{R(o,i,m)=L(o,i,m)[1+\beta I(i,m)]},\qquad \beta=0.15\text{ initially}.
\]

Use L(i,m) when no origin is supplied. Thus member context can add at most 15% and cannot create a supported route from zero. This bounded size is a proposal to validate, not a fitted coefficient. For candidates attached to the same member with identical context, centrality may add no discrimination; their actual route strength still decides. Show L and I separately so the user can see what moved the ranking.

## 7. Checks before any implementation decision

1. Holding tenure, assignment and specificity fixed, a larger concurrent workplace weakens each inferred coworker tie.
2. Splitting payment records or duplicating a parent/team label cannot increase exposure. Fifty shared affiliations cannot create fifty full days of capacity.
3. A verified small committee team retains meaningful connections. Broad committee affiliation does not become personal employment with every committee member.
4. The recommendation changes when origin or target changes. Global staff PageRank cannot override target relevance as the primary sort key.
5. Equal member eigenvectors in disconnected parts of the overall graph do not imply closeness. Zero staff route support stays zero after the centrality modifier.
6. Compare the user's actual good/bad examples, separately for House and Senate, with global and target-specific results. Preserve dedicated committee staff as a control group.
7. Run ablations: size only; exposure allocation only; shared-role discount only; target-first ranking; then member context. Sweep gamma, q_H/q_S, tau, eta and beta. Compare top-k relevance and stability, not a target percentage of shared employees in the top 100.
8. Label uncertain team size, dates, assignments and identity. Guarantee-based exposure should not quietly substitute possible-only overlap. Broader plausible intervals may be shown as a sensitivity scenario, not presumed rigorous upper/lower confidence bounds when headcount also changes.

The primary hypothesis is that a large common workplace is currently producing too much apparent access, and global connectedness is being used where target-specific connection strength is needed. The proposal addresses both; its numerical parameters and ranking quality remain unvalidated.


## Implementation specialization and source boundaries

The active Staffer route already uses authenticated dated directory employment; the payroll graph is a separate historical diagnostic. The new work route retains that evidence gate. Payroll can enlarge the concurrent headcount census but cannot create a directory-work edge. Unknown roster completeness is disclosed as a potential headcount underestimate. Directory-based identities do not inherit payroll identity penalties.

Static member lists are a direct-office-contact comparison: L(i,m)=H_im. They now rank H_im times the bounded member context, with H_im as the tie-break, rather than global staff PageRank. Direct office employment can support an anchor even when the old sampled/social graph has no coworker edge. Bridge lists use these size-adjusted anchors beyond the strongest eligible member office. The sealed historical co-tenure graph and its centrality diagnostics remain versioned separately.

For an interactive office destination, the candidate i is the named final staff contact: L(o,i,m) is the best simple work route from o to i times its direct office anchor H_im. The centrality modifier applies exactly once at that endpoint, inside the search. All candidate endpoints are compared, not just the first few preselected routes. For a person destination, no member-office terminal anchor is asserted.

Routes minimize negative logarithms of the product. The office terminal factor is divided by 1.15, a common factor that preserves ranking and keeps all Dijkstra costs nonnegative. Yen's algorithm includes a virtual terminal sink to enumerate loopless alternatives, including different office contacts. The sink never appears as a person or relationship in the result. This specialization avoids the draft's much harder arbitrary-required-intermediary optimization and does not concatenate potentially retracing shortest legs.

Member centrality is computed within connected components and used only when the candidate member and target member belong to the same component. This permits valid target-relative comparisons without comparing separately scaled components. The current held all-bills AUG network has 533 members in one component, with source date 2026-08-18.
