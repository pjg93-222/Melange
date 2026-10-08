# Bill-recall culling proposal — Opus 5 lane, 2026-07-28

`run_id: bill_recall_culling_opus5_20260728a`
**Status: PROPOSAL ONLY. Nothing integrated, promoted, scored, or recomputed.**

Every row in every output carries `automated_final_decision: false` and
`human_ratification_required: true`.

---

## 1. Coverage identities — all proven

| identity | value | proven |
|---|---|---|
| discovery records | 18,557 | yes |
| legacy recall floor rows | 465 | yes |
| legacy rows present in discovery | 442 | yes |
| legacy rows absent from discovery | 23 | yes |
| absent set == frozen receipt's 23-key list | — | yes |
| legacy canonical keys unique (no dupes) | 465/465 | yes |
| legacy accounting states sum to 465 | — | yes |
| proposal rows | 23, unique, == absent set | yes |
| Quorum recall floor rows | 44 | yes |
| Quorum rows present in discovery | 44 (0 fail-closed) | yes |
| Quorum distinct canonical keys | 44, no duplicates | yes |

Legacy citations were translated to canonical keys by measure-type mapping only
(`H.R.` → `hr`, `H.J.Res.` → `hjres`, …); 465/465 parsed, 0 errors, 0 collisions.
Quorum rows were keyed from their own `Source Link` congress.gov URLs, not from
the free-text label.

## 2. Accounting partition of all 465

| state | count |
|---|---|
| `covered_in_discovery` | 442 |
| `include_candidate` | 6 |
| `exclude_false_positive` | 2 |
| `flagged` | 15 |

All 44 Quorum rows: `covered_in_discovery`. None was used as disposition
evidence; each row records `recall_evidence_only: true` and
`disposition_assigned_from_quorum: false`.

## 3. The 23 absent measures — what the evidence actually was

These 23 are **not hypothetical additions**. All 23 are live in the scoring
archive today: 287 rows, 179 of them selected contributions. This is a
correction proposal against a live plane.

The lane holds **no official summary and no operative bill text for any of the
23**. All 23 lack a BillStatus receipt (that fetch covered 14,854 discovery
bills), lack a GovInfo object (all eight runs are scoped to the same 18,440
jobs), and lack a discovery record; the historical probe ledger records all 23
identifiers as outstanding with `probe_collected: false`. So
`operative_text_reviewed` is `false` on every row, and step 1 of the review
order — the official title — plus official committee referral is the whole
official surface, save two CRS summaries.

A 225,572-file read-only sweep across the repository and the recovered input
root confirmed there is no further local holder (`_local_evidence_sweep.json`).

### include_candidate — 6

**Small LENDER Act** — `117:hr:6732`, `117:s:4004`, `118:s:1159`
→ `member_business_lending` + `cfpb_issues_structural_reform` (legacy MBL
**retained**, CFPB **added**). Confidence high.
The official long title states the operative effect: *Small Lenders Exempt from
New Data and Excessive Reporting Act*, i.e. exemption from the CFPB
small-business-lending data collection under Dodd-Frank §1071 — a rule for which
credit unions are covered financial institutions. Corroborated **inside the
north-star corpus itself**: the same bill family in other Congresses
(`118:hr:1806`, `119:hr:941` — same sponsor, same official title) is already held
in discovery under `member_business_lending` and `cfpb_issues_structural_reform`,
and discovery routes CFPB §1071 Regulation B rule disapprovals (`118:hjres:50`,
`118:sjres:32`) to `member_business_lending`. ACU's own advocacy record files
§1071 as both Consumer Protection (letter 1591, S.557) and Lending (letter 3441,
the CFPB §1071 rule). Sponsor press in the trusted cache states the operative
effect and records a CUNA endorsement.

**CFPB Regulation Z Buy Now, Pay Later rule disapprovals** — `118:hjres:190`,
`118:hjres:195`, `119:sjres:134`
→ `cfpb_issues_structural_reform` + `credit_card_consumer_fee_mandates`
(**category corrected** from the legacy `Payments`). Confidence medium-high.
The official title is dispositive of subject: CRA disapproval of a CFPB rule
under *Truth in Lending (Regulation Z); Use of Digital User Accounts to Access
Buy Now, Pay Later Loans*. America's Credit Unions filed its **own comment
letter on that exact rule** (letter 1126, 2024-07-31), classified by ACU under
its **Consumer Protection** issue area — which establishes the credit-union
policy nexus and places the measure in the outline's Consumer Protection
section, not Payment & Technology. The legacy `Payments` label is affirmatively
unsupported: the north-star Payments boundary is real-time payments, FedNow,
instant payment fraud, payment system access, ACH payment, faster payments and
payment stablecoin. The legacy retrieval URL preserved in the archive shows the
measure was pulled in by a *legacy* Payments query carrying a loose
`"buy now pay later"` term that the outline-derived Payments query does not have
— a query-scope defect, not a category truth. Discovery routes CFPB rule
disapprovals by the rule's subject (Regulation Z credit card penalty fees →
`credit_card_consumer_fee_mandates` at `118:hjres:121`, `118:sjres:70`), and
holds the identical withdrawal-form construction at `119:sjres:167`.

