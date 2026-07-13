# Observed interview-E cross-package validation of expressiveness-v2

**STATUS: LOCKED — 2026-07-13, committed before collection and before any observed-E label
exists.** User direction: use interviews because they are less scripted and more reflective of the
politician's persona. This is a fresh criterion and a fresh round; it does not rewrite the consumed
CREC floor-elaboration MISS in `behavioral_roles_v2_prereg.md`.

## Claim and scope

The fixed `expressiveness_v2` behavior—mean and p90 words per interview turn, standardized within
program and chamber—may converge with a blinded observer read of **expressive-interpersonal
Extraversion** in entirely different interview episodes.

This can establish cross-package, cross-method convergence for **observed interview persona**. It
cannot establish source-disjoint or cross-modal validity because both sides come from broadcast
interviews. It cannot alter the promoted multimethod Big Five's existing 5/5 status, and it cannot
feed the engine. Any PASS must carry the same-venue caveat.

Adverse prior disclosed: expressiveness-v2 missed the source-disjoint CREC floor-elaboration
criterion (partial r=-.023, p=.6425) and had only +.060 descriptive alignment with Blue E. The
present prior is MODERATE-LOW. The design differs legitimately because the criterion does not yet
exist, is observer-rated rather than CREC-derived, and is package-disjoint from every score it
judges. No feature, formula, program floor, or candidate threshold changes.

## Frozen collection

Two deterministic SHA-256 package partitions are fixed:

- primary: `e-persona-primary-v1`
- independent re-derivation: `e-persona-rederive-v1`

For each split, the member's interview packages are divided globally into halves A/B. A member is
eligible when each half has at least 3 packages and 1,000 usable words. Exactly 1,000 words per half
are supplied, deterministically sampled across packages, so corpus quantity cannot drive the judge.
Package URL, program, and official identity are omitted; occurrences of the member's own name are
replaced by `[OFFICIAL]`. Only member response turns are supplied, never interviewer speech.

Pre-collection coverage, computed without labels or criterion pairing:

| split | rating eligible | expressiveness half A | half B | paired both halves |
|---|---:|---:|---:|---:|
| primary | 314 | 251 | 255 | 200 |
| re-derivation | 316 | 259 | 256 | 204 |

Haiku 4.5 rates six frozen fields from 0–100: social energy, enthusiastic engagement, expressive
affect, spontaneous self-disclosure, conversational responsiveness, and reserved/flat presentation.
Observed-E is the mean of the first five plus `100-reserved_flatness`. The prompt forbids political
knowledge, ideology, office, polish, toughness, amount of text, and response length alone as evidence.
The model must require content-based interpersonal cues. Haiku is required by the project's cost rule;
Fable and Opus are forbidden.

## Stage 1 — criterion qualification before any expressiveness file is opened

The criterion script may read only the new labels, roster metadata, the existing inverse-antagonism
A facet, and affective N. It must not import or open expressiveness, interaction features, or Blue E.
All gates must pass:

1. At least 300 complete members in each package partition.
2. Package-half Spearman-Brown reliability at least .60 in both the primary and re-derivation
   partitions.
3. Correlation between the two partitions' member means at least .70.
4. Raw contamination: |r(party_R)|<=.20, |r(female)|<=.15, and |r(log source packages)|<=.20.
5. Construct separation: |r(inverse-antagonism A)|<=.30 and |r(affective N)|<=.30.

A Stage-1 MISS rejects the observer criterion and forbids the trait look. A PASS permits exactly one
collection-record addendum containing the label SHA-256 and verbatim Stage-1 output. The look remains
refused until that addendum is committed.

## Stage 2 — cross-package expressiveness look

For each partition, the frozen interaction scorer is rerun independently on each half. Direction 1
correlates expressiveness from A with observed-E rated on B; direction 2 correlates expressiveness
from B with observed-E rated on A. Package overlap in each direction must be exactly zero.

The two directional correlations are combined by the mean Fisher-z and transformed back to r.
Permutation p uses 5,000 member-level shuffles, applying the same member permutation to the paired
ratings in both directions. Partial tests residualize both sides on party, gender, chamber, log
qualifying turns on the score side, and log source-package count on the rated side.

The primary split passes only if all five bars hold:

1. At least 190 members have both directional pairings.
2. Both raw directional correlations are positive; combined raw r>=+.15 and one-sided permutation
   p<.05.
3. Both partial directional correlations are positive; combined partial r>=+.10 and permutation
   p<.05.
4. Combined partial expressiveness r strictly exceeds the absolute cross-package partial r for
   dominance-v2 and reactivity, computed by the identical machinery.
5. Every episode overlap count is zero and all input fingerprints match.

A primary PASS is only accepted if the independent re-derivation partition re-clears all five bars
with its own package assignment and permutation seed. Failure on re-derivation is `FRAGILE = MISS`.

