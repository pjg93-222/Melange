# Opus 5 employment-completeness review — 2026-08-31

Meta LOOP run: `run-20260831T1850525496629Z-8993807782`  
Reviewer: Claude Opus 5, maximum effort, read-only  
Initial verdict: **BLOCKED**

The reviewer found that the current corpus remains fail-closed in practice because no
producer emits `history_completeness_attestation`, so no false `COMPLETE` result has
shipped. It nevertheless identified latent false-completion paths that would become
active once attestations are introduced.

## Blocking findings

1. **HIGH — collected gaps did not reach the employment verdict.**
   `consolidate_employment_corpus.py` collected gap strings from all source rows but
   passed only the selected base row's attestation to `audit_history_completeness`.
   A base PASS attestation could therefore coexist with a merged unresolved gap.
2. **HIGH — one row's attestation could certify a merged episode union.**
   Consolidation unions episodes from every source row but inherited the attestation
   from only the preferred row. The attestation was not cryptographically bound to the
   episode set it adjudicated.
3. **MEDIUM — arbitrary nonempty date strings passed.**
   Values such as `unknown` and `n/a` satisfied the start/end checks.
4. **MEDIUM — whitespace and non-URL source strings passed.**
   Values such as `"   "` or `"legistorm"` satisfied the sourcing check.
5. **MEDIUM — an empty typed gap field shadowed a nonempty legacy gap field.**
   `unresolved_employment_gaps: []` hid a populated `unresolved_gaps` list.

## Nonblocking findings

- The canonical employment-episode shape is intentionally rejected by this working-
  history audit unless it is adapted; this is fail-closed.
- v2 audit rows were stamped but did not yet have a dedicated JSON Schema validation.
- An unresolved seen profile shared residual priority with a complete profile.
- Education could be labelled complete without an education-exhaustiveness attestation;
  this did not affect the binding employment verdict.

## Confirmed behavior

Education deficiencies remain visible as diagnostics and do not enter employment
`failure_codes`. The reviewer confirmed that the user's employment-first ruling was
implemented correctly.

## Retention ruling

The reviewer ruled the stage safe to retain as a diagnostic surface while acquisition
continues, but not safe to use `COMPLETE` as a gate until the blocking findings are
repaired and re-reviewed.

## Remediation status

Remediation was opened immediately after this verdict. The blocking findings were not
waived. A separate Opus 5 re-review must issue the terminal verdict for this stage.
