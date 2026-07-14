# Official-persona external-perception audit v1

STATUS: LOCKED (2026-07-13, committed before external source collection and before model-score
unblinding for the selected sample)

User directive: "Now I want you to take a random batch of 40 people, 30 representatives and 10
senators, and see how they compare to real world perceptions."

## Scope and claim limit

This is a descriptive corroboration audit of the official/public persona presented by the current
member desk. It is not a self-report, informant panel, clinical assessment, or psychometric
validation. News and profile descriptions are selective public narratives. No result from this
audit can promote, demote, reweight, or wire a trait, behavioral disposition, engine input, rank,
or narrative without a separate user decision and, where applicable, a new preregistered study.

The audit tests whether clearly directional displayed Big Five readings generally agree with
independent descriptions of the professional version of the member a visitor is likely to meet.
It does not test private personality. The operational E slot remains role-adjusted public exposure,
not intrinsic Extraversion; that limitation travels with every E result.

## Inputs pinned before evidence collection

- Git HEAD: `1247281baba396dce1e53432ffddc0bb196c8ce6`
- `member_desk_bundle.json` SHA-256:
  `33F0C4305F07FCA24AEF3098FEB47633E1AEC3FD7880617D5FE7180EA367147A`
- `big5_blue_validated.json` SHA-256:
  `876BC2ECF8672477D586F3DB34472CDB2CF61EE0573E30C4B909448CD0970A8F`
- `communication_style.json` SHA-256:
  `AE834225B135B497E367977B305F2504FED6AD4AD50488033CFBB7A817E14009`
- Eligible roster: 433 House, 100 Senate.

## Random sample, frozen before model-score inspection

Seed string: `official-persona-perception-audit-v1|20260713`.

For every member, compute SHA-256 of `seed|chamber|canonical name`; select the 30 smallest hashes
within the House and the 10 smallest within the Senate. No replacement is permitted for obscurity,
source scarcity, party imbalance, office, recognizability, or unexpected model values.

House: Aaron Bean; Alma Adams; Blake Moore; Brandon Gill; Celeste Maloy; David Taylor; Delia
Ramirez; Erin Houchin; Greg Landsman; Gregory Meeks; Gus Bilirakis; Gwen Moore; James Comer; James
McGovern; John Garamendi; Lloyd Smucker; Marcy Kaptur; Mary Scanlon; Michael Simpson; Mike Quigley;
Morgan Griffith; Randy Feenstra; Robin Kelly; Sam Graves; Scott Fitzgerald; Sean Casten; Shomari
Figures; Terri Sewell; Virginia Foxx; Yvette Clarke.

Senate: James Risch; John Kennedy; John Thune; Katie Britt; Richard Blumenthal; Roger Wicker; Ron
Johnson; Steve Daines; Susan Collins; Ted Budd.

The companion script freezes the selected members' current E/O/C/A/N percentiles and supporting
behavior/communication fields into `official_persona_perception_batch_v1.json.candidate`. The
freeze command prints names/counts only, never scores. External coding must be completed and frozen
before the scoring command is run.

## External-source protocol

Use the same two neutral searches for every member, with no model trait or direction in the query:

1. `"<name>" Congress profile colleagues temperament working style`
2. `"<name>" lawmaker profile biography style`

At least two eligible sources from two different domains are required per person, including at
least one independent source. Preferred evidence is an attributed description by colleagues,
staff, opponents, or a reputable journalist about professional temperament or working style.
Official biographies may supply background as a second source but cannot independently establish a
trait. Campaign copy, member press releases, unsourced social posts, and the speech/interview corpus
used by the model cannot establish a direction. No source is selected because it agrees with the
model. Contrary and ambivalent descriptions are retained.

No member is replaced if the source floor cannot be met. That member remains source-insufficient.

## Blind external coding rubric

Code each trait `+1` high, `-1` low, or `0` unclear/ambivalent. Every nonzero code must cite at
least one eligible independent source.

- E: high only for explicit outgoing, gregarious, energetic, socially forceful, or unusually
  public-facing professional style beyond title obligation; low for quiet, reserved, private,
  understated, or socially withdrawn style. Mere interview frequency or leadership office is not
  external evidence of intrinsic E.
