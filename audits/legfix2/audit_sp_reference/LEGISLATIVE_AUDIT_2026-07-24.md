# Legislative data audit — 2026-07-24
**Read-only. No file under the live tree was modified.** Every change below is PROPOSED and awaits Paul.

Method: Fable coordinated; 24 Opus subagents in 6 audit lanes + 12 adversarial verifiers + 1 completeness
critic (2.7M tokens, 713 tool calls, 0 errors); Grok ran an independent critique pass on Fable's own
findings and killed one of them. 76 subagent findings + 13 coordinator findings, all cross-checked.

---

## PART 1 — WHAT CHANGED ON THE ACU WEBSITE

Pulled live from americascreditunions.org, including its GraphQL API (533 advocacy letters, 2024-01-07
to 2026-07-23, with ACU's own issue tags).

### 1.1 ACU now lists 23 issues; the model has 18 categories
Five live ACU issues have no home in `bill_rules.CATEGORIES`:
| ACU issue (live) | status in model |
|---|---|
| Rate Caps and Fees | none — ACU has SPLIT this from Credit Card Mandates |
| Credit Union-Bank Mergers | none |
| Bank Attacks | none |
| Appropriations and Congressional Budget Process | none |
| State Level Credit Union Issues | none (arguably out of scope — not congressional) |

ACU also tags letters with two Layer-1 groups absent from the Feb-2026 outline:
**Regulatory Relief** (23 letters) and **Diversity, Equity & Inclusion** (2).

### 1.2 Nine bills ACU has lobbied by letter are absent from the model entirely
| Bill | Act | Latest ACU letter |
|---|---|---|
| H.R.3074 | Common Cents Act | 2026-07-12 |
| S.3849 / H.R.7484 | Community Bank Relief Act | 2026-02-11 |
| S.3734 | Close the Shadow Banking Loophole Act | 2026-01-28 |
| H.R.5775 | FCRA Liability Harmonization Act | 2025-12-14 |
| H.R.1 | One Big Beautiful Bill Act (the CU tax vehicle) | 2025-12-04 |
| H.R.9767 | Promoting/Advancing Communities of Color Inclusive Lending | 2024-09-26 |
| S.4521 | CFPB Accountability Act | 2024-06-24 |
| H.R.3335 | IRS eIVES Modernization and Anti-Fraud Act | 2024-01-24 |

### 1.3 Two bills now dominate ACU's 2026 advocacy and post-date the Feb-2026 outline
- **H.R.6644 — 21st Century ROAD to Housing Act**: ACU's most-lettered bill (3 letters, tagged across
  Credit Union Powers & Charter / Lending / Examination). In the archive with 34 rows, scored ONLY in
  Mortgage & Housing. Senate companion **S.2651** is absent from the model.
- **H.R.6955 — Main Street Capital Access Act**: 2 letters, latest 2026-07-19. In the archive with 126
  rows but scored into **Fraud Prevention + Member Business Lending** — it is a CAPITAL bill.

### 1.4 Positions confirmed unchanged
Every OPPOSE in the outline is still OPPOSE on the live site (Credit Card Competition Act S.3623/H.R.7035;
10% Rate Cap S.381/H.R.1944; Credit Card Fairness Act S.3660). No SUPPORT flipped to OPPOSE or vice versa.
An independent lane cross-checked all archive bills in the two negative-default categories against the ACU
tracker and found **zero direction contradictions**.

---

## PART 2 — PAUL'S FIVE QUESTIONS

### Q1. What types of legislative action are being missed?
The corpus captures **sponsorship / original-cosponsorship / cosponsorship on named bills, and nothing
else** (`Role` has exactly 3 distinct values across all 10,986 rows).

Measured against ACU's own 157 advocacy communications published in 2026:
- 64 regulatory rulemaking comments — **out of scope by design** (agency filings, not congressional)
- Of the 58 clearly congressional items: **11 named bills (19%) are representable**; the other 81% are not:
  25 hearing/oversight letters, 11 committee markups, 4 nominations (NCUA board — Crews; CFPB director —
  Johnson), 4 amendments (FY2027 NDAA; the CLF and CDFI amendments to H.R.6644 that ACU called wins),
  3 appropriations/budget-resolution positions.

Verified specifics:
- **Amendments: 0 of 468 bill records are H.Amdt/S.Amdt.** No member earns credit for offering a CU
  amendment — including to the NDAA vehicles `bill_rules.py:59-60` deliberately keeps in scope.
