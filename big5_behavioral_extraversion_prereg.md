# Behavioral Extraversion v1 — preregistration

STATUS: LOCKED

Date locked: 2026-07-13

## User directive and claim boundary

The user directed that Extraversion be tackled first and measured from warmth of speech,
excitement, activity, and gregariousness. High visibility may corroborate the result, but must
not be its principal component. This test therefore removes visibility from construction
entirely. It also adds conversational assertiveness because it is an established Extraversion
facet and appears in the user's supplied construct description and sample-item framing.

A PASS can support only this claim: **a zero-API behavioral Extraversion candidate, estimated
from member-attributed interview behavior, is repeatable and converges with the specified
historical congressional speech criterion.** It cannot establish a member's private need for
stimulation, subjective source of energy, or a clinical/diagnostic personality fact. The RKH
criterion is a historical speech-derived estimate, not self-report ground truth, so it is a
convergent criterion only.

## Frozen corpus fingerprint

The test is available only while every hash and count below matches. The first JSON block is
machine-read by the harness.

```json
{
  "files": {
    "behavior_panel.json": "491761ea130f8458ae0d09d15be20619b31011ab14e56e6a05bfbdf3d703a4cb",
    "behavioral_dispositions.json": "57ca1e2b1731cbeed4411645c2b527a8db0136362c2d3d4654dda8faaa852e03",
    "big5_blue_validated.json": "876bc2ecf8672477d586f3db34472cdb2cf61ee0573e30c4b909448cd0970a8f",
    "congestion.json": "ddc9d746600dbdfc60b76c54537662e19c758cbfb9d7a478a71b7bf90cd727a6",
    "fec/legislators.csv": "c5a6cbdbaae0bb19faa89852c29922809ececc70b97c149b4709588087e5e391",
    "fec/liwc/rkh/congressbios.tab": "451db7f5551e3a0805a07cf0876e471c82f3bbf4ecb7e9f60982879177683004",
    "social_media.db": "21f2e9f6c13d44f5bed27cabfc9414b445ba8b0f047e88b101ac5267112ab6ec",
    "votes/HS117_members.csv": "25b71db893051296bfb2457aa9d1e9193568459a68be186d9c3e34d39d1ddb8f",
    "votes/HS118_members.csv": "7ea0a0f1216c4363de4f1398c199b11adf707dcd41680d34ac0c291dd4a97b6d",
    "votes/HS119_members.csv": "dbbefbdccf3b4c06fc0c8881a0b4809a392cd309ecc8cdbd00feedf9af6c80e0"
  },
  "interview_packages": 51621,
  "interview_rows": 150668
}
```

Only rows whose source is `INTERVIEW` are used. Multi-segment packages from one episode are
merged before appearance counts and before assigning split halves. An appearance is substantial
at four member turns or 200 member words. Full-score eligibility requires 30 qualifying turns,
five substantial appearances, and at least 12 turns in a program cell. A program contributes
only with at least eight eligible members. Half-score thresholds are 15 turns, two substantial
appearances, and six turns per cell.

## Frozen construct and scoring

The implementation is `fec/b5_behavioral_extraversion_candidate.py` in the lock commit. Exact
regular expressions, transformations, missing-data rules, seeds, and thresholds in that committed
file are part of this preregistration.

Five facets are computed within interview program, standardized within program, aggregated by
qualifying turns, residualized separately, and then standardized within chamber:

1. **Warmth** — outward positive-social markers per 1,000 words: thanks, appreciation, gratitude,
   welcome, pleasure/honor, friendship, affection/pride, congratulations, and respect.
2. **Excitement / positive energy** — excitement, enthusiasm, eagerness, energy, delight,
   anticipation, and high-positive-arousal markers per 1,000 words. Exclamation marks are included
   only after within-program standardization, limiting transcript-vendor punctuation effects.
3. **Gregariousness** — equal mean of substantial joint-appearance share, unique-partner share,
   and normalized partner entropy. Raw appearance or partner counts do not enter the facet.
4. **Activity** — equal mean of log turns and log words per merged appearance.
5. **Conversational assertiveness** — equal mean of member-turn-length Gini and explicit
   floor-defense markers. This is conversational floor holding, not ideological extremity.

For every facet, the removed controls are party, gender, formal committee leadership, log
qualifying turns, log substantial appearances, and log program breadth. Chamber is handled by
separate standardization. Interview volume, number of appearances, leadership, and program breadth
therefore cannot directly raise E. High public visibility is absent from all facets and both aspects.

The fixed aspects and score are:

- Enthusiasm = equal mean(Warmth, Excitement, Gregariousness)
- Assertive-energy = equal mean(Conversational assertiveness, Activity)
- E = equal mean(Enthusiasm, Assertive-energy), standardized within chamber

No Blue/Pink E value, audio feature, social-media post volume, appearance count, office, title,
leadership role, or visibility measure is an E input. The process makes no network call and incurs
no API or model cost.

## Frozen validation criteria

The main reliability splits are episode-level deterministic hashes with salts E-A through E-E.
Every segment from an episode stays in the same half. Spearman-Brown correction is applied to the
Pearson half correlation. All bars are conjunctive:

