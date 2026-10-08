# Reversible legislation junk-pile contract

Version: `acu-legislation-junk-pile-v1`

The junk pile is an audit-only, reversible view over the preserved legislation
candidate corpus. It does not delete or edit discovered candidates. It does not
authorize scoring, synchronization, promotion, workbook publication, or any
mainframe write.

## Evidence ledgers

`exclusion_decisions.ndjson` is append-only. Every exclusion records:

- the complete original candidate payload, or an immutable source path,
  locator, byte count, and SHA-256;
- candidate ID, decision ID, UTC decision time, reviewer, and tool version;
- a versioned rule, substantive reason, evidence, and provenance;
- an assertion that the candidate remains in the discovery corpus;
- a self-hash and a link to the preceding record hash.

`restoration_decisions.ndjson` is a separate append-only ledger. A restoration
names and hashes the exact exclusion decision it reverses and carries its own
reason, evidence, provenance, reviewer, UTC time, tool version, self-hash, and
hash-chain link. Restoration never edits or removes the exclusion record.

## Fail-closed state

Effective state is computed deterministically by candidate ID. Computation
fails closed on malformed or noncanonical records, self-hash or hash-chain
drift, a changed immutable source, duplicate candidate exclusions, duplicate
decision IDs, unknown restoration targets, candidate/target conflicts,
duplicate restorations, or target-decision hash drift.

Each successful audit creates a new state-hash-addressed snapshot. Historical
receipts bind the exact prefix and tail of both ledgers, so subsequent
truncation or rewriting is rejected. Existing evidence and snapshots are never
overwritten.

## Human review and recovery

Every successful state snapshot contains:

- `CURRENT_VIEW.md` and `current_view.csv` for human inspection;
- `current_junk_pile.ndjson` with full reversible evidence;
- `restored_candidates.ndjson` containing candidates brought back;
- `audit_receipt.json` with hashes, counts, integrity checks, and explicit
  no-scoring/no-sync/no-promotion/no-mainframe policy.

The command-line manager is `fec/manage_legislation_junk_pile.py`. The initial
operational ledger is intentionally empty. No candidate may be culled until a
review decision supplies all required evidence and provenance.
