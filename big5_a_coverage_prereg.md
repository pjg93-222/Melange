# A-facet coverage / sampling-frame audit - LOCKED 2026-07-12

**STATUS: RESULT CONSUMED - DEMOGRAPHICALLY SELECTED MEDIA-COVERED STRATUM.** This is a sampling-frame robustness audit of
the already-qualified Round-9 inverse-interview-antagonism A facet. It does not reopen the
consumed text-A look, change the 5/5 criterion-quality result, or authorize score fitting.

## Motivation and fixed interpretation

Hargittai (2015, DOI 10.1177/0002716215570866) shows that large trace datasets remain biased
when participation in the source platform is non-random; conclusions must be scoped to the
sampling frame and triangulated across sources. Azucar, Marengo, and Settanni (2018, DOI
10.1016/j.paid.2017.12.018) find Agreeableness is the weakest digital-footprint Big Five target
(meta-analytic r=.29) and that adding demographics increases apparent A/N prediction. Celli et
al. (2026, DOI 10.1145/3806009) distinguish trait, state, ecological validity, and observer/model
representation validity, and note that communication channel changes personality perception.

Therefore demographics are controls/diagnostics only, never predictive A features; interview
coverage is a sampling frame, not the full roster; and the display claim stays facet-specific.

## Frozen inputs

- `interview_antagonism_halves.json.candidate` SHA-256
  `15FFB00BA199708C17733260205E0580CE766F3B37E0C69A74965B35B4AB0575`
  (names only may be used for inclusion; antagonism values are forbidden in this audit).
- `member_desk_bundle.json` SHA-256
  `34879F3397DEA3FA4E1203F61EBF7539DBA58F488C3335F3FC6332E37486416C`.
- `behavioral_dispositions.json` SHA-256
  `57CA1E2B1731CBEED4411645C2B527A8DB0136362C2D3D4654DDA8FAAA852E03`.
- `big5_v2.json` SHA-256
  `385F7FC0881B624E938E7E860DFE593AF0E3C640104B6BCF2DE85C01F3341AC7`.
- Source PDFs SHA-256: Azucar `77D48A...43A91`; Celli `54CD2E...A39A`;
  Hargittai `8FF889...D10E48` (full hashes recorded in the audit report).

Universe is the 533-member desk roster. Included means present in the frozen Round-9 candidate
(expected n=322); excluded is everyone else. Missing values are reported and excluded per metric,
never zero-filled.

## Locked diagnostics and bars

For each metric compute included/excluded means, coverage, and standardized mean difference
`SMD=(mean_in-mean_out)/pooled_SD`; binary variables use the same formula.

1. **Demographic balance:** Republican, female, and Senate indicators. All `|SMD| <= .20` is
   CLEAN; any `>.20` is a demographic sampling caution; any `>.35` is a material failure.
2. **Model-position balance:** composite score and legislative, influence, and demographic
   pillars. All `|SMD| <= .20` is CLEAN; any `>.20` requires a model-position caution.
3. **Media/activity selection:** log(1+article count), press pillar, behavioral visibility, and
   log(1+Blue tokens). All `|SMD| <= .35` is required for a full-roster-generalizability claim.
   This bar is deliberately looser because the criterion requires interview evidence.
4. Report coverage rates by party, gender, and chamber and the maximum percentage-point gap.

## Predeclared consequences

- If 1-3 all clear: call the facet demographically/structurally balanced on observed diagnostics,
  but still do not impute scores to uncovered members.
- If demographic/model-position bars clear but media/activity fails: approved wording becomes
  **"validated inverse-antagonism A facet on the interview/media-covered stratum"**; add the
  sampling-frame limitation to artifact metadata, desk UI, methods, and audit guards.
- If a demographic bar exceeds .35: additionally mark the facet demographically selected and do
  not use roster percentiles without within-group sensitivity reporting.
- No result permits changing the rubric, residualization, thresholds, scores, engine A slot,
  Blue/Pink A, or ranks. No weighting/IPW may be added after seeing the result; that would require
  a new preregistered robustness study.

## RESULT - consumed 2026-07-12 (`fec/b5_a_coverage_audit.py --look`)

All frozen inputs matched. Coverage was 322/533. The preregistered verdict is
**DEMOGRAPHICALLY SELECTED MEDIA-COVERED STRATUM**:

- Demographic max `|SMD|=.620` - MATERIAL FAILURE: Republican `-.322`, female `-.001`,
  Senate `+.620`. Coverage was D 176/259 (68.0%), R 144/272 (52.9%), House 232/433
  (53.6%), Senate 90/100 (90.0%), female 60.7%, male 60.8%. The large party max-gap print
  includes the two Independents (2/2); the D-R comparison is the decision-relevant one.
- Model-position max `|SMD|=.378` - CAUTION: composite `+.219`, legislative `+.080`,
  influence `+.320`, demographic pillar `+.378`.
- Media/activity max `|SMD|=1.877` - FAIL: log articles `+.381`, press pillar `+.028`,
  visibility `+1.877`, log Blue tokens `+1.195`.

**Binding consequence applied:** approved wording is "validated inverse-antagonism A facet on
the interview/media-covered stratum." The displayed percentile is relative only to the 322 covered
members and must be labeled as such. No missing-member imputation, score/rubric/residualization
change, weighting, engine change, Blue/Pink change, or rank change is authorized. The original
criterion-quality result (5/5 on its observed stratum) stands; full-roster generalizability does not.
