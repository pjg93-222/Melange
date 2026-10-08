# Claude Opus 5 handoff — employment and temporal gates

**Date:** 2026-09-01  
**Reviewer:** Claude Opus 5, maximum effort  
**Mode:** read-only; do not edit code, artifacts, receipts, prompts, or source documents

## Current state

- The sealed universe remains exactly **25,340 LDA source IDs**. A5b is unchanged at P0/P1/P2/P3 = **11,720 / 4,932 / 1,784 / 6,904**.
- A7, A8, and A9 are independently verified `PASS` artifacts, but every added observation or match remains review-only. A9 is an immutable scheduling sidecar; it does not overwrite A5b.
- A5c remains **`BLOCKED_PARTIAL_RECOVERY`**. Its verifier reports `audit_status=PASS` for honest accounting and `acquisition_state=BLOCKED`; these are not contradictory.
- Local M1 math review is `PASS` after a fail-closed `INTERVAL_BLOCKED` repair. That local result is evidence, not an Opus verdict.
- The Opus structural-math micro-review returned **`PASS`**. It does not cover temporal math, identity, employment completeness, canonical data, or causal interpretation.
- The broad network/temporal Opus review and the temporal micro-review both timed out with **no output and no verdict**. Do not infer either `PASS` or `BLOCKED` from a timeout.
- The narrower Opus interval/co-tenure and revolving-door micro-reviews both returned **`PASS`** with no blockers. The 900-second terminal employment review and both 600-second core/consolidation reviews timed out with no verdict. Their direct constituent reviews now establish scoped code-safety `PASS` results for employment identity normalization, consolidation identity/accounting, consolidation merged-attestation, and consolidation receipt/determinism after two receipt blocker rounds. Those scoped results do not establish actual employment-corpus completeness. Meta LOOP remains `BLOCKED`.

## Verified A5c blocker

The target is 52 House quarters from 1996Q1 through 2008Q4. Candidate books were discovered for 12 quarters and no candidate was discovered for 40 quarters. Twenty-three authorized Google Books candidate IDs were tested: one direct PDF and 22 HTTP-200 CAPTCHA HTML bodies. Only 1997Q1 Part 2 was acquired and extractable, leaving 51 target quarters unacquired.

That one OCR-derived report produced **4,939** deterministic personnel candidates. They are report-period-bounded observations from a Google Books scan, not an official House-hosted PDF, identity proof, continuity evidence, or complete employment history.

| A5c artifact | On-disk SHA-256 |
|---|---|
| Independent acquisition/accounting verifier | `3407342f66586390e99dbd830f7c7f1fc45f949526ab442c8c4d10feb3c44d38` |
| 1997Q1 Part 2 extraction receipt | `3f748b20c8760e56c98fa1c677bacdd27e98567fd5a9994ae090f2b3ee091530` |
| 4,939-row personnel ledger | `99ce0f633f56d12c4fbce615371d3604a22353411d68c7d25de226e4fd1d89b6` |
| Acquired source PDF | `21bb07508249c8ec28dd731a64bdc343cdc6347c3355b0523fc6e011104215d4` |

## Verified A7–A9 evidence

### A7 — machine-local inventory

- Exact coverage: **25,340 people**.
- LD-203: **143,513 affiliation candidates / 22,754 people**. Registrant affiliation is not employment and is not consumed as employment by A9.
- FEC: **979 three-anchor employer point observations / 37 people**, including 14 beyond the A4 no-candidate baseline. A point observation is not a former position or bounded interval.
- Build receipt: `f005be8f5999dcf006dbdd7093cec12356d9cb35376a6dbc228ef4af9bcfaa1c`.
- Independent verifier: `7c8402784db9861c928bd4045ac7792022d96a92d18bf7e9d91bf38d3590d969`.
- Payloads independently recounted on disk: coverage 25,340 (`2532d2946bd352359c9c79c30156d130a171e88fb3d05f628bfee6545f526546`); FEC 979 (`6f67f0d8c731277a761ad0d18ad1610e57d21d371dfc38f5a84982ed9063db35`); LD-203 143,513 (`bdcd2452afeb6b8f12457e1ef61dcf9e7c6785994ebebb1dc50d1e3688f1fbb2`).

### A8 — 1997Q1 House-to-LDA match candidates

