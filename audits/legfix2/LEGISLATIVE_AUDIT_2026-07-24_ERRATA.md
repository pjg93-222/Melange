# LEGISLATIVE_AUDIT_2026-07-24 — ERRATA (2026-07-25)

Corrections established by the legfix2 evidence-recompute campaign (deterministic offline
re-derivation from hash-manifested copies; every number verified by an independent
7-agent adversarial pass). The original report is archived beside this file in
audit_sp_reference/ — it previously existed only in a volatile session scratchpad.

1. MIS-SCOPED (Q3/item 16): "SAFE/SAFER ... 448 missing cosponsor pairs" — 448 is the
   H.R.2891 (118th) single-bill count from net_gap2.py's TOP-ZERO table. The five-bill
   family total is 472 directed pair-instances vs the June-25 BASE network, and 108
   unique symmetrized pairs vs the production (newest AUG) artifact. Different units
   AND different artifacts; the report conflated them.
2. NOT-REPRODUCED (Q3/item 16): the "1,416 weight" for SAFE/SAFER reproduces under no
   documented method (selected-only p9-exact = 1,231.84 = 12.59%; all-dispositions =
   1,499.84). Best available correction: 12.59% of the plane, not 14.5%.
3. UNDERCOUNT (Q3): "efficiency 30% is 90.7% empty ... 7 categories constant zero" —
   generic-scope recompute gives 91.23% (8,753/9,594 cells) and EIGHT constant-zero
   categories: CU Tax Status was missed.
4. FIELD CONFLATION (Q1): "296 of 297 manual rows are LTR-* letters with
   Role='original-cosponsor'" — 296 is the LTR-any-role count; 284 are
   original-cosponsor; all 297 rows pass the sponsor-substring gate (the load-bearing
   say-do claim stands).
5. POSITION SUM (Tier 1): cu_bill_directions.json's "63 bills (54/6/1)" sums to 61.
   Two bills (HR8398, HR8413) carry BLANK positions — they need adjudication before
   any wiring.
6. REFINEMENT (Q2): Interchange "36 rows, 6 bills, all one act" — one act FAMILY
   (Credit Card Competition Act) in three title vintages (2022/2023/2026).
7. SCOPE CONFIRMED (Q5): the 'disapproval' guard's "0 of 11,283" holds exactly for
   CCM-branch firings (the claim's intended scope). Corpus-wide, 228 titles carry the
   literal — context, not contradiction.
8. DEFINITION SENSITIVITY (Q4): the press-cache "median 1,927 chars" reproduces only
   under verify3.py's exact definition; independent variants give 1,894-1,940.5. The
   floor claim ("counts are FLOORS") is robust to all definitions.
9. NEW WORKBOOK FINDINGS (beyond the audit): Raw-vs-Normalized row-2 weight
   inconsistencies at DP2 (TCPA) and EF2 (Mortgage & Housing) — Raw carries 0 while
   Normalized has no weight cell (behaviourally inert today); header drift at
   EK1/EL1/EM1 (underscore vs space) and EN1 (Raw header absent). Known findings
   CP1/P2/X2/DG2 confirmed.
10. PROVENANCE RESOLVED (Q2): the bill archive's producer was Paul, hand-driving the
    congress.gov API browser — one query per category sheet, pasted across its result
    rows (the recovered catalog: 16 queries; Interchange = 1 atom; CDFI Fund and
    CU Tax Status never configured). Recovered spec: audits/legfix2/
    bill_archive_provenance.json + BILL_ARCHIVE_PROVENANCE.md; standing guard: C13.

Unresolved residue (honest opens): Blended-sheet columns CU/CW (CFPB Restrain
Sponsor/Original) unidentified within one bill-unit (0.64/0.8 decay); AV/DX generic
Success Rates 0.05pp off the sibling-mean formula (NEAR-MISS-DIVERGENT); E16's
reported 1,416 weight unreproduced; ACU-side reverse-gap counts remain the cached
2026-07-24 GraphQL pull (re-fetch = network, user-gated).