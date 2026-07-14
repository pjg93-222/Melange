# Official-persona N target/tone v1 — preregistration

STATUS: LOCKED

Date locked: 2026-07-13

## User directive and construct boundary

The target is the official-facing version of a member that a stakeholder is likely to encounter,
not private personality. The user specifically directed that subject matter be separated from the
tone around the subject, and clarified that language such as “the darkness will consume you” is
N-relevant principally when its dramatic intensity is disproportionate to the presentation needed.

This candidate therefore measures observable public-language facets only. It may describe repeated
owned anxiety, sadness, irritability, disproportionate dramatic amplification, challenge reactivity,
composure under pressure, or episode-to-episode emotional volatility. It cannot establish holistic
Big Five Neuroticism, private affect, a clinical condition, or motive. The candidate must leave
`n_composite` null even if several facets pass.

## Frozen inputs

The first JSON block is machine-read by the harness. The one real-data look is refused if any value
differs. The four-year window is fixed to emphasize the currently encountered official persona
while retaining enough interactions for repeated-behavior tests.

```json
{
  "files": {
    "social_media.db": "21f2e9f6c13d44f5bed27cabfc9414b445ba8b0f047e88b101ac5267112ab6ec",
    "congestion.json": "ddc9d746600dbdfc60b76c54537662e19c758cbfb9d7a478a71b7bf90cd727a6",
    "fec/legislators.csv": "c5a6cbdbaae0bb19faa89852c29922809ececc70b97c149b4709588087e5e391",
    "formal_visibility_roles.json": "233a06b7fc642c6f093aae861d1664b72d0513c8771650a064b6feb698888725",
    "affective_n.json": "f3601ce9338dcbe5d222a10429fd7092c13ffcda020586ecc5f91fc484cde3ce"
  },
  "full_interview_rows": 150668,
  "window_start": "2022-07-12",
  "window_end": "2026-07-11",
  "window_rows": 57030,
  "window_members": 503,
  "window_member_package_date_keys": 36683
}
```

Only member-attributed `INTERVIEW` turns in the frozen window are used. CNN segment packages from
one broadcast are merged for episode-level reliability. Full member coverage requires at least 100
classified sentences across five episodes. A reliability half requires 50 sentences across three
episodes. The score is unavailable when those bars are not met; missing values are never imputed.

## Frozen measurement sequence

The implementation is `fec/official_persona_n_target_tone_candidate.py` in the lock commit. Its exact
regular expressions, weights, target ordering, topic ordering, backoff rules, seeds, missing-data
rules, and thresholds are part of this preregistration.

Each sentence passes through four distinct stages:

1. **Subject** — a transparent high-precision vocabulary assigns one topic and a severity level:
   acute harm or disaster/emergency (3); health, economic hardship, or public-safety harm (2);
   institutional conflict, ordinary economic policy, or family/community matters (1); general (0).
2. **Target** — language is classified as personal-owned, collective concern, empathic concern for
   others, external target, or unknown. First-person emotion is required for the owned facets.
3. **Attribution** — third-party speech reports (“he said,” “according to,” etc.) cannot increment a
   member-owned emotion or dramatic facet. A first-person emotion clause remains member-owned.
4. **Tone and proportionality** — anxiety, sadness, anger, negative evaluation, intensity,
   catastrophe, absolutist threat, and a narrow apocalyptic vocabulary are detected. Apocalyptic
   language receives the largest sentence weight. Tone is compared with leave-one-member-out
   expectations for comparable subject contexts. Target-conditioned expectations are used for
   external tone, drama, reactivity, pressure tone, empathy, and total tone. Owned emotion excludes
   target from the expectation cell so that choosing to direct emotion at oneself is not adjusted
   away. Sparse cells back off in a frozen hierarchy; each baseline needs 80 sentences from eight
   other members.

Severe subject matter raises the expected tone baseline but cannot erase unlimited amplification.
“The darkness will consume you” must trigger the apocalyptic/dramatic cue when it is the member’s
own presentation. “He said the darkness will consume you” must not increment member-owned drama.
One isolated sentence may be a strong sentence-level cue, but member-level description requires
repeated behavior and the reliability/stability bars below.

## Frozen output facets

No composite is calculated. Higher values have these meanings, except where noted:

- owned anxiety, owned sadness, and owned irritability: first-person emotion beyond comparable
  subject contexts;
- dramatic disproportionality: positive excess catastrophic/apocalyptic amplification beyond
  comparable subject, target, and program contexts;
- challenge reactivity: negative tone in explicit response-to-challenge language;
- composure under pressure: calmer language under severe subjects or challenge (higher is calmer,
  so this facet runs opposite the direction of N);
- emotional volatility: variation in residual tone across sufficiently substantive episodes;
- external negative tone and empathic concern: context-only comparison fields that can never be
  called N facets or enter an N score.

Scores are simple context-residual rates per 100 sentences, plus within-chamber z-scores for
comparability. Party, gender, volume, current formal leadership, and average subject severity are
not subtracted from member scores. They are diagnostics: a facet that remains entangled with them
is marked unavailable. This keeps the instrument close to the observed words rather than creating
a heavily residualized personality index.

## Synthetic safeguards required before the look

All frozen fixtures must pass. They include owned versus attributed dramatic language, severe
subject matter without emotional tone, owned versus collective/empathic anxiety, owned anger,
neutral policy disagreement, explicit challenge language, and leave-one-member-out immunity to a
member raising their own expected baseline. Any failure forbids the real-data look.

## Frozen evidence bars

Evidence is judged facet by facet. Every bar below is conjunctive for a facet to be available in an
official-persona description:

- at least 100 qualified members have the facet;
- median Spearman-Brown package/episode split-half reliability across five fixed salts is at least
  .60, and at least four of five splits are at least .50;
- chronological earlier/later stability across members is at least r=.30;
- maximum absolute correlation with party, gender, log sentence count, current formal-leadership
  status, or average subject severity is at most .15 after chamber standardization;
- overall context adjustment leaves absolute sentence-level severity/tone correlation at most .10
  and at most half its raw magnitude.

The result may be “some facets available” or “no facets available.” There is no threshold tuning,
feature editing, or rerun after the real look. A weak facet remains unavailable; it is not rescued
by combining it with other weak facets. The old `affective_n.json` comparison is descriptive only
and is explicitly not a validity criterion.

## Activation and stop rules

`python fec/official_persona_n_target_tone_candidate.py --look` consumes the single real-data look.
It writes `official_persona_n_target_tone_v1.json.candidate` regardless of outcome so the complete
negative or mixed result is preserved. The artifact is consumed by nothing. It may not alter live
N, profiles, ranks, UI, or narratives without a separate explicit user decision.

After the look, the complete result summary is appended below. No expert panel, paid API, audio
feature, interview-burst proxy, or private-personality claim may be introduced as a rescue route.
