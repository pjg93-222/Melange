# Official-persona perception audit: random 30 House + 10 Senate batch

Date: 2026-07-13  
Frozen outcome: **INSUFFICIENT EXTERNAL EVIDENCE**  
Claim limit: descriptive corroboration of the public/professional persona, not psychometric validation

## Bottom line

The observed comparisons are encouraging but do not support saying that the model "checks out" yet.
Fifteen of 18 evaluable directional claims agreed with independent public-persona descriptions
(83.3%; Wilson 95% interval 60.8%-94.2%). Member-macro agreement was 80.8%. The frozen coverage bar
failed because only 18 claims across 13 members were evaluable, versus the required 30 claims across
25 members. The formal result is therefore insufficient evidence, even though the conditional
agreement rate is high.

The batch found three direct contradictions:

1. **Mike Quigley, Extraversion:** model 0.919 (high) versus an independent profile describing him
   as soft-spoken and almost academic (low). His own frozen communication facets are ordinary
   excitement (0.509), ordinary activity (0.539), and low assertiveness (0.228). This is the
   clearest evidence in the batch that the top-level E slot can still be dominated by public
   exposure rather than actual outward interpersonal style.
2. **Mary Scanlon, Conscientiousness:** model 0.179 (low) versus a profile and career record showing
   sustained, organized responsibility, including leadership of large-scale pro bono work (high).
3. **Roger Wicker, Neuroticism:** model 0.051 (very low) versus one recent reported episode of
   disproportionate escalation over an administrative disagreement (high). This external N code is
   deliberately low-confidence because it rests on one incident, so it is a warning rather than a
   stable character judgment.

No production score, rank, profile, or engine input was changed in response to this audit.

## Frozen method

- Deterministic chamber-stratified random draw: the 30 smallest SHA-256 lottery hashes among House
  members and the 10 smallest among senators.
- No replacement for obscurity, source scarcity, missing model coverage, party imbalance, or
  unexpected results.
- Model scores were frozen before any external searching and not opened until the 40-person
  evidence ledger was committed.
- The same two neutral search queries were used for every member.
- At least two sources from two domains, including one independent source, were required for every
  person.
- Leadership title, interview frequency, ideology, subject matter, profanity, depression history,
  and policy severity were not trait evidence by themselves.
- Model values at or above 0.70 and at or below 0.30 made directional claims. Middle values made no
  claim and were excluded rather than counted as agreement.
- Randy Feenstra remained in the locked random sample even though the frozen display supplied no
  Big Five values.

Frozen artifact fingerprints:

- Model batch: BEC1598F12CF1482A591A692291EB154B173C7863D93DB45145790A24C9AD99C
- Blind external evidence: D0F0EEEC1ACAE48B46DD934E356D24B7B947A830883FD31A553A826E28C179FE

## Trait results

| Trait | Agreement | Wilson 95% interval | Reading |
|---|---:|---:|---|
| Extraversion | 4/5 (80.0%) | 37.6%-96.4% | Promising, but Quigley is a serious construct-level contradiction. |
| Openness | 3/3 (100%) | 43.9%-100% | All observed claims matched; far too few for a broad conclusion. |
| Conscientiousness | 1/2 (50.0%) | 9.5%-90.6% | Scanlon contradicts; coverage is too thin to support the prior confidence. |
| Agreeableness | 5/5 (100%) | 56.6%-100% | All available comparisons matched, but missing A values are extensive. |
| Neuroticism | 2/3 (66.7%) | 20.8%-93.9% | Calm cases matched; the single high-reactivity case contradicted and is low-confidence. |

The sample was 24 Republicans and 16 Democrats because the draw was not party-stratified. Exploratory
agreement was 9/10 for Republicans and 6/8 for Democrats; 7/9 in the House and 8/9 in the Senate.
Those cells are too small to interpret as party or chamber performance differences.

## Coverage is the main blocker

- Only 13 of 40 members had at least one evaluable model-versus-external comparison.
- Only five members had two or more comparisons, the minimum for a person-level verdict.
- Independent research yielded at least one directional public-persona description for 25 of 40,
  but the model was middle-band or missing on the same axes for 12 of those 25.
