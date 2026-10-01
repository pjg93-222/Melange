# Contested-bills registry + exposure-artifact fixes — DESIGN (APPLIED)

Status: **RATIFIED AND APPLIED** — Paul, 2026-07-31: "Apply" (same directive closed the
raw-FEC-bulk open item as not needed). Implemented via the Codex executor lane in
worktree cxwt-contested (branch codex/contested-bills), double sign-off complete
(fresh-thread Codex adversarial review + 3-lens workflow review, 19 findings
adjudicated: 8 fixed, 4 kept-with-disclosure below, 2 rejected as house-pattern
conformant). Supersedes CONTESTED_BILLS_DESIGN.candidate.md.

## 0. Corrections to the incoming handoff (verified against code)

1. Handoff commits `84f6f89` / `35e0958` do not exist in this repo; the work is
   `a425952` / `3f66ac9` / `a793db8`. Claims were verified against files.
2. No per-bill record store keyed `119:hr:1919` and no decision/reason/reversible/
   ratification-hash pattern existed anywhere. The design follows the repo's REAL
   patterns instead: `bill_rules` bill identity plus a `tier_overrides.json`-style
   user-ratified JSON registry with verbatim ratification notes.
3. "The correctly-scoped value exists inside the code" was true only for the oppose
   bucket; opposition-scoped support/mixed/conduit accumulators were new (trivial,
   same loop branch).

## 1. Three modes (ratified invariants)

- **Standard (default)**: receptivity, pivotality, access cost. No second-industry
  term. Structural default: no registry file or no record ⇒ standard.
- **Advisory**: counterparty read displayed beside the standard ranking; never
  reorders. Registry record with `"mode": "advisory"`.
- **Contested**: per individual bill with an explicitly selected industry set;
  never global. Registry record with `"mode": "contested"`. (Romero Moreno 2021
  second-party term; term = 0 collapses to standard. Engine wiring belongs to the
  coalition-builder redesign and its own APPLY — this change ships the switch and
  the exact data only.)

## 2. `contested_bills.json` — schema as SHIPPED

Location `MB_ROOT\contested_bills.json`; env dial `CONTESTED_BILLS_PATH` overrides.
The file is deliberately NOT created — absence IS the shipped standard-mode default.
Loader: `fec/lobbying/contested_bills.py` (`load_contested_bills`, `mode_for`, CLI `main`).

```json
{
  "_README": "User-ratified per-bill counterparty registry. Absence = standard mode.",
  "records": [
    {
      "bill": "H.R.1919",
      "congress": "119",
      "mode": "contested",
      "counterparty_industries": ["community_banks", "crypto"],
      "active_from": "2026-08-04",
      "active_to": null,
      "ratified_by": "Paul",
      "ratified_date": "2026-08-04",
      "note": "verbatim directive quote"
    }
  ]
}
```

Fail-loud validation (all raise `ContestedBillsError`, CLI exit 2): unreadable or
malformed JSON (a PRESENT-but-unreadable registry is never treated as absent — only
`FileNotFoundError` means absent); duplicate JSON keys; unknown top-level or record
keys; missing required keys; unparseable bill; bill with trailing text; the
documented-ambiguous `S.R.NNN` spelling (write `S.NNN` or `S.Res.NNN`); non-integral
or non-finite congress; congress outside 100–150; unknown mode; empty/unknown/
duplicate/ours-side counterparty industries; empty `ratified_by`; bad dates;
`active_to` < `active_from`; duplicate (bill, congress).

`mode_for(registry, bill, congress)` → `("standard", None)` for absent registry, no
record, or unparseable identifier (manual/letter evidence such as `LTR-*` is a
legitimate lookup and is never contested); `("standard", record)` for a dormant
record; `(mode, record)` for an active one. Congress accepts workbook-style
float-strings (`"119.0"`).

### Ratified amendments vs the candidate spec (disclosed at the gate)

- **Key is `bill_rules.bill_type_key` (type-aware 3-tuple), not the legacy 2-tuple
  `bill_key`** the candidate text named. The 2-tuple collides H.R.10 with H.Res.10 —
  precisely the mis-fire a ratification registry must exclude. Lookups go through
  `mode_for`, so the key shape is internal.
- **`active_from` defaults to `ratified_date`** when omitted: ratification activates
  the record unless a later start is written.
- **Closed-world schema**: unknown keys hard-fail as typo protection; free-text
  annotations belong in `note` (top-level `_README` allowed).
- **Registry load is strict about bill spelling; lookups stay permissive**, matching
  subsystem-wide prefix parsing.

## 3. Exposure-artifact fixes as SHIPPED (both pure write-time additions)

**Fix A** — four new member fields `opposition_assoc_{oppose,support,mixed,conduit}_total`
(directional buckets restricted to opposition-side industries). The four unprefixed
all-industry fields are retained unchanged for continuity; the oppose-direction
caveat was reworded to direct readers to the scoped fields. `RULE_VERSION` stays v1.

**Fix B** — `associated_by_industry[industry][cycle]` gains `assoc_support`,
`assoc_oppose`, `assoc_mixed`, `assoc_conduit` (refund-netted, may be negative,
clamp at point of use) and `assoc_relational_used` — the stored sum of ROW-level
clamps (sum-of-row-clamps ≠ clamp-of-sum for multi-candidate-ID members), which is
what makes industry-subset recomputation exactly reproduce the aggregate basis and
w_b. `_method()` documents both scopes.

## 4. Dials

- `CONTESTED_BILLS_PATH` — registry path override (default `MB_ROOT\contested_bills.json`).
- `CONTESTED_V1` — RESERVED consumer-side dial (0 = ignore registry); no consumer
  exists yet; activates with the coalition-builder APPLY.
- Producer fixes need no dial: additive keys, byte-stable otherwise (proven below).

## 5. Verification receipts (2026-07-31 session)

- Kernel tests (live tree): **89 passed, 0 FAILED**.
- `fec/tests/test_contested_bills.py`: **41 passed, 0 FAILED** (22 fail-loud cases).
- `fec/tests/test_opposition_prior_scope.py`: **10 passed, 0 FAILED** (opposition
  scoping, all-industry = ours + opposition, row-clamp proof, baseline AND
  current-cycle reconciliation, byte-level determinism, fail-loud intact).
- Live additivity + reconciliation (canonical old-code artifact vs new-code scratch
  rebuild, all 363 members): **PASS, 0 errors** — every pre-existing value
  identical except `provenance.generated`/`run_id` and the one reworded caveat;
  additions exactly the specified keys; opposition-scoped totals, all-industry
  decomposition, baseline/current relational bases, and clamp ordering all exact to
  the cent. (This is candidate-spec test 6, delivered as an executed transition
  proof — the pre-fix builder ceases to exist after commit, so it cannot be a
  standing test.)
- Registry smoke: absent file → `standard mode everywhere`, exit 0.
- Rank delta: structurally zero — no chain script touched; `fec_opposition_prior.json`
  and `contested_bills.py` have zero consumers (grep-proven).

## 6. Still open for Paul

1. Merge of this branch to main.
2. Coalition-builder consumer wiring (advisory column, contested w_b, Romero Moreno
   term) — that build's own APPLY; activates `CONTESTED_V1`.
3. LobbyView network-table acquisition.
4. Industry-set membership ratification.
(Raw FEC bulk pull: CLOSED — not needed, Paul 2026-07-31.)
