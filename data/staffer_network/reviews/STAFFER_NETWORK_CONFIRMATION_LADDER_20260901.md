# Staffer Network Confirmation Ladder — 2026-09-01

Author: Fable (Claude Fable 5.1), read-only measurement, glassbox run
`run-20260901T1952278368647Z-0a9157cd`.
Companion to `STAFFER_NETWORK_EMPLOYMENT_TENURE_DATA_ADJUDICATION_20260901.md`
(sha256 `11658f12…`), which ruled tenure NOT ESTABLISHED under the governing contract.
This document answers Paul's follow-up question of the same evening: can more
confirmations, including partial ones, be extracted by rule from the evidence already on
disk? Every figure below was measured this evening by streaming the on-disk ledgers; no
producer was run, nothing was promoted, nothing in the live tree was modified.

## 0. Answer

Yes, materially. Under rules the lane's own documents already imply, the evidence on disk
supports far more partial confirmation than the v3 overlay recorded, and the lane's
contract already names where such confirmations may lawfully go.

| Confirmation | Measured | What v3 recorded |
|---|---:|---|
| Hill payroll people at L4 (name-unique, office corroborated by the filer's own LDA text, chronology-consistent): House 2009Q3–2026Q1 | 1,137 of 4,392 | 3,588 House rows provisionally accepted, 2009Q3–2015Q4 only; 326 of the 678 qualifying 2009–2015 people left at `REVIEW_REQUIRED`; the 858 qualifying 2016–2026 people never adjudicated |
| Same, Senate 2011–2026 | 640 of 2,798 (470 with contiguous runs) | 125 rows provisionally accepted |
| Partial tenure cores at L4 | 2,131 House person-office spans (median 8 quarters, 78.9% contiguous, up to 10 years) and 754 Senate spans (median 4 half-years, up to 13.9 years) | 3,677 observation-only provisional episodes, all blocked |
| Filer self-attestation naming a specific member | 5,516 people; 2,535 resolve to exactly one bioguide; 2,161 corroborated by a payroll office naming the same member; 574 of those also year-consistent | parse lane: 1,878 provisional, 39,384 `REVIEW_REQUIRED` |
| Prose episodes with a resolvable office and explicit start and end years in one string | 2,525 of the 3,090 A6 near-candidates | 0 safely linked (two universal design gates) |
| People in ≥ 2 / ≥ 3 / ≥ 4 independent evidence sets | 9,388 / 4,236 / 1,081 | not measured |
| Payroll office confirmed by a profile employer string, independent of LDA text | 203 of 228 House-and-profile people; 139 of 168 Senate-and-profile people | not measured |
| Registrant side: LD-203 same-year employer equals LDA registrant | 22,715 of 22,754 people | 25,469 associations accepted at filing-year grain |
| People with both a Hill payroll observation and a dated registrant employer, in revolving-door order | 4,199 of 6,101 (1,821 overlap at year grain; 81 reversed) | not measured |

None of this becomes canonical, and none of it replaces the I-4 gold set. What it changes
is the size and honesty of the corroborated-candidate layer, and it supplies the strict
one-to-one candidates that the mathematics adjudication explicitly admits to an
exploratory tier.

## 1. Why a ladder is lawful

Three rules in the lane's own documents make rule-based partial confirmation legitimate
without touching the canonical plane:

- The math adjudication (§3) states that primary scores exclude all identity review
  candidates, and that "an explicitly exploratory score may add only strict one-to-one
  review candidates". A strict one-to-one review candidate is therefore a defined,
  admissible object, and name uniqueness on both sides is its definition
  (`canonical_facts.py:816–824`: all four multiplicity maxima equal 1).
- The priority partition's P3 instruction is "adjudicate identity with independent
  anchors, reconcile provider overlaps". An independent anchor is a second record system
  agreeing on the same person and container. The House and Senate disbursement ledgers
  and the filer's own LDA covered-position attestation are separate record systems with
  different authors; agreement between them is exactly such an anchor.
- The interval algebra (design §0A, math §6) carries observation-only evidence honestly:
  the union of observed pay periods is the guaranteed core, and the reporting period on
  each side is the envelope. A partial tenure is a first-class input, not a defect.

What the ladder is not: it is not canonical promotion, not a complete history, not an
identity finding, and not a substitute for the I-4 gold set. The I-4 sample measures the
ladder's precision; the ladder does not measure itself.

## 2. Tier definitions (reproducible rules)

| Tier | Name | Rule (all rules casefolded, whole-word) | Evidence class |
|---|---|---|---|
| L1 | Observed | ≥ 1 House or Senate payroll observation for a name-matched LDA person | official ledger, name match only |
| L2 | Name-anchored | L1 and the payroll name resolves to exactly one LDA queue person and one display name (`queue_candidate_count_for_name == 1` and `queue_display_name_count_for_name == 1`; reconstructed identically for the 2009–2015 House lane, which lacks the fields) | strict one-to-one review candidate |
| L3 | Office-corroborated | L2 and the person's own `covered_position` text contains, whole-word, the member surname parsed from the payroll office (`HON. FIRST [MIDDLE] LAST[, SUFFIX]`, `SENATOR NAME`) or a distinctive phrase from a fixed dictionary of ~80 committee and leadership office families; administrative payroll buckets never satisfy L3 | two record systems agree on person and container |
| L4 | Chronology-consistent | L3 and the last observed pay period's year ≤ the first LDA filing year + 1 | revolving-door order holds |
| L5 | Multi-source | L4 and a third source (LegiList page binding, structured or authenticated profile, Politico candidate) names the same office | three record systems agree |
| S | Split-clean (Senate) | for every office the person held, the observed semiannual periods form one contiguous run (each start = prior end + 1 day) | what `MULTIPLE_OR_REVIEW_MARKED_OBSERVATION_INTERVALS_REQUIRE_SPLIT` demands |
| R | Registrant-side dated | a post-Hill employer from LD-203, LittleSis, or FEC equals, after normalisation (casefold, non-alphanumerics to single spaces), the LDA registrant of the same year | the other end of a revolving-door path |

Partial tenure at L3 and above: core = union of observed pay periods; envelope = core
widened by one reporting period on each side (quarter for House, half-year for Senate).
The v3 rule differs from L3 in one respect: v3 required role and office corroboration
together (`INDEPENDENT_LDA_ROLE_AND_OFFICE_CORROBORATION`), the ladder's L3 tests office
only. Title text is present on 100% of payroll rows in both chambers, so a role test can
be added as a further tier; it was not measured here.

## 3. Measured yield

### 3.1 Hill payroll ladder

| Tier | House 2009Q3–2015Q4 (2,135 people) | House 2016Q1–2026Q1 (3,355) | House union (4,392) | Senate 2011–2026 (2,798) |
|---|---:|---:|---:|---:|
| L2 name-anchored | 1,685 | 2,125 | 2,878 | 1,710 |
| L3 office-corroborated (L2 ∧ office) | 678 | 909 | 1,195 | 667 |
| L4 chronology-consistent (L3 ∧ C) | 678 | 858 | 1,137 | 640 |
| S split-clean | — | — | — | 2,195 (L4 ∧ S = 470) |
| Office corroborated regardless of name uniqueness | 823 | 1,422 | 1,798 | 1,120 |
| Chronology-consistent regardless | 2,135 | 2,866 | 3,903 | 2,472 |
| Chronology-inconsistent | 0 | 489 | 489 | (2,798 − 2,472 includes unknowns) |
| None of the tests | 0 | 151 | 151 | 27 |

Notes. The 2009–2015 House lane is chronology-consistent by construction: the sealed LDA
window is 2021–2026, so every 2009–2015 pay period precedes the first filing year by at
least six years; the test is only informative for 2016 onward. Row-level, the office test
fails mostly because the person's covered-position text does not mention the office at all
(50.0% of 2009–2015 rows, 43.2% of 2016–2026 rows), not because the parse disagrees; the
covered-position field is a discovery seed and is often empty or generic.

Partial tenure cores at L4:

| | House 2009–2015 | House 2016–2026 | House combined | Senate (L4 ∧ S) |
|---|---:|---:|---:|---:|
| person-office spans | 861 | 1,270 | 2,131 | 754 |
| median periods observed | 7 quarters | 8 quarters | 8 quarters | 4 half-years |
| share contiguous | 53.3% | 96.2% | 78.9% | 100% by definition |
| longest span | 6.25 years | 10.0 years | 10.0 years | 13.9 years |

The 2009–2015 contiguity gap reflects the PDF-era extraction (missing quarters inside
spans), not employment gaps; it is a parse-coverage measure.

Against v3: v3's House rule was all-or-nothing (every accepted row carries the same four
codes; every rejected row carries the single code
`HOUSE_PAYROLL_NAME_MATCH_NOT_STRICTLY_CORROBORATED_OR_CLEAN`), so 326 of the 678
qualifying 2009–2015 people sit at `REVIEW_REQUIRED` with no record of which prong
failed, and the entire 2016–2026 lane (858 qualifying people) was never an input. The
Senate rule accepted 125 rows; the ladder reaches 640 people, 470 of them with clean
contiguous runs, which is exactly the split the v3 rejection code asked for.