- Three members had no displayed value on any Big Five axis: Randy Feenstra, Gus Bilirakis, and
  David Taylor.
- Agreeableness was missing for 17 of 40 members. E, O, C, and N were each missing for three.
- Of the available model values, the number making a strong directional claim was E 21/37, O 18/37,
  C 20/37, A 12/23, and N 25/37.

This is not merely a sourcing limitation. The missing A values and three all-axis gaps are product
coverage problems. A deployable five-factor product cannot silently present incomplete factor
coverage as though all five axes were equally observed.

## All 40 members

High and low in the external column are blinded evidence codes. Frozen values are shown only for
externally directional axes. "No formal overlap" means that the corresponding model value was
middle-band or missing; it does not mean agreement or disagreement.

| Member | Ch. | Party | External directions | Frozen values on those axes | Formal result |
|---|---:|:---:|---|---|---|
| Randy Feenstra | H | R | C high | C missing | No formal overlap |
| Celeste Maloy | H | R | — | — | External evidence unclear |
| Mary Scanlon | H | D | C high; N low | C 0.179; N 0.513 | 0/1; C conflict |
| Shomari Figures | H | D | — | — | External evidence unclear |
| Morgan Griffith | H | R | O high | O 0.571 | No formal overlap |
| Aaron Bean | H | R | — | — | External evidence unclear |
| Delia Ramirez | H | D | — | — | External evidence unclear |
| Marcy Kaptur | H | D | — | — | External evidence unclear |
| Alma Adams | H | D | O high | O 0.882 | 1/1 agree |
| John Garamendi | H | D | — | — | External evidence unclear |
| Erin Houchin | H | R | — | — | External evidence unclear |
| Sam Graves | H | R | E low; C high; A high; N low | E 0.285; C 0.577; A 0.601; N 0.182 | 2/2 agree |
| Lloyd Smucker | H | R | — | — | External evidence unclear |
| Greg Landsman | H | D | A high | A 0.829 | 1/1 agree |
| Robin Kelly | H | D | C high; A high | C 0.513; A missing | No formal overlap |
| Gus Bilirakis | H | R | — | — | External evidence unclear |
| Blake Moore | H | R | — | — | External evidence unclear |
| David Taylor | H | R | — | — | External evidence unclear |
| Virginia Foxx | H | R | C high | C 0.521 | No formal overlap |
| Sean Casten | H | D | E high; O high | E 0.758; O 0.968 | 2/2 agree |
| Brandon Gill | H | R | E high; A low | E 0.317; A missing | No formal overlap |
| Terri Sewell | H | D | O high | O 0.417 | No formal overlap |
| Yvette Clarke | H | D | A high | A missing | No formal overlap |
| Gregory Meeks | H | D | A high | A 0.364 | No formal overlap |
| Gwen Moore | H | D | E high; O high | E 0.589; O 0.481 | No formal overlap |
| Scott Fitzgerald | H | R | — | — | External evidence unclear |
| James McGovern | H | D | — | — | External evidence unclear |
| Michael Simpson | H | R | A high | A missing | No formal overlap |
| Mike Quigley | H | D | E low; O high; C high | E 0.919; O 0.917; C 0.397 | 1/2; E conflict |
| James Comer | H | R | N low | N 0.374 | No formal overlap |
| Susan Collins | S | R | C high; A high | C 0.827; A 0.829 | 2/2 agree |
| Richard Blumenthal | S | D | E high; O high; C high; A high | E 0.907; O 0.532; C 0.447; A 0.548 | 1/1 agree |
| John Thune | S | R | A high | A 0.829 | 1/1 agree |
| John Kennedy | S | R | E high; O high; A low | E 0.860; O 0.415; A 0.174 | 2/2 agree |
| Ted Budd | S | R | A high; N low | A missing; N 0.346 | No formal overlap |
| Steve Daines | S | R | A high; N low | A 0.486; N 0.241 | 1/1 agree |
| Roger Wicker | S | R | N high | N 0.051 | 0/1; N conflict |
| Ron Johnson | S | R | — | — | External evidence unclear |
| James Risch | S | R | — | — | External evidence unclear |
| Katie Britt | S | R | A high | A 0.745 | 1/1 agree |

