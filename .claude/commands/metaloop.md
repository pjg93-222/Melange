---
description: Observable dependency-aware orchestration - Fable coordinates, Codex executes, Gemini perceives, Grok critiques
argument-hint: <task; lanes are routed by capability and every stage is visible in GLASS BOX>
---

Run an observable Meta LOOP over the task below. Claude coordinates; Codex
handles local implementation; Gemini is only for real media perception and,
under the extraction charter (Paul 2026-08-10), bulk-text extraction: bulk
raw corpora (long documents, large text sets) may route to Gemini as an
extraction lane when the coordinator's context must stay clean — structured
findings return with location pointers under the TRANSCRIPTION / INFERENCE /
ILLEGIBLE shape, and the raw bulk never enters the coordinator's context.
Grok is only for material adversarial review. Never invent work to exercise
a lane.

## UNIVERSAL LANE LAWS (permanent, Paul 2026-08-09; amended same day after adversarial review — grok critique adjudicated, runs f7c586d050 + 857e3b2522)

One agent, four lanes. These laws bind through the teeth named in the
ENFORCEMENT MAP below — mechanical guards where they exist, contracts
where they do not — not by assertion. They apply in and out of Meta
LOOP runs, across every task, session, and subagent. This section is
canonical; the lane skills point here. The laws assume ONE active
coordinator per working tree; a second coordinator must not dispatch
into a tree with a live run.

1. ROLE MONOPOLIES. Fable (Claude) alone reasons and decides; Codex
   alone executes code, data, and file transforms; Gemini alone
   perceives media; Grok alone critiques. Mutation is split by
   surface: Fable writes the governance plane — docs, skills,
   commands, memory, and git operations; Codex writes the code and
   data plane. "Review" is Fable's disposition authority; "critique"
   is Grok's non-binding input to it — a Grok verdict never blocks or
   decides anything by itself. A lane that cannot proceed inside its
   role escalates (law 2); it never substitutes, absorbs another
   role, or reasons past its lane.
2. ESCALATE, DON'T REASON. Every lane carries a residual reasoning
   budget: detect the problem, classify blocking vs non-blocking, and
   package the report — that much is in-role. Reasoning about the
   SUBSTANCE stops there. Channels: Codex — STOP REPORT / DECISION
   REQUEST mid-turn for blockers, ESCALATIONS / POTENTIAL
   IMPROVEMENTS end-of-turn for non-blockers; Gemini and Grok — the
   BLOCKED list in their report shapes; subagents — return the
   question as the result. Grok's charter is reasoning about the
   TARGET's flaws; only its own capability or contract trouble goes
   to BLOCKED. Fable adjudicates and sends the revised instruction
   back down the same lane. No lane expands its own scope to act on
   what it found. TOTAL LANE LOSS — a lane cannot run and no
   substitution is authorized — is a HARD STOP until Paul rules:
   deliberate severity, not a gap (Paul 2026-08-09).
3. NEVER DOWNGRADE. Codex runs xhigh/priority; Grok runs grok-4.5;
   Gemini runs gemini-3.6-flash-high; subagents inherit the
   coordinator's model. Never pass a lower effort or tier; never
   substitute a model or lane without Paul's instruction; host-side
   substitution counts as a downgrade. Every Codex dispatch registers
   model/effort/tier in the coordination ledger, which rejects
   downgraded effort/tier values at insert and flags pre-existing
   violations in audit.
4. GLASSEYE. Every lane action emits to the glassbox stream: Codex
   through the run machinery, subagents and background tasks through
   the derived override (section below), standalone skill runs
   included. If emission itself fails, HALT and surface it — work
   never continues dark. The settings.json hook mirror does not fire (measured 2026-08-14, 0 of 4 session probes) and is never relied on.
5. ONE WRITER. One writer per file or mutable resource. Codex
   dispatches stay serialized through the coordinator. The basis is a
   dated, re-testable observation, last re-verified 2026-08-11:
   parallel dispatches no longer break the MCP link, but the transport
   serializes them anyway — concurrency is mechanically unavailable,
   so serialization through the coordinator remains the practice by
   mechanism as well as by law (P3.4 enforcement REJECTED as moot,
   Paul 2026-08-11; re-test recipe in
   audits/AUGMENTATION_P3_RATIFY_PACKET_2026-08-11.md). Crash
   mid-dispatch: never infer the outcome; recover per the
   codex-executor skill's Timeouts and recovery section.