### 3.2 Filer self-attestation (covered-position text)

Of 9,484 people with covered-position text (9,154 substantive by the none-like filter;
the A5a receipt says 9,152, a two-person discrepancy not traced):

| Class | People |
|---|---:|
| (a) names a specific member (`Rep./Sen./Senator/Hon./Office of` + name) | 5,516 |
| (b) names a committee | 2,197 |
| (c) names an agency or executive office | 1,065 |
| (d) generic Hill title only, no office | 682 |
| (e) explicit "none" | 370 |

Resolution of class (a) against the congress-legislators roster (current + historical,
5,852 surnames): exactly one bioguide 2,535; ambiguous 2,536 (1,201 surname collisions
the first name could not break; 1,335 people who cleanly name two or more different real
members across a multi-office career); surname not in roster 445. A ~40-entry nickname
table moves 44 people into "resolved" and loses a few to new collisions (net 2,533); the
mechanism is real, the scoping is not yet worth it.

Year tokens against roster service years (resolved people with a year token, 684):
consistent 584, inconsistent 100.

Payroll cross-check: 2,623 of the 5,516 also appear in a payroll lane; 2,161 have a
payroll office containing the text-named surname; 574 of those also carry a year token
inside that payroll row's observed service years. That is the filer's own attestation
corroborated by an official ledger, the strongest two-author agreement the corpus holds.

