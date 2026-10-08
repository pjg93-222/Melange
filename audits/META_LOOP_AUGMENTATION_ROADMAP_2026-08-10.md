# META LOOP AUGMENTATION ROADMAP — ARCHIVED

**Execution record (added at archival, 2026-08-11):** delivered to the
coordinator 2026-08-10, echo-gated, and executed to completion
2026-08-11. All phases ran as receipted Meta LOOP runs: P0
`dc28bb31e4`, P1 `8134123cc5`, P2 `2dad99c8b2`, P3 `452513c655`, P4
`604b8724d9`, P5 `b40d2cdea4`, plus the Paul-delegated
improvements-queue disposition `07819ef625`. Every [RATIFY] item
stamped or explicitly rejected (P3.4 REJECTED — transport serializes
parallel dispatch; concurrency mechanically unavailable). Commits:
c4e22c45f/b296cf221/f58434a13 (P0), 4f3b57af0/a02a55be1/0b6e7066f
(P1), d1b72953c/f34166e0d/dcf7b4c8a (P2), fab4836e4/9cc47f16f (P3.0
hotfix), 2051da717 (P3), 3ed1b6ea7 (P4+P5, N=5), 502e014eb/579278b10/
1132a7f22 (queue hardening). Ratification packets:
AUGMENTATION_P1_RATIFY_PACKET_2026-08-10.md,
AUGMENTATION_P2_RATIFY_PACKET_2026-08-10.md,
AUGMENTATION_P3_RATIFY_PACKET_2026-08-11.md. Standing practices +
plant records: LANE_LAWS_VALIDATION_2026-08-09.md. Global exit report
delivered in-session 2026-08-11. The text below is the roadmap as
issued, preserved verbatim as the campaign's source document.

---

META LOOP AUGMENTATION ROADMAP
Authority: Paul-directed. Drafted 2026-08-10 with Fable (chat) against the canonical metaloop command doc (UNIVERSAL LANE LAWS, Paul 2026-08-09 amendment) and current multi-agent failure research. Status: proposal until ratified node-by-node below.
Purpose: close the comprehension layer (the failure category the current laws do not yet bite), harden context integrity across long runs, and shorten the serial spine — without adding lanes, coordinators, or frameworks, and without weakening any existing law.
Research basis (informative, not re-litigable during execution): MAST failure taxonomy (Cemri et al., NeurIPS 2025) — specification failures ~41.8%, inter-agent misalignment ~36.9%, task verification ~21.3% of observed multi-agent failures; base-model improvements alone insufficient. Anthropic context-engineering guidance (2025) — context rot; compaction, structured note-taking, tool-result clearing. Multi-agent isolation buys large quality gains at ~15x token cost, which is why the compact-mode trigger gets sharpened rather than the max-effort default questioned.
HOW TO EXECUTE THIS DOCUMENT

1. Each phase runs as its own Meta LOOP run, full mode, lanes `claude,codex`. Add `grok` only where a node names it. `gemini` is not needed for this work. Never invent work to exercise a lane — several nodes are governance-plane only and will show Codex SKIP; that is correct.
2. All UNIVERSAL LANE LAWS bind throughout, unchanged until a node here amends them with Paul's stamp. In particular: role monopolies (Fable writes the governance plane — docs, skills, commands, memory, git; Codex writes code and data), one writer, never downgrade (Codex xhigh/priority, grok-4.5, gemini-3.6-flash-high), glasseye emission around every fan-out, copy sync with md5 verification in the same session as any ratified change.
3. RATIFICATION PROTOCOL. Nodes tagged [RATIFY] end in a decision packet to Paul: proposed canonical text, diff against current, expected effect, reversal. No [RATIFY] change lands without Paul's stamp in the standing convention ("permanent, Paul YYYY-MM-DD"). Untagged nodes land under normal Fable review. This document authorizes drafting and testing; it does not pre-ratify anything.
4. DRAFT-AGAINST-LIVE RULE. This roadmap specifies REQUIREMENTS for each amendment, not final wording. Final wording is drafted by Fable against the live canonical files, because this document was written without access to them and pre-written text would risk exactly the drift the laws exist to prevent.
5. NODE SCHEMA. Nodes below carry ID, owner, objective, and falsifiable check. At plan time, Fable completes each to the full §2 schema — dependencies, expected output, impact envelope, reversal — against the live tree. Envelope and reversal depend on current file state and are deliberately left to plan time.
6. ECHO GATE ON THIS DOCUMENT. Before any Phase 0 work: restate the objective, the binding constraints above, and the per-phase deliverables in your own words, and wait for Paul's confirmation. The mechanism being installed applies to its own installation.
7. Phases are serialized. Within a phase, follow the dependency graph; read-only nodes parallelize per law 6.