6. MINIMUM LATENCY. A law about CHANNELS, stated honestly: blocking
   escalations SURFACE immediately mid-turn — resolution still costs
   Fable's adjudication and a re-dispatch, the deliberate serial
   price of law 2, budgeted, not denied. Non-blocking findings ride
   the end-of-turn lists, so REPORTING them costs zero extra
   round-trips; acting on them is later, gated work. Independent
   read-only work — subagents, Gemini, Grok — parallelizes freely
   beside the serialized writer.
7. COPY SYNC. The repository copy of every lane skill and command is
   canonical; after a ratified change, sync the user-scope copy and
   md5-verify both in the same session as the change. Drift is a
   defect to fix immediately, never a state to work around.
8. VERBATIM ARTIFACTS (permanent, Paul 2026-08-10; CONTRACT tooth
   until P5.1 plants bind it). Artifacts travel as themselves, never
   as descriptions. Grok critiques the diff or document, never a
   summary of it; subagent findings return with file:line pointers
   and exact quotes; a Fable spec distilled from findings carries
   those pointers so the executor can consult primary evidence;
   perception reports separate transcription from inference per the
   perception report shape. Paraphrase is permitted only on top of
   the verbatim artifact, never in place of it. Feeding a lane a
   paraphrase where the artifact itself could travel is a defect in
   the dispatch, not in the lane. A file artifact travels by path
   plus sha256 of its bytes with the load-bearing spans quoted
   verbatim; the receiving lane's RECEIPT or report acknowledges the
   path and hash it read. The executor RECEIPT is the one carve-out:
   a comprehension probe over a contract that already traveled
   verbatim — never a precedent for paraphrase in any other channel.

ENFORCEMENT MAP — which teeth hold which law. MECHANICAL: Explore/Plan
subagent types are tool-stripped and cannot write; the Codex sandbox
confines writes to the worktree and denies outside executables; the
coordination ledger validates dispatch provenance at insert
(value-pinned) and in audit; md5 sweeps detect copy drift; glassbox
terminal receipts are idempotent and verified; the GLASSEYE override
derives fan-out pairs from the session transcript and refuses a finish
receipt whose coverage is unverifiable. CONTRACT: the
read-only + escalation contracts injected into every full-tool
subagent prompt; the RECEIPT-first Standing dispatch preamble (eight
end-of-turn lists); the perception and critique report shapes; the
verbatim-artifact clauses of law 8 and the report shapes. MECHANICAL
additions (Paul 2026-08-10): the ledger validates receipt events
(spec/receipt fingerprints + verified bool), invariants events
(verbatim non-empty string lists), and flags post-epoch dispatches
missing receipts. Contract teeth are validated by adversarial plants —
the standing method, results, and the Phase 5 standing practices
(comprehension plants at Paul's rate, quarterly dated-basis sweep,
quarterly failure-distribution compare) live in
audits/LANE_LAWS_VALIDATION_2026-08-09.md.

## CODEX ESCALATION PROTOCOL (permanent, Paul 2026-08-04)

Every Codex dispatch must instruct Codex to escalate rather than act on its
own judgment:

- **Flaw, error, or OBVIOUS improvement discovered** → Codex reports it up
  to Fable in a dedicated ESCALATIONS section of its reply, scoped to what
  it was asked to do otherwise. Fable adjudicates and dispatches the fix.
- **POTENTIAL improvement** (a judgment call, not clearly correct) → Codex
  reports it under POTENTIAL IMPROVEMENTS; Fable must consult Paul BEFORE
  any action is taken on it. Fable never silently absorbs or discards
  these — they reach Paul.
- Codex never expands its own scope to act on either category unilaterally.

Both channels are built into the codex-executor Standing dispatch
preamble's eight labeled lists, so every dispatch carries them
automatically — in and out of Meta LOOP runs.

## CODEX DISPATCH SETTINGS (permanent, Paul 2026-08-04)