### 3.3 Prose episodes (A6 near-candidates)

The A6 generation blocks all 3,090 near-candidates on two universal reasons
(`DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE`, `ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED`),
present on every row by design; the content-specific reasons are minorities (ambiguous
abbreviation 693, no closing year 311, review flag 306, generic title 230, two-digit year
152, overlap 36, reversed 5). Every row already has exactly one role, one office mention,
and one date range (`filter_funnel.exact_one_role_one_office_one_date_range: 3090`).

| Content of the 3,090 | Rows |
|---|---:|
| office mention is a member office or committee | 2,816 |
| both explicit start and end year | 2,779 |
| both of the above | 2,525 |

Representative row: "Regional Director to U.S. Senator Bill Nelson (2001-2002)". A
stricter same-string binding rule (role, office, and date range must sit in one
sentence, years explicit, no abbreviation flags) would release about 2,525 filer-asserted
episodes at year precision. They remain filer-asserted, single-author, uncorroborated
until crossed with payroll; the subset whose member also appears in the same person's
payroll rows is the natural first cut and was not measured.

### 3.4 Multi-source overlap

People-level sets: HOUSE 4,392 (both lanes); SENATE 2,798; LEGILIST page-bound 10,691;
POLITICO candidates 412; PROFILE (structured, rapid, or authenticated employment) 912;
covered-position text 9,484.

