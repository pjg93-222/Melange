# Blind grading rubric, member personal relationships (frozen)

Frozen 2026-09-10. This file is the graded instrument. Its sha256 is recorded in
every output written by `blind_grading.py`. Editing it invalidates every label
produced under the previous hash: re-grade, do not re-use.

The rubric is assembled from four already-adjudicated lane sources and adds no
new measurement doctrine of its own:

- `outputs/member_personal_relationships/20260910_chambers_neutrality_research/RESEARCH.md`
  (measurement contract, interpretation space, neutrality rules, ritual courtesy
  vs personal regard).
- `fec/research/member_personal_relationships/CHAMBER_DEGREES_V6.md`
  (the 0-4 anchors for each dimension).
- `fec/research/member_personal_relationships/chamber_annotations.py` `DECISIONS`
  (worked grade anchors and their rationales).
- `outputs/member_personal_relationships/20260910_frozen_v5/annotation_schema.json`
  (the 13 required review keys, blinding, unknown-is-not-zero).

---

## 1. What is being measured

Directed, dated assessments of **personal affinity** and **personal friction**
supported by public evidence. These are proxies for relationships. They are not
measurements of private feelings, and they are not calibrated probabilities of
friendship.

The two dimensions are **separate**. A pair can have little of either, much of
both, or an asymmetric relationship. Either dimension may be `unassessable`
independently of the other.

Direction matters. `a_to_b` is what the first-named member's own conduct and
speech support about that member's regard for, or friction with, the second.
`b_to_a` is the reverse. Grade them separately. Evidence in which only one member
speaks supports a degree only in that speaker's direction.

**Unknown is not zero.** Absence of evidence is `unassessable`, never 0. Grade 0
is an affirmative finding of little regard (or little aversion) supported by
observation, not a default.

---

## 2. Affinity degrees (0-4)

Anchors, from CHAMBER_DEGREES_V6.md:

| Degree | Anchor |
| --- | --- |
| 0 | Affirmative evidence of little personal regard. |
| 1 | Mild personal regard. |
| 2 | Clear personal liking. |
| 3 | Strong affection. |
| 4 | Exceptionally strong personal affection. |

Worked anchors, from the `DECISIONS` rationales:

- **1** - mild personal regard: enjoyment of collaboration; contemplated visits;
  personal appreciation of collegiality inside a tribute, where the evidence
  supports mild regard more clearly than private closeness.
- **2** - explicit personal friendship or liking **without** an intimacy account:
  a specific friend nomination; "explicit personal friendship beyond a passing
  salutation, without a concrete intimate relationship account"; a years-long
  friendship and work acknowledgment; explicit friendship and social
  compatibility despite political opposition; a remembered supportive advice
  call.
- **3** - close or treasured friendship: an explicit account of a personal
  friendship; naming someone among one's closest friends in the body; personal
  faith conversations and increased closeness beyond a legislative
  acknowledgment; treasuring an enduring friendship in response to specific
  bereavement support; a decades-long friendship described while discussing
  differences.
- **4** - best friend / deeply valued: "nobody in the House is a better personal
  friend"; a best-friend description; a deeply valued condolence call to a
  parent; being entrusted with private family news; a hospital visit during
  hospitalization described as personally important; a deep personal friendship
  surviving a consequential disagreement.

---

## 3. Friction degrees (0-4)

Anchors, from CHAMBER_DEGREES_V6.md:

| Degree | Anchor |
| --- | --- |
| 0 | Affirmative evidence of little personal aversion. |
| 1 | Mild personal irritation. |
| 2 | Clear personal aversion. |
| 3 | Strong personal hostility. |
| 4 | Exceptionally intense personal hostility. |

Worked anchors, from the `DECISIONS` rationales:

- **1** - an isolated personal epithet, without a sustained confrontation with
  this target.
- **2** - a direct rebuke or bully characterization; a targeted accusation; a
  direct character accusation with described name calling; a dated
  personal-trust conflict such as accusing a colleague of deceiving colleagues
  about a promise. Stronger than policy disagreement, but no claim of persistent
  intense hatred.
- **3** - severe personal insinuation; an escalating personal confrontation that
  persists through an exchange; personalized violent imagery; a targeted refusal
  to work with a named colleague while welcoming others.
