# Stance pipeline integrity contract

This document describes the production rules enforced from raw media and bill
evidence through the network dashboard and member desk.

## Code divergence (2026-10-04)

Added on 2026-10-04 to record where the code has moved past this contract.
The text below this section is unchanged since commit `e3d2923d0`
(2026-07-15). Checked against Melange `main` at `4a81d5022`; only the points
listed here were re-checked. Copies of this file with the same text sit in
the Melange live tree and in the Mentat checkout. The Mentat branch,
`codex/mentat-crypto`, has its merge base with `main` at `78ef3488f`
(2026-07-28): it holds items 1 and 2 but none of items 3 to 6.

1. Path J (provenance only: the code matches the say-do rule below). Commit
   `2636444e6` (2026-07-08) extended the say-do gate with paths V and J; J
   credited a Chair or Ranking seat on a committee of jurisdiction over a
   gatekeep category (`GATEKEEP_JURIS`, marked USER-RATIFIED 2026-07-08).
   J is in the code at `d66da46ac` (2026-07-14) and gone from its child
   `e3d2923d0` (2026-07-15), the commit that added this document. That
   commit's message says it captured another session's uncommitted work as
   the working base at Paul's direction. No ruling to drop J was found in
   that message, in any commit message on `main`, or in the brain's
   DECISIONS, DEADENDS, CONSTRAINTS or STATE. The code has paths A and V
   only (`fec/moneyball_core.py:624-625`, `:747-763`; kernel check
   "committee title does not substitute for action",
   `fec/tests/run_tests.py:224`).
2. Champion crown and the aggregate say-do check. Commit `391a4a8b5`
   (2026-07-16) made overall Champion a display crown instead of a score
   band: the scored overall ladder tops out at Ally, and the crown went to
   every Tier-1 member of the display-tier policy. The overall-Champion
   check in "Say-do rule" no longer vetoes that crown. The check still
   runs, but its result changes no label: it is recorded as
   `gate.overall_capped` in `category_stance.json`
   (`fec/stance/per_category_stance.py:119-122`, `:174`).
3. Curved label domains. Since commit `b4801b172` (2026-08-03, an
   agent-created checkpoint of in-flight work), four declared domains take
   their labels from a curve: Member Business Lending, Mortgage & Housing,
   Charter Modernization and Technology & Emerging. There the fixed bands
   are applied to the tie-aware midrank CDF of the adjusted score, with
   positive and negative evidence curved separately; raw and adjusted
   scores are unchanged (`fec/stance/stance_rules.py:28-33`, `:92-142`;
   `fec/stance/per_category_stance.py:78-83`). The rule that no percentile
   changes a label therefore holds only outside these four domains. Scale
   id: `fixed-bands-with-declared-signed-empirical-curves-v3`.
4. Board crown and displayed labels. Since commit `e3e5ece7c` (2026-09-16;
   brain decision D-031) the crown is the active primacy board's top 13
   (`fec/moneyball_core.py:565-579`), and a top-13 member without a
   qualifying action stops the honors publication
   (`fec/stance/overall_stance_policy.py:172-173`). Every other member gets
   the analytic overall band (`fec/moneyball_core.py:519-521`). The
   dashboard and member desk show this crowned band as the overall label
   (`OVERALL_LABEL=analytic`, the default;
   `fec/surfaces/dashboard_honors.py:18-36`,
   `fec/surfaces/make_member_desk.py:2631-2665`); in the bundles published
   on 2026-10-01 exactly the board's 13 show Champion on both. Their
   per-domain labels are rank-honors recognitions
   (`fec/stance/RANK_HONORS.md`; projection added in `296f40e2b`), not the
   labels this contract describes, which remain the stance input in
   `category_stance.json`.
5. Fail-closed cell gate. Commit `742b68aec` (2026-09-16; it records an
   earlier live edit) removed the cell gate's fail-open return. An empty
   accepted-evidence map now caps every Champion/Defender cell without a V
   path (`fec/moneyball_core.py:747-763`), and the corroboration loader
   raises on a missing or invalid source instead of disabling the gate
   (`:648-721`). Only the aggregate check in item 2 still fails open on an
   empty map (`:786`, `:798`); the kernel pins both halves
   (`fec/tests/run_tests.py:255-264`). The commit left this asymmetry open
   for Paul (O-A1-1), and the brain records no ruling on it.
6. Cross-posts. Since commit `a0c45a709` (2026-09-16; brain decision D-034)
   an exact cross-post duplicate is scored under its own sign, and the desk
   notes `also posted on <platform> <date>` instead of marking it not
   scored. A link-only post, with no text left once the URL is removed,
   still does not score. `CROSSPOST_DEDUP` defaults to off
   (`fec/stance/build_media_blend.py:45-47`,
   `fec/surfaces/make_member_desk.py:259`, `:295`); `CROSSPOST_DEDUP=1`
   restores the exclusion.

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
