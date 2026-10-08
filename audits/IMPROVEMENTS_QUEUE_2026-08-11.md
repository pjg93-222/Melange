# Improvements Queue — standing record (opened 2026-08-11)

Status: **FILE-OF-RECORD, OPEN.** The item #11 specification below is
**STAMPED — permanent, Paul 2026-08-11 ("stamp item #11 and dispatch
C1+C3 to Codex")**. The stamp ratifies the spec as the plan of record;
execution proceeded stepwise by Paul's order and is now **COMPLETE**:
C1+C3 `295068ee1` → merge `f437a3830`; C4 `e5e9f19c0`; C2 `c01d48596`
→ merge `93c972422`. 119/119 tests on main, copy-synced 4/4 by md5,
mirror synced. C4 landed before C2 because enforcing tag coverage
before the tag convention exists would fail every receipt for want of
tags.

## Why this file exists

POTENTIAL IMPROVEMENTS raised under law 2 have been recorded inside
whichever phase packet happened to be open when they were raised. That
works while the phase is live and fails afterwards: an item deferred in
Phase 3 is invisible to anyone reading Phase 4, and invisible to the
audit machinery entirely. Items 9-11 below were correctly recorded in
the Phase 3 packet and then went unreferenced through the roadmap's
completion — the one open item with live failure data attached
(`#11`) survived only as two lines of prose in a different document.

This file is the standing index. Phase packets keep their own record;
an item that is not closed inside its phase is copied here verbatim and
stays here until it lands or is explicitly rejected.

**Convention.** Items keep the number they were assigned when raised.
Each entry carries: verbatim source text, source path + sha256, status,
and — once specified — the spec inline. Closure requires either a
commit reference or a dated Paul rejection. Nothing leaves this file by
going stale.

---

## Open items

Source artifact (law 8 — path + sha256, load-bearing spans quoted
verbatim below):

`audits/AUGMENTATION_P3_RATIFY_PACKET_2026-08-11.md`
sha256 `b3b51e62f443d3edda0e949b505eb938f3dfa68f0f92fc205a4d380dd3c64e15`
lines 112-124, section "POTENTIAL IMPROVEMENTS added this phase (queue
for Paul)".

### #9 — receipt-window rule for batch-registered dispatch pairs

> 9. Receipt-window rule refinement for batch-registered dispatch pairs
>    (see p33-probe-a above).

**Status: OPEN.** Currently mitigated by procedure only (the
register → verify receipt → record receipt → register-next sequencing
rule in `SKILL.md`). Still producing exactly one live audit finding
(`p33-probe-a`, ledger id 125). **Subsumed by C3 of the item #11 spec
below** — the two are one mechanism, and specifying them separately
would build the same pairing logic twice.

### #10 — cross-session propagation of the receipt law

> 10. Cross-session propagation of the receipt law: other live lanes
>     (`phase4-tensor`) dispatch under pre-augmentation habits; decide
>     the adoption path (memory update reaches future sessions; live
>     sessions need a nudge).

**Status: OPEN, partially resolved by events.** The
`universal-lane-laws-2026-08-09` memory now carries the receipt epoch,
which reaches future sessions. The live-session nudge was performed
once by hand (glassbox `handoff.queued`, 2026-08-11T00:59:49Z) and the
`phase4-tensor` lane's receipt subsequently landed `verified=true`.
No mechanism exists; the adoption path for concurrent sessions is still
Paul's call. Not specified here.

### #11 — mechanical validation of receipt-block emission