| Intersection | People |
|---|---:|
| HOUSE ∩ SENATE | 1,089 |
| HOUSE ∩ LEGILIST | 3,905 |
| SENATE ∩ LEGILIST | 2,165 |
| HOUSE ∩ POLITICO / SENATE ∩ POLITICO | 298 / 215 |
| HOUSE ∩ PROFILE / SENATE ∩ PROFILE | 228 / 168 |
| (HOUSE ∪ SENATE) ∩ covered-position text | 3,536 |
| (HOUSE ∪ SENATE) ∩ LEGILIST ∩ text | 3,477 |
| in ≥ 2 / ≥ 3 / ≥ 4 / ≥ 5 / all 6 sets | 9,388 / 4,236 / 1,081 / 139 / 9 |

Profile employer strings (from the working-history, rapid structured, and authenticated
ledgers) name the payroll office for 203 of the 228 House-and-profile people and 139 of
the 168 Senate-and-profile people. This is a cross-source office confirmation that does
not depend on LDA text at all.

The 1,089 people matched in both chambers are either bicameral careers or name
collisions; the ladder does not distinguish them and neither should anyone without the
gold set.

### 3.5 Registrant side

| Source | People | Dated | Bounded | Corroborated by another source |
|---|---:|---:|---:|---:|
| LDA registrant association | 25,340 (25,272 with one registrant; spans 1–6 filing years) | filing-year grain | — | 22,773 |
| LD-203 affiliations | 22,754 | filing-period grain | — | 22,715 same-year name-equal; 2,321 extend the LDA span (269 earlier, 2,121 later); 0 introduce a new employer |
| FEC employer observations | 37 | point | — | 36 same-year |
| LittleSis positions | 3,907 | 34.8% | 14.3% | 479 registrant matches; 82 Hill-member rows agree with a payroll office |

Minimum evidence for a revolving-door path (a Hill payroll observation plus a dated
registrant employer): 6,101 people. Hill span ends before the registrant span starts for
4,199 (68.8%); the spans overlap at year granularity for 1,821 (29.9%); 81 are reversed.
The overlap class is where name collisions and same-year transitions mix; it is a
down-tier signal, not evidence either way.

## 4. What the ladder changes, and what it does not

Changes:
- The corroborated-candidate layer grows from the v3 figures (3,588 House rows, 125
  Senate rows, 1,186 provisional people) to about 1,137 House and 640 Senate people at
  L4 with measured partial tenure cores, plus 2,161 filer-attested offices corroborated
  by payroll, plus about 2,525 year-precision prose episodes if the same-string rule is
  adopted.
- Each rejection becomes decomposed: which prong failed (name, office, chronology,
  split), instead of one undifferentiated code. That is what makes the P3 queue
  workable.
- The strict one-to-one population (L2: 2,878 House, 1,710 Senate, overlap not computed)
  is exactly what the math adjudication admits to an exploratory temporal tier.
- The I-4 gold sample can be stratified by tier, so precision is measured where it
  matters (L3/L4) and where it is weakest (L1, overlap class).

Does not change:
- Canonical promotions stay at zero. The governing gates are unchanged; the ladder is a
  candidate-plane overlay.
- Precision is unmeasured. The rules were written and run this evening; two defects were
  found and fixed during the run (an em-dash row-continuation artifact in House office
  strings; middle-initial punctuation fragmenting one tenure into two spans). Only the
  I-4 sample can say what share of L4 is right.
- The v5 verdict stands. The ladder would have reached most of v5's 2,672 people by a
  different road, with the prongs recorded; it does not retroactively license v5.
- No influence, access, or predictor language attaches to any of it (metrics I-15).

## 5. Proposed build (Paul-gated)

A tiered corroboration sidecar, v4-class, immutable, twin-verified, consumed by nothing
until ruled:

- Inputs (all already on disk): both House payroll lanes, the Senate lane, the
  employment-lookup queue, the LegiList bindings, the three profile ledgers, LD-203, the
  A6 near-candidates, the congress-legislators roster.