- **Roll-call votes add nothing where a member has no cosponsorship.** `apply_leg_stance.py:49` computes
  `IMP[t] * act * SM[stance[t]]`; `act = 0` zeroes the term. All 148 vote-only cells contribute exactly 0.
- The vote artifact `vote_category_lean.json` is 28 days stale and **its producer cannot run** —
  `vote_by_category.py` needs `votes\cu_rollcall_votes_clean.csv`, which exists nowhere under the data root.
  Only 2 of 18 categories have any cell passing its n>=5 gate.
- Floor speeches and hearing testimony ARE collected at scale but routed to the media plane only.

### Q2. Is everything that should be covered, covered?
No, and the collection mechanism itself is the problem.

- **The bill archive has no producer script anywhere in the repo or in git history.** Verified: 16 files
  reference `congress_bills_archive`, all readers, zero writers; `git log --all --diff-filter=A` shows no
  bill collector ever committed. The workbook is machine-written (XlsxWriter signature). **It cannot be
  regenerated, diffed, or refreshed by running anything in the repo.**
- The same uncommitted collector also produced **16 further artifacts** — `congress_cosponsor_network_*`
  (13 files) and `congress_centrality_*` (3) — which feed the cascade/influence engines, HCoI, coop, the
  desk and the dashboard.
- **Interchange was scraped with ONE search term** (`"Credit Card Competition Act"`) against 17-72 tokens
  for every other category. Yield: 36 rows, 6 bills, all one act. The outline specifies nine identifiers
  including proximity searches. This is ACU's most contested issue and it is 0.41% of the plane.
- **Two of 18 categories have zero scraped legislation.** Sheet `12 CDFI Fund` is a header row with 0 data
  rows; there is no CU Tax Status sheet at all. CDFI Fund is 244/262 sign-on letters; **CU Tax Status is
  34/34 rows from a single letter** (LTR-119-CUTAX-CISCOMANI) — and it is the category the model weights
  highest (IMP 3.0).
- Executed search queries contain **misspellings inside quoted phrases**, which match nothing on Congress.gov.
- The archive captures only **83.2%** of the cosponsors it itself reports in `CosponsorCount`.
- **There is no date column.** `LastAction` is a 7-value status, not a date, so staleness and cosponsorship
  timing are unmeasurable from the file. Archive is 23-30 days stale; press 30 days; votes 28 days.

