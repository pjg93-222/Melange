# The 454 orphan review-ledger edges: classification and verdict

**Date:** 2026-07-27
**Question:** Are the 454 review-ledger edges absent from discovery a legacy artifact of an older ACU taxonomy, or evidence of a real gap in the 62-query discovery set?
**Answer:** **Neither.** They are a deterministic, fully-explained *attribution convention* difference between the two artifacts. There is **no discovery gap** and **no taxonomy restructure** involved.

**Status:** evidence for a human decision. No registry change is proposed or made. All existing artifacts were read-only. No network requests were issued.

---

## 1. Headline result

| Class | Definition | Count |
|---|---|---|
| **(a)** retrieved by the *current* query for the *same* category — bookkeeping/ordering artifact | 0 | **0** |
| **(b)** retrieved by a *different* current query — taxonomy/attribution remap | **454** | **454** |
| **(c)** retrieved by **no** current query — genuine discovery gap | 0 | **0** |

**Class (c) is empty.** Every one of the 454 candidates is already inside the discovery universe, retrieved by the current 62-query set. Not one of them requires a new identifier, a new search term, or a re-scrape to be found.

All 454 resolve to a single mechanism, stated precisely:

> The review-ledger builder **rolls a non-dispositive title-alias coverage-probe hit up onto its parent scoring category** and discards the probe edge. Discovery does the opposite: it keeps the raw probe edge and never rolls up. The 454 are the parent edges the ledger created; the 1,023 title-alias entries in the mirror-side 1,771 are the probe edges it consumed to create them.

The two "disagreements" in the reconciliation receipt are therefore **two sides of one transformation**, not two independent defects.

---

## 2. Evidence

### 2.1 Inputs are byte-identical to the reconciliation receipt

SHA-256 verified against `audits/legfix5/coverage_reconciliation/recon-20260727a/receipt.json`:

| Artifact | SHA-256 | Matches receipt |
|---|---|---|
| `congress_advanced_memberships.ndjson` | `f6d61c83…3a3c3204` | yes |
| `congress_advanced_records.ndjson` | `f71add90…9f9a9c7b61b1` | yes |
| `membership_review_ledger.ndjson` | `bf46e8bc…67e681a81fb` | yes |

The ledger **survived** the OneDrive restore intact (200,363,847 bytes) and hashes to the receipt's value, so no reconstruction from receipts was necessary. My derivation runs on exactly the bytes the failing audit ran on, and reproduces its numbers exactly: 64,004 discovery edges, 62,687 ledger edges, 1,771 discovery-only, 454 ledger-only, 64,004 − 1,771 + 454 = 62,687.

### 2.2 Discovery is a faithful materialization of the stored query sets

Rebuilding the edge set directly from the 62 `queries/*.json` result sets yields **64,004 edges**, and:

- stored-query edges **not** in `congress_advanced_memberships.ndjson`: **0**
- discovery memberships **not** in the stored query sets: **0**

This is an exact, bidirectional identity. It has two consequences. First, the stored result sets are a sound offline substitute for re-running the searches — the zero-request method is valid. Second, **class (a) is empty by construction**: an orphan is by definition not in discovery, and discovery ≡ the stored query sets, so no orphan can be in its own category's stored result set.

### 2.3 Every orphan sits in a child probe of its own parent

For all 454, the candidate appears in the result set of a `title_alias_probe_*` query whose `parent_category_id` is **exactly the orphan's `query_id`**. 454 / 454, no exceptions:

| Ledger category (orphan `query_id`) | Orphans | In a child probe of that same parent |
|---|---:|---:|
| `cdfi_fund` | 175 | 175 |
| `mortgage_lending_housing` | 138 | 138 |
| `examination_supervision` | 67 | 67 |
| `technology_emerging_issues` | 62 | 62 |
| `fraud_prevention` | 12 | 12 |
| **Total** | **454** | **454** |

### 2.4 The mirror side closes the arithmetic exactly

Of the 1,771 discovery-only edges:

