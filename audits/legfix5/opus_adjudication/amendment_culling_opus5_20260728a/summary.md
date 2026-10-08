# Amendment culling adjudication — Opus 5 lane

Run `amendment_culling_opus5_20260728a` · 2026-07-28 · proposal only, nothing integrated.
Receipt schema `…-v2-corrected` — see **Correction CORR-01** below.

## Correction CORR-01 — canonical category IDs

**The defect.** This lane validated category IDs against a nineteen-item list
typed by hand out of `query_guard_registry_v2.json`. That registry carries two
**noncanonical source aliases**, so the hand-written copy inherited them and the
receipt's `categories_are_canonical_19` assertion compared the lane against its
own aliased vocabulary. It proved nothing.

| noncanonical alias (was) | authoritative ID (now) |
|---|---|
| `ncua_budget_share_insurance_fund` | `ncua_budget_share_insurance` |
| `telephone_consumer_protection_act_issues` | `telephone_consumer_protection_act` |

**The authority is local and explicit.** `fec/legislation_original_method_evidence.py`
is the production module that builds this frozen bundle. It declares exactly
these two mappings in `CATEGORY_ID_ALIASES` and canonicalises them on the way in
while still requiring nineteen categories. Two `category_review_queue` manifests
independently carry the same nineteen canonical IDs in
`receipt.category_registry`, which is the list production feeds to
`OriginalMethodEvidence`. All three sources agree.

*(For the record: `query_guard_registry.json` — the v1 vintage — does use the
short IDs, but it holds only seventeen categories and lacks
`credit_union_tax_status` and `credit_union_bank_competitive_dynamics`. The
correct vocabulary is v2's nineteen categories **with the two IDs renamed**, not
the v1 registry.)*

**The fix.** `work/canon.py` now *derives* the canonical nineteen: it loads the
frozen registry bound in the manifest, applies the alias map read out of the
production source by AST (never executed, never retyped), asserts no alias
survives, and cross-checks the result against the queue registries. Every helper
imports that set. No list is hand-written anywhere in the lane. IDs are
canonicalised at the single point a category ID enters the lane — the guard scan
in `build_evidence_index.py` — which is what keeps the aliases out of every
downstream artifact.

**Affected rows, before → after.**

| artifact | `category_ids` rows | `evidence_ids` rows |
|---|---|---|
| `proposal_adjudications_419.ndjson` | 7 → **0** | 15 → **0** |
| `amendment_partition_3703.ndjson` | 7 → **0** | 15 → **0** |
| `flagged_amendments.ndjson` | 1 → **0** | 2 → **0** |
| `work/evidence_index.ndjson` | 15 guard-operative + 1 guard-remarks rows → **0** | — |

Only `ncua_budget_share_insurance_fund` ever reached an output row;
`telephone_consumer_protection_act_issues` existed solely in the hand-written
validator list, which is precisely why the bad assertion went unnoticed.

**Nothing substantive moved.** The partition is unchanged at 60 / 2,503 / 1,140,
the queue split unchanged at 60 / 112 / 247, direction unchanged at 46 / 14, the
679-row unavailable-text subset unchanged at 646 / 33 / 0, and the prior-partition
crosswalk unchanged. Preservation is *proven*, not asserted: the receipt compares
all nine substantive fields — disposition, direction, confidence, rule_id, reason,
amendment_weight, text_available, press_evidence_used, parent_context_used —
plus category sets and evidence-reference counts across all 3,703 rows against a
pre-correction snapshot, with the aliases mapped through so a rename does not
read as a change. Zero drift.

**Proof count rose from 24 to 31**, all passing. The seven added:
`canonical_registry_derived_not_declared`, `canonical_registry_corroborated`,
`no_noncanonical_alias_in_any_output_row`, `no_noncanonical_alias_in_lane_rulings`,
`lane_helpers_free_of_alias_literals`, `substantive_dispositions_preserved`,
`before_after_key_sets_identical`.