- Input: **4,939** source rows. Output: **453** match rows covering **388** LDA people.
- Ambiguity: 143 ambiguous candidate rows and 310 single-candidate rows. “Single” still does not mean adjudicated identity.
- A5b people with a report-bounded candidate by original bucket: P0/P1/P2/P3 = **77 / 89 / 43 / 179**.
- Producer receipt: `8c3f5abba8c6f81b4afea2a1646add11a7c98fa5bb5964f9a6dd402a3cda93e8`.
- Independent verifier: `e05c9e31b32229b116ec91c043950ec84321ff5e3d88a9cc77cdb6038bd5e87d`.
- 453-row payload: `fd7adbdd68cd9c23fb511ae737c1892e4d50212207f434d4e0a5f96fd8918607`.

### A9 — immutable A7/A8 priority sidecar

- Exact output: **25,340 unique IDs**; provider overlap is zero.
- Evidence combinations: FEC-only 37; A8-only 388; both zero; neither 24,915.
- FEC point observations cause **zero** bucket moves. A8 causes 209 moves to P3: 77 from P0, 89 from P1, and 43 from P2; 179 A8 people were already P3.
- Revised scheduling buckets: P0/P1/P2/P3 = **11,643 / 4,843 / 1,741 / 7,113**.
- Producer receipt: `ebb40e26c4eaf2766024b47a1b32cd51666c411c669d239e06ee517141d59f1f`.
- Independent verifier: `0b1dca553a254c686bee197d172e0d35ce1a86eb27a3ddf2c2bf7c4960423429`.
- 25,340-row payload: `f7e3350f122b5d5c5347baabf4ec1e268c00e300df282ae61db78ab0b8a68423`.

All A7–A9 receipts and payloads above were re-hashed on disk. Primary/twin equality, zero canonical promotions, source binding, and token-negative checks are asserted by their independent verifiers.

## M1 repair and completed structural review

M1 reproduced a valid-schema crash when an accepted Hill/industry pair lacked an ordering boundary: `transition_gap_bounds` returned `INTERVAL_BLOCKED`, but selection fell through to `min([])`. The repair retains exactly one deterministic blocked path per key, emits null gap bounds and zero weights, excludes it from edge aggregation, conserves it in receipt counts, and gives it precedence over `WRONG_ORDER` when no guaranteed or possible pair exists.

- M1 diagnostic (`PASS after one fail-closed temporal fix`): `0d6eb3dd36874946b8e330a9e6dfbbb2ce3b9536e2cc0e7a063bd44749ad5354`.
- M1 focused evidence: **43 passed** — 7 graph, 33 employment-history, and 3 interval tests.
- Current `employment_history.py`: `6d6003112388a9986b70f8a69822024fdf9d1be4932f40e6e34a849ea3dd6bad`.
- Current `publication.py`: `84ab032b0896373887fd42cf1f539b0c19458044aa7d18efd4aeb22691a49b9f`.
- Opus structural-math `PASS` review: `d3395163eb706710cbf9c80cddf113428c94484eeee369ac1d60aa8d3abcfeb3`.
- Current `network_math.py`: `011ae4dcb7e4611f5215fa0ac1a9fb24950a24984f65844ae3419f316a3daf5c`. The phrase flagged by the review is absent from the current module label; treat the review as an equation-level PASS, not a claim of byte-identical review coverage after its recorded snapshot.

The structural review found no invalid emitted structural values. Its eight nonblocking findings remain backlog items, including direct dangling/candidate-exclusion tests, caller-side dedup hardening, bridge edge cases, clearer within-kind documentation, and canonical-ID-order assertion.

## Timeout records are non-verdicts

| Attempt | Result | On-disk SHA-256 |
|---|---|---|
| Broad network/temporal Opus review, 900 seconds | no review text; no verdict | `964afb74b6ac3a55a94af6d96697fd73809a3455710a63384f8e442de3a3496b` |
| Temporal-math Opus micro-review, 600 seconds | no output; no verdict | `9b95e8b40ae2678fc9b5cf1ca677e80e218d7e93a8e5d98901c46e87bf6a9724` |
| Terminal employment-gate Opus review, 900 seconds | no output; no verdict | prompt `64a0eafe4384391aa91912b1543307b68c3d7eac1b7b0a7225ddf7a0d4c74ed2`; timeout record `de39ba0228b8b9d0b791a14207345bc647edb58637c9b0d22dea8df0e168ae37` |
| Employment-core terminal Opus review, 600 seconds | no output; no verdict | prompt `b34ce9aeadfc54cddae0b9527f1db7494902a85b8651ad0a8c98a0a56abd7a24`; timeout record `54d727f73e08b82f32d5e4b13ddca4b5d6bb6286d69815800f586d4e1abe1482` |
| Employment-consolidation terminal Opus review, 600 seconds | no output; no verdict | prompt `3b43fa1f0101936cf0e951a6cf15d9cf92a9bc538783574c4aa640e67194c074`; timeout record `c88b03867879acaf81bf6a7405add2f875ae3a5a444e4c44f1756aba391ed171` |