### exclude_false_positive — 2

**National Small Business Week resolutions** — `117:hres:634`, `117:hres:1076`.
Confidence high. These are the only two of the 23 for which a genuine official
CRS summary is held, and it states the measure's complete operative content: the
resolution celebrates small businesses and supports the designation of National
Small Business Week. A simple House resolution expressing support for a
commemorative designation has no operative policy effect on any regulated
institution, so it cannot fall inside any of the nineteen policy categories —
affirmative official evidence of falling outside, not mere absence from
discovery. Independent prior art agrees: the 2026-07-24 legislative audit named
these two among the bills with no credit-union nexus on their face, a finding
that survived adversarial review.

These two are also **the largest scoring artifact in the group**: 93 of the 179
selected contributions across all 23 keys, under Member Business Lending.

### flagged — 15

Twelve Small Business Act / SBA-program measures (Small Business Child Care
Investment Act ×5, Service-Disabled Veteran Opportunities in Small Business Act
×2, Heroes Business Opportunity Act ×2, Veteran Entrepreneurship Empowerment
Act, Unlocking Opportunities in Emerging Markets Act, Keeping Our Promise to
Small Businesses Act) and three consumer-credit measures (Small Business Credit
Protection Act ×2, Protecting Consumer Information Act).

For each, the official review order stops at the title. Nothing affirmatively
establishes a material credit-union nexus, so they cannot be proposed for
inclusion. Equally, nothing affirmatively establishes that they fall outside all
nineteen categories, so they cannot be culled:

- Committee referral to the Small Business committees is **not** disqualifying —
  America's Credit Unions files its own advocacy under the outline's Lending
  section with those same committees (letters 341, 346 on SBA oversight; 3416 on
  a veteran-entrepreneurs hearing).
- The MBL boundary carries veteran-specific identifiers (`MBL veteran`,
  `exempt loan credit union veteran`) because the outline's flagship MBL bill is
  the Veterans Member Business Loan Act, so the veteran small-business measures
  sit in the exact near-miss neighbourhood.
- `117:s:63`'s underserved/emerging-markets subject plausibly overlaps the CDFI
  Fund boundary (minority depository institution, MDI, underserved community
  lending).
- `117:hr:474` is referred to **House Financial Services**, so it does reach
  financial institutions, and its consumer-information subject plausibly falls
  under Data Privacy & Cybersecurity rather than the legacy Fraud Prevention.
  It is the strongest inclusion candidate among the flagged rows.
- Absence from discovery is neutral by rule and was not used as exclusion
  evidence anywhere.

A mechanical north-star term test over the official title+summary surfaces
returned **zero hits for all 23**, including the six proposed for inclusion. The
registry identifiers are built to match full text, so that test discriminates
nothing here and carries no exclusion.

Each flagged row names the single artifact that closes it:
`resolution_artifact_required` = that key's GovInfo BILLSTATUS XML. Fetching it
is network collection, which this lane is barred from performing.

## 4. Category findings independent of disposition

- The **legacy Payments assignment for the three BNPL resolutions is wrong** on
  the north-star boundary, regardless of whether a ratifier accepts the
  inclusion.
- The **legacy Fraud Prevention assignment for `117:hr:3854` / `117:s:2034` /
  `117:hr:474` is unsupported** — every north-star Fraud Prevention identifier
  is credit-union or payment-fraud specific.
- The **legacy MBL assignment for the Small LENDER Act family is correct** and
  is confirmed by discovery's own memberships for the sibling instances.
- The mechanism behind the MBL false positives is visible in the archive's
  preserved retrieval URLs: the legacy MBL query was a bag of loose unquoted
  tokens (`veteran`, `commercial`, `threshold`, `limit`, `loan`), while the
  outline-derived MBL query is phrase-bound and every phrase either names credit
  unions or is an MBL term of art.

## 5. Outputs

| file | records | sha256 |
|---|---|---|
| `proposal_adjudications_23.ndjson` | 23 | `57c8c43c95e00a5e8274f54cc6f082304755b397988ae50819190ba0b35212cb` |
| `legacy_recall_partition_465.ndjson` | 465 | `8b45b5bd0f6fdde1fd5ada75531e4d456a33a7a102fb49384602c467a2b4186e` |
| `quorum_recall_partition_44.ndjson` | 44 | `4211488b2d6dd6ccaadd7cf08065283ab0558de78920f8626e633003e885ca87` |
| `receipt.json` | — | binds 14 inputs + 3 outputs by sha256 |

Helper code (`reconcile_recall_floor.py`, `sweep_local_evidence.py`,
`build_outputs.py`) and intermediates (`_reconcile_state.json`,
`_local_evidence_sweep.json`, `_boundary_test.json`) live in this directory only.

## 6. Safety

`integration_performed: false` · `production_write_performed: false` ·
`scoring_performed: false` · `rank_recompute_performed: false` ·
`discovery_mutated: false` · `manual_bill_evidence_mutated: false` ·
`workbook_written: false` · `junk_ledger_written: false` ·
`recovered_input_root_mutated: false` · `network_collection_performed: false`

No proposed include was added to discovery. No semantic decision was delegated.
