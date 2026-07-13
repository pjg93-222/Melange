# Behavioral / Big-Five Alignment Audit — 2026-07-13

## Outcome

The promoted Blue Big-Five instrument remains 5/5 on split-half reliability, known-groups direction, and held-out discriminant/diagonal-dominance validity. The default member radar now shows Blue alone. The frozen Pink/Opus item-read remains in the data bundle only for reproducible historical diagnostics.

The behavioral panel is not a second Big-Five instrument. Three role-to-trait relationships are strong and directionally clean (policy breadth/O, legislative follow-through/C, interview visibility/E). Cross-party cooperation is correctly separate from low-antagonism Agreeableness. Affective N is shared with Blue N and therefore cannot count as independent corroboration.

## Data and method

Inputs were `behavioral_dispositions.json`, `coop_v2_candidate.json`, `interaction_features.json`, `behavior_panel.json`, `affective_n.json`, `big5_blue_validated.json`, and `fec/legislators.csv`.

For each available member, the audit correlated each behavioral role with every Blue trait. The partial matrix residualized both variables on party, gender, chamber, log Blue text tokens, and log combined observed activity (floor words, interview count, and tweet count). No missing trait or behavior value was imputed.

## Alignment matrix

Raw Pearson correlations (pairwise covered samples):

| Behavioral role | O | C | E | A | N |
|---|---:|---:|---:|---:|---:|
| Policy breadth | **.688** | .083 | .079 | .132 | -.030 |
| Legislative follow-through | .088 | **.715** | -.111 | .075 | -.120 |
| Interaction dominance | .212 | .174 | **.105** | -.005 | -.016 |
| Interview visibility | .147 | -.164 | **.900** | -.111 | .092 |
| Cross-party cooperation v2 | -.105 | -.023 | -.092 | **.072** | .013 |
| Affective N | .013 | -.092 | .050 | -.149 | **1.000** |

Partial correlations after party, gender, chamber, token-volume, and activity controls:

| Behavioral role | O | C | E | A | N |
|---|---:|---:|---:|---:|---:|
| Policy breadth | **.658** | .101 | -.028 | .091 | -.022 |
| Legislative follow-through | .092 | **.697** | -.107 | .068 | -.116 |
| Interaction dominance | .194 | .151 | **.049** | -.011 | -.015 |
| Interview visibility | .051 | -.069 | **.512** | -.162 | .075 |
| Cross-party cooperation v2 | -.133 | .024 | -.056 | **.064** | .032 |
| Affective N | .010 | -.079 | -.005 | -.148 | **1.000** |

Pairwise sample sizes are 451 for breadth, 467 for follow-through, 469 for visibility/dominance/N, 289 for cooperation against O/C/E/N, and 207 for cooperation against covered A.

## Cross-contamination findings

1. **Behavior roles are internally distinct.** The largest absolute correlation among the six behavioral rows is .171 (policy breadth with interaction dominance). This is low cross-contamination.
2. **Visibility is activity-heavy.** Interview visibility correlates .786 with the combined activity control and .517 with Blue token volume. Its E relationship falls from .900 raw to .512 controlled. It remains useful as an exposure role, but it must not be labeled as Extraversion.
3. **Cooperation is not Agreeableness.** Cooperation/A is r=.072 raw and r=.064 controlled (n=207). This is construct separation, not a failed A score: strategic cross-party action and low interpersonal antagonism are different behaviors.
4. **N alignment is shared-source.** Behavioral affective N and Blue N are the same promoted member score (r=1.000). It is an operational consistency check only and is excluded from claims of independent cross-panel convergence.
5. **O/C/E alignment is expected, not a new validity leg.** Blue O/C/E were behavior-calibrated against source-separated behavioral packages. The high member-level correlations show that the promoted scores preserve their intended behavioral meaning; held-out package-disjoint diagonal dominance remains the validity test.
6. **Observed covariate contamination is bounded except visibility.** The largest party associations are cooperation -.184, breadth -.167, and follow-through +.150; the largest gender association is affective N +.074; the largest chamber association is breadth -.062.

