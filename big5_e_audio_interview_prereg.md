# Source-disjoint audio-E validation of interview expressiveness-v2

**STATUS: LOCKED — 2026-07-13, committed before any audio/Blue correlation or
audio/interview-behavior pairing is computed.** User direction: use off-script interviews as a more
persona-revealing E behavior and include the audio channel. This study keeps the already frozen
`expressiveness_v2` formula unchanged and tests it against a criterion derived entirely from verified
voice acoustics.

## Why this is a fresh route

The same-venue interview-observer criterion was rejected at Stage 1: it was reliable but strongly
party- and gender-loaded. No expressiveness pairing was taken. The present criterion shares no
interview text, package, transcript, program, LLM rating, or turn-length input with expressiveness.
It uses the 88 eGeMAPS acoustic functionals from identity-verified solo audio. The prior N=90 faithful
audio study established that the full eGeMAPS block carries E signal; this study does not reopen its
consumed result. It asks a new question on the current 410-voiceprint cache: can a clean, cross-fitted
audio read of the promoted Blue E trait corroborate turn-level expression in interviews?

The claim is deliberately narrower than full-trait validation. A PASS validates
`expressiveness_v2` as a cross-modal behavioral manifestation of E. It does not replace any of the
promoted Big Five instrument's existing five validity legs, promote a candidate, or feed an engine.

## Frozen sample and measures

- Audio: `b5_audio_cache.json`, 410 members with at least 180 verified clean seconds; all 88
  eGeMAPSv02 functionals, already duration-pooled, standardized, and winsorized at +/-5.
- Trait target: promoted `big5_blue_validated.json` E only. Projected audio/Blue intersection is 393.
- Interview behavior: the existing `expressiveness_v2` candidate only—the mean of within-program
  standardized mean and p90 response words per turn, aggregated by qualifying turns and standardized
  within chamber. No formula, floor, or member value may change.
- Projected audio/Blue/expressiveness intersection is 250. No missing value is imputed.

Two independent outer-CV panels are fixed:

- primary seeds `[7,17,29,43,61]`
- re-derivation seeds `[11,23,37,47,71]`

For every seed, a shuffled 5-fold outer split generates member-level held-out predictions. Inside
each training fold, Ridge alpha is selected by 3-fold CV from `[1,3,10,30,100,300,1000]`. Predictions
are averaged over the five seeds. Every member's audio-E value is therefore predicted by models that
never saw that member's Blue E value.

## Stage 1 — qualify audio-E before opening interview behavior

The criterion stage may read only verified audio features, Blue traits, roster controls, and clip
durations. It must not open the behavioral candidate, behavioral dispositions, interaction features,
or interview transcripts.

Audio score reliability is computed from two fixed clip partitions,
`audio-e-rel-primary-v1` and `audio-e-rel-rederive-v1`. Each clip is indivisible and assigned by
SHA-256. A member must have at least 90 verified seconds in each half. Half features are independently
duration-pooled and standardized; the already cross-fitted audio-E models predict both halves.
Pre-outcome coverage is 293 and 287 Blue-covered members for the two partitions.

Each CV panel must clear all gates:

1. At least 350 complete audio/Blue members.
2. Held-out audio-E vs Blue E `r>=+.20`, one-sided 5,000-permutation `p<.05`.
3. After residualizing party, gender, chamber, and log verified audio seconds, `r>=+.15`, `p<.05`.
4. The E correlation exceeds the absolute audio-score correlation with Blue O, C, A, and N.
5. Spearman-Brown half reliability is at least .60 in both clip partitions, each with n>=250.
6. Raw audio-score contamination is bounded: `|r(party_R)|<=.20`, `|r(female)|<=.20`, and
   `|r(log audio seconds)|<=.20`.

The primary and re-derivation predictions must correlate at least .90. Any Stage-1 failure rejects
the audio criterion and forbids the interview-behavior look. A PASS writes a candidate consumed by
nothing; its SHA-256 must be added to this preregistration and committed before the look.

## Stage 2 — the one source-disjoint interview look

For each independently cross-fitted audio panel, correlate audio-E with the frozen interview roles on
an identical complete-case sample. Permutation p uses 5,000 member-label shuffles.

Partial tests residualize both variables on party, gender, chamber, log qualifying interview turns,
and log verified audio seconds. The same partial machinery is applied to three rival roles:
dominance-v2, cutoff reactivity, and interview visibility.

Each panel passes only if all gates hold:

1. n>=230.
2. Raw expressiveness/audio-E `r>=+.15`, one-sided `p<.05`.
3. Partial expressiveness/audio-E `r>=+.10`, one-sided `p<.05`.
4. The expressiveness partial r is positive and strictly exceeds the absolute partial r of all three
   rival roles.

The final result is PASS only if both seed panels pass all four bars. Primary PASS plus
re-derivation failure is `FRAGILE = MISS`. The fixed expressiveness formula, criterion, controls,
features, alpha grid, thresholds, rivals, and samples may not be substituted after either stage opens.

