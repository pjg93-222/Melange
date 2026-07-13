# Behavioral roles v2 candidate study

**LOCKED 2026-07-13 before any v2 score, split-half result, criterion pairing, or rank-sensitivity
result was computed.** This study executes the first two open items in
`AUDIT_FINDINGS_2026-07-13_BEHAVIOR_ALIGNMENT.md`. It is criterion-side measurement work only.
The candidate artifacts are consumed by nothing, and this lock does not authorize an engine
promotion.

## Questions

1. Can observed conversational dominance be measured without embedding committee leadership or
   manufacturing values for members with no qualifying interaction evidence?
2. Can turn-level expressiveness be measured separately from the number of interview appearances?
3. Is either role stable, reasonably uncontaminated, and decision-robust enough to remain a viable
   candidate?

The existing `reactivity_z` criterion is re-audited for reliability only. Its Round-8 text-N look
was already consumed and is not reopened. Blue N already has independent LIWC convergence in the
promoted multimethod 5/5 instrument, so no new N corroboration is required here.

## Frozen data and construction

Input is every `source='INTERVIEW'` row in `social_media.db`, grouped into indivisible transcript
packages. The program parser, transcript cutoff rule, and cell controls are inherited from
`fec/interaction_features.py`: at least 12 member turns in a program cell, at least 8 members in a
program, feature z-scores within program, and turn-weighted aggregation across programs. A member
score requires at least 30 qualifying turns. Missing interaction evidence stays missing in the
candidate and maps to neutral only inside the offline engine-sensitivity simulation.

The formulas are fixed before the look:

- **dominance_v2** = mean(`gini`, `defense`). `gini` is inequality in turn length; `defense` is
  floor-defense phrases per 1,000 words. Formal leadership and verbal-output length are excluded.
- **expressiveness_v2** = mean(`wpt_mean`, `wpt_p90`). It measures elaboration within a turn, not
  appearance count. Burst is excluded because the prior N audit found it situationally unreliable.
- **reactivity audit** = `cutoff`, the already shipped pressure-reactivity behavior; no formula or
  score promotion is proposed.

After program aggregation, dominance and expressiveness are z-scored within chamber. This gives a
directly comparable role scale without using party, leadership, Blue traits, or any outcome in score
construction.

The one-look script refuses any input drift. SHA-256 pins at lock:

| Input | SHA-256 |
|---|---|
| `social_media.db` | `21f2e9f6c13d44f5bed27cabfc9414b445ba8b0f047e88b101ac5267112ab6ec` |
| `congestion.json` | `ddc9d746600dbdfc60b76c54537662e19c758cbfb9d7a478a71b7bf90cd727a6` |
| `behavior_panel.json` | `491761ea130f8458ae0d09d15be20619b31011ab14e56e6a05bfbdf3d703a4cb` |
| `behavioral_dispositions.json` | `57ca1e2b1731cbeed4411645c2b527a8db0136362c2d3d4654dda8faaa852e03` |
| `big5_blue_validated.json` | `876bc2ecf8672477d586f3db34472cdb2cf61ee0573e30c4b909448cd0970a8f` |
| `coop_v2_candidate.json` | `f0f958dfd35e89f7ab08e73e4f4aab59f762e50558803da4f6dec3a455ff224c` |
| `member_receptivity.json` | `84391fd4438588d162ddf9d2caacee86a8ab0cbeca3a740455e080d79bb06c33` |
| `fec/legislators.csv` | `c5a6cbdbaae0bb19faa89852c29922809ececc70b97c149b4709588087e5e391` |

## Reliability and package independence

Five deterministic SHA-256 package partitions are used (`roles-a` through `roles-e`). A transcript
package is indivisible and globally assigned to one half, so no episode can enter both halves.
Each half reruns the full program-floor, within-program standardization, and member aggregation.
Members need at least 15 qualifying turns in each half. Reliability is Pearson split-half r with the
Spearman-Brown correction.

Candidate reliability clears only if, for both dominance and expressiveness:

- median Spearman-Brown reliability across the five partitions is at least **.50**; and
- at least **4 of 5** partitions have Spearman-Brown reliability at least **.40**.

The carried reactivity audit is expected to retain median SB at least **.45**. A miss changes its
current-data quality note but cannot reopen or reverse a consumed trait look.

## Criterion and contamination tests

All partial tests residualize both variables on party, gender, chamber, and log qualifying interview
turns. The expressiveness criterion additionally controls log floor-speech count.

- Dominance is compared with committee leadership as a source-disjoint status-attainment correlate.
  Because formal leadership is intentionally not the same construct, its direction and uncertainty
  are reported but are **not** a promotion gate.
- Expressiveness is compared with source-disjoint floor elaboration,
  `log(floor_words / n_floor_speeches)`, among members with at least 20 CREC speech rows. It qualifies
  as an independent behavioral E indicator only if partial r is at least **+.10** with one-sided
  5,000-permutation p below **.05**.