These records preserve failed review attempts only. They remain non-verdicts even though later direct constituent reviews produced scoped merits results. Local tests and scoped `PASS` results do not replace the missing broad verdict.

The later scoped interval/co-tenure review returned `PASS`, blockers none (`OPUS5_INTERVAL_COTENURE_MICROREVIEW_20260901.md`, SHA-256 `1417a683ec41f873eaf31a04cc0d70324cb9f1d38a7281a3978c18337d952586`). It accepted half-open normalization, union-before-overlap, guaranteed-versus-possible bounds, the duration transform, and duplicate suppression. Its nonblocking backlog includes direct transform/guard tests, multi-row integration coverage, and the fact that right-censored episodes without an upstream as-of clamp are fail-closed and may understate possible upper bounds. This scoped PASS does not retroactively convert either timeout into a broad verdict.

The later scoped revolving-door review also returned `PASS`, blockers none (`OPUS5_REVOLVING_DOOR_MICROREVIEW_20260901.md`, SHA-256 `58db6b2e3ca1b4d7cc03131407d358521655ba5538c6d3e236e5a4425625c01f`). It accepted the ordering partition and gap bounds, unique-person raw weights, ordered decay sensitivity, role separation, deterministic zero-weight `INTERVAL_BLOCKED` paths, edge exclusion, schema/publication validation, and receipt conservation. This is a code-and-validation-path verdict only: it does not authorize scoring review-candidate identities, incomplete histories, or causal language, and it does not convert either timeout into a broad verdict.

Retain the revolving review’s nonblocking backlog:

1. `possible_weight` on revolving paths is an upper gap-decay factor, not a probability or an upper bound on unit primary contribution; cross-predicate aggregation is prohibited.
2. Publication validation should independently enforce `gap_decay_lower <= gap_decay_upper <= raw_weight` and primary weight exactly one for a guaranteed path.
3. Defensive skips for missing member/organization IDs need dedicated receipt counters even though upstream validation should reject those accepted rows.
4. Reverse-order paths display zeroed gaps, so consumers must read status with gaps; their weights remain zero.
5. Three zero-valued receipt invariants are literal fail-closed assertions rather than independently measured counts.
6. Direct coverage remains thin for possible-only, wrong-order, blocked/wrong precedence, deterministic multi-candidate selection, multiple people per edge, and numeric decay sums.
7. `interval_from_episode` relies on upstream as-of clamping for current episodes; absent bounds fail closed as `INTERVAL_BLOCKED`.
8. A selected path carries provenance for only the chosen episode pair; discarded candidates for the same key are not emitted.

## Terminal-employment constituent disposition

The original terminal prompt (`OPUS5_EMPLOYMENT_GATE_TERMINAL_REVIEW_PROMPT_20260901.md`, `64a0eafe4384391aa91912b1543307b68c3d7eac1b7b0a7225ddf7a0d4c74ed2`) timed out after 900 seconds. Its timeout record (`OPUS5_EMPLOYMENT_GATE_TERMINAL_TIMEOUT_20260901.md`, `de39ba0228b8b9d0b791a14207345bc647edb58637c9b0d22dea8df0e168ae37`) explicitly returns no verdict. It preserved all nine routes by splitting them into core and consolidation surfaces.

The core prompt (`OPUS5_EMPLOYMENT_CORE_TERMINAL_MICROREVIEW_PROMPT_20260901.md`, `b34ce9aeadfc54cddae0b9527f1db7494902a85b8651ad0a8c98a0a56abd7a24`) then timed out after 600 seconds. Its timeout record (`OPUS5_EMPLOYMENT_CORE_TERMINAL_TIMEOUT_20260901.md`, `54d727f73e08b82f32d5e4b13ddca4b5d6bb6286d69815800f586d4e1abe1482`) also explicitly returns no verdict. Its unchanged five routes are split again, without dropping any requirement.