**Scope.** Identifier rename and validator replacement only. No integration, no
scoring, no rank recomputation, no promotion, no sync, no source-ledger mutation.
The frozen input `amendment_review_queue.ndjson` was not modified — it is an
input, and the lane's queue-derived artifact is
`proposal_adjudications_419.ndjson`, which was rebuilt.

Every amendment in the corpus now has exactly one accounting state, every state
names the rule and the evidence that produced it, and every row is marked
`human_ratification_required: true`. No scoring, no rank recompute, no write to
the discovery corpus, `manual_bill_evidence.csv`, the workbook or the junk
ledger. The recovered input folder was read only.

## The partition

| state | count | share |
|---|---:|---:|
| `include` | 60 | 1.6% |
| `exclude_false_positive` | 2,503 | 67.6% |
| `flagged` | 1,140 | 30.8% |
| **total** | **3,703** | |

Of the 419 review-queue rows: **60 include, 112 exclude_false_positive, 247 flagged.**
Every one of the 60 includes falls inside the 419.

Direction on the includes: **46 at +1, 14 at −1.** Amendment weight is a fixed
0.5 on every row, recorded separately from direction, and no row carries a
computed score.

Included amendments by category (a row may carry more than one) —
`cfpb_issues_structural_reform` 9, `interchange` 8, `cdfi_fund` 7,
`technology_emerging_issues` 7, `fraud_prevention` 7,
`ncua_budget_share_insurance` 6, `mortgage_lending_housing` 5,
`examination_supervision` 5, `payments` 4, `field_of_membership` 4,
`defense_credit_union_issues` 3, `credit_card_consumer_fee_mandates` 3,
`member_business_lending` 2, `data_privacy_cybersecurity` 2,
`charter_modernization_governance` 1, `credit_union_tax_status` 1. Three of the
19 categories draw no included amendment: `credit_union_capital_requirements`,
`credit_union_bank_competitive_dynamics`, `telephone_consumer_protection_act`.

## Did the prior 160-in / 3,543-out partition survive? No — and the stated prior
## is not what is on disk

**First, a correction to the premise.** The tasking names a prior partition of
160 in / 3,543 out. The original-method artifact actually on disk,
`audits_out/amendments/amendment_domain_verdict_v2.json`, records **170 IN /
3,533 OUT** (its predecessor `amendment_domain_verdict.json` records 259/3,444).
No artifact in the recovered folder produces 160/3,543. Everything below is
measured against the 170/3,533 that exists.

**Second, the prior partition was reproduced before it was overturned.** The
query guard was re-run here from `query_guard_registry_v2.json` using the exact
operator semantics of `fec/match_with_query_guards.py` — windowed `containsAll`
at 30 tokens on surfaces over 400 tokens, the domain-anchor requirement for
generic terms, bill-number suppression, `notContains` exclusions. It returns the
**same 170 keys, set-identical**. So the divergence below is adjudication, not a
different instrument.

**Third, it did not survive.** Crosswalk of all 3,703:

| prior verdict | → include | → flagged | → exclude_false_positive |
|---|---:|---:|---:|
| prior IN (170) | 47 | 85 | **38** |
| prior OUT (3,533) | **13** | 1,055 | 2,465 |

- **38 of the prior 170 are false positives.** The largest single family is the
  Native American Housing reauthorisation, refiled across fourteen vehicles,
  where `credit_union_tax_status` fired on the words *appropriations* and
  *financial services* inside a committee-referral list and `cdfi_fund` fired on
  a definitional eligible-lender cross-reference. Others: the *Regulation E* hit
  that is really the token *regulation* followed by subparagraph *(E)*; the
  *Durbin amendment* hit that is really the Congressional Record header naming
  Mr. DURBIN as proposing senator; groundwater *overdraft* and intermodal
  freight *interchange*; the NCUA appearing as one entry in a list of consulted
  agencies.
