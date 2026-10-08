# Opus 5 interval/co-tenure micro-review

Maximum-effort, read-only. Inspect only these functions in
`fec/staffer_network/employment_history.py`:
`normalize_bound_to_half_open`, `union_ranges`, `intersection_days`,
`episode_core`, `episode_envelope`, `co_tenure_bounds`, and
`duration_weight`; plus only their tests in
`fec/tests/staffer_network/test_staffer_employment_history.py` and sections 6
and 9 of `STAFFER_NETWORK_MATH_ADJUDICATION_20260831.md`.

Return only:

- `VERDICT: PASS` or `VERDICT: BLOCKED`
- `BLOCKERS:` or `none`
- `CHECKS:` half-open precision, union-before-overlap, guaranteed <= possible,
  monotone bounded `1-exp(-days/365.2425)`, no repeated-observation inflation
- `EVIDENCE:` file/line citations

Do not inspect revolving, acquisition, identity, graph, or consolidation code.
Correct math does not open any data or canonical gate.