The consolidation prompt (`OPUS5_EMPLOYMENT_CONSOLIDATION_TERMINAL_MICROREVIEW_PROMPT_20260901.md`, `3b43fa1f0101936cf0e951a6cf15d9cf92a9bc538783574c4aa640e67194c074`) likewise timed out after 600 seconds. Its timeout record (`OPUS5_EMPLOYMENT_CONSOLIDATION_TERMINAL_TIMEOUT_20260901.md`, `c88b03867879acaf81bf6a7405add2f875ae3a5a444e4c44f1756aba391ed171`) returns no verdict and preserves the unchanged consolidation gate in three exact line-bounded surfaces.

Current direct-constituent disposition:

1. **Employment date/identity plus completeness normalization — post-fix `PASS`.** The date/identity prompt (`OPUS5_EMPLOYMENT_DATE_IDENTITY_MICROREVIEW_PROMPT_20260901.md`, `8c881a548512e22b4cea1b1bb5afe799e7ac45318a9715460cc06090ca5a8cd6`) initially returned `BLOCKED` because top-level and nested nonblank IDs were not compared (`OPUS5_EMPLOYMENT_DATE_IDENTITY_MICROREVIEW_20260901.md`, `f670dcd937b005a200e6d0bf74eaa2209594b72915b44614fa85845e45d790d2`). The completeness/attestation prompt (`OPUS5_EMPLOYMENT_COMPLETENESS_ATTESTATION_MICROREVIEW_PROMPT_20260901.md`, `a18c047f08de0d90bb7d34f3b578755495bede219381a1b626e4753b04e02161`) also returned `BLOCKED` because validated IDs could still be emitted without normalization (`OPUS5_EMPLOYMENT_COMPLETENESS_ATTESTATION_MICROREVIEW_20260901.md`, `b20583cb9acf5da29efef57bf1bab1b9dde0de2cfd85dc6e327860fb0a011a65`). One fresh post-fix prompt (`OPUS5_EMPLOYMENT_IDENTITY_CONFLICT_POSTFIX_PROMPT_20260901.md`, `a17c2c220984faf5488b82a3173f03e73459e3590471562ec210898363f12c1f`) covered both accepted repairs; its review returned `PASS`, blockers none (`OPUS5_EMPLOYMENT_IDENTITY_CONFLICT_POSTFIX_REVIEW_20260901.md`, `d1464db753e98fbb5bfa9a56ee0412098166ecdd16a90e5feaf3eddf40e6ebd8`). This is identity/date/completeness code safety only.
2. **Consolidation identity/accounting — `PASS`.** The exact prompt is `OPUS5_CONSOLIDATION_IDENTITY_ACCOUNTING_MICROREVIEW_PROMPT_20260901.md` (`254e9c8820d0be21b7af9dcbc4ee320cf21b4206a1a05c5fa90fdbef86fddda5`); the result returned `PASS`, blockers none (`OPUS5_CONSOLIDATION_IDENTITY_ACCOUNTING_MICROREVIEW_20260901.md`, `8745ba3bf4202d2794274bf90c4dd622c0daa7675e7b5917b271c27c9c9e9c75`). It accepts fail-closed blank/whitespace/sentinel/conflicting IDs, separately conserved unidentified rows, normalized duplicate accounting, and exact row/person conservation on the reviewed code path.
3. **Consolidation merged-attestation — final `PASS` after two blocker rounds.** The original prompt is `OPUS5_CONSOLIDATION_ATTESTATION_MICROREVIEW_PROMPT_20260901.md` (`8a0150269db6038fd49fa51f767e4e03c8e9e8c30b87008be64992aae0b43e80`). Its nominal `PASS` result contained a conditional missing/null typed-gap laundering issue that the coordinator conservatively escalated and repaired (`OPUS5_CONSOLIDATION_ATTESTATION_MICROREVIEW_20260901.md`, `8dff169b62140ffcfdda4d36ee290a3fdcb47806bc7a16cf8ca6078349a131b0`). The first post-fix prompt (`OPUS5_CONSOLIDATION_ATTESTATION_POSTFIX_MICROREVIEW_PROMPT_20260901.md`, `755ff66bc08baf2e2cb42a911c15b371635db3b996fbaaf255a6cc1e2114e137`) then returned `BLOCKED` for discarded non-list legacy gap evidence (`OPUS5_CONSOLIDATION_ATTESTATION_POSTFIX_REVIEW_20260901.md`, `602f9d81a873fe58fa0fa14a48b55dd81b22e3a220b351dcba7ad179fe508678`). After the second repair, the final review returned `PASS`, blockers none (`OPUS5_CONSOLIDATION_ATTESTATION_FINAL_REVIEW_20260901.md`, `2dc3dec1bf6104a644ed2a567390714aa885c54fdd2cf3394b11883a41f7c04d`).
4. **Consolidation receipt/determinism — final `PASS` after two blocker rounds.** The original prompt is `OPUS5_CONSOLIDATION_RECEIPT_DETERMINISM_MICROREVIEW_PROMPT_20260901.md` (`670eb138e0ccde419f4010e53189c8f1bf3f8d8b101270e6b8d250753bc67257`). Its result returned `BLOCKED` for trusted rather than independently re-derived conservation booleans, unidentified-reason totals not required to sum, and duplicate-person counts not coupled to duplicate rows/output uniqueness (`OPUS5_CONSOLIDATION_RECEIPT_DETERMINISM_MICROREVIEW_20260901.md`, `641c02f5082af1fc5d0f6ad7fe04633a50a3892fd4ffdae4ec7b4299bc5f92a0`). After the first repair, the post-fix review remained `BLOCKED` because the row-to-person bridge and residual-incomplete identity were not re-derived (`OPUS5_CONSOLIDATION_RECEIPT_POSTFIX_REVIEW_20260901.md`, `6385bad0acd601759e60c8a56f064c9e57e634af6537cedef578d92772078ffe`). Both findings were repaired and adversarial forged-receipt tests were added. The final re-review prompt is `OPUS5_CONSOLIDATION_RECEIPT_POSTFIX_MICROREVIEW_PROMPT_20260901.md` (`a2bbaa7ea6b7cac1738f7e122214983a0254d366393f21b31630e5f263a10211`); the final review returned `PASS`, blockers none (`OPUS5_CONSOLIDATION_RECEIPT_FINAL_REVIEW_20260901.md`, `eb9f118cb4f5e9ff3db65fbce753b85e58fb9415f1b874857d75d8429b7559ba`). This is receipt-internal semantic safety only; it does not reopen artifacts, recompute their hashes, or establish actual corpus completeness.