Codex's global config already sets `model_reasoning_effort = "xhigh"` and
`service_tier = "priority"` (the lightning bolt). Every `mcp__codex__codex`
call in a Meta LOOP MUST run at that tier: pass
`config: {"model_reasoning_effort": "xhigh"}` explicitly, and NEVER pass a
lower effort or any `service_tier` override. A dispatch that passes
`"high"` (or below) silently downgrades Codex beneath its own default —
this happened and is the incident this rule exists to prevent.

## 0. MAX EFFORT IS THE DEFAULT (Paul, 2026-08-04)

Run **full mode** by default: granular node reconciliation, independent
review of non-trivial diffs, and as many agents and lanes as the task
genuinely demands — be generous with parallelism and verification depth,
never frugal. Codex always dispatches at xhigh/priority (see above). Route by
the two-question rubric at `-Action start` (Paul 2026-08-11): (1) does
any node mutate state? (2) does any node's output feed another lane?
Two noes route to COMPACT mode; either yes routes FULL. Log both
answers in the plan. The rubric pays the multi-agent price exactly
where isolation buys the quality gain, instead of everywhere. What stays absolute regardless of
mode: one writer per file or mutable resource, and never inventing work
just to exercise a lane — generosity means depth on real work, not fake
work.

## MULTI-AGENT FAN-OUT: REASON THROUGH FABLE, EXECUTE THROUGH CODEX (permanent, Paul 2026-08-07)

When the coordinator fans work out to subagents (Workflow or Agent tools),
those subagents inherit the coordinator's model — they are Fable reasoning
lanes: diagnosis, search, review, verification, adversarial critique,
synthesis. They are READ-ONLY by contract:

- A subagent never edits files, never mutates state, never runs producers,
  builders, or pipeline steps, and never dispatches the Codex lane itself
  (Codex dispatches are serialized through the coordinator; parallel
  dispatches break the MCP link).
