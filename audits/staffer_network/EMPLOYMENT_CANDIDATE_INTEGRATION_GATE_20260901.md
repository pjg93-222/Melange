# Employment candidate integration gate

This lane produces one deterministic diagnostic row for every sealed LDA source identity. It integrates candidate coverage only. Every row remains `REVIEW_REQUIRED`; no identity, employment fact, service date, or lifetime chronology is promoted to canonical status. Education is retained only as a nonblocking diagnostic.

## Runner

```powershell
python audits/staffer_network/merge_employment_candidate_coverage.py `
  --manifest audits/staffer_network/employment_candidate_integration_manifest_house_checkpoint_20260901.json `
  --output-dir audits/staffer_network/employment_candidate_coverage_house_checkpoint_20260901_a
```

The manifest is parameterized. Each optional candidate lane supplies `name`, `ledger`, `receipt`, and, when available, `verification`. Relative paths are resolved from the manifest directory. The House and Senate schemas currently observed are supported, including direct House service-date pairs, historical House ISO service-date pairs, and Senate `observed_report_intervals`.

## Binding gates

The runner fails closed before writing output when any of these conditions occurs:

- the validated public queue loses or duplicates an LDA source ID;
- the public or candidate receipt is not `PASS`;
- a supplied independent verification is not `PASS`;
- a ledger hash differs from the hash bound in its receipt;
- the public receipt or queue is not bound by the byte-twin validation receipt;
- a candidate references an LDA source ID outside the sealed public scope;
- a canonical promotion field, canonical identifier, adjudicated identity decision, or complete-lifetime assertion is nonzero;
- a receipt-declared candidate row count differs from the ledger row count.

The output is deterministic compact NDJSON in a gzip stream with `mtime=0`, sorted by sealed queue ordinal and LDA source ID. The receipt reports exact input hashes, scope conservation, source-specific candidate coverage, bounded/dated flags, explicit gaps, and zero canonical promotions.

## Current verified checkpoint

The public validation and final historical House v2 inputs produce byte-identical A/B twins:

- output rows and unique LDA source IDs: 25,340 / 25,340;
- historical House candidate coverage: 2,135 people;
- output SHA-256: `f4845ac4ffc98299f16948a75cfe6244c57c9848f915522b7cb4db7a72fa7e8e`;
- receipt SHA-256: `b9786b10e65c8a8574eac34dc92b8e1e94314989088b9e270eb14ee7b2210bf5`;
- canonical identity and employment promotions: 0 / 0.

## Final House + Senate integration

The independent Senate verifier landed `PASS`, so the final manifest now binds the validated public queue, historical House v2 candidates, and Senate 2011–2026 candidates. Primary and twin integrations are byte-identical and the independent integration verifier is also `PASS`:

- final payload SHA-256: `453d34666509a20c9154f775996824574e81cb31311c238f8e515d374c0c6f56`;
- final receipt SHA-256: `b9cbb4fcbaee00744c04eecf5e31f7b991ac5aeac0c175e0adf72f7873ec09fd`;
- independent verification receipt SHA-256: `602f24b64c5d8b1fbc34802c20d0ea708424560ab35f9dda4a12421bb1a51d06`;
- rows / unique sealed LDA IDs: 25,340 / 25,340;
- public candidate people: 12,653;
- historical House candidate people: 2,135;
- Senate candidate people: 2,798;
- people with no candidate in those three integrated coverage families: 11,720;
- bounded-interval candidate gap: 18,436;
- dated-former-position candidate gap: 16,652;
- canonical identity and employment promotions: 0 / 0.

No input dependency remains for this integration checkpoint. Corpus completion still depends on identity adjudication and gap-directed acquisition: all 25,340 rows explicitly retain the lifetime-history, unresolved-employment-gap, Hill-exhaustiveness, private-sector-exhaustiveness, and identity-adjudication gaps. These are substantive evidence gaps, not integration failures.