PHASE 0 — BASELINE INSTRUMENTATION
Rationale: no later phase can claim improvement without a before-measure, and if the local failure distribution differs materially from MAST's, Phases 1–4 reorder. One run. Cheapest phase; nothing lands anywhere else until it finishes.

* P0.1 ledger-metrics (owner: Codex) — Extend the coordination ledger's audit to report, per run: per-node wall latency and token cost, and the serial-spine total versus parallel-side total. Check: audit over the last five closed runs emits the table; numbers reconcile against glassbox timestamps for one spot-checked run.
* P0.2 failure-attribution field (owner: Fable for policy text; Codex for schema) — Every node that ends blocked, failed, or reworked must carry one tag: `spec-misread | coordination | verification | infra`. Mirrors MAST categories so local numbers are comparable to published ones. Check: ledger rejects a terminal blocked/failed/rework record without the tag.
* P0.3 behavioral plants, round one (owner: Fable) — On the next three or four pieces of REAL queued work (never invented work), seed each Codex dispatch with one subtle, easily droppable constraint. Record whether the delivered work honors it. This measures constraint survival in output — the true pre-echo-gate baseline. Method and results append to `audits/LANE_LAWS_VALIDATION_2026-08-09.md` or a dated successor. Check: per-lane constraint-survival rate exists as a written number.
* P0.4 baseline report (owner: Fable) — Report to Paul: local failure distribution versus MAST 42/37/21, plant survival rate, spine latency profile. If the local distribution materially inverts the published one, propose a phase reordering and stop for Paul's ruling before Phase 1. Check: report delivered; ordering confirmed or amended by Paul.

Exit: run finished with `receipt_verified=true`; baseline numbers on file.
PHASE 1 — COMPREHENSION LAYER
Rationale: targets the two largest failure categories (~79% of failure mass combined). The existing escalation protocol catches problems a lane detects; a confident misread detects nothing. These nodes verify what goes INTO a lane, not only what comes out. This phase amends canonical governance; it ends with the same adversarial-review step that produced the 2026-08-09 amendment.