> 11. Executor receipt-block emission remains unreliable for NOVEL
>     preamble text (6 of 8 initial drops across Phases 2-3; the verify
>     tooth caught every one). Consider whether receipt emission should
>     also be validated mechanically (e.g., dispatch wrapper checks the
>     reply's first block) rather than by coordinator eyes alone.

**Status: CLOSED 2026-08-11 — all four changes landed.**

| Change | Commit | Merge |
|---|---|---|
| C1 + C3 | `295068ee1` | `f437a3830` |
| C4 (preamble tags) | `e5e9f19c0` | — (governance) |
| C2 (structural check) | `c01d48596` | `93c972422` |

119/119 tests on main; copy sync 4/4 by md5; mirror at `93c972422`.

**What this bought, and what it did not.** Fingerprints are computed
from bytes rather than asserted by the caller (D2). Pairing is explicit
(D3), retiring the `p33-probe-a` class by mechanism instead of
procedure. A PASSING receipt can no longer be recorded over text with
no receipt in it (D1), while a FAILING one always can — the asymmetry
is deliberate, because those records are the evidence that justified
the item.

**Scope limit, stated rather than implied:** `INV-<n>` coverage is
mechanically checkable because invariants are pinned in the ledger
verbatim and immutable. `CON-<n>` coverage is NOT, because the ledger
never sees the dispatched contract and cannot know how many numbered
constraints it carried. No heuristic was added to guess. Constraint
coverage remains a coordinator read.

**Closing datum.** Four of four dispatches during this work emitted no
RECEIPT block, including two after C4 went live. On its first real use
the new check rejected `verified=true` over its own build dispatch's
reply for a missing RECEIPT block, and accepted the same reply at
`verified=false`. The emission problem is unchanged; it is now
mechanically visible instead of dependent on the coordinator reading
carefully.

### #14 — the one-coordinator-per-tree rule has no mechanical guard

The metaloop constitution states: "The laws assume ONE active
coordinator per working tree; a second coordinator must not dispatch
into a tree with a live run." That is an assumption plus a prohibition
on the second coordinator, with nothing enforcing either. `-Action
start` overwrites the working directory's registered run rather than
refusing when one is already live and not stale.

**Observed 2026-08-11.** Run `run-20260811T0437512752604Z-08e5573c1a`
(item #11 C1+C3) was started in the main tree at 04:37Z. Another
session registered `run-20260811T1443271724756Z-ccd0abf0e4` in the SAME
tree at 14:43Z while the first was still open. The consequence was not
a collision — it was that the first run could no longer be CLOSED:

```
metaloop.ps1 -Action finish -RunId run-...-08e5573c1a
RunId does not match the registered Meta LOOP run for this working directory.
```

The terminal state was emitted directly through `emit.ps1` to keep the
glassbox record honest, and the other coordinator's live run was not
recovered or interfered with. `-Action recover` was not an option: it
is idle-time gated, it emits a terminal `run.blocked`, and it would
have been aimed at someone else's live run.

**Why it matters beyond bookkeeping.** A run that cannot be closed
through the adapter produces no verified terminal receipt, so
`receipt_state` and the run's closed-state in `run_metrics` are wrong
for reasons unrelated to the work. Silent slot takeover also means the
prohibition is only ever discovered after the fact, by the coordinator
that lost the slot.

**Candidate fixes, none decided.** (a) `-Action start` fails closed when
a live non-stale run is registered for the cwd, with an explicit
override flag for the case Paul wants it. (b) The state file holds a
map keyed by coordinator or session rather than a single slot.
(c) Minimal fix for the observed symptom: `-Action finish` accepts a
RunId that was registered for this cwd earlier even if it is no longer
the current holder — closing your own run should not depend on still
holding the slot.

Related but distinct, same session: `main` advanced underneath this
work twice from other sessions' commits, and a mirror push reported
"Everything up-to-date" because a sibling session had already carried
the commit up. No collision occurred in either case — different files —
but both are the same underlying condition of multiple coordinators in
one tree, which the laws assume away rather than prevent.

Status: OPEN, unspecified.

### #13 — `list_events()` on a never-initialized ledger

Two consecutive rounds of this work produced a new test that called
`list_events()` before any insert on a fresh path, hitting the
deliberate "missing DB = clean error" behaviour from `502e014eb` —
once as a post-rejection assertion, once as a pre-insert baseline. The
ledger behaviour is intentional and should not change. The sharp edge
is that test authors keep walking into it. `repeated_triggers` fired.
Status: OPEN, unspecified — candidate fixes include a test helper that
initializes-then-baselines, or a documented note at the `list_events`
definition.

Two amendments were made to the C3 text below during execution, both
forced by defects the Codex lane caught via STOP REPORT:

- The fallback is RUN-LEVEL and data-driven — if ANY receipt in a run
  carries a non-empty key, match by key for that run; otherwise the
  original time window applies unchanged. It is deliberately NOT the
  "rows recorded before this change" rule written below, because that
  would plant a second dated epoch in this ledger and P3.0 was a
  hotfix for exactly that time-bomb class.
- `dispatch_trigger_key` is REQUIRED on new inserts, as written below.
  Required plus run-level presence resolves correctly at both ends
  without anyone recording a cutoff date.

Open design question, recorded not decided: R3 selects key mode on ANY
keyed receipt, not any VALID keyed receipt. The independent review
refuted the coordinator's claim that this was a defect — it is the
specified rule — but a keyed receipt that fails validity will put a run
in key mode with no valid keys, and every dispatch in it reports
missing. Reachable only via a directly-written, imported, or corrupt
row, since `record()` now rejects invalid receipts. Left as-is on the
reasoning that failing loud on corrupt data beats silently reverting to
time windows. `test_audit_any_keyed_receipt_selects_key_mode_when_invalid`
pins this behaviour; a mutation test confirms the pin is non-vacuous.

### #12 — failure-attribution vocabulary has no author-side class

The four classes are `spec-misread`, `coordination`, `verification`,
`infra`. `spec-misread` is defined reader-side ("the lane misunderstood
or dropped part of the specification"), but the Round 3 finding and both
defects in this run were coordinator SPEC-AUTHORING failures — the lane
read correctly and the author was wrong. Those were tagged
`coordination` as the least-wrong fit, which distorts the distribution
P5.3 compares against MAST. Status: OPEN, unspecified.

---

# Item #11 — SPEC: mechanical receipt validation

## Evidence as of 2026-08-11T04:00Z

Measured from the live ledger
(`C:\Users\pgoff\.claude\state\codex-executor-ledger.sqlite3`), not
from recollection:

| Measure | Value |
|---|---|
| `receipt` events recorded, all time | 8 |
| of those, `verified=false` | 6 (`p33-receipt-a`, `p33-receipt-b`, `p30-receipt-late`, `iq-build-receipt`, `iq-review-receipt`, `shakedown-receipt`) |
| `verified=true` | 2 (`p24-receipt-r2`, `receipt:phase4:r1`) |
| post-epoch dispatches | 7, all `gpt-5.6-sol/xhigh/priority` |
| coordinator catch rate on drops | 6 of 6 |
| P5.1 plant #1 receipt reflection | FAIL — no RECEIPT block emitted at all |
| P5.1 plant #1 output survival | PASS — final bytes 56,54,10, law names byte-exact |

Source for the plant row: `audits/LANE_LAWS_VALIDATION_2026-08-09.md`
sha256 `39541b850bfef2e8f78b34aee9fe60259cd51e78355083d3cdf8a154b916f046`,
line 269.

**The signal split is the whole argument.** Comprehension is healthy —
output survival is 5/5 across every scored plant. Emission is not —
roughly three of four first attempts arrive with no conforming RECEIPT
block. Every one was caught, and every catch was a human-equivalent
read by the coordinator. The law currently runs on attention.

## Defects, separated

The single symptom decomposes into three independent mechanical gaps.
Specifying them together matters because a fix for D1 alone would be
built on D2's dishonest input.

- **D1 — no structural check.** Nothing verifies that the executor's
  reply contains a RECEIPT block at all. Detection is entirely Fable's
  step-5 read (`SKILL.md:167`). This is the observed 6-of-8 failure.
- **D2 — caller-computed fingerprints.** `spec` and `receipt` are
  stored as `{sha256, utf8_bytes}` supplied *by the caller*
  (`coordination_ledger.py:569-595`). `SKILL.md:353` already names the
  hazard: "the fingerprint is only as honest as its input; a pointer
  string fingerprints the pointer, not the artifact." A mechanical
  check over a caller-asserted fingerprint proves nothing.
- **D3 — temporal, not explicit, receipt↔dispatch pairing.** The audit
  matches a receipt to a dispatch by time window only: a receipt counts
  for dispatch *i* when `dispatch[i].created_at < receipt.created_at <
  dispatch[i+1].created_at` (`coordination_ledger.py:975-991`). Two
  dispatches registered 0.183s apart therefore closed the first one's
  coverage window permanently — the `p33-probe-a` finding, and item #9.

## Design

Four changes. C1-C3 are code-plane (Codex). C4 is governance-plane
(Fable) and changes the executor contract, so it gates part of C2.

### C1 — the ledger computes the fingerprints (closes D2)

`coordination_cli.py record` gains `--spec-file` and `--receipt-file`,
each a path to a UTF-8 text file holding the **true** dispatch text and
the **true** reply text. The ledger reads the bytes, computes `sha256`
and `utf8_bytes` itself, and constructs the `spec`/`receipt` payload
fields.

The text is never stored — only the fingerprint — preserving the
existing rule that content-bearing fields live as sha256 plus byte
count (`SKILL.md:319-322`). The caller-supplied dict path stays
accepted for back-compatibility, and audit reports its use as
informational `receipt_fingerprints_caller_supplied`.

### C2 — structural validation at insert (closes D1)

When `--receipt-file` is supplied, the ledger runs a structural check
before insert, stores the outcome in the payload as a `structure`
object, and:

> **REJECTS the insert when `verified=true` and the structural check
> fails.**

Recording a *failed* receipt (`verified=false`) over any text remains
legal and unchanged — the honest record of a drop must stay
recordable. What becomes impossible is recording a PASS over a reply
that structurally has no receipt.

Structural checks, tier 0, zero judgment:

1. `has_block` — the reply contains a `RECEIPT` labeled block.
2. `enumerated_items` — the block contains at least one enumerated
   item.
3. `invariants_covered` — every line of the run's pinned `invariants`
   event is referenced by ordinal tag in the block. The pinned lines
   are already stored **verbatim** and are immutable
   (`coordination_ledger.py:551-568`), so this is a set difference,
   not a fuzzy match. **Requires C4.**

`verified` keeps exactly its current meaning: Fable's semantic verdict
on own-words fidelity, modality preservation, and N/A justification.
The structural check never sets `verified=true` on its own. Structure
is necessary, never sufficient — a receipt can be structurally perfect
and semantically hollow, and only the reader catches that.

### C3 — explicit receipt↔dispatch pairing (closes D3, subsumes #9)

The `receipt` payload gains a required `dispatch_trigger_key`. The
audit matches receipts to dispatches by key first, falling back to the
existing time window only for rows recorded before this change.

This makes batch registration safe by mechanism instead of by
procedure, and retires the `p33-probe-a` finding class permanently. The
`SKILL.md:353-358` sequencing rule stays as good practice but stops
being load-bearing.

### C4 — preamble amendment (governance plane; needs Paul's stamp)

Coverage cannot be checked mechanically unless each receipt item names
its source. Proposed amendment to the RECEIPT paragraph of the Standing
dispatch preamble (`SKILL.md:224`), adding one requirement to clause
(b):

> each item opens with its source tag — `CON-<n>:` for the nth numbered
> constraint of the contract, `INV-<n>:` for the nth line of the
> INVARIANTS block — so that coverage is checkable without
> interpretation.

This is a change to the executor contract, so it is Paul's stamp, not
mine. Until it lands, C2 ships with checks 1-2 only.

## Falsifiable acceptance checks

Negative controls are mandatory per the house standard — a gate that
has never been observed rejecting anything is not evidence.

1. **Positive.** A reply with a conforming RECEIPT block covering all
   pinned invariants records with `structure.pass=true`.
2. **Negative control A.** The plant-#1 reply text (no RECEIPT block)
   with `verified=true` → insert **REJECTED**, message naming the
   missing block.
3. **Negative control B.** The same text with `verified=false` →
   insert **ACCEPTED**. Honest failure records must survive the gate.
4. **Negative control C.** A receipt covering 3 of 4 pinned invariants
   with `verified=true` → **REJECTED**, naming the uncovered ordinal.
5. **Pairing regression.** Two dispatches registered 0.2s apart, the
   first's receipt arriving after the second → `dispatches_missing_
   receipt` is **empty** under key matching. This is the `p33-probe-a`
   case replayed.
6. **Fingerprint honesty.** `--receipt-file` yields a sha256 equal to
   an independent `Get-FileHash`; the caller-supplied path is flagged
   informational, not rejected.
7. **Back-compat.** The 8 existing receipt rows audit exactly as they
   do today; total findings change only by the new sections.

## Impact envelope

`.claude/skills/codex-executor/scripts/coordination_ledger.py`,
`.claude/skills/codex-executor/scripts/coordination_cli.py`,
`.claude/skills/codex-executor/scripts/test_coordination_runtime.py`,
and `.claude/skills/codex-executor/SKILL.md`. No stored row is
rewritten. No engine, Moneyball artifact, rank surface, or dashboard is
touched.

## Reversal

Revert the ledger commit. Existing rows are unaffected: every new field
is additive and the caller-supplied fingerprint path stays accepted, so
a reverted ledger reads pre-change and post-change rows identically.

## Sequencing and gates

1. **C1 + C3 + C2(checks 1-2)** — one Codex dispatch, xhigh/priority,
   with the independent review round required for a non-trivial diff.
   No contract dependency.
2. **C4 stamp, then C2(check 3)** — enforcing coverage before the
   ordinal-tag convention exists would fail every receipt for lack of
   tags. Paired second step.

Free-tier verification first per §4 of the metaloop command: the test
suite and a replayed audit over the existing ledger are ground truth
and cost nothing; no model review is dispatched on a red suite.

## Reopen-trigger status

The Phase 5 record notes item #11 "sits deferred with a reopen trigger"
(`LANE_LAWS_VALIDATION_2026-08-09.md:274`). The trigger's threshold text
is not recorded in the repo. On the data — 6 of 8 all-time receipts
`verified=false`, and P5.1 plant #1 scoring receipt reflection FAIL on
the first standing plant — the condition appears met. **RESOLVED: Paul stamped item #11 on
2026-08-11 and ordered C1+C3 dispatched** — the trigger question is
closed by that ruling, and this section stands as the evidence behind
it.

---

## Landed items (Phase 3 queue, closed 2026-08-11)

Seven ledger-hardening items and one governance item landed in
`502e014eb` and `1132a7f22` respectively. Per those commit messages,
verbatim:

> sha256 64-hex pins on all fingerprint validation; whitespace
> provenance rejected; read-only audit access (constructor no longer
> creates DBs, readers mode=ro via encoded as_uri, missing DB = clean
> error); dispatch effort/tier pin on sanitized payload (alias
> closure); finite-token guard incl. component-sum overflow;
> runs_missing_invariants informational array; coordinator-bookkeeping
> exemption (invariants/receipt-only runs).

> receipt hygiene doc (true-bytes convention + register-receipt-register
> sequencing)

**Known gap in this record:** the mapping from queue numbers 1-8 to
those specific items is not recoverable from the repository — the
commits describe the changes without the numbering, and the numbered
list lived in a session transcript. Items 9-11 are numbered here
because the Phase 3 packet recorded them that way. Future items are
appended to this file at the moment they are raised, which is the
practice that prevents a repeat.
