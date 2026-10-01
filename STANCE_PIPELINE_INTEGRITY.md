# Stance pipeline integrity contract

This document describes the production rules enforced from raw media and bill
evidence through the network dashboard and member desk.

## Fixed stance scale

Every policy domain uses the same score bands. No category median, IQR,
percentile, positive rate, or neutral-band tertile changes a label.

| Score | Offensive domain | Defensive domain |
|---:|---|---|
| `>= 0.70` | Champion | Defender |
| `>= 0.35` | Ally | Ally |
| `>= 0.25` | Highly Persuadable | Highly Persuadable |
| `>= 0.15` | Persuadable | Persuadable |
| `>= 0.05` | Lean Persuadable | Lean Persuadable |
| `>= -0.05` | True Neutral | True Neutral |
| `>= -0.15` | Lean Skeptic | Lean Skeptic |
| `>= -0.35` | Skeptic | Skeptic |
| `>= -0.70` | Highly Skeptical | Highly Skeptical |
| `< -0.70` | Opponent | Opponent |

No evidence is an em dash, not Neutral. Legislation uses one fixed square-root
scale (`2.0`) and media uses one fixed blend scale (`1.0`) across all domains.
Only sources actually present in a member-domain cell enter its weighted
denominator, so incomplete press collection does not dilute valid sponsorship.

## Exceptional-performance rounding

For a scored domain, other domains with an absolute raw score of at least
`0.70` contribute five percent of their signed mean, capped at `+/-0.05`.
This can resolve a near-boundary score in either direction. It cannot create a
score in a domain with no evidence. Raw scores and per-cell factors are retained
in `category_stance.json`. The overall tier also receives a bounded `+/-0.05`
nudge based on the balance of exceptional Champion/Defender versus Opponent
domains; this is enough to resolve a near boundary but not jump a full band.

## General Credit Union media

Item text is first routed through the shared subject-word rules. Residual
General Credit Union evidence is then allocated to at most four non-defensive
domains in proportion to that member's demonstrated subject profile. If no
profile exists, it is split across Examination & Supervision, NCUA Budget &
Insurance, Charter Modernization, and Field of Membership. The signed amount is
conserved and its member-by-member allocation ledger is embedded in
`category_stance.json`.

## Say-do rule

A Champion/Defender domain must be backed by either sponsored/original-
cosponsored legislation in that domain or a recorded CU-aligned final-passage
vote. Committee jurisdiction is not an action signal and cannot preserve a top
tier. An overall Champion must additionally have A/V evidence in at least two-
thirds of at least six raw top-tier domains supporting the aggregate. This
prevents one exceptional domain from becoming an overall Champion. A fixed,
non-curve follow-through check also caps prolific direct sponsors (at least 10 CU bills)
when no more than 20 percent advanced past introduction. This preserves credit
for incomplete sponsorship while preventing a repeated introduced-only paper
trail from manufacturing the exceptional overall Champion label.
Both cell and aggregate caps lower only to Ally, preserve the raw tier and
evidence denominator in `category_stance.json`, and fail open if the authorship
source is unavailable.

## Influence bonus

The additive positional term is restricted to current chamber or party elites
listed in `formal_visibility_roles.json`. A listed party elite who is also a
committee or subcommittee Chair or Ranking Member receives no additive term,
because that authority is already measured in the workbook's base committee
score. The rank authority records the nominal term, applied term, office,
eligibility reason, and committee overlap for every member.

## Identity and visibility

Member joins accept an exact/normalized name, a unique first-initial plus last
name, or a bioguide match. Ambiguous surnames fail closed and appear in the
unmatched audit; the resolver never chooses the first roster row.

The member desk displays both tracked press and related verified social posts.
Exact cross-post duplicates remain visible but are marked as not scored. The
integrity report records all media and bill source rows, displayed unique bills,
rule-based exclusions, unmatched identities, and collapsed duplicate role/topic
rows. `dashboard_exclusion_reconciliation.json` enforces an exact equation for
each source: every row must be displayed or assigned one explicit routing or
exclusion reason; any unexplained difference stops dashboard generation.

## Regeneration safeguards

The canonical pipeline order is media blend -> stance -> rank authority ->
workbook stance view -> downstream engines -> dashboards. Generated JSON, HTML,
and the two production workbook writes use verified atomic replacement.

Before the member desk is written, the preflight requires identical 533-member
rosters across the canonical roster, workbook, stance matrix, score matrix,
network bundle, and desk source. It also verifies category width, stance-string
width, bioguide non-conflict, and General CU conservation. The postflight writes
`dashboard_integrity_report.json`; identical input fingerprints must reproduce
the same semantic bundle hash.