- **748** come from `credit_union_headline_recall_net`, which has `parent_category_id: null`. No roll-up is possible, so the ledger simply drops them. (Already settled as by-design; noted only for completeness.)
- **1,023** come from `title_alias_probe_*` queries, all of which have a parent.

For those 1,023, the parent edge exists in the ledger in **1,023 of 1,023** cases — **zero unpaired**. They collapse to **1,008** distinct `(candidate, parent)` pairs (15 candidates matched two probes of the same parent). Of those 1,008:

- **554** already existed in discovery as genuine direct hits on the parent category → no orphan created
- **454** did not → **these are exactly the 454 orphans**

554 + 454 = 1,008. Orphans not explained by a dropped probe edge: **0**.

### 2.5 The builder source implements precisely this rule

`fec/review_legislation_candidate_memberships.py`, lines 793–815:

```python
for membership in raw_memberships:
    parent_category_id = membership.get("parent_category_id")
    if (membership.get("membership_non_dispositive")
            and parent_category_id in category_by_id):
        key = (membership["canonical_key"], parent_category_id)
        alias_probe_hits.setdefault(key, []).append(membership)
        if key not in existing_category_memberships:
            category = category_by_id[parent_category_id]
            memberships.append({**membership,
                "query_id": parent_category_id,
                "label": category["label"],
                "scoring_category": category["scoring_category"],
                "record_kind": "title_alias_probe_candidate",
                "source_title_alias_probe_id": membership["query_id"]})
            existing_category_memberships.add(key)
        continue          # <-- the probe edge itself is NOT carried forward
    memberships.append(membership)
```

The `continue` is the dropped probe edge; the appended dict is the created parent edge; the `if key not in existing_category_memberships` guard is why 554 of the 1,008 produce no orphan.

### 2.6 The taxonomy hypothesis is refuted directly

The hypothesis was that the 454 were created under an older ACU outline that the current 62-query set no longer retrieves. Three independent facts refute it:

1. **The registry hash did not change.** Every one of the five categories' query artifacts records `equivalent_query_reuse.prior_registry_sha256` == `current_registry_sha256` == `ba865417…a169d20b39`, which is also the `registry_sha256` in the review manifest. The ledger and the current query set were built against the **same registry revision**. No outline restructure sits between them.
2. **The remap is not category-to-category.** A taxonomy merge would show old-category → different-new-category movement. Instead 100% of the movement is category → *its own child probe*, which is a parent/child relationship inside one unchanged registry, not a renaming across two.
3. **The candidates are not credit-union bills at all.** A real remap would move topical bills between topical homes. What actually moved are items like *Health Care Affordability Act of 2019* and *Refuge From Cruel Trapping Act* — see §4.

---

## 3. Class (b) mapping: old → new

Because the remap is parent↔child within one registry, the honest "mapping" is per **supplying probe**, not per category pair:

| Supplying probe (`title_alias_probe_…`) | Alias | Parent category the ledger attributed to | Orphans |
|---|---|---|---:|
| `cdfi_fund_afford_act` | `AFFORD Act` | `cdfi_fund` | 175 |
| `mortgage_lending_housing_supply_act` | `SUPPLY Act` | `mortgage_lending_housing` | 106 |
| `technology_emerging_issues_clarity_act` | `CLARITY Act` | `technology_emerging_issues` | 55 |
| `examination_supervision_streamline_act` | `STREAMLINE Act` | `examination_supervision` | 35 |
| `mortgage_lending_housing_helper_act` | `HELPER Act` | `mortgage_lending_housing` | 32 |
| `examination_supervision_smart_act` | `SMART Act` | `examination_supervision` | 28 |
| `fraud_prevention_traps_act` | `TRAPS Act` | `fraud_prevention` | 12 |
| `technology_emerging_issues_genius_act` | `GENIUS Act` | `technology_emerging_issues` | 4 |
| `examination_supervision_firm_act` | `FIRM Act` | `examination_supervision` | 3 |
| `technology_emerging_issues_secure_notarization_act` | `SECURE Notarization Act` | `technology_emerging_issues` | 2 |
| `examination_supervision_tailor_act` | `TAILOR Act` | `examination_supervision` | 1 |
| `technology_emerging_issues_stable_act` | `STABLE Act` | `technology_emerging_issues` | 1 |
| **Total** | | | **454** |

