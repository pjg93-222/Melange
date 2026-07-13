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