- Shared-interview alignment with promoted Blue E is reported descriptively and cannot count as
  independent validation.
- Dominance qualification requires its largest absolute partial correlation with expressiveness,
  interview visibility, policy breadth, legislative follow-through, cooperation_v2, and reactivity
  to be at most **.45**.
- Expressiveness qualification requires absolute partial correlation with interview visibility at
  most **.45**, and its largest absolute partial correlation with policy breadth, legislative
  follow-through, cooperation_v2, and reactivity at most **.35**.

Cooperation and Agreeableness remain separate by construction. No cooperation value is relabeled as
A, and the promoted low-antagonism A facet is untouched.

## Offline engine sensitivity

The study substitutes dominance_v2 for the old dominance slot in memory only, with missing candidate
values treated as neutral zero. No file read by an engine is changed. The current `-.10 * dominance`
coefficient and persona blend are reproduced, then the established flip-model winnability decision
surface is recomputed.

Decision robustness clears if Spearman rank rho is at least **.995**, top-20 overlap is at least
**18/20**, and top-50 overlap is at least **45/50**. These are sensitivity bars, not authorization to
promote.

## Verdict rules

- **dominance_v2 QUALIFIED CANDIDATE** requires coverage at least 250, exact missingness behavior,
  the dominance reliability gate, the dominance contamination gate, and all rank-sensitivity bars.
- **expressiveness_v2 QUALIFIED ROLE** requires coverage at least 250, exact missingness behavior,
  the expressiveness reliability gate, and its contamination bars.
- **expressiveness_v2 INDEPENDENT E INDICATOR** additionally requires the source-disjoint floor-
  elaboration criterion gate.
- Any failed bar is a MISS at the frozen specification. No feature swapping, coefficient tuning,
  floor relaxation, or threshold movement follows the look.

Before the real look, `python fec/behavioral_roles_v2_study.py --simulate` must demonstrate that the
statistical gates admit a planted signal, reject a null, compute split-half correction correctly,
and enforce missingness. The real look is exactly one invocation with `--look`. Its stdout and
machine-readable result are appended after this lock without rewriting the rules above.

## RESULT — consumed 2026-07-13 after prereg lock `9b6074b`

The synthetic battery passed before the real invocation. The one look was then consumed against the
pinned inputs. No input or production artifact changed. Candidate SHA-256 is
`d6b7bd35e330549b40a1820b0709c9bf7e2768e3dd8456a3293b6793fec9f755`; result SHA-256 is
`94b61f0c97ffd91411ea42a856105b88c4ac00ff1d7646bf1864e8710e8ce62b`.

```text
BEHAVIORAL ROLES v2 — THE ONE LOOK
coverage: dominance 272 | expressiveness 272
reliability dominance_v2       median SB=0.564 | >=.40 5/5 | 0.438, 0.478, 0.657, 0.660, 0.564
reliability expressiveness_v2  median SB=0.749 | >=.40 5/5 | 0.761, 0.724, 0.753, 0.749, 0.720
reliability reactivity_raw     median SB=0.555 | >=.40 5/5 | 0.498, 0.555, 0.534, 0.597, 0.594
criterion dominance~leadership partial r=-0.003 p=0.5075 n=270 (descriptive)
criterion expressiveness~floor-elaboration partial r=-0.023 p=0.6425 n=257
partial contamination:
  dominance~expressiveness -0.074
  visibility     dominance +0.099 | expressiveness -0.175
  breadth        dominance +0.081 | expressiveness +0.054
  diligence      dominance +0.033 | expressiveness +0.010
  cooperation_v2 dominance +0.002 | expressiveness +0.167
  reactivity     dominance +0.245 | expressiveness +0.027
shared-interview Blue E (descriptive): dominance +0.052 | expressiveness +0.060
rank sensitivity: rho 0.999980 | top20 20/20 | top50 50/50
gates:
  coverage                                 PASS
  missingness                              PASS
  dominance_reliability                    PASS
  expressiveness_reliability               PASS
  reactivity_reliability                   PASS
  dominance_contamination                  PASS
  expressiveness_visibility                PASS
  expressiveness_other_contamination       PASS
  expressiveness_floor_criterion           MISS
  rank_sensitivity                         PASS
verdicts:
  dominance_v2_qualified_candidate                 PASS
  expressiveness_v2_qualified_role                 PASS
  expressiveness_v2_independent_E_indicator        MISS
wrote behavioral_roles_v2_candidate.json and behavioral_roles_v2_study.json (consumed by nothing)
```

Interpretation fixed by the prereg: dominance_v2 is a qualified candidate for observed
conversational dominance. Its near-zero leadership correlation confirms that committee office and
observed floor behavior are separate rather than interchangeable. Expressiveness_v2 is stable and
distinct from interview exposure, but it misses the source-disjoint criterion and therefore cannot
be called an independent E indicator. The frozen specification is closed without feature shopping.
Reactivity retains acceptable current-corpus reliability; no N trait look was reopened.