Latest on-disk code and test evidence:

| File | SHA-256 |
|---|---|
| `fec/staffer_network/employment_history.py` | `6d6003112388a9986b70f8a69822024fdf9d1be4932f40e6e34a849ea3dd6bad` |
| `fec/tests/staffer_network/test_staffer_employment_history.py` | `9c9b37a7e3fbeb0b19cf50a053383909758236399608784f26a473c3bf50be40` |
| `audits/staffer_network/consolidate_employment_corpus.py` | `b6bade2d542a9e2650a615dbca5bc48c574e40a0426ea1fe916a2bd27fc42c7c` |
| `audits/staffer_network/test_consolidate_employment_corpus.py` | `18d915149ee74e8acb6474444213df1503596de5ec6516307804eea07edac63d` |
| `fec/staffer_network/schemas/working_history_corpus_receipt.schema.json` | `607d072aa4da2f45a2da7eed68fc758e95031fbdac9fae5e3820417d0ee1cbf0` |

The latest measured Python evidence is **48 focused tests, 222 staffer tests, and 73 subtests, all passing**, as recorded in the final receipt review; the reviewer inspected the code and did not rerun those tests. These tests support implementation safety and do not establish corpus completeness.

The completed scoped reviews establish code-level employment-completeness and receipt safety only. They do not establish actual 25,340-person completeness, adjudicate identity/employer/container/chronology, authorize canonical promotion, open temporal scoring, or close the project.

## Controlling non-claims

- No artifact establishes full lifetime employment coverage for any of the 25,340-person universe.
- No candidate, exact name match, numeric-ID equivalence, FEC observation, LD-203 affiliation, A9 move, local test, or review `PASS` is a canonical identity or employment promotion. Promotions remain zero.
- A5c is not complete; its extraction/verifier PASS values do not clear its acquisition blocker.
- Structural, interval, revolving, and direct terminal-constituent Opus `PASS` results do not open temporal scoring over the current corpus. All five timeout records remain non-verdicts, and code safety remains distinct from actual-corpus completion.
- Correct temporal code would still require accepted identity/container decisions and admissible employment intervals; the present review-candidate plane cannot enter canonical temporal outputs.
- Nothing in this handoff authorizes public-release readiness, causal/influence claims, a composite influence score, canonical-network mutation, or Meta LOOP closure.