## What checks out, and what does not

### Strongest corroborations

- **Sam Graves:** independent reporting says reserved, all-work/no-show, cordial, and exceptionally
  even-tempered. The model's low E and low N directional claims both agree.
- **Sean Casten:** assertive public commentary and technical policy curiosity agree with high E and
  high O.
- **Susan Collins:** the independently reported tenacious broker style agrees with high C and A.
- **John Kennedy:** garrulous engagement and a sharp-edged rhetorical persona agree with high E and
  low A. His vivid metaphors were not automatically treated as N.
- **Alma Adams, Greg Landsman, John Thune, Steve Daines, Katie Britt, and Richard Blumenthal:** each
  had one clean directional match.

### Extraversion

The formal 4/5 result is better than feared, but it masks a structural concern. Mike Quigley's 0.919
top-level E directly conflicts with both his external soft-spoken reputation and the model's own
low-assertiveness facet. Brandon Gill's strongly attention-seeking public persona received only
0.317, while Gwen Moore's unusually expressive persona received 0.589. Those latter two are not
formal errors because the model made no directional claim, but descriptively they show weak
separation. Among externally high-E people in this batch, the mean E value was 0.686; among the two
externally low-E people it was 0.602. That small gap is exploratory, not a validation statistic.

Conclusion: the E slot is not failing universally, but it is not yet a clean measure of the warmth,
excitement, activity, gregariousness, and assertiveness construct the product intends to display.
Quigley is exactly the kind of title/exposure confound this audit was meant to catch.

### Neuroticism

The two clearly calm professional personas that made directional model claims, Sam Graves and Steve
Daines, matched low N. James Comer's even-keeled description, Ted Budd's calm behavior in a crisis,
and Mary Scanlon's poise all landed in the model's middle band and were not scored. Roger Wicker is
the only externally high-N case and the model placed him at 0.051, the opposite extreme.

Conclusion: N remains unresolved. The target-tone idea is directionally useful because it prevented
policy severity or dramatic subject matter from being mislabeled. However, one recent reactive
episode cannot establish a stable trait, and three evaluable cases cannot establish model quality.

### Agreeableness, Openness, and Conscientiousness

- A agreed in all five evaluable cases, including a low-A case (John Kennedy). That is encouraging
  for directional discrimination, but 17 missing A values make the display incomplete.
- O agreed in all three evaluable cases. External high-O descriptions for Gwen Moore, Morgan
  Griffith, and Terri Sewell fell in the middle band, not the wrong direction.
- C split 1/2 because Scanlon was placed at the low extreme. Several other externally diligent
  people landed in the middle band. The evidence does not support assuming C is already settled.

## Product decision

This batch does **not** justify a rewind, and it does **not** justify declaring the five-factor
display deployment-ready. It supports retaining the current system as a candidate while fixing
coverage and isolating the E exposure confound. The next safe product steps are:

1. Make missing factor values explicit in the UI and stop rendering them as if observed.
2. Trace why A is absent for 17/40 and why three members lack all five values.
3. Use the existing speech facets as the principal E evidence and cap or separately label the
   role-adjusted exposure component; Mike Quigley is the required regression case.
4. Keep target-conditioned N as a cautious public-reactivity score, but do not call it holistic
   Neuroticism until a larger, repeated-evidence audit resolves the Wicker-type case.
5. Re-run a newly preregistered batch only after those engineering changes and an explicit user
   decision. This completed one-look batch must not be reused to tune thresholds.

## Artifacts

- official_persona_perception_audit_prereg.md
- fec/official_persona_perception_audit.py
- official_persona_perception_batch_v1.json.candidate
- official_persona_perception_evidence_v1.json.candidate
- official_persona_perception_result_v1.json.candidate