## Dominance defect

The current producer mixes observed interview dynamics with a binary committee-leadership flag. Coverage inspection found:

- 272 members with at least 30 observed interaction turns;
- 27 leadership-only members;
- 234 with neither qualifying interaction evidence nor leadership;
- 222 members assigned exactly -0.381;
- 24 members assigned exactly +2.619.

Those repeated values are roster coding artifacts, not person-specific dominance measurements. Overall dominance/E alignment is weak (r=.105 raw; r=.049 controlled). Among the 272 interaction-covered members it is r=.081 raw and r=.028 controlled.

## Changes implemented

- Removed Pink/Opus from the default Big-Five radar; retained the frozen artifact and bundle fields for historical diagnostics.
- Renamed behavioral axes to their measured roles: legislative follow-through, interaction dominance, interview visibility, and policy breadth.
- Suppressed dominance from the person-facing radar unless the member has at least 30 observed interaction turns. Missing axes display as `n/a` at the neutral ring; the engine artifact and rankings are unchanged.
- Marked affective N as shared with Blue N and explicitly excluded it from independent alignment claims.
- Kept cooperation and validated low-antagonism A side by side with no substitution.
- Added audit guards so Pink cannot silently return to the default radar and synthetic dominance cannot silently return as a person-specific display value.

## Behavioral improvement disposition — completed 2026-07-13

1. **Dominance-v2 candidate qualified.** The locked candidate excludes formal leadership and verbal-output length, requires at least 30 qualifying interaction turns, and leaves everyone else missing. Coverage is 272; five-split median SB is .564; maximum preregistered partial contamination is .245; offline targeting sensitivity is rho .999980 with 20/20 and 50/50 overlap. Committee leadership is unrelated after controls (r=-.003), confirming the two roles should stay separate. The candidate is consumed by nothing pending a distinct engine-promotion decision.
2. **Turn-level expressiveness measured, but not validated as E.** The visibility role remains an exposure variable. Expressiveness-v2 is stable (median SB=.749), minimally related to visibility after controls (r=-.175), and qualifies as a distinct operational role. It misses the source-disjoint CREC floor-elaboration criterion (partial r=-.023, p=.6425), so it is not an independent behavioral Extraversion indicator and the frozen route is closed without feature substitution.
3. **Cooperation/A separation preserved.** Cooperation-v2 remains the coalition-behavior input; the validated inverse-antagonism facet remains the Big-Five A measure. Dominance-v2 has essentially zero partial association with cooperation-v2 (r=.002), while expressiveness is modestly associated (r=.167); neither is substituted for A.
4. **No N re-look was needed or taken.** The promoted Big-Five N already has independent LIWC convergence in the 5/5 multimethod instrument. The existing behavioral cutoff-reactivity measure now has 272 covered members and fresh five-split median SB=.555. Its previously consumed text-N criterion test remains historical; current affective N was not paired with a duplicate/shared-source criterion.

## Verification

- Kernel tests: 37 passed, 0 failed.
- Full-body audit: 88 passed, 0 failed.
- Dashboard and combined member desk regenerated successfully for all 533 members.
- Person-facing dominance: 272 observed values shown, 260 unavailable values hidden, 0 coverage mismatches.
- Pink default-overlay checks: no Pink radar call and no dashed-Pink legend in the rendered desk.
- Behavioral-roles v2: synthetic battery passed; locked one-look completed; dominance candidate PASS, expressiveness operational-role PASS, independent-E criterion MISS.
- Candidate consumer scan: the two v2 JSON paths occur only in the candidate study and its preregistration; no engine or dashboard consumer exists.
- Rank authority SHA-256 remained `797a6490ca0c0f63496f76ac9f030c0a8b538d5f46dbc18e39092bbbc74b00c6`.