### Q3. Is everything being weighted correctly?
**Framing correction, verified: `archive_leg.json` does not feed the rank.** `archive_leg` appears 0 times
in `compute_pillars.py`; the rank's legislative percentile reads workbook `Bill Model` column O. Every
weight-share figure below describes the **18-category stance matrix**, not the rank. The two measures agree
at rho = 0.912 but disagree hard in the tail (Merkley O#471 vs archive#41).

- **82.0% of legislative weight is signed by a code default** that assumes any scraped bill is pro-CU
  (`sign = -1 if cat in NEG else 1`). Only 54 of 436 scored bills (12.4%) carry an adjudicated direction,
  and all 60 registry rows are CFPB-seeded. Failure mode is silent and one-directional.
- **Cross-listing**: 1,463 of 5,466 (member,bill,congress) triples are filed under 2-5 categories, because
  `event_key` at `build_archive_legislative.py:113` includes the category. This is **DESIGN, not a defect** —
  the comment above the line already says "effective-domain", and a verifier established it produces
  *breadth across the 18-domain matrix*, not a 5x payout on one score. Magnitude for the record: 26.8% of
  triples, 28.9% of raw weight. It is a decision for Paul, not a bug to fix.
- **The vendor's own tagging is provably self-inconsistent**: of 112 acts filed under more than one bill
  number, 13 (11.6%) land in disagreeing category sets — 912 rows, 8.3% of the archive. H.R.2808 gets
  {Data Privacy, MBL, Mortgage} while its three siblings get {Data Privacy} alone. So the multi-category
  spread is measurably artifact, not judgment.
- **Bill status is collected but unused by the pillar.** A bill that became law weighs the same as one
  merely introduced in `archive_leg.json`. Status IS used by the say-do gate (`say_do_gap.py` ADV_W).
- **The "efficiency" 30% of the legislative pillar is 90.7% empty** and a constant zero in 7 categories
  (Interchange, Payments, Field of Membership, CDFI Fund, CFPB, Credit Card Mandates, TCPA).
- **Say-do gate counts a sign-on letter signature as having authored a bill.** `moneyball_core.py:358-359`
  filters on `'sponsor' in role`; 296 of 297 manual rows are LTR-* letters with Role='original-cosponsor',
  so all pass. 187 top-tier cells rest on it. Verifier could not refute.
- **Congress mix**: 119th is only 41.7% of weight; 58.3% is decayed 117th/118th history.
- **Reverse gap** — ACU's advocacy attention vs pillar weight, by ACU's own Layer-1 tags:
  Information Security 4.04x over-weighted, Lending 2.77x over; Tax/Budget/Bank Attacks 0.44x under,
  Credit Union Powers & Charter 0.58x under, Examination 0.60x under. (Directional only: ACU letters
  cover 2024-2026 while the pillar spans 2021-2026.)

### Q4. Are we missing key pieces of legislation?
- **5 of 55 outline-named bills have zero rows anywhere**: S.427 + H.R.3380 (TAILOR Act, both chambers),
  **H.R.1**, S.3940 (AFFORD Act), S.1880 (CDFI Bond Guarantee Improvement). A verifier confirmed this is
  not scrape truncation.
- **S.2704 is the wrong bill.** The outline calls it CDFI Fund Transparency Act; the archive's S.2704 is a
  117th-Congress "Small Business Surcharge Relief Act" scored into Mortgage & Housing.
- **From ACU's own press**: H.R.1 appears in 37 articles touching 21 members with zero corpus evidence.
  Also absent: H.R.4478 (TRUST Act, 6 articles), H.R.4460 (Stop Agency Fiat Enforcement of Guidance, 4),
  H.R.1606, H.R.3380, H.R.3709, H.R.9767, S.2651, H.R.7338.
  H.R.4437, H.R.4460, H.R.4478 and H.R.4544 were in the SAME HFSC markup — the corpus has two and misses two.
- **CAVEAT, verified myself**: 797 of 816 ACU cached articles (97.7%) are truncated at "LOG IN FOR ACCESS"
  with a median 1,927 chars. Bill numbers past the paywall are invisible, so this gap list is a **floor**.

### Q5. Is everything sorted into its proper category?
Against ACU's own issue tags for the 32 bills it named in letters: 12 agree, 11 mismatch, 9 not in corpus —
**52% agreement among bills we hold**. But ACU's own tagging is loose (its site files "Credit Card Mandates"
and "Rate Caps and Fees" under EXAMINATION AND SUPERVISION), and on several mismatches our categorization is
the better one. Defensible errors on our side: **3 of 23**.
- **H.R.6955 Main Street Capital Access Act** -> Fraud Prevention + MBL. It is a capital bill.
- **S.J.Res.18 / H.J.Res.59** (CFPB overdraft CRA disapproval) -> CU Capital Requirements + MBL. Neither is
  right; `bill_directions.csv` already says Category=CFPB but **that column is never read**. Paul's own
  outline annotates this line "Move this over else where".

Latent, currently 0 rows: `bill_key()` maps H.R.59 == H.J.Res.59 == H.Res.59 and drops H.Con.Res/S.Con.Res;
`bill_directions.csv` has no Congress column. **S.919 already means two different bills** (Data Care Act 2021,
GENIUS Act 2025), so adding a GENIUS direction row would silently sign the 2021 bill too.
The **'disapproval' guard never fires**: 0 of 11,283 rows. 119th-Congress style is "Disapproving...", and
123 of 130 current-Congress disapproval rows fail the substring test.

---

## PART 3 — PROPOSED CORRECTIONS (NONE APPLIED — ALL AWAIT PAUL)

### Tier 1 — data already adjudicated, sitting unused (highest value, lowest risk)
1. **Wire up `cu_bill_directions.json`.** It holds **63 bills with ACU's real tracker positions**
   (54 SUPPORT / 6 OPPOSE / 1 MONITOR), including S427 and HR3380. **Verified: zero code consumers.**
   `bill_direction_queue_FILLED.csv` holds a further 57 human-adjudicated directions, also unused.
   This is the direct fix for "82% of weight signed by a code default" — the adjudication is already done.
2. **Add a Congress column to `bill_directions.csv`** before wiring anything, or the S.919 trap arms.
3. **Recover the true category semantics**: `cfpb_bill_directions.csv` is still read live by
   `vote_by_category.py` and its Category column is {Reduce 49, Neutral 6, Expand 5} — the migration to
   `bill_directions.csv` flattened all 60 to "CFPB". The remediation is a join, not a re-derivation.

