# Opus 5 temporal-math micro-review

Use Opus 5 maximum effort, read-only. Inspect only:

- `STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md` sections 6–8;
- `fec/staffer_network/employment_history.py` from interval-bound helpers
  through `build_temporal_sidecar`;
- `fec/staffer_network/publication.py` temporal path/edge validation;
- `fec/staffer_network/schemas/temporal_build_receipt.schema.json`;
- temporal tests in
  `fec/tests/staffer_network/test_staffer_employment_history.py`; and
- `audits/staffer_network/M1_MATH_ADVERSARIAL_AUDIT_20260901.md`.

Return `VERDICT: PASS` or `VERDICT: BLOCKED`, then `BLOCKERS`,
`NONBLOCKING_FINDINGS`, `EQUATION_CHECKS`, and exact file/line `EVIDENCE`.

Check only:

1. uncertain half-open interval conversion preserves day/month/year precision;
2. union-before-overlap prevents repeat observations multiplying time;
3. guaranteed and possible overlap bounds are ordered and the duration
   transform `1-exp(-days/365.2425)` is bounded/monotone;
4. revolving paths require accepted identity/container and guaranteed
   Hill-before-industry ordering; primary organization edge counts unique
   persons;
5. the declared 730.485-day half-life is sensitivity only;
6. client-activity participation and registrant employment remain distinct;
7. `INTERVAL_BLOCKED` accepted pairs retain one deterministic zero-weight path
   with null gaps and conserved receipt count, emit no edge, and cannot crash;
8. wrong-order, possible-only, and blocked cases cannot leak primary weight;
9. inverted bounds, NaN/division, double counting, and causal-language
   counterexamples.

Correct temporal math does not authorize running it over review-candidate
identities or incomplete employment histories.