All twelve are declared `record_kind: coverage_probe`, `scoring_category: false`, `membership_non_dispositive: true`, `ambiguous_short_act_alias: true`, and each runs a bare quoted phrase — `("AFFORD Act")`, `("SUPPLY Act")`, `("TRAPS Act")`, and so on.

---

## 4. Class (c): none — and the finding that replaces it

There is no class (c), so **there are no proposed identifier additions**. The discovery query set does not need a single new term on account of these 454. Adding terms to chase them would be actively wrong.

The material finding runs the other way. congress.gov's phrase search **stems and tokenizes**, so `("AFFORD Act")` matches *Affordability Act* and *Affordable Act*. The probes are therefore pulling in large numbers of topically unrelated bills, and the roll-up promotes each one into a **scoring** category. Representative results, verbatim from the stored sets:

| Candidate | Title | Rolled up into |
|---|---|---|
| `116:hr:1868` | Health Care Affordability Act of 2019 | **CDFI Fund** |
| `116:hr:3784` | Air Ambulance Affordability Act of 2019 | **CDFI Fund** |
| `116:hr:8394` | Improving Diaper Affordability Act of 2020 | **CDFI Fund** |
| `116:hr:3567` | Securing Americas Rare Earths Supply Act of 2019 | **Mortgage Lending & Housing** |
| `116:s:2316` | MICROCHIPS Act of 2019 | **Mortgage Lending & Housing** |
| `118:hr:2925` | Mining Regulatory Clarity Act of 2024 | **Technology & Emerging Issues** |
| `118:hr:5217` | Refuge From Cruel Trapping Act | **Fraud Prevention** |
| `116:s:1559` | Fly Smart Act | **Examination & Supervision** |

### 4.1 The short-act guard is silent on 345 of the 454

The ledger's own defence — `short_act_title_requires_independent_evidence` — fires only when the alias literal is present in the measure title (`matched_short_act_title_aliases` non-empty). It caught **109**. The other **345** entered through the *stemmed* match, so the literal never appears and the guard never fires:

| Category | Orphans | Guard fired | **Guard silent** |
|---|---:|---:|---:|
| `cdfi_fund` | 175 | 0 | **175** |
| `mortgage_lending_housing` | 138 | 22 | **116** |
| `examination_supervision` | 67 | 30 | **37** |
| `technology_emerging_issues` | 62 | 57 | **5** |
| `fraud_prevention` | 12 | 0 | **12** |
| **Total** | **454** | **109** | **345** |

The 109 land in `review_bucket: ambiguous_short_act_collision` at `review_priority: 2` with `likely_false_positive_reason` populated. The 345 land in `official_text_unavailable_or_not_enriched` at `review_priority: 9` with `likely_false_positive_reason: null` — **indistinguishable in the review queue from an ordinary unresolved category membership**, even though 343 of the 345 already carry a title on the ledger row itself (314 of them a real measure title, the rest amendment `Purpose:` strings) that would settle most of them on sight.

### 4.2 Provenance is stripped on the rolled-up rows

On all 454 ledger rows as written to disk:

- `membership_non_dispositive`: **false** on all 454 (the probe's own flag is `true`)
- `title_alias_probe_is_non_dispositive`: false on all 454
- `ambiguous_short_act_alias_probe`: false on all 454
- `source_title_alias_probe_ids`: `[]` on all 454
- `record_kind`: `category` on all 454
- `scoring_category`: **true** on all 454

So a reviewer reading the ledger alone cannot tell these edges came from a non-dispositive ambiguous short-act probe. The current builder source *does* stamp `record_kind: "title_alias_probe_candidate"` and `source_title_alias_probe_id` (lines 809–810), but the on-disk ledger carries neither, and the whole-file scan finds **zero** rows with either marker. The on-disk ledger was therefore produced by an **earlier revision** of the builder that performed the same roll-up without the provenance stamps.

### 4.3 Current exposure is zero; the risk is prospective

- Of the 454, **0** appear in `included_memberships.ndjson` (55 edges total).
- **2** are already adjudicated `exclude_false_positive` — both `SMART Act` rows (`117:hr:3664`, `118:hr:1707`), correctly reasoned as the *Save Money on Auto Repair Transportation Act*.
- The remaining **452** are `unresolved`.

Nothing has been scored off these edges. The exposure is entirely forward-looking: it lands on the never-performed 19-category review, where 345 mislabelled edges would arrive unflagged at ordinary priority.

---

## 5. Verdict

**Legacy taxonomy artifact: NO.** Same registry hash on both sides; the movement is parent↔child inside one unchanged registry, not category→category.

**Real discovery gap: NO.** Class (c) = 0. All 454 candidates are retrieved by the current query set. Discovery reproduces the stored query sets exactly, 0 edges adrift in either direction. **This question should not block a scrape** — no additional collection is implied by these 454.

**What it actually is:** a deliberate roll-up rule in the review-ledger builder, operating losslessly and reversibly on discovery data that is fully intact. The `COVERAGE_GAPS_PRESENT` status on `review_ledger_introduces_no_edge_outside_discovery` is a **true positive for an undeclared transformation**, not for missing data. The check compares a rolled-up artifact against a raw one and has no way to know the roll-up is intentional.

**The finding worth a decision** is not the 454 as a set — it is the **345** of them on which the short-act guard is silent, sitting in the review queue at ordinary priority with their probe provenance stripped, when their titles (already on hand, no collection needed) show most to be alias collisions such as *Health Care Affordability Act* → CDFI Fund.

---

## 6. Derivation method and limitations

**Method.** Load `(canonical_key, query_id)` edge sets from discovery memberships and from the review ledger (streamed; 62,687 lines). Difference them both ways. Load all 62 `queries/*.json` and index each `records[].canonical_key`. For each orphan, test membership in (i) its own category's stored set, (ii) every other stored set, (iii) the stored sets of probes whose `parent_category_id` equals the orphan's `query_id`. Cross-check the mirror side by mapping each dropped probe edge to its parent and testing for the corresponding ledger edge. Re-read the 454 ledger rows in full for guard-flag and disposition fields.

**Zero network requests.** Every membership test is a set lookup against stored result sets. Nothing was fetched, and no collection was touched.

**Limitations.**

1. **Class (a) is unobservable, not merely empty.** Since discovery ≡ the stored query sets exactly, no orphan could have been class (a). A pure ordering/bookkeeping artifact would have shown up as a difference in §2.2, and none exists.
2. **The roll-up rule for the on-disk vintage is inferred, not re-executed.** It rests on exhaustive set arithmetic (1,023/1,023 paired, 1,008 = 554 + 454, 0 unexplained) plus current source that implements exactly that rule. I did **not** re-run the builder. The on-disk rows lack the `title_alias_probe_candidate` / `source_title_alias_probe_id` markers the current source emits, which is itself the evidence that the ledger predates that revision — so a re-run would confirm the mechanism *and* change these rows' shape. `fec/` is untracked by git here, so I could not diff builder revisions to date the change.
3. **Membership is tested on `canonical_key` only.** Two artifacts agreeing on a key are taken to agree on the candidate. The receipt's own check `every_membership_candidate_is_a_discovery_record` passes, which supports this.
4. **"Alias collision" in §4 is a title-level reading**, offered as characterization, not adjudication. 452 of the 454 remain `unresolved` and none of these classifications resolves them. Category assignment stays a human call.
5. **Titles for 31 amendment candidates** (2 `hamdt`, 29 `samdt`) are absent or are `Purpose:` strings; those are characterized by key only.

**Machine-readable output.** `audits/legfix5/orphan_edge_classification_2026-07-27.ndjson` — one header record (schema, input hashes, totals) then 454 rows carrying the classification, supplying probe and its alias and query string, guard flags, ledger disposition/bucket/priority, title, and the candidate's full discovery query list.