- O: high for broad curiosity, intellectual exploration, unconventionality, or cross-domain
  interest; low for unusually narrow, rigid, conventional, or novelty-resistant style. Ideology by
  itself is not O.
- C: high for disciplined, prepared, meticulous, organized, persistent, or reliable working style;
  low for disorganized, inattentive, erratic, or unreliable work habits. Electoral success or long
  tenure alone is not C.
- A: high for warm, courteous, conciliatory, collaborative, or relationship-oriented interaction;
  low for abrasive, hostile, combative, contemptuous, or needlessly confrontational interaction.
  Bipartisan voting or cosponsorship alone is not interpersonal A.
- N: high for visibly reactive, anxious, volatile, catastrophizing, or disproportionate negative
  emotional presentation; low for calm, even-tempered, unflappable, or unusually composed public
  presentation. Policy severity, profanity alone, depression history, and clinical inference are
  excluded.

The evidence artifact must contain the source metadata, a neutral external summary, the coded
directions, and the exact source IDs supporting each code. It contains no model values.

## Model claims and comparisons

The scoring script is fixed in the same commit as this prereg. Model values at or above the 70th
percentile make a high directional claim; values at or below the 30th make a low claim. Values in
the middle 30th-70th band make no directional claim and are excluded, never counted as agreement.
An external `0` is also excluded. A comparison agrees only when both nonzero directions match.

Person verdicts require at least two evaluable axes: more agreements than disagreements = `match`;
more disagreements = `mismatch`; a tie = `mixed`. Fewer than two = `thin_external_overlap`.

Primary statistics:

- micro directional agreement across all evaluable trait claims, with Wilson 95% interval;
- member-macro agreement, giving each member equal weight;
- mismatch rate among members with at least two evaluable axes;
- trait-specific agreement, with an alert when any trait has n >= 6 and agreement below 50%;
- coverage by chamber and party, reported descriptively only.

Supporting behavior/communication facets are frozen as secondaries for interpretation only. They
cannot rescue a Big Five disagreement or ground an accuracy claim.

## Frozen outcome tiers

- `INSUFFICIENT EXTERNAL EVIDENCE`: fewer than 30 evaluable trait claims or fewer than 25 members
  with at least one evaluable comparison.
- `CHECKS OUT DESCRIPTIVELY`: coverage floor met; micro and member-macro agreement both at least
  65%; mismatch rate no more than 25%; and no trait-level alert.
- `DOES NOT CHECK OUT`: coverage floor met and either micro or macro agreement is below 50%, or the
  member mismatch rate exceeds 40%.
- `MIXED`: every other covered outcome.

These are audit communication tiers, not validation bars. Whatever the outcome, the report must
name the strongest matches, clearest contradictions, trait-specific weak points, source-coverage
limitations, and the E construct caveat. No thresholds, sample members, source rules, coding rules,
or consequence language may change after this lock.

## One-look discipline

External evidence is collected and frozen without opening the model values in the batch artifact.
Then `python fec/official_persona_perception_audit.py --score` is run once. Its output is appended
verbatim under a newline-anchored `RESULT-PERCEPTION` heading in this file during the same session.
Any malformed evidence or fingerprint mismatch refuses the look without consuming it. Exploratory
secondary summaries are labeled as such and cannot change the frozen outcome.

## ADDENDUM 1 (2026-07-13, PRE-LOOK; sample, bars, source protocol, and consequences untouched)

The first freeze attempt refused before writing an artifact because one locked random-draw member,
Randy Feenstra, has no five-axis Big Five display row. No score was printed or inspected and no
external evidence had been collected. The sample's no-replacement rule controls: the freeze utility
now retains any such member with five explicit null model values. The member remains in the 40-person
source audit but contributes no directional comparison unless a pinned model value exists. This is
a machinery/coverage correction only; no sample member, threshold, rubric, outcome tier, input
fingerprint, or one-look consequence changed.

## RESULT-PERCEPTION

official_persona_perception_result_v1.json.candidate: INSUFFICIENT EXTERNAL EVIDENCE; 18 claims across 13 members; micro 0.833 macro 0.808
