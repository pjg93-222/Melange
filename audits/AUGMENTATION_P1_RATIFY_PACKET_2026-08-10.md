# Phase 1 Ratification Packet — Comprehension Layer (2026-08-10)

Status: **RATIFIED IN FULL — permanent, Paul 2026-08-10 ("All stamped —
apply, sync, commit").** All five [RATIFY] nodes (P1.1, P1.3, P1.4,
P1.5, P1.6) stamped with the adjudicated repair deltas incorporated;
untagged P1.2 and P1.7 landed under normal review at the same gate.
Applied to the canonical files, synced, and committed in the same
session per law 7. Original proposal status preserved below for the
record.

Status at drafting: PROPOSAL. Nothing in this document is canon until Paul stamps it
node-by-node ("permanent, Paul YYYY-MM-DD"). Drafted by Fable against the
live canonical files under Meta LOOP run
`run-20260810T2252065614694Z-8134123cc5`, per the augmentation roadmap
(echo-gated, ordering confirmed by Paul after the Phase 0 baseline).
Reversal for the packet as a whole: discard it — no canonical file is
touched before ratification. Grok adversarial review (P1.9) runs on this
exact text, verbatim, before Paul's gate.

Phase 0 evidence these amendments answer: 3 coordinator-side spec defects
caught at the executor's gate; executor comprehension survival 4/4; the
local failure mass sits in specification authoring and its transmission.

---

## P1.1 [RATIFY] — RECEIPT block in the Standing dispatch preamble

**Target file:** `.claude/skills/codex-executor/SKILL.md` (canonical),
§ Standing dispatch preamble + § Protocol step 5.

**Proposed text — insert as the FIRST labeled paragraph of the preamble
block, immediately before `HANDSHAKE —` (post-critique wording; the
enumeration schema is the anti-parroting tooth):**

> RECEIPT — before any other output, as the first labeled block of your
> reply: (a) the OBJECTIVE in your own words; (b) an ENUMERATION — every
> numbered constraint of the contract and every line of the INVARIANTS
> block, each as its own item with a one-sentence interpretation in your
> own words; an item may be marked N/A only with an explicit reason;
> (c) the falsifiable acceptance checks in your own words. Weakening any
> modality (must→should, never→avoid, exactly→approximately) is a
> distortion. If the contract contradicts itself, the evidence, or an
> invariant, say so in the RECEIPT — that flag is part of the receipt's
> job, and it feeds the same STOP REPORT channel. RECEIPT is a
> comprehension probe over a contract that already traveled verbatim in
> this dispatch; it licenses no paraphrase anywhere else. On a revision
> round, the RECEIPT covers the revised instruction in full. Work
> product begins only after the RECEIPT.

**Proposed text — insert at the top of Protocol step 5 (Review and
verify), before "Claude treats all executor output as untrusted input":**