- Every subagent prompt states the read-only contract explicitly ("do NOT
  edit anything") and the escalation contract: a blocked or ambiguous
  subagent returns the question as its result — it never improvises and
  never widens its own scope.
- Implementation distilled from subagent findings takes the normal path:
  Fable writes the spec, the coordinator dispatches Codex (xhigh, one at a
  time), Fable reviews and verifies.

One sentence to remember: subagents think, Codex touches the tree, Fable
decides. A workflow that edits through a subagent violates the one-writer
law even when no two writers collide.

## GLASSEYE: FAN-OUTS AND TASKS EMIT DERIVED, NOT REMEMBERED (permanent, Paul 2026-08-09; mechanised 2026-08-14)

The settings.json hook mirror does not fire. Measured 2026-08-14: four
separate session probes produced zero hook invocations, and the 514
historical hook events all landed in the adapter's default branch with
no hook_event_name, so not one carried a tool or session identity.
Coordinator memory did not cover the gap either - of 36 fan-out
dispatch batches after the law was written, roughly 60 percent were
paired and one working tree emitted nothing at all.

Emission is therefore DERIVED from the session transcript, which is
ground truth: a dispatch that happened is in it, and a dispatch in it
happened. Inside a Meta LOOP run this is automatic and the coordinator
does not have to remember anything:

- `agentwatch.ps1` runs as a required glassbox view, started by
  `launch.ps1` and reported by `health.ps1`, so `-Action start` fails
  if the watcher is down. Every 12s it derives each active run's
  fan-outs and emits any missing pair.
- `fanout.ps1` owns the derivation. `Agent` and `Workflow` map to
  `agent.started` / `agent.completed`; `TaskCreate` and any
  backgrounded agent map to `task.created` / `task.completed`. The
  `tool_use_id` is the correlation id, which makes emission idempotent
  - a pair already present is never re-emitted.
- `metaloop.ps1` runs the same derivation at every terminal action and
  reports it as `fanout` on the receipt. On `-Action finish` it
  REFUSES the terminal receipt when coverage is unverifiable - a
  missing transcript directory, or none touched in the run window.
  Recording a failure is never blocked: `fail`, `block` and `recover`
  record the unverifiable state and close.

A silent zero is not a pass. Unreadable ground truth reports
`verifiable: false`, never `derived: 0`.

OUTSIDE a Meta LOOP run the override does not apply (scope ruling,
Paul 2026-08-14) and the manual contract still holds: emit one pair
through `emit.ps1` around the fan-out, `-Lane claude -Source
coordinator`, one pair per subagent, never one per tool call.
## 1. START RELIABLY

Verify `metaloop.ps1` and `flow.ps1` exist in
`C:\Users\pgoff\.claude\glassbox`. If either is absent, report
`runtime incomplete`, name it, and stop.

Choose lanes before launch. The normal implementation path is
`claude,codex`; add `gemini` or `grok` only when the task genuinely needs
them. Start the correlated run in one call:

`& C:\Users\pgoff\.claude\glassbox\metaloop.ps1 -Action start -Coordinator claude -Summary "<redacted task>" -Lanes claude,codex`

Parse the JSON receipt and retain its `run_id`. It is the only run ID for the
task. Require `start_receipt_verified=true`. If startup fails, the adapter
emits `run.blocked`; do not continue.

## 2. DECOMPOSE AND SCHEDULE

Create the smallest useful dependency graph. Each node needs a stable ID,
owner lane, objective, dependencies, expected output, falsifiable check,
impact envelope, and reversal. Publish it once with `flow.ps1 -Action plan`.
After the plan, emit exactly one `skip` for each omitted optional lane so the
dashboard shows `SKIP` rather than a misleading failure.

Front-load the parallel side (Paul 2026-08-10, roadmap P3.2): at plan
publication, launch EVERY independent read-only node — subagent
research, perception, review preparation — rather than when the serial
spine reaches them. Results wait for the spine instead of the spine
waiting for them; law 6 already prices this at zero extra rounds.

Pin run-level invariants (permanent, Paul 2026-08-10): a multi-node run
MUST record an `invariants` event in the coordination ledger at
`-Action start` or first reconciliation (payload: the constraint
strings, stored verbatim), and MUST produce every subsequent dispatch's
INVARIANTS block with `coordination_cli.py invariants <ledger> --run-id
<id>` — quoted mechanically from the pinned record, never re-serialized
from recollection. Pins are immutable; mid-run re-pinning requires an
explicit revision recorded as a `decision-resolved` event naming the
reason. This is law 7's copy-sync logic applied to a run's own state:
one pinned source, quoted everywhere.

Dispatch only ready nodes. Parallelize independent read-only nodes, but keep
one writer per file or mutable resource. Emit `handoff` and
`handoff-accepted` only when ownership actually crosses lanes--not for routine
tool calls inside one lane. `handoff-accepted` carries the receiver's
receipt in `-Detail` (permanent, Paul 2026-08-10): the receipt text
verbatim when ≤1200 chars, else exactly `RECEIPT sha256=<hex64>
evt=<receipt ledger event id>` — so glassbox records what the receiver
believed it received at the exact hop where meaning can diverge; a
handoff-accepted with neither form does not satisfy the law. Verify a
provider exists before routing to it; otherwise emit `skip` for optional
work or terminal `block` for required work.

## 3. KEEP THE STREAM USEFUL

The session transcript already records prompts, tools, and results, and the
GLASSEYE override derives fan-out pairs from it. The hook mirror records
nothing - it does not fire (DE-005). Do not restate any of that as Meta LOOP
lifecycle events. Emit lifecycle events only for meaningful state transitions:

- one `plan`;
- `stage-start` and `stage-complete` around a substantive stage;
- cross-lane handoffs;
- a decision or block when progress genuinely pauses;
- reconciliation and one terminal receipt.

NAMED STAGE PER DISPATCHED NODE (permanent, Paul 2026-08-27). Every node the
coordinator dispatches — subagent, Codex round, workflow, perception or
critique lane — gets its OWN `stage-start`, named with the node ID from the
plan, carrying that node's falsifiable check, impact envelope and reversal
verbatim in `-Detail`. The derived fan-out pair is not a substitute: it is
anonymous (`general-purpose: <description>`), it carries no check, and it
cannot say what the node was for or how anyone would know it failed. The plan
names the nodes; the stream must name them too, or the run is legible only to
whoever wrote the plan.

`stage-complete` IS EMITTED ONLY AFTER THE NODE'S RESULT IS IN HAND AND
ADJUDICATED — never on dispatch, never on a timer, and never inferred from a
derived `agent.completed`. The derivation's close condition is not the agent's
return: MEASURED 2026-08-27, three backgrounded subagents emitted
`agent.completed` 350 ms, 1,028 ms and 476 ms after their `agent.started`,
while ground truth showed all three still running four minutes later, every
event carrying `duration_ms: -1`. A derived completion is therefore evidence
that a dispatch HAPPENED, never that a node FINISHED. Treating it as the latter
makes `open: 0` on a terminal receipt worthless and lets `-Action finish` take
a clean receipt over work still in flight — the falsely-green twin of the
always-red gate, and precisely what the coverage refusal exists to prevent.
Ground truth for node completion is the task notification or `ListAgents`.

In compact mode, reconcile once after each mutating stage and once before
finish. Batch independent read-only nodes into one reconciliation. In full
mode, reconcile after each risk-bearing node, and give each dispatched node its
own reconciliation rather than folding several into one — a batched
reconciliation cannot record which node invalidated which assumption, which is
the only thing a reconciliation is for. Compare predicted versus observed
results, impact envelope, invalidated assumptions, evidence quality, and newly
ready dependencies. Never advance on stale assumptions.

Context hygiene (Paul 2026-08-10). TOOL-RESULT CLEARING: once a lane
output is adjudicated and its disposition recorded (ledger signoff or
receipt plus a reconciliation event), the raw output is dead weight in
the coordinator's working context — never re-quote or carry it forward;
cite the ledger record and the verified evidence instead. The ledger is
the record: every reconciliation must be completable from it alone.
SOFT CONTEXT CEILING (values ratified, Paul 2026-08-10): the soft line
is 70% of the visible context window; the end-of-window band is the
final 15%. Between 70% and 85%: finish the current node, reconcile to
the ledger, and emit a reconcile event tagged soft-ceiling before
continuing. Past 85%: no new dispatch work — reconcile and let
compaction land on a clean state. The coordinator never plans work
inside the degradation band. PROVENANCE AT RECONCILIATION: any claim entering the
coordination ledger as fact requires a provenance pointer — a node ID,
file:line, receipt or event id, or an external citation — recorded as a
`fact` event (claim fingerprinted, provenance verbatim); the ledger
rejects an orphan fact at insert. The compounding failure this blocks:
a hallucinated "fact" from node 3 silently steering nodes 7-12.

## 4. VERIFY AND FINISH

Use targeted tests for reversible local work. Require a fresh independent
review for non-trivial diffs, security-sensitive work, or full mode--not for
trivial read-only inspection.

Verification economics (Paul 2026-08-11). TIERED VERIFICATION: free
ground truth — execution, tests, schema validation, hashes — always
precedes any model-based review; never pay premium rates to find what
the interpreter finds free. Grok is dispatched only on diffs that are
material AND passed the free tier; a failing-tests diff gets no
critique dispatch. ORIGINAL-CHECK RE-VERIFICATION: a reworked node is
re-verified against its ORIGINAL falsifiable check, quoted verbatim
from the plan — the rework's verification references and quotes the
original check unchanged. Reformulating a check under rework requires
Paul: acceptance-criteria drift during rework is exactly the failure
this blocks.

Finish through the adapter:

`& C:\Users\pgoff\.claude\glassbox\metaloop.ps1 -Action finish -Coordinator claude -RunId "<run_id>" -Summary "<verified result>"`

Use `block` when authority or capability is missing and `fail` when execution
cannot safely continue. Parse the terminal JSON and do not return a successful
final answer unless `receipt_verified=true` and `terminal_event_id` is
non-empty. Terminal calls are idempotent: retrying the same action must reuse
the original receipt.

`metaloop.ps1 -Action status` reports worker health plus `receipt_state`. If
an interrupted run is `stale-running`, confirm that no live owner remains,
then close it with `-Action recover -RunId "<run_id>" -Coordinator claude
-Summary "<reason>" -StaleAfterMinutes <minutes>`. Recovery is idle-time
gated and emits a terminal `run.blocked`; never recover a live run simply to
clear the working-directory slot.

Return the run ID, mode, lane/node states, changes, measured evidence,
deviations, and anything not verified.

Task: $ARGUMENTS