Blue E against the new observed-E criterion is a secondary same-venue read only. It may be printed
but can change no trait, instrument, display, engine, or 5/5 status.

## Power and interpretation

At n=200, simulation of the all-must-pass two-partition rule gives approximately 73% power for a true
r=.20, 97% for r=.25, and >99% for r=.30. Therefore a PASS supports a moderate observed-persona
effect. A MISS closes this exact interview-observer route but is not evidence that effects below .20
are absent.

Fixed consequence wording:

- PASS: **“Expressiveness-v2 has cross-package convergent validity for an observed
  expressive-interpersonal Extraversion facet in broadcast interviews. The evidence is same-venue,
  not source-disjoint, and does not replace the promoted Big Five validity legs.”**
- MISS/FRAGILE: **“Expressiveness-v2 remains a reliable operational speaking-style measure, but is
  not validated as observed interview Extraversion by this route.”** The route closes without
  feature/rubric/threshold substitution.

## Input pins at lock

| Input | SHA-256 |
|---|---|
| `social_media.db` | `21f2e9f6c13d44f5bed27cabfc9414b445ba8b0f047e88b101ac5267112ab6ec` |
| `congestion.json` | `ddc9d746600dbdfc60b76c54537662e19c758cbfb9d7a478a71b7bf90cd727a6` |
| `fec/legislators.csv` | `c5a6cbdbaae0bb19faa89852c29922809ececc70b97c149b4709588087e5e391` |
| `fec/behavioral_roles_v2_study.py` | `94b4f582e2469caa3550c2ad9b8b463067008a9c2ceb4c32126335ae539d46eb` |
| `behavioral_roles_v2_prereg.md` | `864d3cb4a64c4bc3add4199d70581fbdb2e2698b82b4e81be781bbab7d9b6d50` |
| `affective_n.json` | `f3601ce9338dcbe5d222a10429fd7092c13ffcda020586ecc5f91fc484cde3ce` |
| `interview_antagonism.json` | `20752950b908e8b0ac5b79c06ccfae687fe6a486057e53e1915f361d58672c29` |
| `big5_blue_validated.json` | `876bc2ecf8672477d586f3db34472cdb2cf61ee0573e30c4b909448cd0970a8f` |

The look script requires this lock, a committed `COLLECTION_SHA256:` addendum, no prior
newline-anchored RESULT-EI heading, matching pins, a green in-process planted/null/confound battery,
and a fresh Stage-1 PASS. One real look, consumed whether PASS or MISS. Result stdout is appended
verbatim and committed in the same session.

## PRE-COLLECTION AMENDMENT PC-1 — prompt-cache coding manual (2026-07-13)

After the lock commit, the first API attempt returned billing errors. The user restored API funds and
explicitly required prompt caching. Haiku 4.5 has a 4,096-token minimum cacheable prefix, while the
original short rubric was below that floor. See PC-2 for the subsequently discovered orphan-process
correction; no old-rubric rating is admissible in this round.

The six fields, positive/reverse composite, model, two salts, 1,000-word halves, eligibility, sample,
criterion gates, behavior formula, acceptance bars, and one-look rule remain unchanged. The coding
instructions are expanded into the member-independent manual
`fec/interview_e_persona_rubric.md`: it supplies fixed score anchors and explicit separation from
dominance, Agreeableness, affective N, Openness, Conscientiousness, ideology, identity, and volume.
The manual is the cached system prefix; it is pre-warmed before parallel scoring and uses a 5-minute
ephemeral cache refreshed by hits. This is a pre-collection measurement clarification, not a
post-result rubric substitution. Its SHA-256 is pinned in the collection artifact and below when the
amendment is committed.

`RUBRIC_SHA256: 51fceb122ec5463b80026301fb7676a39d909f062b75285d9d08ba182b28306c`

`SCORER_SHA256: 01f93eb38175bdce195de5e1a157dd2d9641b87b329337fb7965f008c30cc642`

## PRE-COLLECTION CORRECTION PC-2 — orphan output quarantined (2026-07-13)

The shell cancellation of the unfunded first attempt did not initially terminate its Python child.
After funds returned, that orphan wrote 10 member-partition ratings under rubric version
`observed-interview-e-v1-locked-2026-07-13` before exiting; it also retained 180 request errors. The
precommit check inspected counts and version only, never rating values. The complete artifact was
moved to `interview_e_persona_halves.precache_short_rubric.CANCELED.json`, SHA-256
`f98a6134029bcc0c3cb40bc17b397069ed734490f4ca564a78a7d5df74f2cb64`. It is excluded from every
criterion and trait calculation. The active candidate path was absent before the cached-manual run.
The validator requires the new rubric version and hash and therefore also hard-refuses this quarantined
artifact. This correction is committed before collection under the cached manual begins.