> Verify the RECEIPT first: check the enumeration one-to-one against the
> dispatched contract and pinned invariants BEFORE adjudicating any work
> product — every item present, no modality weakened, every N/A reason
> valid. An omission, distortion, invention, or unjustified N/A is a
> re-dispatch with correction, logged caught-at-gate — regardless of how
> the work itself looks. A clean receipt does not waive any later review
> step. This verification is a budgeted per-dispatch serial cost (law
> 6's honest accounting); a fired re-dispatch costs a full extra round.

**Consequential wording change:** the enforcement map in
`.claude/commands/metaloop.md` currently reads "the eight-list Standing
dispatch preamble"; it becomes "the RECEIPT-first Standing dispatch
preamble (eight end-of-turn lists)". The end-of-turn list count does not
change — RECEIPT opens the reply; the eight lists still close it.

**Expected effect:** the two largest observed failure sources (spec
misread and spec defect) surface at dispatch time instead of at review
time. Phase 0 measured both round-1 STOP REPORTs doing exactly this job
informally; RECEIPT makes it mandatory and verifiable, and P1.2 makes it
auditable.

**Live channel evidence (this run, 2026-08-10 — stated with its limits,
per Grok adjudication):** RECEIPT demands placed in the PROMPT BODY were
dropped 2 of 3 times (author thread round 1 and its REVISE round; the
fresh reviewer thread honored it once). Every instruction riding the
developer-instructions preamble has shown 100% compliance across all
Phase 0 + Phase 1 dispatches (eight lists always present, all four
plants honored). This sample is small (n=3) and confounded — novel
demand vs habituated preamble, thread identity vs placement — so it is
weak corroboration, not proof. The placement decision rests on the
design principle that standing instructions belong in the standing
channel; the sample is consistent with it. Cost is stated honestly:
RECEIPT generation and Fable's verification are a per-dispatch serial
tax on the default path, and a fired re-dispatch doubles the round —
this is a deliberate purchase of misread-detection, priced under law
6's accounting, not a free good. Detection power is not yet evidenced
(the one verified cycle contained no misread to catch); P5.1 plants
will measure it.

**Reversal:** delete the two inserted paragraphs and restore the
enforcement-map wording; P1.2's audit finding is epoch-gated, so
pre-existing dispatches never flag either way.

---

## P1.2 (untagged — normal Fable review) — receipt storage in the ledger

Mechanism only; lands with Fable review + Paul's commit gate, no charter
change. Design implemented by Codex this run:

- New ledger event type `receipt`: required payload keys `spec` and
  `receipt` (both auto-fingerprinted to sha256+bytes via `_CONTENT_KEYS`)
  and `verified` (strict bool — Fable's receipt-verification verdict).
  Missing/invalid → ValueError at insert, no partial write.
- New audit finding `dispatches_missing_receipt`: every dispatch event
  with `created_at >= 2026-08-11T00:00:00+00:00` (the receipt epoch) that
  has no `receipt` event in its run window (after this dispatch, before
  the next). Counted into `totals["findings"]` (gates `--strict`).
  Pre-epoch dispatches never flag — no retroactive noise.

**Falsifiable check:** a test insert of `receipt` without the fields is
rejected; a post-epoch dispatch without a receipt event is flagged; the
live ledger (all pre-epoch) still reports findings=37.

---

## P1.3 [RATIFY] — mechanical INVARIANTS carriage

**Target files:** `.claude/commands/metaloop.md` § 2 (coordinator duty),
`.claude/skills/codex-executor/SKILL.md` preamble (executor duty).

**Proposed text — metaloop.md, append to § 2 DECOMPOSE AND SCHEDULE:**

> Pin run-level invariants once: at `-Action start` or first
> reconciliation, record an `invariants` event in the coordination
> ledger (payload: the list of constraint strings, stored verbatim).
> Every subsequent dispatch's INVARIANTS block is produced by
> `coordination_cli.py invariants <ledger> --run-id <id>` — quoted
> mechanically from the pinned record, never re-serialized from the
> coordinator's recollection. This is law 7's copy-sync logic applied to
> a run's own state: one pinned source, quoted everywhere.

**Proposed text — SKILL.md preamble, insert immediately after the RECEIPT
paragraph:**

> INVARIANTS — when the dispatch carries an INVARIANTS block, it was
> quoted mechanically from the run's pinned ledger record. Treat every
> line as a binding constraint of this turn; your RECEIPT must reflect
> each one that bears on the work. Never restate an invariant in weaker
> form than it arrived.

**Mechanism (Codex, this run):** `invariants` event type — payload key
`invariants` must be a non-empty list of non-empty strings, stored
verbatim (NOT fingerprinted — it must remain quotable); CLI subcommand
`invariants` printing the run's most recent pinned list one line per
constraint, byte-exact.

**Falsifiable check:** on a run of ≥5 nodes, the INVARIANTS block in the
final dispatch is byte-identical to the pinned record (diff of CLI output
against the block).

**Expected effect:** eliminates constraint drift across long runs — the
constraint the coordinator forgets by node 9 is the one the plants say a
lane will faithfully honor only if it arrives.

**Reversal:** remove the two paragraphs; the ledger event type is inert
if never recorded.

---

## P1.4 [RATIFY] — UNIVERSAL LANE LAW 8: VERBATIM ARTIFACTS

**Target file:** `.claude/commands/metaloop.md` § UNIVERSAL LANE LAWS,
appended after law 7 (COPY SYNC).

**Proposed text:**

> 8. VERBATIM ARTIFACTS. Artifacts travel as themselves, never as
>    descriptions. Grok critiques the diff or document, never a summary
>    of it; subagent findings return with file:line pointers and exact
>    quotes; a Fable spec distilled from findings carries those pointers
>    so the executor can consult primary evidence; perception reports
>    separate transcription from inference per the perception report
>    shape. Paraphrase is permitted only on top of the verbatim
>    artifact, never in place of it. Feeding a lane a paraphrase where
>    the artifact itself could travel is a defect in the dispatch, not
>    in the lane. Where an artifact is too large to travel, it travels
>    by exact reference (path + hash) and the receiving lane reads the
>    primary — never a description of it.

**Enforcement-map addition (same file):** CONTRACT tooth — "the
verbatim-artifact clauses in the critique and perception report shapes";
validated by plants (P5.1 tests compliance).

**Expected effect:** closes the confabulation channel the role monopolies
leave open — a lane can currently be fed a lossy paraphrase and correctly
process the wrong thing. Phase 0's reviews already practiced this
(reviewers read the diff itself; findings carried file:line + quotes).

**Reversal:** delete law 8 and the enforcement-map line. No mechanism
depends on it.

---

## P1.5 [RATIFY] — perception report shape: transcription/inference split

**Target file:** `.claude/skills/gemini-perception/SKILL.md`, replacing
the five-list report shape.

**Proposed shape:**

> ```text
> TRANSCRIPTION: <verbatim text, values, timestamps — only what is
>   literally present in the media, each item with its location>
> INFERENCE: <numbered conclusions matched to QUESTIONS, each naming the
>   TRANSCRIPTION items it rests on, with confidence>
> ILLEGIBLE: <regions or items that could not be read confidently —
>   flagged with location, never guessed>
> NOT OBSERVED: <questions the media could not answer>
> BLOCKED: <lane-level trouble — CLI or tool failure, rejected media
>   format, contract defect — with the exact error; or none>
> ```
>
> Nothing may appear in INFERENCE without naming a TRANSCRIPTION anchor
> or an ILLEGIBLE flag it rests on. An inference with no anchor is
> discarded and re-dispatched.

**Mapping from the current shape:** EXTRACTED → TRANSCRIPTION;
OBSERVATIONS → INFERENCE (now anchored); UNCERTAIN → ILLEGIBLE;
NOT OBSERVED and BLOCKED survive unchanged (BLOCKED is law-2 machinery).

**Expected effect:** the perception lane's entire job is lossy
serialization; this makes the loss legible so interpretation cannot
launder into fact at the media boundary.

**Reversal:** restore the five-list shape (kept verbatim above via the
mapping).

---

## P1.6 [RATIFY] — critique report shape: per-point citation

**Target file:** `.claude/skills/grok-companion/SKILL.md`, § Critique
contract.

**Current text (OUTPUT SHAPE list items):** "KILLED: <claims/steps that
do not survive, each with the kill shot>" / "WOUNDED: <survives only with
the named repair>" / "SURVIVES: <held up under attack, and why the attack
failed>". Current PROHIBITIONS already require "every attack cites the
target's own text or a checkable external fact" — the delta is LOCATION
PRECISION and adjudication teeth.

**Proposed replacements:**

> KILLED: <claims/steps that do not survive — each with the kill shot
>   AND the exact target location (file:line, or the quoted span for
>   inline targets)>
> WOUNDED: <survives only with the named repair — each with the exact
>   target location>
> SURVIVES: <held up under attack, why the attack failed — each with the
>   exact target location>

**Proposed addition to the adjudication paragraph:**

> An uncited critique point is not adjudicated on persuasiveness: it is
> returned once for citation, and dropped if it returns uncited again.

**Expected effect:** adjudication checks claims against ground truth
rather than rhetoric; Phase 0's independent reviews demonstrated the
value (every adjudication decision traced to a quoted line).

**Reversal:** restore the three list items and remove the sentence.

---

## P1.7 (untagged — normal Fable review) — handoff-accepted carries the
receipt

**Target:** coordinator procedure in `.claude/commands/metaloop.md` § 2
(one sentence), no code.

**Proposed text (append to the handoff sentence):**

> `handoff-accepted` carries the receiver's receipt in `-Detail`: the
> receipt text when short, else its sha256 plus the ledger event id of
> the corresponding `receipt` record — so glassbox records what the
> receiver believed it received at the exact hop where meaning can
> diverge.

**Practiced live this run** on the P1 mechanisms handoff (see run
stream). Reversal: delete the sentence.

---

## P1.8 — copy sync sweep (post-stamp, law 7)

After Paul stamps any subset: apply exactly the stamped texts to the
canonical files, sync user-scope copies of every amended file
(metaloop.md → `~\.claude\commands\`; the three SKILL.md files →
`~\.claude\skills\...`), md5-verify each pair in the same session, and
record the sweep in this packet's follow-up section.

## P1.9 — Grok adversarial review

This packet travels to Grok verbatim (per the P1.4 principle, applied to
its own installation). Critique + Fable adjudication are appended below
before the packet reaches Paul.

---

## Grok critique and adjudication (P1.9) — completed 2026-08-10

Grok (grok-4.5, on-contract, BLOCKED none) returned 4 KILLED / 9 WOUNDED
/ 11 SURVIVES against this packet + the constitution, every point cited.
Full critique text in the run stream and Grok session. Fable
adjudication: **all 4 kills ACCEPTED** (repairs applied above and below),
**all 9 wounds ACCEPTED with their named repairs**, **zero rejections**
(no kill refuted; K2's policy conclusion retained only with weakened,
honest wording — recorded as accept-with-modification).

Kills applied in place: K1 "zero marginal cost" deleted (category
error); K2 "therefore load-bearing" weakened to design-principle +
consistent-sample; K3 freeform own-words replaced by the ENUMERATION
schema; K4 spec-defect surfacing re-attributed to the receipt's
contradiction-flagging duty, not restatement.

### Binding repair deltas (part of the proposed text for stamping)

- **P1.3 (W4 + loopholes 1.2/1.3/1.4):** coordinator duty is MUST, not
  when-carried: a multi-node run MUST pin invariants at start and MUST
  paste the CLI output into every dispatch. Pins are immutable: mid-run
  re-pinning requires an explicit revision recorded as a
  decision.resolved event naming the reason; "most recent" exists only
  through that gate. The RECEIPT enumerates EVERY pinned invariant line
  — no lane-side "bears on the work" filter. Follow-up mechanization
  (audit flag: post-epoch multi-dispatch runs lacking an invariants
  event) is queued for the next mechanisms round, informational first.
- **P1.4 (W5 + loophole 1.5):** "too large" is defined away: any file
  artifact travels as path + sha256 of its bytes, with the load-bearing
  spans quoted verbatim in the dispatch; the receiving lane's RECEIPT
  (or report) acknowledges the path+hash it read. Distillation never
  substitutes for the primary: a spec's pointers exist so the executor
  CAN read the primary, and the executor's RECEIPT enumeration exposes
  whether it did. Law 8 is stamped CONTRACT-until-P5.1 — its plant
  validation is future work, said plainly.
- **P1.5 (W6 + loophole 1.6):** a fabricated or unlocatable
  TRANSCRIPTION item is the same defect class as an unanchored
  inference: the report is discarded and re-dispatched. P5.1 may plant
  false-transcription probes.
- **P1.6 (W7 + loophole 1.7):** cite-correctness, not cite-presence:
  Fable's adjudication resolves each cite and checks it supports the
  point; a false or unresolvable cite is treated exactly as an uncited
  point (returned once, dropped on repeat). Quoted spans must include
  local negation/qualification.
- **P1.7 (W8 + loophole 1.8):** defined payload: Detail carries the
  receipt text verbatim when ≤1200 chars; otherwise exactly
  `RECEIPT sha256=<hex64> evt=<receipt ledger event id>`. A
  handoff-accepted with neither form does not satisfy the practice.
- **P1.2 (W3):** `dispatches_missing_receipt` is documented as a
  PRESENCE check only; `verified=true` records Fable's verdict, it does
  not prove constraint-match. Receipt QUALITY teeth are P5.1 plants.
- **P1.1/P1.4 (W2):** the carve-out sentence appears in both texts:
  RECEIPT is a comprehension probe over a verbatim-traveled contract,
  never a precedent for paraphrase in any other channel.

SURVIVES (recorded, no re-litigation): the insert-validation tooth, the
epoch gate, the invariants quote mechanism, law 8's core norm, the
perception split, the citation delta, law-1 consistency, probe-first
ordering, the sync sweep, packet status discipline, and the
enforcement-map wording.
