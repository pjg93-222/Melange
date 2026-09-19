# Independent review of the four-priority candidate

Reviewed 2026-09-13 UTC. Result: **PASS for the isolated implementation and frozen-data reconciliation described below.** This is not a finding of predictive validity, causal attribution, or optimal calibration.

The final artifacts are [generation_03/board.json](C:/Users/pgoff/Mentat/outputs/pesv_implementation_20260913/generation_03/board.json) and its independent repeat, [generation_04/board.json](C:/Users/pgoff/Mentat/outputs/pesv_implementation_20260913/generation_04/board.json). Both have complete receipts, all recorded gates pass, and production activation is false.

## Review method

I read the candidate engine and runner, the original legislative methodology, and the canonical frozen inputs. I independently streamed the raw bill, impact, role, signal, and historical roster files with a separate standard-library calculation. That calculation did not import the candidate engine or any production module. It checked the contribution traces against raw records, recomputed the chamber denominators, recomputed available member totals and percentiles, and verified file hashes. I wrote only this review; no production or frozen input was changed by the review.

The full arithmetic check first examined generation_02. I subsequently confirmed that every member record, historical metric, chamber aggregate, policy, and numerical summary is exactly equal in generations 02 and 03. Generations 03 and 04 have byte-identical board, contribution ledger, HTML, Markdown report, and all three copied candidate source files. The final runner adds frozen-manifest integrity validation without changing the mathematics.

## Mathematical findings

The implementation follows strict P, then E, then S, then V ordering. Lower criteria stop contributing after an unavailable higher criterion. Comparisons use stored values rather than display rounding. I independently reconstructed the ordering and matched every strict rank in both 533-member boards. All published primacy values match the frozen authoritative factor file exactly. Institutional position is absent from the new scoring dimensions and ordering.

The progressive effectiveness calculation is:

`E_i = (N_chamber / 5) * sum_stages sum_measures [impact_b * signed_CU_ib * active_role_credit_ib * timing_ib / chamber_impact_total_stage]`.

All five stage shares are additive, without another progression multiplier. Chamber denominators include the full eligible universe and remain positive; CU sign, roles, and timing affect individual credit only. Later cosponsor credit uses the first join delay and H=180 days. Sponsor/original/later role weights are 1, 0.5, and 0.25. The source's documented pre-introduction official committee activity remains in denominators, while members receive no credit before joining or at/after withdrawal. Later milestones can credit an official sponsorship after the member leaves office; joining itself requires verified service.

For substance, the engine divides the sum of positive-CU/role/timing-weighted impact by the same positive engagement weights. Volume is the sum of those engagement weights, with no impact multiplier. This separates average substance from amount. Each member-measure appears once in engagement volume; stage records remain separate progressive results.

Checks against the raw files found:

- **4,716 stage contributions:** every independently recomputed amount matched exactly, with maximum numerical error zero. The 19 negative contributions remain negative: seven in Congress 118 and twelve in 119.
- **3,833 engagement contributions:** source CU values, impact weights, role credits, timing, and beneficial-volume arithmetic matched. No duplicate member-measure engagement or duplicate member-measure-stage trace was present.
- Every credited stage had an active raw official role at its recorded date. No pre-join or withdrawn-stage credit was found.
- Every available member E and V matched the independently summed contribution ledger exactly.
- Every historical chamber percentile matched the first-tie share-below convention, floored to five decimal places, with the correct available-peer count.
- Every one of the **886 available historical substance means** was exactly 5 and every corresponding substance percentile exactly 0. This reflects uniform provisional selected impact data, not a substantive distinction among bills.

For a concrete signed arithmetic check, the 118:hr:3881 sponsor BILL contribution is `(451 / 5) * (5 / 53260) * 1 * (-1) = -0.00846789335336087`, exactly matching the trace.

## Denominator and population reconciliation

The independently recomputed values below exactly match both final generations. The five named 119th House placeholders are the only derived reserved-number exclusions.

| Congress | Chamber | Historical N | Eligible measures | BILL | AIC | ABC | PASS | LAW |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 118 | House | 451 | 10,740 | 53,260 | 6,892 | 5,460 | 3,129 | 679 |
| 118 | Senate | 105 | 5,755 | 28,611 | 3,420 | 3,501 | 1,345 | 415 |
| 119 | House | 449 | 10,450 | 51,874 | 6,728 | 4,866 | 3,346 | 325 |
| 119 | Senate | 104 | 5,567 | 27,735 | 3,414 | 2,847 | 991 | 196 |

The 119 House BILL denominator removes 25 impact units for reserved H.R. 2, 3, 5, 8, and 10, whose frozen records have the exact reserved title and no actions. Original input records remain intact. The canonical 118 closing-day introduction remains included and disclosed. Sixteen pre-introduction official milestones in 118 and six in 119 remain disclosed rather than silently repaired.

## Ranking and integrity results

Congress 118 has 428/533 available displayed E values; Congress 119 has 459/533. Unavailable accepted alignment scopes remain unavailable: two member-measure scopes in 118 and six in 119. Other absent evidence is not converted to zero.

Ranks change for 149 members in 118 and 138 in 119, but **no tier memberships change**. Both boards preserve the published tier membership and seat counts: 13, 24, and 48, with 448 untiered. I independently checked exact primacy values, legacy rank/tier mappings, candidate seat boundaries, the 0.75 CU-primary evidence floor for every seated member, recorded conduct ceilings, and 533 unique candidate ranks. All checks passed. The receipt separately confirms exact reproduction of the baseline by the copied tier helpers.

The review identified a runner gap: merely hashing the consumed files did not prove they matched their frozen manifest. The final runner now checks the five required legislative artifacts against the frozen manifest's SHA-256 values and byte sizes before staging a result. I independently verified all ten artifact/hash/size comparisons, five per Congress. Both final receipts record the integrity gate as passed.

For each final generation, all **31 recorded input hashes** still match the current files, and every recorded output hash matches its file. This includes the production baseline inputs, frozen evidence, and final candidate sources. The deterministic artifacts are byte-identical across generations 03 and 04. Receipt timestamps and output paths appropriately differ.

- Final board SHA-256: `b40581ce2b1e98f07fd71789f065d0c9cdc0bf27ca438094831671787dc3c830`
- Final contribution ledger SHA-256: `f0faf8b6a004273024fcf76ba2c6cbb9238294ae7295f2206ced3f19ea72b269`

## Limits on interpretation

E measures progressive realized output, not a member's per-attempt passage rate. It is participation attribution and can grow with activity volume. The H180 timing policy remains illustrative and uncalibrated. All selected impact weights remain provisional 5, so current evidence supplies no substantive tie-breaking power. Missing letter dates/signatures are not invented. The frozen archive is internally reconciled but not independently certified complete against a live congressional inventory. Both Congresses are retrospective comparisons using current primacy, not an out-of-sample validation. These limitations are appropriately preserved in the final reports and receipts.

Implementation references: [metric calculation and finalization](C:/Users/pgoff/Mentat/outputs/pesv_implementation_20260913/src/pesv.py:340), [priority ordering](C:/Users/pgoff/Mentat/outputs/pesv_implementation_20260913/src/pesv.py:430), [frozen-manifest validation](C:/Users/pgoff/Mentat/outputs/pesv_implementation_20260913/src/replay_pesv.py:99), and [original methodology](<C:/Users/pgoff/OneDrive/Desktop/Melange Systems/research/LEGISLATIVE_IMPACT_EFFECTIVENESS_IMPLEMENTATION_PLAN_2026-09-10.md:221>).