* P1.1 RECEIPT list (owner: Fable) [RATIFY] — Amend the codex-executor Standing dispatch preamble: a ninth labeled list, RECEIPT, positioned first. Requirements: before any work, Codex restates in its own words (a) the objective, (b) every binding constraint, (c) the falsifiable check. Fable verifies the receipt against the node spec BEFORE adjudicating any output; a mismatched receipt is a re-dispatch with correction, logged as caught-at-gate. Check: next three live dispatches all carry RECEIPT and the ledger shows Fable's verify step preceding adjudication.
* P1.2 receipt storage (owner: Codex) — Ledger stores the node-spec and the receipt as a pair at insert; audit flags any dispatch without one. Same value-pinning pattern as the existing effort/tier enforcement. Check: a test insert without a receipt is flagged; audit lists receipt coverage per run.
* P1.3 invariant carriage (owner: Fable for law text; Codex for mechanism) [RATIFY] — Run-level invariants (constraints that bind every node) are pinned into the ledger at `-Action start` or first reconciliation. A tenth standing list, INVARIANTS, is populated MECHANICALLY from the ledger into every dispatch — never from Fable's recollection. This is law 7's copy-sync logic applied to a run's own state: constraints are quoted from one pinned source, not re-serialized per node. Check: on a run of ≥5 nodes, the INVARIANTS block in the final dispatch is byte-identical to the pinned record.
* P1.4 verbatim-artifact law (owner: Fable) [RATIFY] — Draft a new UNIVERSAL LANE LAW. Requirements: artifacts travel as themselves, never as descriptions. Grok critiques the diff, never a summary of the diff. Subagent findings return with file:line pointers and exact quotes. When Fable distills findings into a Codex spec, the spec carries those pointers so Codex can consult primary evidence. Paraphrased artifacts are the confabulation channel the role monopolies do not currently close. Check: the next Grok dispatch's input contains the raw diff; the next subagent report contains pointers; a later plant (P5.1) tests compliance.
* P1.5 Gemini report-shape split (owner: Fable) [RATIFY] — Amend the perception report shape into three sections: TRANSCRIPTION (literal, verifiable content), INFERENCE (Gemini's conclusions), ILLEGIBLE (flagged low-confidence regions). The perception lane's whole job is lossy serialization; the shape must make the loss legible so interpretation cannot launder into fact. Check: next perception dispatch returns the three-section shape.
* P1.6 Grok citation requirement (owner: Fable) [RATIFY] — Amend the critique report shape: every critique point cites the artifact location it concerns, so adjudication checks claims against ground truth rather than persuasiveness. Check: next critique report has zero uncited points.
* P1.7 handoff-accepted payload (owner: Fable for shape; Codex if the adapter/emit path needs code) — `handoff-accepted` carries the receiver's receipt (or its hash plus ledger pointer), so glassbox records what the receiver believed it received. Converts telephone-game failures from invisible to auditable at the exact hop where meaning diverged. Check: glassbox stream for one live handoff shows the receipt content or resolvable pointer.
* P1.8 copy sync sweep (owner: Fable) — Per law 7: sync user-scope copies of every file amended in this phase and md5-verify both, same session as ratification. Check: md5 sweep clean.
* P1.9 adversarial review of the amendments (owner: Grok critiques; Fable adjudicates; Paul ratifies) — Add the grok lane for this node only. Grok receives the full amended texts verbatim (per P1.4) and critiques for loopholes, contradictions with existing laws, and unenforceable clauses. Fable adjudicates; Paul stamps final text. Matches the precedent that produced the 2026-08-09 amendment. Check: critique on file; adjudication recorded; stamps present.

Exit: all P1 [RATIFY] items stamped or explicitly rejected by Paul; sweep clean.
PHASE 2 — CONTEXT HYGIENE
Rationale: context rot is the silent failure mode — no error is emitted; the coordinator just attends less accurately as noise accumulates. Industry attributions put context drift/memory loss behind most long-horizon agent failures. All four nodes are latency-neutral.

* P2.1 tool-result clearing policy (owner: Fable) — Standing policy: once a Codex output is adjudicated and its disposition is in the ledger, the raw output is cleared from the coordinator's working context; the ledger is the record. This is the documented safest compaction lever, and the structured note store it depends on already exists — it is the ledger. Check: after one adjudication, a context audit shows the raw result cleared and reconciliation still completes from the ledger alone.
* P2.2 Gemini extraction charter (owner: Fable) [RATIFY — this widens law 1's wording, "Gemini is only for real media perception," and must be ratified as a charter amendment or explicitly rejected; without the stamp, routing documents to Gemini is a lane violation] — Requirements: bulk raw corpora (long documents, large text sets) may route to Gemini as an extraction lane; structured findings with pointers return; raw bulk never enters the coordinator's context. The P1.5 TRANSCRIPTION/INFERENCE split applies to extraction output identically. Check: one live extraction run where the coordinator's context contains findings and pointers but never the source bulk.
* P2.3 soft context ceiling (owner: Fable for policy; Codex if tooling needed) — The coordinator reconciles-and-compacts at a soft threshold well below the hard window, and never operates in the end-of-window band (the documented degradation zone — models near their visible limit truncate and abandon). Threshold value proposed by Fable at plan time, ratified by Paul. Check: one long run's stream shows a compaction/reconciliation event fired at the soft line, before the hard limit was approached.
* P2.4 provenance at reconciliation (owner: Fable for policy; Codex for ledger validation) — Any claim entering the ledger as fact requires a provenance pointer (node ID, file:line, receipt, or external citation). Reconciliation rejects orphan facts. This is the anti-poisoning gate: the compounding failure is a hallucinated "fact" from node 3 silently steering nodes 7–12. Check: a test reconciliation containing one deliberate orphan fact is rejected with the orphan named.

Exit: all four in force; P2.2 stamped or rejected.
PHASE 3 — LATENCY
Rationale: law 6 already states it honestly — the serial spine is a deliberate price. Latency work means shortening the spine and moving work beside it, never denying the price. Ordered by ambition.

* P3.1 compact-mode rubric (owner: Fable) [RATIFY — sharpens §0, does not weaken it; present to Paul exactly as such] — At `-Action start`, Fable answers two questions: does any node mutate state? does any node's output feed another lane? Two noes route to compact mode. Converts "max effort by default" from "always pay the multi-agent token multiple" into "pay it where isolation buys the quality gain." Check: two consecutive qualifying trivial tasks route compact; one non-qualifying task routes full; rubric answers logged in each plan.
* P3.2 plan-time front-loading (owner: Fable) — Decomposition launches ALL independent read-only nodes (perception, research, subagent review) at plan publication rather than when the spine reaches them, per law 6's existing allowance. Results wait for the spine instead of the spine waiting for them. Check: next full run's stream shows every independent read-only node started within one event of `plan`.
* P3.3 parallel-dispatch re-verification (owner: Fable designs; Codex executes inside the sandbox) — Law 5's own text calls its basis "a dated, re-testable observation — re-verify before ever relying on parallel dispatch." This node is that re-test, explicitly authorized HERE AND ONLY HERE: a disposable sandboxed worktree, two Codex dispatches touching disjoint files, MCP link observed throughout. Either outcome is recorded as a fresh dated observation in the law's basis. On PASS: draft a [RATIFY] amendment permitting parallel Codex dispatch across disjoint files — one-writer-per-FILE fully preserved — for Paul's ruling. On FAIL: refresh the dated basis; no behavior change anywhere. Guard: this test is not license for parallel dispatch in any other run until and unless Paul ratifies the amendment. Check: dated observation written either way; on PASS, decision packet delivered; on FAIL, law 5 basis updated with the new date.
* P3.4 disjoint-file enforcement (owner: Codex; CONDITIONAL on P3.3 PASS and Paul's stamp) — Ledger validates at insert that concurrently open Codex dispatches declare non-overlapping file sets; overlap is rejected the way downgraded effort/tier already is. Check: a test pair with one overlapping path is rejected at insert.

Exit: P3.1–P3.2 in force; P3.3 outcome on file; P3.4 only if ratified.
PHASE 4 — VERIFICATION ECONOMICS
Rationale: the smallest failure category gets the leanest phase. Tier checks by cost; never pay premium rates to find what the interpreter finds for free.

* P4.1 tiered verification (owner: Fable) — Free ground truth (execution, tests, schema validation) always precedes any model-based review. Grok is dispatched only on diffs that are material AND passed the free tier. Check: next reviewed run's stream shows a test/execution event preceding any grok handoff; a failing-tests diff shows no grok dispatch.
* P4.2 original-check re-verification (owner: Fable) — A reworked node is re-verified against its ORIGINAL falsifiable check, quoted verbatim from the plan. Reformulating a check during rework requires Paul — reformulation under rework is exactly where acceptance criteria drift. Check: a rework node's verification event references the original check ID and quotes it unchanged.

Exit: both in force.
PHASE 5 — SELF-MEASUREMENT (standing practice, not a one-time run)
Rationale: the plants that validated the lane laws tested compliance — does the lane obey. These extend the same method to comprehension fidelity — does the lane understand — and make loss a tracked number with a trend, not an assumption.

* P5.1 standing comprehension plants (owner: Fable) [RATIFY the rate] — At a low steady rate (proposed: one in N live dispatches, N set by Paul), seed one subtle constraint and score both receipt reflection (post-P1.1) and output survival (the P0.3 measure, for continuity). Results append to the standing audit file; per-lane loss rate becomes a tracked trend. Check: after the first interval, the audit file shows the rate held and the trend line exists against the P0.3 baseline.
* P5.2 dated-observation sweep (owner: Fable) — Quarterly: every dated observation cited as a basis anywhere in the laws is re-verified or its date refreshed, generalizing law 5's own instruction. Check: sweep log lists each dated basis with a current verification date.
* P5.3 quarterly distribution compare (owner: Fable) — Compare the local failure-attribution distribution (P0.2 tags) against the Phase 0 baseline. Shrinking spec-misreads with static coordination failures is the signal to revisit handoff shapes next — future tightening ordered by local data, not by the next paper. Check: quarterly report delivered with the comparison and one recommendation.

GLOBAL EXIT CRITERIA

* Every phase's run finished through the adapter with `receipt_verified=true` and a non-empty terminal event.
* Every [RATIFY] item stamped or explicitly rejected; every ratified file synced and md5-verified per law 7.
* Post-augmentation report to Paul: receipt-catch rate at the echo gate, plant survival delta versus P0.3, spine latency delta versus P0.1, token cost delta, and the complete POTENTIAL IMPROVEMENTS list accumulated across all runs — none silently absorbed or discarded.

WHAT THIS DOCUMENT DOES NOT AUTHORIZE
No lane substitutions. No model or effort downgrades. No parallel Codex dispatch outside P3.3's sandbox unless P3.4 is ratified. No invented work to exercise a lane. No silent absorption of POTENTIAL IMPROVEMENTS. No amendment landing without Paul's stamp. TOTAL LANE LOSS during any phase remains a HARD STOP until Paul rules.