- **13 amendments the prior partition culled are real and were recovered**, all
  at +1, including the ECOA §704B **1071 repeal** (119:samdt:2280), the **CTR/SAR
  threshold update** (119:samdt:6241), the **HELPER Act** FHA first-responder
  mortgage insurance (118:samdt:3048, 119:samdt:4320), **CFPB into regular
  appropriations** (117:samdt:4704), the **IRS financial-institution reporting
  ban** (117:samdt:4811), and Bank Secrecy Act reform (119:samdt:2247). Each
  matches a position ACU records in its own registry; the guard missed them
  because the registry identifiers are act names, not statutory citations.
- **85 of the prior 170 are real domain but unresolved direction**, overwhelmingly
  the GENIUS Act stablecoin cluster.

## What changed in the method, and why

Three deliberate departures from the producer scripts, each required by the
binding rules:

1. **Floor remarks no longer establish domain.** `match_with_query_guards.py`
   accepted a remarks-only hit as an on-domain verdict, and 18 of its 170 arrived
   that way. Rule 3 makes remarks sponsor context that cannot substitute for
   operative text, so remarks are scanned and recorded on a separate surface and
   a remarks-only hit routes to review. `floor_evidence_used` is `false` on all
   3,703 rows.

2. **Parent stance no longer composes direction.**
   `adjudicate_amendment_queue.py` derived a signed credit as
   `sign(ACU position on parent) × sign(intent)`, and read a member's own press
   release about the parent bill as evidence of the amendment's intent. Rule 1
   bars that. Direction here is the amendment's own ultimate effect on the
   category. `parent_relevance_transferred` is `false` on all 3,703 rows.
   `parent_context_used` is `true` on 49 rows only — internal edits to a
   single-subject bill, where the parent is needed to construe *what the edit
   operates on*, never to inherit the parent's relevance.

3. **The official purpose line was added to the operative surface.** The producer
   read a `declared_purpose` field that `amendment_content_v2.ndjson` does not
   carry, so that surface was silently empty. congress.gov's *Purpose:* statement
   is amendment-specific official evidence and it is the only thing that resolves
   33 of the 679 text-less rows.

