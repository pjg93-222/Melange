# Fable P2 residual-closure preflight review

Meta LOOP run: `run-20260830T0416179390616Z-17a7cf4477`

## Verdict: PROCEED

The two residuals are real and the proposed closure matches them. The committed
corpus advertises `staffer-network-legacy-source-native-record-v1`, but that ID
has no registered schema. The boss-redaction path also has no fixture coverage.

## Binding requirements

1. **Schema parity, not substitution.** Require exactly all six existing keys,
   reject extras, and bind `source_system_id` to
   `quorum-legacy-derived`. Preserve the per-row public-safety scan and exact
   record-count check in construction and local validation.
2. **Derive types from sealed rows.** Scan the 5,773-row production file before
   fixing value types. Run upgraded validation against the accepted local
   generation and bind the PASS to corpus receipt hash `3914df98…`. Do not
   replace the committed receipts.
3. **Keep publication closed.** Registering the schema removes the prior
   incidental unregistered-schema barrier. Add an explicit refusal in
   `publish_generation` (or equivalent) for this restricted schema plus a
   negative-control test.
4. **Boss negative and positive controls.** Cover a spine-absent ID, a valid
   in-spine ID, and a malformed non-integer ID. Assert redaction counts, null
   output for bad values, valid namespacing for the good value, and absence of
   the dangling identifier from emitted bytes.
5. **Preserve byte gates.** Update the registered-schema census from 25 to 26;
   rerun the complete staffer suite and preservation tests. Do not edit any
   2026-08-29 document and do not claim closure of the separate committee,
   IPEDS/CIP, and container-gold residual.
6. **No gate movement.** Do not enable source, analysis, LDA, Politico,
   identity resolution, consumers, or `STAFF_NET`.

Fable also suggested validating a non-null boss ID's LittleSis namespace in
row semantics. This is accepted as a cheap defense in depth.
