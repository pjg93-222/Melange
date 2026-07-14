# Official-facing negative emotional reactivity v2 — exploratory engineering protocol

STATUS: FROZEN EXPLORATORY PROTOCOL — NOT FRESH CONFIRMATORY VALIDATION

Date frozen: 2026-07-13

## Why this is a separate v2

The locked v1 target/tone test showed that subject severity can be separated from sentence tone
(raw r=.074; residual r=.004), but none of seven N-relevant facets cleared every preregistered bar.
After seeing that result, the user explicitly permitted a narrower improved N score even if it is
not holistic Neuroticism. Because the v1 result informed this design and v2 reuses the same corpus,
v2 is exploratory engineering, not a new independent validation. No result can change that label.

The exact product label is **Official-facing negative emotional reactivity (N-expression; not
holistic Neuroticism)**. It describes repeated public presentation likely to be encountered by a
stakeholder. It does not describe private personality, clinical status, motive, or energy source.

## Frozen score

The v1 sentence classifier, target classes, attribution guard, topic severity, leave-one-member-out
context cells, corpus window, and input fingerprints are reused without modification. v2 uses three
observable aspects:

1. **Residual tone level** — signed mean member-owned negative tone after the v1 subject, target,
   program, and severity expectation.
2. **Disproportionate intensity** — signed mean dramatic/apocalyptic amplification residual. Signed
   residual replaces v1's positive-tail transform because the positive tail can reintroduce
   subject-mix effects; this is a construct correction, not a threshold change.
3. **Emotional volatility** — standard deviation of residual episode tone means across at least five
   substantive episodes.

For each aspect, a deterministic five-fold member cross-fit predicts the aspect from party, gender,
current formal-leadership status, log sentence coverage, average subject severity, and chamber.
Each member receives the held-out residual from a model that did not include that member. Residuals
are standardized within chamber. The score is the equal mean of the three aspect z-scores and is
then standardized within chamber. Equal weights are frozen; no fitted personality weights, PCA,
audio, visibility, title bonus, paid model, or old affective-N value enters the score.

Raw aspect values and a raw unadjusted equal-weight score remain in the artifact for auditability.
The cross-fit adjustment is narrow and explicit: it prevents party rhetoric, title obligations,
coverage volume, or severe subject portfolios from silently becoming personality.

## Frozen engineering checks

The same five episode-disjoint split salts and chronological earlier/later split are reused. The
candidate is `READY-PROVISIONAL` only if every bar passes:

- at least 200 members scored;
- score median Spearman-Brown split-half reliability at least .60 and at least four of five splits
  at least .50;
- at least two of three aspects have median corrected reliability at least .50;
- chronological score correlation at least .30;
- all three adjusted aspect-pair correlations between .10 and .80, avoiding both incoherence and
  redundancy;
- maximum absolute held-out score correlation with party, gender, current formal leadership, log
  sentence coverage, average subject severity, or chamber at most .15;
- v1 sentence-level subject adjustment still passes its frozen bar.

These are engineering-readiness checks, not construct validation. `READY-PROVISIONAL` means only
that the score is repeatable, coherent, and not obviously dominated by the listed nuisance factors
in this corpus. A temporally new interview holdout or independent criterion remains mandatory
before a validated-N claim.

## Activation boundary

The output is `official_persona_n_expression_v2.json.candidate`. It is consumed by nothing and may
not replace live N, alter a profile, appear in the UI, or move a rank without the user's explicit
approval after reviewing the result. Weakness is reported as `NOT READY`; no post-result tuning is
permitted under this protocol.

## RESULT-N-EXPRESSION-V2

Build completed: 2026-07-13

Outcome: **NOT READY**. Seven of eight frozen engineering bars passed. The sole miss was
chronological score stability, r=.266 against the frozen .30 floor. The threshold was not relaxed.

```text
SELF-TEST: PASS (6/6)
corpus: 290720 sentences | 32574 episodes | 210 scored members
score                         SB=0.645 split=5/5 chrono=0.266 n=175
residual_tone_level           SB=0.648 split=4/5 chrono=0.173 n=175
disproportionate_intensity    SB=0.700 split=5/5 chrono=0.312 n=175
emotional_volatility          SB=0.532 split=3/5 chrono=0.250 n=175
coherence: tone-intensity=.616 tone-volatility=.613 intensity-volatility=.216
score confounds: party=.016 gender=-.014 current-role=-.026 log-sentences=.008
                 subject-severity=.007 chamber=.000
ENGINEERING RESULT: NOT READY
CANDIDATE QA: PASS
```

The candidate artifact SHA-256 is
`f5085d1edfb65857c69d001a6df254e06b4c14e66c154b9d854f44764090abd6`.
It remains disconnected. Reliability, coherence, coverage, subject separation, and held-out
confound control all passed, but the score did not meet the predeclared across-time stability
requirement. This is consistent with an official presentation that may move with role, events, and
time; it is not permission to redefine the bar after seeing the result.
