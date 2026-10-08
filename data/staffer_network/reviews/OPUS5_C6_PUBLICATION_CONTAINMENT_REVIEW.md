# Opus 5 C-6 Publication-Containment Review

**Reviewed:** 2026-08-30  
**Model:** `claude-opus-5` (canonical model reported by Claude Code)  
**Verdict:** **PROCEED**  
**Blocking findings:** None

## Scope

Read-only adversarial review of the restricted LDA source-native publication
boundary: `RESTRICTED_SCHEMA_IDS`, the LDA-specific industry-edge schema and
producer, publish/load rejection paths, and their negative tests. The generic
industry-edge schema intentionally remains available for a future reviewed
derived layer.

## Verified controls

- Restricted schemas are rejected before publication staging writes bytes.
- Restricted manifest entries are rejected before payload loading.
- The LDA industry schema excludes `HILL_TO_LOBBYING_TRANSITION`.
- LDA rows carry their restricted schema ID and cannot validate under the
  generic industry-edge schema because it is closed to extra properties.
- The source-native receipt conserves the five required output roles.

## Nonblocking findings and disposition

1. Role-to-schema binding was free-form. **Remediated:** semantic validation
   now pins every LDA receipt role to its exact schema ID.
2. LDA edge endpoint namespaces were weak. **Remediated:** schema patterns and
   semantic kind-to-prefix checks now bind lobbyist, activity, registrant, and
   client namespaces.
3. Reverse relabeling lacked a negative test. **Remediated:** LDA edge bytes
   advertised under generic `industry-edge-v1` are rejected.
4. Restricted enrollment coverage was hard-coded. **Remediated:** tests now
   assert the restricted set is registered and exercise every member.
5. Load-side forgery covered only a subset. **Remediated:** every restricted
   schema ID is exercised.
6. Offset-bearing timestamps were compared as strings. **Remediated:** emitted
   LDA timestamps normalize to UTC microsecond `Z` form before min/max.
7. Bare numeric/string `const` rules inherited boolean-permissive validation.
   **Remediated:** explicit JSON types now accompany all three constants.
8. Full-directory atomic promotion remains an optional future hardening; the
   builder requires an empty output root, writes file bodies atomically, and
   emits a terminal receipt only after successful completion.

## Residual boundary

Publication safety remains a claim-governance boundary, not a content
classifier. The restricted source-native schemas and candidate schemas are
mechanically blocked; any future public derived LDA layer still requires its
own review and authority packet.
