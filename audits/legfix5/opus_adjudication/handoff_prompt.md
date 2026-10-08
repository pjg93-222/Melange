You own the proposal-adjudication node of an active Meta LOOP run. Work at
Claude Opus 5 maximum effort. You replace Fable as the adjudication
coordinator, but you do not replace the human ratifier.

This first turn is READ-ONLY PLAN MODE. Inspect the files yourself and return
an evidence-grounded execution plan. Do not edit files, run network fetches,
or claim that model output is human-ratified.

Primary reference worktree:
C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\legislative-changes-data-prep-217560

Active culling workspace:
C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\legfix5

Read at minimum:
- the worktree's legislative audit and errata under audits\legfix2;
- LEGISLATION_RELEVANCE_REVIEW_METHOD.md;
- LEGISLATION_JUNK_PILE_CONTRACT.md;
- fec\LEGISLATION_19_CATEGORY_ADJUDICATION_DESIGN.md;
- the current category queue manifest and representative worksheet/queue rows;
- candidate evidence receipt and representative rows;
- fec\run_legislation_claude_ambiguity_review.py;
- fec\legislation_culling_integration_contract.py;
- the current reversible-culling and staged-integration receipts.

Recover and honor these invariants:
- the current universe is exactly 18,557 candidates, 64,004 discovered
  memberships, and 19 category slots per candidate;
- all memberships for a candidate stay in one proposal unit;
- title, official CRS summary or explicit official unavailability, all
  official text versions, action/stage, and relationship evidence are
  evidence inputs; search membership is not decision evidence;
- affirmative nexus may support include; affirmative false-positive evidence
  may support exclude; absence or incomplete evidence must remain flagged;
- automated output is proposal-only and cannot set human_ratified;
- do not write the corpus, scoring files, junk ledger, rank outputs,
  integration outputs, sync state, or production;
- preserve existing user changes and use a new hash-addressed audit generation;
- integration remains blocked pending a separate user Greenlight.

Determine whether existing producers and archives can assemble complete
candidate-level packets without new network access. Prefer a bounded,
resumable, immutable-receipt design. A full run must be computationally and
operationally realistic: quantify model-call count, candidate eligibility,
prompt-size distribution, and subscription/cost or rate-limit risks. Identify
what can be finalized after adjudication and what must remain flagged.

Return JSON with exactly these top-level fields:
- verdict
- recovered_method
- authoritative_inputs
- candidate_level_design
- evidence_join
- eligibility_gates
- output_contract
- canary
- full_run
- verification
- blockers
- integration_boundary

Every assertion about a file or count must name the local path or receipt that
supports it.
