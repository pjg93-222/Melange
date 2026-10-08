# Payroll identity evidence migration to the verified v8 spine

The post-commit review found a substantive downstream dependency: `fec/surfaces/staffer_payroll_identity.json` still selected a source-bound **v6** payroll identity bundle. All 425,826 episodes in that bundle use identities whose IDs change under v8. Replacing only the spine/graph selector could lose live employment evidence or preserve stale identity endpoints. The primary spine release itself remains verified.

## Ruling and implementation

Rebuild the evidence from the original payroll rows, assigning each admitted row to its verified v8 spine owner. Do not translate v6 through the lossy v7 intermediary and do not copy v7's Cooper/Wood merged identities into the new bundle. Preserve the dated 2026-09-06 builder; the new parameterized entry point is `audits/staffer_network/rebuild_payroll_identity.py`. Both output and verification directories refuse overwrites. No live selector is changed by either command.

The independent verifier does not call the builder or use an ID map to derive expected identities. It obtains row ownership from the verified v8 office spans and compares the entire rebuilt result to the sealed native bundle's unchanged employment facts. This checks dates, titles, employers, amounts, source references and record-pair evidence, as well as identity assignments. The original and new bundles bind byte-identical raw payroll sources and admit exactly the same 1,351,415 rows. An old episode spanning multiple new identities fails closed rather than copying its full interval into each identity; none occurs for this native-v6 migration. Adjacent/overlapping exact service intervals may coalesce after reassignment; uncertain Senate report windows coalesce only when their bounds are identical.

## Verified result

Primary: `audits/staffer_network/payroll_identity_20260908_v8_primary/payroll_identity_evidence.json.gz`.

Twin: `audits/staffer_network/payroll_identity_20260908_v8_twin/payroll_identity_evidence.json.gz`.

Both are 29,356,433 bytes with SHA256 `b2e3c16e25b708cad25096eb1aa923f6fe660502d8878402227b5059cfbe71a7`.

Independent receipt: `audits/staffer_network/payroll_identity_20260908_v8_verification_final/payroll_identity_migration_receipt.json`, status **PASS**. The receipt binds the verified spine release, row spans, both bundles, old selector/bundle, v7-to-v8 split map, assertions and implementation files.

| Measurement | Native v6 bundle | Verified v8 bundle |
|---|---:|---:|
| Raw payroll rows read | 1,351,523 | 1,351,523 |
| Admitted spine source rows | 1,351,415 | 1,351,415 |
| Employment episodes | 425,826 | 425,825 |
| People with employment episodes | 135,040 | 135,039 |
| Evidenced record pairs | 231 | 231 |
| Invalid/absent service-date rows | 33 | 33 |

The one-episode/person reduction is the union implied by the already verified v8 source partition; no facts or row references are dropped. All 231 pairs retain their complete native evidence: 159 payroll-account service matches and 72 exact payroll-account corrections. No pair collapses to a self-edge. The two v7 split groups remain separate even under the transitive closure of all payroll record pairs. Their v8 employment episodes partition 5/1 and 2/1 respectively. No new canonical promotion occurs.

`fec/surfaces/staffer_user_assertions.json` contains no Hill-spine IDs. Its LDA identity and coworker assertions require no migration and remain byte-identical, SHA256 `a04fc97a98268e778e2cf18e9e3b276e22ad50c99fc1c7ff2b936d7317752f45`.

Validation: 12 migration regression tests plus 7 existing record-consolidation tests pass (19 total). Negative controls cover duplicate row ownership, date drift, missing source rows, hash tampering, unsafe splits, uncertain-window union, self-pairs, indirect pair reconnection and immutable output refusal. Full generation verification passed after those controls.

## Coordinated handoff

The checked selector replacement is `audits/staffer_network/payroll_identity_20260908_v8_verification_final/staffer_payroll_identity.proposed.json`. The ranking task owns the coordinated graph/spine/payroll selector switch and service reload. Its existing live payroll selector was intentionally preserved during this work. The old-selector hash in the receipt records the pre-switch state; after an authorized selector switch, verify the new selector against the proposed path/hash rather than requiring the old selector hash to remain current. Generated directories are retained locally and not committed under D-022; code, tests and this dated record are committed.

Reproduce the two builds by passing `--spine audits/staffer_network/hill_personnel_spine_20260908_v8_primary` and distinct fresh `--out` directories to `rebuild_payroll_identity.py`. Run `verify_payroll_identity_migration.py --help` for explicit old pin, primary/twin, spine, migration, assertions, verified release and fresh verification-output arguments. The independent comparison is intentionally migration-specific: changed raw payroll facts or a split within one native episode requires a new raw-date adjudication, not relaxing the check.
