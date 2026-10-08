# Opus 5 post-block employment review — 2026-08-31

**Mode:** read-only static review, maximum effort  
**Verdict:** `BLOCKED`  
**Hash note:** the Claude sandbox denied `Get-FileHash`/Bash, so the reviewer
read the named working-tree paths but could not independently compute their
hashes. The Codex lane verified the pinned hashes before dispatch.

## Prior-blocker dispositions

1. **Date parsing: still blocking.** Arbitrary prose and malformed months/days
   were closed, but no employment-date ordering or project-window check existed.
   `raw_dates: "2099 to 1800"` and structured start `2099` / end `1800` could
   satisfy presence checks and certify.
2. **Current markers: closed.** Raw and structured currentness require a dated
   as-of bound.
3. **Year-bearing prose: closed.** Date atoms are full-match whitelisted.
4. **`UNRESOLVED` sentinel: closed in the core audit.**
5. **Duplicate person rows: closed in the core receipt.**
6. **Contradictory row/receipt verdict schemas: closed.**

The reviewer accepted the combined producer PASS logic, pre-write schema
validation, and conditional schemas as adequate. It correctly noted that four
additional conservation raises are algebraic safeguards, not independent
read-back verification.

## New blocking findings

1. `audits/staffer_network/consolidate_employment_corpus.py` hardcoded receipt
   `status: PASS` regardless of complete/partial/unresolved counts and performed
   no receipt-schema validation.
2. The consolidator accepted literal `UNRESOLVED` as a grouping key and silently
   dropped identity-less rows, permitting cross-person sentinel merging and
   unreconciled input loss.

## Important nonblocking findings

- IDs should be stripped before deduplication.
- RFC3339 retrieval/observation timestamps were not accepted as date evidence,
  which failed closed but reduced usability.
- A source as-of bound earlier than the episode start was not rejected.
- Core corpus PASS means all supplied rows pass; it is not an assertion that
  the supplied paths contain the sealed 25,340-person population.
- Input attestations remain trust-bearing adjudications and need a reviewer
  registry outside this function.
- Display-name typing, strict external receipt hash patterns, orphan artifact
  ordering on schema failure, and CLI traceback behavior remain hardening
  opportunities.

## Binding disposition

The `BLOCKED` verdict was accepted. The local lanes are repairing date
ordering/window/current-as-of logic and the consolidation receipt/identity
accounting. No PASS, canonical promotion, temporal readiness, or Meta LOOP
closure is inferred.
