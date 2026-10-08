# Fable C1 v4 document review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

The original C1R dispatch completed with `PASS`, but its stored result was
truncated. Fable independently re-read all six evidence files and returned this
bounded recovery receipt.

## Verdict: PASS

## Findings

- **LOW / accept:** Diagnostic section 7.5 lists three carried residuals where
  the C1 preflight named “two P2 residual gates.” The third (committee side,
  IPEDS/CIP, and container gold) is a pre-existing absent layer, not a P2
  regression. No document change is required.
- **INFO / accept:** The preservation test binds the 69/69 test result and all
  four 2026-08-29 document hashes. The review checked its required and
  prohibited text against the live v4 documents but did not re-execute the
  suite or re-hash the preserved files.
- **No arithmetic faults:** `424,323 + 1,456,165 + 3 = 1,880,491`;
  `443,140 + 424,323 + 5,773 = 873,236`; emitted categories
  `368,995 + 44,673 + 10,655 = 424,323`; the out-of-scope categories sum to
  1,456,165; and Transaction `35,268 = 35,265 + 3` rejects. The reported
  61.3477% undated share and 99.999840% acceptance rate recompute correctly.

## Verified scopes

- **C-6:** PASS for restricted source-native use only. Observational pairing,
  the unfrozen quality bar, disabled source, and open ShareAlike review are
  stated consistently.
- **C-10a:** PASS for conservation, coverage, and PII invariants only:
  5,773/5,773 records, 533/533 offices, and zero contacts. A-0 remains
  provisional pending Paul; append-only withdrawal is specified.
- **Q-1:** REPORT only. The 100-row all-MATCH calibration has undefined kappa,
  zero human gold, null precision, and a sealed single-use holdout. No threshold
  is frozen.
- **R-2:** PASS source-native with 38 contact redactions, two parent redactions,
  and zero boss redactions. Canonical-ledger R-2 is not exercised.
- **C-5:** FAIL / REMEDIATION RUNNING. The collection is not treated as a pass;
  terminal reconciliation is required.
- **I-16:** PASS for new same-machine twin-build determinism. The initial
  one-byte alias-tie failure and total-key remediation are disclosed;
  cross-machine determinism is unevaluated.
- **Readiness:** The package consistently distinguishes source-native substrate
  from canonical and analytical readiness: zero cross-source identity
  assertions, zero merges, zero nonzero temporal weights; canonical, analysis,
  and consumer enablement false; Politico, LDA, payroll, and the historic spine
  absent from this generation; `STAFF_NET=off` throughout.
- **Preservation:** The 2026-08-29 documents remain historical, hash-pinned
  records. The v4 documents supersede by date, not by editing old evidence.
  Fable made no file changes.

## Remaining gates

Paul's legacy A-0 ratification; LittleSis CC BY-SA publication review; terminal
C-5 LDA reconciliation; human I-4/Q-1 calibration and holdout packet; historic
member normalization; House and Senate payroll collection; two P2 residuals
(legacy per-record schema registration and a fabricated dangling-boss fixture);
and canonical fact, graph, analysis-loader, and per-consumer packets.