- **4** - **reserved.** Sustained, intense hostility across multiple episodes.
  A single episode, however severe, does not reach 4. If the packet contains one
  episode, 4 is unavailable.

**An isolated confrontation describes that episode.** It does not automatically
establish persistent aversion. Assign the degree the episode supports and record
the episode date.

---

## 4. Ritual courtesy versus personal regard

Both chambers regulate personal speech, and both produce ceremonial warmth that
is not evidence of private affection. Senatorial courtesy can convey admiration
or a concealed insult. House Rule XVII confines debate to the question and
directs members away from personal remarks. Therefore a courtesy baseline
applies to both chambers.

`ritual_courtesy_only` is **true** for a direction when every warm expression
cited is ceremonial floor or hearing courtesy - "my friend and colleague", a
yield of speaking time, a committee-performance thanks, a memorial or retirement
tribute, an introduction of a bill's co-sponsor - **and none** of the following
is present:

1. **Spontaneous specificity** - a concrete, unprompted detail about this person
   that a ceremonial formula would not supply.
2. **Concrete support** - a described personal act: a condolence call, a hospital
   visit, advice sought or given, a favour done.
3. **Reciprocity** - independent warmth running the other way, from a separate
   source.

When `ritual_courtesy_only` is true, **affinity is capped at 1** for that
direction. Public courtesy alone cannot separate neutral from concealed warmth
or hostility; the remaining uncertainty is recorded in the range, not in the
degree.

Courteous language whose personal meaning is unresolved stays unresolved. Do not
promote it, and do not read it as counterevidence either.

---

## 5. Degree ranges (uncertainty)

`*_range` is the range of **supported interpretations** of the relationship, with
`lo` the lowest degree the evidence still supports and `hi` the highest. It is
**not** the amount of press coverage, and it is not a confidence interval.

Two independent accounts of the same warmth can increase confidence without
making the underlying friendship closer. One very informative account can
describe a very close friendship. Repetition raises `confidence`; it does not
raise the degree.

The assigned degree must lie inside its own range. When the dimension is
`unassessable`, both range endpoints are `unassessable`.

---

## 6. Closeness and trust evidence

Separate descriptive indicators, recorded only when the cited text actually shows
them. Warmth alone does not imply intimacy.

| Indicator | Means |
| --- | --- |
| `disclosure` | Private information shared or entrusted - family news, health, personal difficulty, personal faith. |
| `personal_reliance` | One member relied on the other personally - sought advice, asked for help, leaned on them. |
| `off_duty_contact` | Contact outside official business - meals, travel, visits, socialising, contact during an illness or bereavement. |
| `concrete_support` | A specific supportive act performed - a call, a visit, a defence of the person (not the policy), a favour. |

Each indicator carries the `mention_ids` that show it. An indicator with no
citable mention must not be listed.

---

## 7. Neutral, mixed, and unknown

The interpretation space, from RESEARCH.md:

| Affinity | Friction | Supported interpretation |
| --- | --- | --- |
| High | Low | Predominantly warm |
| Low | High | Predominantly antagonistic |
| High | High | Mixed or ambivalent |
| Low | Low, with affirmative evidence and adequate observation | Neutral or emotionally distant |
| Uncertain | Uncertain | Unknown |

`neutral_assessment` is `true` **only** when all of the following hold:

1. Both degrees are <= 1 in **both** directions, and neither is `unassessable`.
2. The packet shows **repeated routine contact** between these two members.
3. That contact carries **contextual evidence of an ordinary, emotionally
   uninvested relationship**.

Silence cannot establish it. No recorded insults cannot establish it. Absence of
shared work cannot establish it. Public courtesy alone cannot establish it -
courtesy leaves private affinity unresolved, so a packet of nothing but
ceremonial warmth is `unknown`, not neutral.

If the conditions are not met but the packet is not silent either, use
`"unknown"`. `neutral_assessment` is a substantive assessment, not the default
for missing information.

`mixed_ambivalent` is `true` when affinity >= 2 **and** friction >= 2 in the
**same direction and the same period**. Warm signals from one year and hostile
signals from another may indicate **change** rather than simultaneous
ambivalence: in that case `mixed_ambivalent` is `false`, and the change is
described in the rationale with the dates.