### Tier 2 — correctness fixes
4. Re-route **S.J.Res.18 / H.J.Res.59** to CFPB and **H.R.6955** to CU Capital Requirements via
   `bill_overrides.csv` (the supported user-editable mechanism).
5. Replace the `'disapproval'` substring test with a regex covering `disapprov(al|ing)`. The same bug is
   duplicated in `bill_audit_console.py`.
6. Make `bill_audit_console.py` mirror production: an override cannot rescue a title-excluded bill, but the
   console reports that it can.
7. Fix `bill_key()` to distinguish bill types, or document the collision and add a guard.
8. Add a provenance-aware audit check: `audit_full.py:474` asserts all 18 categories are present, but the
   guard is **vacuous** — CU Tax Status and CDFI Fund are satisfied entirely by hand-entered rows, so a
   scrape that returns zero CDFI bills forever will keep passing.
9. `canonical_category()` routes all 11,283 rows and has **zero test coverage**.

### Tier 3 — collection (the real fix, and the biggest job)
10. **Write and commit a bill collector.** The executed Congress.gov queries survive in the `hl=` parameter
    of 8,520 DetailLink values — the spec is recoverable from the artifact itself.
11. Re-scrape **Interchange** with the outline's nine identifiers, and add CDFI Fund and CU Tax Status
    queries (which appear never to have been configured — sheets are numbered 01..17 contiguously).
12. Add the 9 ACU-lettered bills and the 5 outline bills listed above.
13. Capture a **date** per row, and capture amendments, committee/markup votes, and nomination votes.

### Tier 4 — user-domain, evidence only (I will not touch these)
14. **Press stance.** 267 of 816 ACU rows (32.7%) have `stack_label != debate_stance`. `stack_label` is a
    **document-level label broadcast to every member anchor** — verified: cached text is byte-identical
    across all 7 anchors of the 2026-03-05 GAC article. Six of the seven members labelled "oppose" there
    are never criticised in the article; the only oppose language targets Marshall's bill. A verifier
    established those 7 rows carry zero score impact, so this is a labelling-hygiene issue, not a live
    scoring error. **Relabeling is Paul's call — this is evidence, not a proposal.**
15. **`press_date_overrides.json` holds 232 recovered dates that the scoring path never reads**, so 140
    undated articles are scored as if published today.
16. **SAFE/SAFER Banking Act is 14.5% of the plane** (5 bills, 1,416 weight) and has no home in ACU's live
    23-issue taxonomy or in the outline. It is also **entirely absent from the cosponsor network** (448
    missing pairs), so the same members are pushed up by one artifact and down by another. Scope call for Paul.

---

## PART 4 — ADJUDICATION RECORD

**Grok (adversarial counsel) verdicts on Fable's 13 findings**: 1 KILLED, 2 WOUNDED, 10 SURVIVE.
- **F2 KILLED — ACCEPTED.** Fable claimed "51% of pillar weight is on bills ACU never lobbied". The ACU
  letter corpus starts **2024-01-07** while the bill corpus spans 2021-2026, so absence of a letter proves
  nothing for 117th/118th bills — 58.2% of the weight. Restated: **3.5%** of the plane is bills with no
  credit-union nexus on their face (H.R.7910 Protecting Our Kids Act, H.R.4052 National Infrastructure Bank,
  H.R.793/S.255 RESTAURANTS Act, H.Res.634/H.Res.1076 National Small Business Week). SAFE Banking moved to
  an open scope question (item 16).
- **F1 WOUNDED — ACCEPTED.** 28.9% is raw pre-compression weight; the pipeline applies sqrt then clips, and
  21.1% of cells are already clipped. Reclassified DESIGN. Rank impact is **unmeasured** — measuring it
  needs a pipeline run, which is user-gated.
- **F3 WOUNDED — ACCEPTED the restatement, REJECTED the drop.** Grok wanted F3 dropped as a scope error.
  Rejected because it answers Paul's Q1 directly. Denominator corrected from 7% of all advocacy to
  **19% of congressional advocacy**, with agency filings excluded as out of scope by design.
- Two subagent findings were also refuted by their verifiers and are reported in corrected form only:
  "roll-call votes contribute zero" (the true mechanism is multiplicative gating on activity) and
  "S.2704 is a HIGH defect" (reclassified GAP/LOW, moved onto the registry).