- Coverage: at least 200 E scores and at least 80 joined RKH criterion cases.
- Overall repeatability: median corrected split-half reliability at least .60, with at least four
  of five splits at least .50.
- Aspect repeatability: median corrected reliability at least .50 for both Enthusiasm and
  Assertive-energy.
- Facet repeatability: at least four of five facets have median corrected reliability at least .35.
- Historical convergence: partial r with RKH `extra_avg` at least .20, one-sided 5,000-permutation
  p below .05, controlling the same six variables.
- Visibility corroboration: partial r with current visibility at least .10, one-sided
  5,000-permutation p below .05, controlling the same six variables. Visibility never enters E.
- Aspect coherence: Enthusiasm–Assertive-energy r between .10 and .65 inclusive.
- Discriminant ceiling: maximum absolute controlled correlation with current O/C/A/N no more than .45.
- Confound ceiling: maximum absolute zero-order correlation with each removed control no more than .10.
- Facet distinctness: maximum absolute facet-pair correlation no more than .75.

The historical criterion comes from Ramey, Klingler, and Hollibaugh's congressional speech
personality estimates and covers an earlier congressional era. It is deliberately not called a
gold label. Current visibility is a secondary corroborator only after volume, appearance,
leadership, party, gender, and program-breadth control.

## Power and pre-look feasibility

A coverage-only probe, performed without calculating correlations or inspecting member scores,
found roughly 229 likely fully eligible current members and roughly 91 possible RKH overlaps before
the final episode-merging correction. The locked coverage bars govern the actual result.

At n=91, a fixed synthetic simulation of the locked one-sided r>=.20 and p<.05 criterion gave
estimated power of .498, .693, .845, .941, and .980 for true correlations .20, .25, .30, .35,
and .40 respectively. Thus the floor is not guaranteed to pass and the criterion has useful power
for effects around .30 or larger. This limitation must accompany any MISS.

## Adversarial re-derivation

Only if all main bars pass, the harness performs a second, already-frozen re-derivation:

- five fresh episode-level salts E-F through E-J must again meet the overall and both aspect
  reliability bars; and
- leave-one-program-family-out scores for CNN, Meet the Press, PBS, NPR, and Other must have minimum
  Spearman rho at least .65 and median rho at least .80 against the full score.

Failure here is `FRAGILE = MISS`, not a qualified pass.

## Outcome rule and activation boundary

The one real-data look is consumed by `python fec/b5_behavioral_extraversion_candidate.py --look`.
Its full output is appended below without editing the bars. PASS requires every main bar and the
adversarial re-derivation. MISS or FRAGILE ends v1; no threshold, feature, control, or label may be
tuned after seeing the result.

On PASS only, the harness writes `behavioral_extraversion_v1.json.candidate`. The file remains
candidate-only and consumed by nothing until explicit user review. On MISS, no E candidate is
written and profile-generation code must continue to report behavioral E as unavailable rather
than fall back to visibility.

## RESULT-E-BEHAVIORAL

Look consumed: 2026-07-13

Outcome: **MISS**. No candidate artifact was written and no Extraversion score was activated.
The preregistered adversarial re-derivation was correctly not run because the main bars did not
all pass.

```text
prereg: LOCKED | look: AVAILABLE | fingerprints: MATCH
  OK   residualization_removes_confounds
  OK   synthetic_signal_recovered
  OK   warmth_lexicon_operates
  OK   excitement_lexicon_operates
  OK   stable_split_is_deterministic
SIMULATE BATTERY: ALL GREEN
coverage: E=241 | RKH joined=93
reliability score              median SB=+0.567 pass>=.50 5/5 median-n=220
reliability enthusiasm         median SB=+0.531 pass>=.50 5/5 median-n=220
reliability assertive_energy   median SB=+0.608 pass>=.50 5/5 median-n=220
reliability warmth             median SB=+0.636 pass>=.50 5/5 median-n=232
reliability excitement         median SB=+0.453 pass>=.50 2/5 median-n=232
reliability gregariousness     median SB=+0.444 pass>=.50 1/5 median-n=220
reliability assertiveness      median SB=+0.648 pass>=.50 4/5 median-n=232
reliability activity           median SB=+0.734 pass>=.50 5/5 median-n=232
RKH E partial: r=-0.070 p=0.7534 n=93
visibility partial: r=-0.016 p=0.6163 n=241
aspect coherence: r=-0.071 n=241
discriminant: O=-0.012 C=+0.149 A=+0.162 N=-0.046
confounds: party=+0.007 gender=-0.034 leader=+0.034 log_turns=+0.037 log_substantial=+0.032 program_breadth=+0.063
BAR coverage                     PASS
BAR overall_reliability          MISS
BAR aspect_reliability           PASS
BAR facet_reliability            PASS
BAR rkh_convergence              MISS
BAR visibility_corroboration     MISS
BAR aspect_coherence             MISS
BAR discriminant                 PASS
BAR confound_control             PASS
BAR facet_distinctness           PASS
FINAL VERDICT: MISS
```

