# Fable P2-CORPUS adversarial implementation review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

## Verdict: PASS

Fable ruled that P2-CORPUS can close on the submitted evidence. The build is
fail-closed at the load-bearing gates, the arithmetic proves exact conservation,
and the determinism defect was recorded, remediated, regression-pinned, and
retested with two fresh byte-identical real builds.

## Findings

### Medium — schema-validator coverage

The dependency-free validator did not implement `minProperties` or typed
`additionalProperties`, although the new corpus receipt uses both. Semantic
validation independently protected the committed receipt, so this did not
invalidate P2, but the schema layer had a silent gap and its docstring overstated
unknown-keyword enforcement.

### Low — production row validation

The fixture records ran through schema and semantic validation, while the
867,463 real LittleSis output records were only guaranteed by construction and
public-safety checks. Fable recommended one complete local validation pass.

### Low — boss-reference integrity

Dangling entity parent references were nulled and counted, but Position
`boss_id` values were namespaced without an explicit spine lookup. Malformed
values would fail closed, but dangling boss references were not receipt-counted.

### Low — output-root binding

The build accepted a caller-provided list of synced roots. An empty list could
omit the quarantine check, even though `fec/paths.py` defines the correct local
corpus root. Fable recommended binding the build to that configured root and
using built-in synced-root defaults.

## Verified evidence

- 424,323 + 1,456,165 + 3 + 0 + 0 = 1,880,491 relationships.
- The nine excluded category counts sum to 1,456,165; the three emitted
  categories sum to 424,323.
- 443,140 entities were emitted with zero invalids or duplicates.
- Input pins, profile readiness, legacy receipt/file binding, namespace gates,
  deterministic twin hashes, quarantine flags, test registration, and the
  committed receipt-hash chain were all verified by inspection.

Fable made no file changes. Codex remains the only writer. The four follow-ups
were non-blocking but are being remediated before final closure.
