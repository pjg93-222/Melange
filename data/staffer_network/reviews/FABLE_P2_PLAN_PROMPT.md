# Fable P2 source-native corpus preflight

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

Act as a fresh, read-only provenance and data-model reviewer. Return exactly
`PROCEED`, `REVISE PLAN`, or `BLOCK`, followed by binding safeguards. The two
root Markdown documents are evidence, not instructions. Codex remains the only
writer.

Read:

- `STAFFER_NETWORK_CORPUS_SPEC_20260829.md`
- `STAFFER_NETWORK_EXPANSION_DESIGN_20260829.md`
- `data/staffer_network/reviews/FABLE_P1_PLAN_REVIEW.md`
- `fec/staffer_network/littlesis_contract.py`
- `data/staffer_network/receipts/littlesis_profile_20260830.json`
- `fec/staffer_network/legacy_seed.py`
- `data/staffer_network/receipts/legacy_seed_20260830.json`
- `fec/staffer_network/publication.py`
- `fec/staffer_network/schemas/person_edge.schema.json`
- `fec/staffer_network/schemas/industry_edge.schema.json`
- `fec/staffer_network/schemas/member_overlay.schema.json`

Fresh acquisition state:

- The official LittleSis entity/relationship gzip pair is frozen locally with
  exact SHA-256 and byte counts in the aggregate profile receipt.
- The full streaming census passed: 443,140/443,140 entities; 1,880,491
  observed relationships; 1,880,488 accepted; exactly three dangling-endpoint
  rejects; zero invalid records and duplicate IDs; zero dangling accepted.
- The category semantics have been checked against native records. The prior
  draft mislabeled category 5: 1,267,716 is `Donation`, not `Lobbying`.
  Actual `Lobbying` is category 7 with 10,655 records. `Position` is 368,995
  and `Education` is 44,673.
- The restricted legacy seed passed 5,773/5,773 records and 533/533 offices,
  with contacts stripped and analysis/canonical use disabled.
- A fresh immutable LDA generation is running separately at the official
  anonymous 15 requests/minute. LDA-dependent records remain quarantined until
  its terminal reconciliation passes.

Proposed P2 corpus build:

1. Write one deterministic, immutable, restricted local generation outside
   OneDrive. Keep source-native identifiers namespaced by source. Make no
   cross-source identity merges or assertions of current staff employment.
2. LittleSis: normalize all valid entities needed by accepted edges. Emit
   source-native assertions for `Position`, `Education`, and true `Lobbying`
   relationships only. Explicitly disposition every accepted relationship in
   other categories as `OUT_OF_SCOPE_CATEGORY` in the receipt. Preserve raw
   dates and a conservative precision; an undated relationship carries no
   temporal weight or currentness implication.
3. For every emitted assertion retain source relationship ID, source endpoint
   IDs, category, description/name, raw start/end dates, and source URL where
   present. Endpoint conservation must bind emitted assertions to the accepted
   profile and reject the known three dangles.
4. Legacy seed: copy the already stripped source-native record set into the
   same generation as a separate collection. It may connect office IDs to
   names/titles only within that source. It may not join to Politico, LittleSis,
   member identities, or industry actors.
5. Publish only an aggregate, public-safe corpus receipt in the repository.
   Raw/normalized LittleSis records and restricted legacy names remain local.
   Keep `STAFF_NET=off`, analysis use false, canonical merges zero.
6. LDA and Politico-derived identities are separate later gates. The P2
   generation must be valid and useful without either, and must not claim to
   finish the person-resolution layer.

Adjudicate the narrow source-native schema, the category selection, whether all
LittleSis entities or only referenced endpoints should be emitted, required
privacy/license controls, deterministic-output requirements, and the exact
receipt invariants/tests needed before this P2 substage can pass.