## Power and fixed consequences

At the projected n=250, a one-sided correlation test has approximately 80% power near r=.16 and over
95% near r=.22. The two-panel all-must-pass rule is stricter; it is designed to support a moderate,
replicable cross-modal effect, not rescue a weak association.

- PASS: **“Interview expressiveness-v2 has source-disjoint cross-modal convergence with a
  gender/party-controlled acoustic E read. It is validated as an observed expressive-interpersonal
  E behavior, while interview visibility remains an exposure measure.”**
- MISS/FRAGILE: **“Interview expressiveness-v2 remains a reliable speaking-style measure but is not
  validated as E by the clean-audio route.”** The route closes without feature, target, or threshold
  changes.

## Input pins at lock

| Input | SHA-256 |
|---|---|
| `b5_audio_cache.json` | `4af340d1df9daa0c2df3b3f8ea29a189c384d5597d5de6ac980554664e9e9830` |
| `b5_audio_clipcache.json` | `b4f42a9448e3141dfcb4d9ee4a7f2260ec1611febdf110ff0849bbe0d6a3dd1f` |
| `b5_audio_verify.json` | `69b7cc5685c8adbf34a2382282f16b700bab0d04a8997a5611319abe22f56c84` |
| `big5_blue_validated.json` | `876bc2ecf8672477d586f3db34472cdb2cf61ee0573e30c4b909448cd0970a8f` |
| `behavioral_roles_v2_candidate.json` | `d6b7bd35e330549b40a1820b0709c9bf7e2768e3dd8456a3293b6793fec9f755` |
| `fec/behavioral_roles_v2_study.py` | `94b4f582e2469caa3550c2ad9b8b463067008a9c2ceb4c32126335ae539d46eb` |
| `behavioral_dispositions.json` | `57ca1e2b1731cbeed4411645c2b527a8db0136362c2d3d4654dda8faaa852e03` |
| `fec/legislators.csv` | `c5a6cbdbaae0bb19faa89852c29922809ececc70b97c149b4709588087e5e391` |
| `congestion.json` | `ddc9d746600dbdfc60b76c54537662e19c758cbfb9d7a478a71b7bf90cd727a6` |

The executable harness must pass its planted/null/confound-only battery before either real stage. The
criterion and final result stdout are recorded verbatim. No artifact produced here has a production
consumer.

`AUDIO_CRITERION_SHA256: PENDING_STAGE1`

## RESULT-AUDIO-E — STAGE 1 REJECTED; INTERVIEW LOOK NOT TAKEN (2026-07-13)

The cross-fitted audio criterion was cleanly separated from Blue O/C/A/N, remained within all raw
party/gender/duration bounds, and replicated strongly across the two outer-CV panels. The primary
panel missed the held-out convergence magnitude by .007, and neither panel cleared the predeclared
clip-half reliability floor. Under the locked gate, the audio criterion is rejected and the interview
behavior files remain unopened. No score averaging change, clip floor change, feature subset,
residualization change, or threshold repair is permitted.

```text
=== AUDIO/INTERVIEW SYNTHETIC BATTERY ===
  planted partial r=+0.675 p=0.0002
  null raw        r=-0.015 p=0.5931
  gender-only partial r=-0.015 p=0.5933
  planted_admitted             PASS
  null_refused                 PASS
  gender_only_refused          PASS
BATTERY PASS
=== CLEAN-AUDIO E CRITERION GATE ===
  primary n=391 raw=+0.193 p=0.0002 partial=+0.151 p=0.0020
    heterotrait: O=-0.020(n=391) | C=-0.155(n=391) | A=-0.092(n=284) | N=+0.099(n=391)
    reliability: primary SB=0.540(n=291) | rederive SB=0.536(n=285)
    contamination: party_R=-0.039 | female=-0.113 | log_audio_seconds=+0.178
    gates: coverage=PASS, convergent=MISS, partial=PASS, diagonal=PASS, reliability=MISS, contamination=PASS -> MISS
  rederive n=391 raw=+0.225 p=0.0002 partial=+0.184 p=0.0002
    heterotrait: O=-0.009(n=391) | C=-0.160(n=391) | A=-0.082(n=284) | N=+0.101(n=391)
    reliability: primary SB=0.567(n=291) | rederive SB=0.537(n=285)
    contamination: party_R=-0.041 | female=-0.120 | log_audio_seconds=+0.179
    gates: coverage=PASS, convergent=PASS, partial=PASS, diagonal=PASS, reliability=MISS, contamination=PASS -> MISS
  panel-repeat r=+0.964 -> PASS
  CRITERION VERDICT: REJECTED
  AUDIO_CRITERION_SHA256: 47dcd6b3eb155f587f35f01bbf94da28f82c291a59f232e17ab7daf90fc7c978
wrote audio_e_oof_criterion.json.candidate (consumed by nothing)
```