---

## 8. Observation coverage

| Value | Means |
| --- | --- |
| `adequate` | Enough relevant encounters, across enough of the period and enough venues, to support the degrees assigned. |
| `thin` | Some relevant material, but too few encounters, too narrow a window, or a single venue. |
| `none` | No relevant encounter between these two members in the packet. |

Give a one-line basis naming the count, the span, and the venues. Extra review
effort for a quiet member should improve information; it must not mechanically
raise the relationship degrees.

---

## 9. Confidence

`low` / `medium` / `high`, describing how firmly the evidence fixes the degree -
independent of the degree itself. A confident 0 and a confident 4 are both
possible. Grade degree separately from certainty.

---

## 10. What the grader sees, and what it must never use

You see: the two members' names, the chamber context, and the packet of
encounters (date, venue, and a context window for each), plus the count of
hearings at which both appeared.

You do **not** see, and must not infer or ask for: party, state, ideology or
DW-NOMINATE, cosponsorship or any other work measure, personality or Big Five
values, any model prediction or score, any automated cue or keyword flag, and
the design stratum or sampling weight. Blinding is recorded in every output as
`reviewer_blinding: {model_scores: false, personality_values: false,
work_scores: false}`.

If your own background knowledge about these members supplies a fact the packet
does not, **do not grade on it**. The degree must be supported by cited text in
this packet. Every degree carries `cited_mention_ids`; a degree above 0 with no
citation is invalid.

---

## 11. Per-mention calibration review (encounter review)

For a single mention, decide the 13 required review keys from
`annotation_schema.json` v5, plus speech purpose. These are observations about
**this excerpt**, not about the relationship.

| Key | Type | Decision |
| --- | --- | --- |
| `speaker_verified` | bool | The excerpt establishes that the named actor is the speaker. |
| `target_verified` | bool | The excerpt establishes that the named target is who is being spoken about or to. |
| `quoted_only` | bool | The actor's words reach us only as someone else's quotation or paraphrase. |
| `content_status` | `resolved` / `unresolved` | Whether the excerpt is intact enough to decide the warmth and hostility keys. Truncation, mixed voices, or a missing referent make it `unresolved`. |
| `substantive_warmth` | bool | Personal warmth beyond ceremonial formula, per section 4. A bare "my friend" in a yield of time is **false**. |
| `personal_hostility` | bool | Hostility directed at the target **as a person**. Policy or institutional attack alone is **false**. |
| `promptedness` | `spontaneous` / `prompted` / `unknown` | Whether the remark answers a question or a ceremonial occasion, or arises unbidden. |
| `ritual_language` | bool | The excerpt uses chamber courtesy formulae. |
| `personal_act` | bool | The excerpt describes a concrete personal act between these two members. |
| `escalation` | `none` / `single_exchange` / `sustained` / `unknown` | How far a hostile exchange runs inside this excerpt. |
| `reciprocity` | bool | The target's own response appears inside this excerpt and runs in the same direction. |
| `repair` | bool | The excerpt contains an apology, a walk-back, or a de-escalating gesture. |
| `alternative_explanation` | enum | The strongest non-relationship explanation for the language: `none`, `institutional_courtesy`, `ceremonial_tribute`, `policy_dispute`, `procedural`, `constituent_or_third_party`, `other`. |

`speech_purpose` is one of `floor_debate`, `floor_tribute`, `procedural_yield`,
`hearing_question`, `hearing_exchange`, `interview_answer`, `other`. It records
the opportunity, which differs in what it makes ordinary: a routine floor
acknowledgment, a memorial tribute, a television interview, and a personal
hearing exchange are different opportunities.

Both `substantive_warmth` and `personal_hostility` may be true. Neither being
true is a normal outcome and does not mean the excerpt is defective.

---

## 12. Output discipline

- Every field is decided from the packet, not from memory.
- The rationale is <= 120 words, describes what the cited text shows, and uses no
  causal verb about a relationship the evidence does not establish.
- Cite `mention_ids` exactly as given. Never invent one.
- Return only the JSON object the schema requires.