Interpretation fixed at the look: warmth, conversational assertiveness, and activity were the
most repeatable individual facets. Excitement and gregariousness were weaker. More importantly,
Enthusiasm and Assertive-energy did not show the positive coherence required of one Extraversion
construct, and the composite did not converge with the locked historical criterion. The near-zero
controlled visibility correlation confirms that spotlight exposure was successfully removed; it
does not rescue construct validity.

## Post-result literature audit (not part of the locked test)

Added after the result at the user's direction. This review informs interpretation and any future
v2; it does not alter the preregistered bars or reclassify the MISS.

### Ramey, Klingler, and Hollibaugh (2016)

`Measuring Elite Personality Using Speech` is the provenance of the RKH criterion used above. It
applies the Mairesse et al. observer-trained SMOreg personality recognizer to Congressional Record
floor speeches from 1996-2014. The paper is explicit that its estimates need not be sincere or
intrinsic personality; they may reflect revealed and strategic public presentation (PDF p. 5). It
also says more stringent validation was not then possible (p. 6), uses indirect face-validity tests,
and warns that its corpus-normalized scores are only relatively comparable within the Congressional
Record rather than to ordinary inventories or other corpora (p. 4).

Most importantly for this test, RKH's displayed Extraversion feature is **total words** (Figure 4,
p. 10), and the authors interpret greater speaking volume as Extraversion face validity (p. 11),
citing prior correlations above .60 between Extraversion and total word count. Floor access,
leadership, agenda role, and public visibility can all affect total words. RKH is therefore not an
independent construct-validity target for an E measure deliberately purged of exposure and volume.
The locked RKH MISS remains a MISS, but it cannot be interpreted as proof that the candidate failed
to recover intrinsic Extraversion.

### Yang, Lau, and Abbasi (2023)

`Getting Personal: A Deep Learning Artifact for Text-Based Measurement of Personality` validates
DeepPerson against survey-labeled PANDORA/Reddit, myPersonality/Facebook, and Essays data, with
user-disjoint train/validation/test splits repeated ten times (PDF pp. 14-16). That is a materially
stronger target than a visibility or word-count proxy. Its learned psycholinguistic, syntactic,
semantic, and person-level representations also outperform hand-feature baselines. For
Extraversion, reported document-level F1 is .649 on PANDORA and .674 on myPersonality; overall AUC
is .750 and .707 respectively (Table 4/5, p. 17). These are useful but not accurate enough to treat an
individual politician score as a fact without domain-specific validation.

The model was trained on social posts and student essays, not congressional interviews, and its
method depends on substantial labeled and unlabeled training corpora. The paper supports replacing
the v1 regex composite with a learned, self-report-anchored representation; it does not validate
transferring DeepPerson scores directly to members of Congress. Reproduction could avoid paid API
spending if code, labels, weights, and sufficient local compute are available, but that feasibility
must be established before a v2 is registered.

### Birkenmaier and Lechner (2025)

`Measuring Politicians' Public Personality Traits Using Computational Text Analysis` supplies the
most appropriate claim boundary. Its lens model states that researchers do not directly observe a
politician's intrinsic personality: public cues jointly reflect intrinsic disposition and strategic
self-presentation (PDF pp. 3-4). It specifically critiques the RKH approach for lacking validation
against human-annotated political text and argues for domain-specific constructs and codebooks
(p. 5).

Their workflow starts from a validated political-personality inventory, distinguishes strong from
weak cues, and obtains human labels from three coders. Agreement was only alpha .70-.78 even with a
purpose-built codebook (pp. 8-9). The best models reached macro-F1 .76-.77, while no method exceeded
.80 (pp. 10 and 14). Strong cues were easier to recover. A local Llama-3-8B reached only about
.55-.60 and the compact supervised/fine-tuned models failed several functional tests (pp. 10-12), so
"runs locally" is not itself adequate validation. The paper measured public agency/communion cues,
not intrinsic Big Five traits or member-level Extraversion.

### Consequence for v1 and a possible v2

The three papers strengthen the decision not to activate v1. Its hand-built excitement and
gregariousness facets were weak, the two aspects did not cohere, and the only external criterion was
itself substantially volume-laden. A defensible next test would:

1. target **publicly expressed Extraversion cues**, not claim unobservable intrinsic Extraversion;
2. build a congressional-interview codebook for strong warmth, excitement/positive energy,
   gregariousness, activity, and assertiveness cues, including a large `none` class and explicit
   separation of warmth from Agreeableness;
3. require independent human labels and interrater agreement before model training;
4. use speaker/episode-disjoint validation and source/venue holdouts, with visibility, office,
   leadership, appearance opportunity, party, gender, and transcript source controlled;
5. compare a locally trainable model against the lexical baseline and require human-label,
   functional, reliability, discriminant, and venue-robustness bars; and
6. retain RKH and visibility only as diagnosed secondary comparisons, never score inputs or decisive
   construct-validity criteria.

This route can be designed with zero paid-API use. It requires a human-labeled political-speech
criterion or an openly reproducible equivalent; the three papers do not supply a ready-to-use,
validated current-Congress Extraversion score.
