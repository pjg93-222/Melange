# Opus 5 employment audit core re-review — 2026-08-31

Meta LOOP run: `run-20260831T1850525496629Z-8993807782`  
Reviewer: Claude Opus 5, maximum effort, read-only  
Verdict: **PASS_WITH_NONBLOCKING_FINDINGS**

The reviewer confirmed closure of the original malformed-date, malformed-source,
typed/legacy-gap-shadowing, stale-digest, row-schema, and education-blocking findings.
It also confirmed that dating, gap adjudication, episode-set binding, and person-ID
presence now fail closed.

Remaining findings accepted for hardening, not waived:

- A missing source person ID returned an incomplete row that then failed the strict
  result schema, aborting corpus output instead of reporting the bad row.
- Any nonempty `support_observation_ids` string satisfied provenance without an
  observation index proving that the identifier resolved.
- `raw_dates` used substring tests for `present`/`current`.
- The audit receipt itself lacked JSON Schema validation.
- A completeness attestation was not yet attributed to a reviewer or timestamp.
- ISO-shaped impossible dates were not rejected.
- `asserted_current` lacked an explicit as-of bound.
- Receipt row counts could be mistaken for distinct-person counts.
- Completeness `PASS` used a separate status vocabulary without a named constant.

The reviewer ruled the repaired core safe for dating, gap, digest, and person-ID
gates, but not yet sufficient by itself to claim verified provenance. Remediation
continues under the same stage; a fresh terminal verdict is still required.
