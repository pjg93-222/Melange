**Chamber-aware degrees, development experiment v6**

Authorized by the user's “Proceed” following the chamber/neutrality research.
This plan is recorded before fitting v6. Earlier binary results and the prior
research audit have already been seen. This is development, not preregistration.

Outcome: directed, dated assessments of personal affinity and personal friction
supported by public evidence, each on an ordered 0–4 scale. These are proxies for
relationships, not direct measurements of private feelings. Each dimension can
be unassessable independently. No inference of a zero from an absent sign.

Affinity anchors: 0 affirmative evidence of little personal regard; 1 mild
personal regard; 2 clear personal liking; 3 strong affection; 4 exceptionally
strong personal affection. Friction anchors: 0 affirmative evidence of little
personal aversion; 1 mild personal irritation; 2 clear personal aversion;
3 strong personal hostility; 4 exceptionally intense personal hostility.
Specificity, repetition, trust, intimacy, and confidence are separate fields.
Observable confrontation can support a dated friction assessment, not a claim
of enduring dislike. Courtesy alone leaves private affinity unresolved.

Re-review existing development evidence against these anchors; do not map old
evidence grades automatically. Save a rationale and plausible grade range for
every assigned grade. Grades are single-assistant research annotations; no claim
of independent inter-rater reliability. New discovery must use development
members only. Seek routine contact and neutral evidence, record rejected leads,
and never use search-result snippets as verified relationship labels.

Keep House–House, Senate–Senate, and cross-chamber contexts distinct at the
assessment date. Preserve source venue and purpose separately. When the date is
publication rather than a known event date, disclose it. Records before the
2019 start of our work history have missing work, not zero work. Original
cosponsorship features use bills introduced strictly before the assessed date;
within-chamber work remains separate across a member's chamber transitions.
For current cross-chamber pairs same-bill features are structurally missing.
Include distinct IDs, introduction eligibility, and subsequently withdrawn
original signatures. No 30-day filter and no title-based bill collapse.

Context: contemporaneous party and state, fixed-roster DW-NOMINATE endpoint
values and distance, issue-profile similarity, shared service, and available
coverage. Ideology/geography coefficients may have either sign. Fixed-roster
personality and ideology are retrospective measurements; the evaluation cannot
be called a historical forecast. Do not manufacture historical leadership
positions from current leadership flags. Independently dated leadership
allegiance/challenge remains missing unless sourced.

Candidate cumulative-logit ordinal models, separately for affinity and friction:

- G0: chamber-only graded baseline.
- G1: pooled context and original work with chamber intercepts.
- G2: same predictors with regularized chamber slope deviations.
- G3: G2 plus endpoint E/A levels and E/A/O similarity.
- G4: G3 plus joint-high E and joint-high E × ideological distance.

Fit all candidates; do not select a model on its outer scores and present that
score as independent validation. Primary coefficient penalty is fixed at 1.0
on standardized features; chamber slope deviations get four times that penalty.
Ordered-cutpoint regularization is 0.01 toward the five-grade uniform reference
distribution. It makes missing grade levels numerically possible, not validated.
Repeat G2/G3 at penalties 0.3 and 3.0 as disclosed sensitivity checks.
No sign constraints. No personality-based sincerity multiplier.

Each dimension uses only its explicitly assessed rows. Give each unordered dyad
total weight one across its directions/episodes. Outer development validation
holds out both endpoints and transitively overlapping source families. Fit
imputation, missingness encoding, and scaling only on training data. Report
dyad-weighted ordinal log loss, ranked probability score and absolute error of
the expected grade, plus chamber/grade coverage and convergence diagnostics.
Use the same rows for paired model comparisons. A grade range sensitivity may
score probability mass within the reviewed range, but is not an exact-label
accuracy estimate. No fit is a calibrated private-friendship probability.

Language: provide chamber/venue/purpose/speaker baseline plumbing using resolved,
context-reviewed interactions with an explicit denominator and source exclusion.
Do not use selected lexical hits as the denominator for substantive warmth, or
reuse an outcome episode in its predictor. If representative reviewed exposure
is unavailable, keep these features missing and report that availability gap.
Personality may condition measured excess warmth only when available.

Neutral display requires explicit low ratings on both dimensions with resolved
coverage/context. Strong ratings on both are mixed. Unknown ratings stay unknown.
Predicted class probabilities alone cannot promote an unobserved pair to neutral.
Report dated observed grades and cross-validated model estimates separately; do
not overwrite old outputs or label historical relations as current.

Preserve frozen v5 assignments and hashes. No held-out labels may be inspected
or used; all fitting and source discovery is development-only. Freeze v6 inputs,
annotations, code, and this plan before fitting. Report source omissions, absent
neutral labels, sparse Senate friction, annotation dependence, and any remaining
personality-language leakage. Do not claim new population accuracy if these
coverage requirements are unmet.
