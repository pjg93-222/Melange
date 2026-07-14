# Official-persona N target/tone audit — 2026-07-13

## Bottom line

The requested subject/target/tone separation works. Sentence-level correlation between subject
severity and member-owned negative tone fell from .074 to .004 after leave-one-member-out context
adjustment. Severe subject matter is therefore no longer the principal reason someone scores high.
Third-party quotations are blocked from member-owned cues, and the exact example “the darkness will
consume you” is detected as disproportionate dramatic language when presented as the member's own.

The research does **not** support a holistic Neuroticism claim. At the user's direction, a narrower
score was built instead: **Official-facing negative emotional reactivity (N-expression)**. It is an
equal-weight, text-only combination of context-adjusted negative tone, signed disproportionate
intensity, and episode-to-episode emotional volatility. Party rhetoric, gender, current formal
leadership, interview volume, subject severity, and chamber are held-out controls. There is no paid
API, audio, visibility, title bonus, old-N input, or fitted personality weighting.

The score is technically promising but remains candidate-only. It passed 7/8 frozen engineering
bars: corrected split-half reliability .645 with 5/5 splits, 210-member coverage, coherent aspects,
and maximum observed score-confound correlation .026. Chronological earlier/later stability was
.266, missing the frozen .30 bar. The honest outcome is **NOT READY**, not a threshold-adjusted pass.

## Tina Smith

Tina Smith's old affective-content N was +2.093. The new subject-, party-, role-, and volume-adjusted
candidate is also high: +2.676 within the Senate, fourth of 210 covered members. The three adjusted
aspects point in the same direction:

- residual negative tone: +3.240;
- disproportionate intensity: +1.310;
- emotional volatility: +2.038.

This does not show private anxiety or holistic Neuroticism. In v1, none of her 430 classified
sentences were assigned to a personal-owned emotion target; 86.3% were external-target language.
Her high result is therefore best read as an official rhetorical style: unusually strong negative
presentation and variation around policies, political actors, and events, even after the subject
and nuisance controls. The old high N was not simply a subject-matter artifact, but its label was
too broad. The narrower public-expression interpretation checks out better than “Tina Smith is
personally neurotic.”

## Mike Johnson

Mike Johnson is approximately average on the new text-only candidate: +0.046, 98th of 210 covered
members. His adjusted aspects are +0.244 residual tone, -0.032 disproportionate intensity, and
-0.100 volatility. That does not support describing him as unusually dramatic. Nothing in this
text audit supports the earlier rapid-speech claim either; the audio guards remain fail-closed and
no audio descriptor is used.

His coverage is large—12,783 sentences across 1,620 merged episodes—but volume and current Speaker
status are controls, not reasons to infer Extraversion or N-expression.

## Product status and decision boundary

Artifacts:

- `official_persona_n_target_tone_v1.json.candidate` — facet-level diagnostic, no composite;
- `official_persona_n_expression_v2.json.candidate` — provisional narrow score;
- `fec/official_persona_n_target_tone_candidate.py` — zero-API target/tone engine;
- `fec/official_persona_n_expression_v2_candidate.py` — zero-API operational score and QA.

Both candidate artifacts are consumed by nothing. The live N value, profiles, dashboard, narratives,
and ranks were not changed. The hashes of `ranks_python.json`, `big5_blue_validated.json`, and
`member_narratives.json` matched before and after both builds.

The candidate can be packaged for display only after explicit user approval. If approved despite
the temporal miss, the accurate UI label is “Neuroticism — public expression” or “Negative emotional
reactivity,” with the full construct and confidence details inside the psychology sub-dropdown.
It should not be silently presented as holistic Big Five N. The research-clean alternative is to
wait for a genuinely later interview holdout and test the unchanged v2 scorer prospectively.
