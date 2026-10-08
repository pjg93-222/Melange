# Legislation computation decisions required before shadow acceptance

Status: **PENDING — no production or mainframe promotion permitted**

The user directed the refresh to follow the existing computation method and to
surface anything wrong. The audit found five decisions that cannot be inferred
without changing scores. This template is fact-bound to audited layout SHA-256
`f772257658b3600da54e59dd30db587f8bc027de2f164af9a7eb30887a7d3437`
and production workbook SHA-256
`5c61cab60f4831fb5842fa8c20c2703c05a986b2a7e32e39f61fe3a08cc19c31`;
those bindings are evidence, not approvals.

1. **Role weights are consumer-specific in the current system.** The archive
   uses Sponsor/Original/Later = 3/2/1; the workbook grid is exactly
   4/2/1; stance uses 1/1/1; say/do uses 1/.5/.25; and the base network uses
   Original = 1 and Later = .5, divided by the square root of current
   cosponsor count. Selecting one global policy would not preserve the current
   method. The recommended resolution is an explicit
   `consumer_specific_legacy_preservation` profile rather than silently forcing
   one policy across every consumer.

2. **Congress decay has not been selected.** The current production schedule is
   119/118/117/116 = 1/.8/.64/.512. The proposed aggressive scenario is
   1/.66/.33/.16. Asking whether to use the aggressive scenario staged it for
   comparison; it did not authorize cutover. Any selection must bind bills,
   letters, roll-call diagnostics, efficiency, and every downstream consumer
   to the same declared schedule.

3. **Legislative efficiency omits CU Tax Status.** The workbook unambiguously
   maps AG:AW to 17 individual categories—Examination through Mortgage—with
   533 formulas per slot. `Table1` ends at `EM`, while the CU Tax block is
   `EW:FD`; there is no evidence that two categories share a column. A uniform
   18-category replacement therefore requires an explicit decision about
   adding/routing CU Tax and may change ranks.

4. **Accepted CFPB bills need an explicit activity-column route.** The audited
   legacy CFPB `CU`/`CW` cells contain manual sign-on-letter units, `CV`/`CX`
   are dead zero, and the remaining columns hold cosponsor activity and
   success rates. Accepted CFPB Sponsor/Original-Cosponsor bill relationships
   therefore have no unambiguous legacy activity destination. Dropping them
   would violate coverage; mixing them with letters or repurposing a dead-zero
   column would change the computation. The numeric producer fails closed
   until this routing is approved.

5. **Five press-based non-legislative vectors are row-misaligned in the legacy
   workbook.** Press order places André Carson before Andrea Salinas and the
   three Andrews; legislative/sublayer order places him after them. The
   existing literal row formulas therefore swap press contributions among
   André Carson, Andrea Salinas, Andrew Clyde, Andrew Garbarino, and Andrew
   Ogles. A same-method shadow must preserve the literal row semantics, but
   production promotion requires an explicit choice between preserving the
   legacy result and repairing it with a member/Bioguide join.

Audited special-value semantics must also be handled explicitly:

- `Legislative Score - Raw!CU3:CU535` and `CW3:CW535` are decay-weighted
  sign-on-letter units, not bill relationships. They must be recomputed from a
  hash-bound staged copy of `manual_bill_evidence.csv` under whichever schedule
  is explicitly approved. The old letter values cannot be mixed with a newly
  selected bill schedule.
- `CV3:CV535` and `CX3:CX535` are explicit dead-zero siblings.
- `AV3:AV535` and `DX3:DX535` are authored one-decimal success percentages;
  their prior 0.05 percentage-point residual is storage precision. Their old
  values cannot be preserved when the accepted bill corpus changes; the
  approved uniform success definition must regenerate them and declare the
  materialization precision.

The two contradictory gate contracts have now been replaced with typed,
fail-closed contracts:

- `cu-tax-efficiency-treatment-v1` preserves the 17 audited singleton slots
  and can represent either legacy AG:AW omission with CU Tax's separately
  recomputed `FB` generic-success metric, or an explicitly named audited-slot
  merge with workbook-fact and rank-effect acknowledgements. It never invents
  a merge and remains blocked until a choice is explicitly approved.
- `cfpb-accepted-bill-sponsor-original-route-v1` permits `UNSELECTED` only
  when a generation has no matching accepted relationships. A named route
  requires explicit approval and a registered physical implementation. The
  registry is intentionally empty, so invented or unimplemented routes fail
  closed until the selected route is actually implemented.
- `press-member-alignment-policy-v1` is bound to the exact audited layout SHA
  and normalized mismatch facts. Preserve-literal validates only the current
  literal-row reconstruction; repair requires a different audited sidecar that
  proves a Bioguide join was actually applied. Missing, unapproved, stale, or
  inconsistent choices fail closed.

The shadow workbook producers fail closed unless generation-bound approvals
and a complete numeric recompute plan explicitly resolve these issues. Until
then, no recalculated rank claim is valid.
