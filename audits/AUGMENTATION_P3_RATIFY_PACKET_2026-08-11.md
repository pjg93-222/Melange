# Phase 3 Ratification Packet — Latency (2026-08-11)

Status: **RATIFIED — permanent, Paul 2026-08-11 ("Stamped with the P3.4
rejection").** P3.1 rubric and the law-5 basis refresh applied to
canon; **P3.4 explicitly REJECTED** (recorded, re-openable only if a
future client multiplexes MCP sessions); applied, synced, and committed
same session per law 7.

Status at drafting: PROPOSAL. Drafted under Meta LOOP run
`run-20260811T0045382019984Z-452513c655` (invariants pinned, event
`p3-invariants-pin`). P3.0 (epoch time-bomb hotfix) and P3.2
(front-loading text) landed untagged this phase; P3.1 and the law-5
basis refresh below await Paul's stamp; P3.4 comes with a SKIP
recommendation.

---

## P3.1 [RATIFY] — compact-mode rubric

**Honest framing first:** the roadmap bills this as "sharpens §0, does
not weaken it." It does sharpen the trigger from a size test to a risk
test — but it also WIDENS compact routing: a multi-file read-only
research task routes compact under the rubric where today's "trivially
small" wording arguably routes it full. That is a real coverage change,
priced deliberately: isolation buys its quality gain on mutating and
cross-lane work; pure-read work pays the multi-agent token multiple
without the gain.

**Proposed text — `.claude/commands/metaloop.md` § 0, replacing "Drop
to compact mode only when the task is trivially small (a single
read-only question, a one-line mechanical edit)":**

> Route by the two-question rubric at `-Action start` (Paul
> 2026-08-11): (1) does any node mutate state? (2) does any node's
> output feed another lane? Two noes route to COMPACT mode; either yes
> routes FULL. Log both answers in the plan. Max effort remains the
> default posture: the rubric pays the multi-agent price exactly where
> isolation buys the quality gain, instead of everywhere.

**Falsifiable check (post-stamp):** two consecutive qualifying trivial
tasks route compact with rubric answers logged; one non-qualifying task
routes full.

**Reversal:** restore the "trivially small" sentence.

---

## P3.3 outcome — law-5 parallel-dispatch re-test (dated observation,
2026-08-11)

Executed as roadmap-authorized: disposable sandbox worktree
`codex/p33-parallel`, two ledger-registered dispatches (`p33-probe-a`,
`p33-probe-b`) creating disjoint probe files, issued as parallel MCP
tool calls in a single message.

**Observation, two-sided:**

1. **The 2026-08-04..06 link breakage did NOT reproduce.** Both
   dispatches returned distinct threads, both files landed byte-exact
   (84 bytes each, LF), envelopes respected, zero cross-interference.
2. **True concurrency was NOT achieved.** The MCP transport serialized
   the calls: thread creation ~27s apart, file writes 23s apart
   (20:47:31 vs 20:47:54), zero execution overlap. "Parallel dispatch"
   through the current single MCP connection is queued dispatch.

**Consequence:** there is no latency prize to unlock — wall-clock
overlap is mechanically unavailable through this path — and therefore
no reason to spend an amendment relaxing one-writer serialization.

**Proposed law-5 basis refresh [RATIFY] — replacing the dated-basis
sentence in law 5:**

> The basis is a dated, re-testable observation, last re-verified
> 2026-08-11: parallel dispatches no longer break the MCP link, but the
> transport serializes them anyway — concurrency is mechanically
> unavailable, so serialization through the coordinator remains the
> practice by mechanism as well as by law. Re-verify before ever
> relying on parallel dispatch (recipe: audits/
> AUGMENTATION_P3_RATIFY_PACKET_2026-08-11.md).

## P3.4 — recommendation: SKIP

Disjoint-file ledger enforcement was conditional on a PASS that
unlocked value. The safety half passed; the value half failed
(serialized transport). Building enforcement for a capability that
cannot be exercised is dead weight. Recommend explicit rejection,
recorded here, re-openable if a future client multiplexes MCP sessions.

---

## Enforcement went live this phase — honest ledger state

The receipt epoch (2026-08-11T00:00Z) activated mid-phase. Current
audit: findings 39 = 37 legacy + 2 live receipt findings, both real
information:

1. `dispatch:phase4:r1` (run `phase4-tensor-20260810`) — **another
   lane's session** dispatched post-epoch without a receipt event. The
   enforcement caught cross-session governance drift mechanically.
   Not mine to clear; needs the other lanes' practice to adopt the
   ratified receipt flow (Paul's call on how to propagate).
2. `p33-probe-a` — a design wrinkle the re-test itself exposed:
   batch-registering both dispatches before executing closed probe-a's
   coverage window (1 second) before any receipt could land.
   Permanent honest record; fix is procedural (register→receipt→
   register) or a window-rule refinement (improvements queue).

**Pinned invariant #4 ("run ends findings==37, missing_receipt==0")
was MISSED** for exactly these two reasons, both stated plainly rather
than scrubbed.

## POTENTIAL IMPROVEMENTS added this phase (queue for Paul)

9. Receipt-window rule refinement for batch-registered dispatch pairs
   (see p33-probe-a above).
10. Cross-session propagation of the receipt law: other live lanes
    (`phase4-tensor`) dispatch under pre-augmentation habits; decide
    the adoption path (memory update reaches future sessions; live
    sessions need a nudge).
11. Executor receipt-block emission remains unreliable for NOVEL
    preamble text (6 of 8 initial drops across Phases 2-3; the verify
    tooth caught every one). Consider whether receipt emission should
    also be validated mechanically (e.g., dispatch wrapper checks the
    reply's first block) rather than by coordinator eyes alone.