- Output per person-office: tier (L1–L5, S, R), core and envelope intervals, evidence
  digests per prong, rule version; a receipt with per-tier counts and the prong-failure
  distribution; a `FILER_ASSERTED_YEAR_EPISODE` candidate class for the A6 same-string
  releases, year precision, single-author.
- Gates preserved: zero canonical promotion; no model labels gold; every row keeps
  `REVIEW_REQUIRED` semantics; language lint.
- Two lawful consumers, each its own ruling: (1) the I-4 gold sample, 200 pairs
  stratified by tier, labelled by Paul or a named delegate; (2) the exploratory temporal
  tier over L2 and above, labelled exploratory, primary weights untouched.

Rulings needed: T-8 authorise the sidecar build; T-9 whether the exploratory temporal
tier is computed at all; T-2 (from the adjudication) the I-4 owner. T-5 (fold the
2016–2026 House lane) is subsumed by T-8.

## 6. Receipts

Inputs (paths relative to the live tree unless stated):

| Artifact | SHA-256 or count |
|---|---|
| `audits\staffer_network\house_sod_pdf_lda_name_matches_2009Q3_2015Q4_20260831_generation2_personnel_only\house_sod_pdf_lda_name_match_candidates.ndjson.gz` | `1083fdeb0e1b5ccaf95cf8b32923df64c99228c75a97d519bf6bad04abaac64d`, 32,103 rows |
| `audits\staffer_network\lda_house_payroll_matches_2016_2026\lda_house_payroll_match_candidates.ndjson.gz` | `9d6634ec635ea85ed22680ede08d2d98e6dd2695cea124dcf7b2d5353df227c1`, 1537939 bytes, 11,788 rows |
| `audits\staffer_network\lda_senate_payroll_matches_2011_2026_v1\lda_senate_payroll_match_candidates.ndjson.gz` | `e08d1e1b6c642d452db67d073ce2d15a2b209124e1a49bb97bf33cd2060d3b20`, 1148518 bytes, 6,953 rows, 2,798 people |
| `AppData\Local\Melange\staffer_network\employment-lookup\generation-20260831T050000Z\employment_lookup_queue.ndjson.gz` | `5e240a91a21e237525547eef84456daee7dd5339723073ced9437a9f5ea5f649`, 25,340 rows |
| `audits\staffer_network\employment_adjudication_generation_20260901_v3_primary\candidate_adjudication_decisions.ndjson.gz` | `157451540b421a06ac5340b58b68311f82a99d7be05de0c2c64f1badd79fade2`, 235,454 rows |
| `audits\staffer_network\a7_machine_local_source_inventory_20260901_primary\a7_ld203_affiliation_candidates.ndjson.gz` | `bdcd2452afeb6b8f12457e1ef61dcf9e7c6785994ebebb1dc50d1e3688f1fbb2`, 143,513 rows |
| `audits\staffer_network\a7_machine_local_source_inventory_20260901_primary\a7_fec_employment_observation_candidates.ndjson.gz` | `6f67f0d8c731277a761ad0d18ad1610e57d21d371dfc38f5a84982ed9063db35`, 979 rows |
| `audits\staffer_network\lda_conservative_bounded_episode_candidates_20260901_b\` (byte-identical to `_a`) | 3,090 near-candidate rows, receipt status `BLOCKED_SAFE_LINKAGE_NOT_ESTABLISHED` |
| `data\staffer_network\reference\congress-legislators\` `legislators-current.yaml` + `legislators-historical.yaml` | 12,768 legislator-term entries, 5,852 surnames |

Measurement scripts and machine-readable tallies (reproducible, read-only):
`build_ladder.py` / `ladder_house.json`, `ladder_senate_multisource.py` /
`ladder_senate_multisource.json`, `ladder_registrant.py` / `ladder_registrant.json`,
`part_a.py`, `part_b.py` / `ladder_cp_a6.json`, `house_2016_join.json`. Placed alongside
this document under `data\staffer_network\reviews\confirmation_ladder_20260901\`.
