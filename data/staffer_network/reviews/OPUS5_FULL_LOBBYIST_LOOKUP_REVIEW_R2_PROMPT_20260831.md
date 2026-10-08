# Opus 5 max review — full lobbyist lookup corpus only

Read-only review. Do not edit or use the network. In
`C:\Users\pgoff\OneDrive\Desktop\Melange Systems`, inspect only:

- `fec/staffer_network/employment_history.py`, function `build_lookup_queue` and its helpers;
- the two `employment_lookup_*.schema.json` files;
- the employment-lookup branches and registry entries in `publication.py`;
- the lookup tests in `test_staffer_employment_history.py`;
- `C:\Users\pgoff\AppData\Local\Melange\staffer_network\employment-lookup\generation-20260831T050000Z\employment_lookup_receipt.json`;
- the upstream LDA receipt named inside that receipt.

The user asked to materialize every local LDA lobbyist as an employment-history lookup task.
Claimed result: exactly 25,340 unique LDA person rows partitioned P0=6,527, P1=2,957,
P2=15,856; output SHA-256
`5e240a91a21e237525547eef84456daee7dd5339723073ced9437a9f5ea5f649`; zero accepted
identity matches and zero merges. Discovery queries and covered-position text must remain
leads, not canonical identity/date facts. The full suite reports 113 passed, 65 subtests.

Return concise Markdown beginning exactly `PASS`, `CONDITIONAL PASS`, or `FAIL`. Review only:

1. source/file/candidate binding and persisted-row conservation;
2. deterministic output;
3. zero-merge/review-required enforcement;
4. restricted-publication containment;
5. whether any receipt PASS field is materially self-attesting;
6. missing adversarial tests that block this lookup corpus from shipping.

Do not review or gate the unpopulated temporal sidecar in this pass.
