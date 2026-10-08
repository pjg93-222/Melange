# Phase 2 Ratification Packet — Context Hygiene (2026-08-10)

Status: **RATIFIED — permanent, Paul 2026-08-10 ("Both stamped — apply,
sync, commit").** P2.2 extraction charter and P2.3 threshold (70% soft /
85% band) applied to canon, synced, and committed the same session per
law 7. Untagged items (P2.1, P2.4 policy + mechanism) landed at the same
gate. The POTENTIAL IMPROVEMENTS queue below remains open — nothing in
it was acted on.

Status at drafting: PROPOSAL for the two [RATIFY] items below. Drafted under Meta
LOOP run `run-20260810T2339180731141Z-2dad99c8b2` with invariants pinned
in the coordination ledger (event `p2-invariants-pin`) and quoted
mechanically per the stamped P1.3 law. Untagged Phase 2 items (P2.1
tool-result clearing, P2.4 provenance policy + `fact` mechanism) landed
under normal Fable review this run and await only the commit gate.

---

## P2.2 [RATIFY] — Gemini extraction charter

Without this stamp, routing documents to Gemini remains a lane
violation: law 1 and the metaloop routing line currently read "Gemini is
only for real media perception."

**Proposed text — `.claude/commands/metaloop.md`, replacing the routing
clause "Gemini is only for real media perception":**

> Gemini is only for real media perception and, under the extraction
> charter (Paul 2026-08-10), bulk-text extraction: bulk raw corpora
> (long documents, large text sets) may route to Gemini as an
> extraction lane when the coordinator's context must stay clean.
> Structured findings return with location pointers under the
> TRANSCRIPTION / INFERENCE / ILLEGIBLE shape; the raw bulk never
> enters the coordinator's context.

**Proposed text — `.claude/skills/gemini-perception/SKILL.md`, new
section after Task fit:**

> ## Extraction charter (Paul 2026-08-10)
>
> Bulk raw text (long documents, large text sets) may route here as an
> EXTRACTION dispatch when the coordinator's context must stay clean:
> same contract fields, same report shape — TRANSCRIPTION carries the
> verbatim extracts with locations, INFERENCE carries conclusions
> anchored to them, ILLEGIBLE flags unreadable regions. The raw bulk
> never travels back; findings and pointers do. Everything else about
> the lane is unchanged: no decisions, no code, no scoring; the
> fabricated-anchor rule applies identically. First live use doubles as
> the charter's verification run (no invented work before then).

**Expected effect:** the coordinator's context is protected from bulk
ingestion — the complement of P2.1's clearing policy. The lane widening
is formal and bounded rather than an ad-hoc violation under pressure.

**Reversal:** revert both texts; the lane returns to
perception-only.

---

## P2.3 [RATIFY] — soft context ceiling threshold value

The policy text is in canon (uncommitted, this run) with the value
pointing here. **Proposed value: the soft line is 70% of the visible
context window; the end-of-window band is the final 15%.** Between
70% and 85%: finish the current node, reconcile to the ledger, emit the
soft-ceiling reconcile event, then continue. Past 85%: no new dispatch
work — reconcile and let compaction land on a clean state.

**Expected effect:** compaction/summarization always lands on a
reconciled ledger state instead of mid-node; the coordinator never
plans work inside the documented degradation zone.

**Reversal:** delete the threshold sentence; the policy text without a
value is inert.

---

## Record — untagged items landed this run (normal review, commit gate)

- **P2.1** tool-result clearing + **P2.4** provenance policy: canon
  text in `.claude/commands/metaloop.md` § 3 (uncommitted).
- **P2.4 mechanism** on branch `codex/p2-provenance` (uncommitted):
  `fact` event type — claim fingerprint + verbatim string provenance,
  validated raw-side AND sanitized-side (repr-laundering and alias-key
  paths both closed), orphan rejected at insert naming its trigger_key,
  `facts_missing_provenance` audit array gating `--strict`. 88/88
  tests; live ledger invariant intact (findings 37, all new keys 0).
  Independent review: F1 HIGH + F2 MEDIUM found, fixed, re-verified.

## Live receipt-protocol evidence from this run

The stamped RECEIPT law fired twice on live dispatches (author round 1
led with HANDSHAKE; reviewer led with the verdict): both caught at
Fable's verify gate, receipts obtained, zero spec distortions found in
the corrected receipts — first live `receipt` and `invariants` ledger
events recorded. Across Phases 1-2: 4 of 6 explicit receipt demands
were initially dropped regardless of channel; the verify tooth caught
all 4 at one round-trip each. The tooth, not the channel, is the
enforcement — exactly as adjudicated from Grok's K2.

## POTENTIAL IMPROVEMENTS accumulated (none acted on; Paul's queue)

1. Pin `sha256` fields to exactly 64 lowercase hex chars (review, P2.4).
2. Decide whitespace-only provenance validity (review, P2.4).
3. True byte-capture for receipt-event fingerprints (currently
   pointer-string fingerprints; coordinator could save dispatch/reply
   bytes to files automatically).
4. Read-only audit connection: `CoordinationLedger` creates/initializes
   the DB even for `audit` of a nonexistent path (P0.1 review).
5. Dispatch effort/tier pin validates the raw payload — same alias-key
   hardening as attribution/fact gates would close it (P0.2 review).
6. `--glassbox-dir` path/symlink policy; non-finite token floats
   (P0.1 review).
7. Tie-break policy for equal dispatch timestamps in receipt windows;
   whether receipt/invariants bookkeeping events should count in
   run_metrics node timing (P1 review).
8. Audit flag for multi-dispatch runs lacking an invariants pin
   (queued mechanization from the P1 adjudication, informational
   first).