**The press finding that matters most.** `press_amendment_pairs.json` was built
as *same sponsor, ±30 days, article text names the parent bill number*. That is
not an identification of the amendment, so under rule 4 it establishes nothing on
its own. Reading the cached ACU article texts shows the association names exactly
**two** amendments by sponsor and substance: Sen. Marshall's interchange
amendment (*"we urge Senators to oppose it"*) and Sen. Hawley's 10 percent
credit-card rate cap (*"America's Credit Unions also joined ... a letter opposing
Hawley's amendment"*). Those four rows — 119:samdt:2229, 2230, 2345 and
119:samdt:2239 — are the only rows with `press_evidence_used: true`. The other
29 press-paired amendments, including all of Sen. Reed's, are paired only with
their own sponsor's release about the parent bill and are adjudicated on their
own text.

## The 679 unavailable-text cases, kept as a distinct subset

| | count |
|---|---:|
| total with no recoverable amendment text | 679 |
| flagged (no amendment-specific evidence resolves them) | 646 |
| excluded on their own official purpose statement | 33 |
| included | 0 |

No amendment was excluded because its text was missing. The 33 exclusions rest on
the amendment's own congress.gov purpose statement resolving its subject —
*"To expand the list of diseases associated with exposure to certain herbicide
agents"*, *"To fund activities relating to the suppression and control of Mormon
crickets and grasshoppers"* — which is evidence, not absence. Where the purpose
is a formula (*"To improve the bill"*, *"Of a perfecting nature"*, *"Purpose
displays after an amendment is proposed"*) the row is flagged.

## Why the flag list is large, and what a ratifier should do with it

1,140 flags is 31% of the corpus. It decomposes into four classes, and three of
them are bulk decisions a human can make in one stroke:

| class | count | what it is |
|---|---:|---|
| `D-NOTEXT` / `D-NOTEXT-QUEUE` / `D-SIDECAR-NOTEXT` / `D-VAGUE-PURPOSE` | 645 | no recoverable text and nothing amendment-specific to resolve it |
| `D-POINTER-UNRESOLVED` / `F-POINTER*` | 332 | text exists but is a bare positional edit — *"Page 24, line 6, after the dollar amount, insert ``(increased by $5,000,000)''"* — which states no subject of its own |
| `D-STABLE-OPEN` / `D-GENIUS-INTERNAL` / `F-STABLE-CFPB` | 114 | operative amendments to the GENIUS Act payment-stablecoin statute: real domain, unresolved direction |
| named `F-*` boundary and open-direction rulings | 49 | individually reasoned: FCRA credit reporting, CFPB reporting duties, TILA consumer credit, NFIP, SCRA, mortgage-finance |

The pointer class is the one to look at first. A page-and-line dollar adjustment
is unreadable without the underlying bill page, so rule 8 forbids culling it —
but if you judge that appropriations pointer edits are categorically outside the
19 categories, that is one decision that resolves 332 rows.

The GENIUS cluster is the substantive open question. ACU supported the GENIUS Act
and wanted it *clean*, and it named two amendments it opposed. A preference for a
clean vehicle is a statement about the vehicle, which rule 1 bars from
transferring direction to each amendment, so these are not blanket −1. Three
exceptions were resolvable on their own effect and are included at +1: the
prohibitions on paying interest or yield on a payment stablecoin (119:samdt:2299,
2305, 2315), which is the provision insured depositories sought to prevent
share and deposit disintermediation, and the limit of Federal Reserve service
access to insured depository issuers (119:samdt:2329).

`F-NFIP-BOUNDARY` is a deliberate referral, not an evasion: the National Flood
Insurance Program is not one of the 19 categories, but NFIP lapse and pricing bear
directly on mortgage closings. Six rows whose operative subject *is* the NFIP are
referred up rather than culled; incidental flood cross-references elsewhere are
excluded.

## How direction was grounded

Every ±1 is anchored to a position ACU records in `acu_category_registry.json`
rather than to an inference about what ACU would think. Interchange −1 follows
OPPOSE on the Credit Card Competition Act; the 10 percent cap −1 follows OPPOSE
on the rate-cap act; CBDC prohibitions +1 follow SUPPORT on the Anti-CBDC
Surveillance State Act; the payment-scams task force +1 follows SUPPORT on the
TRAPS Act; trigger leads +1 follows SUPPORT/PASSED on the Homebuyers Privacy
Protection Act; CLF agent membership +1 follows SUPPORT on CLF Enhancements;
1071 repeal and CFPB appropriations +1 follow SUPPORT on the 1071 Repeal and TABS
Acts; CTR/SAR thresholds +1 follows SUPPORT on the STREAMLINE Act; FHA
first-responder insurance +1 follows SUPPORT on the HELPER Act. Where a category
has no recorded ACU position and the amendment's effect turns on a second-order
parity argument, the row is flagged rather than assigned a manufactured sign.

## Files

| file | rows |
|---|---:|
| `proposal_adjudications_419.ndjson` | 419, one per review-queue key |
| `amendment_partition_3703.ndjson` | 3,703, one per amendment key |
| `flagged_amendments.ndjson` | 1,140 |
| `receipt.json` | SHA-256 binding of every input and output, 24 coverage proofs, all passing |

`work/` holds the helper code and the review cards the rulings were made from:
`build_evidence_index.py` (guard re-derivation), `make_review_cards.py`,
`decisions.py` (the rulings), `adjudicate.py`, `receipt.py`, and the rendered
card files. All of it is bound by hash in the receipt.

## Standing blockers for ratification

1. The tasking's 160/3,543 prior does not exist on disk; 170/3,533 does. Confirm
   which figure the meta-loop should carry forward.
2. 332 pointer-edit rows need one categorical decision.
3. 114 GENIUS Act rows need a direction policy, or acceptance that they stay out
   of scoring.
4. 645 text-less rows remain unresolvable without further official text; they are
   preserved, not culled.
5. Nothing here is ratified. `human_ratification_required` is `true` on all 3,703
   rows and no downstream artifact has been touched.
