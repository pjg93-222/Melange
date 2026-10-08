Your read-only plan is accepted with the following corrections and execution
limits. Continue as the Opus 5 maximum-effort owner of the proposal-
adjudication node.

Implement and verify the candidate-level adjudication path in the main
checkout:
C:\Users\pgoff\OneDrive\Desktop\Melange Systems

Do not modify the supplied reference worktree:
C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\legislative-changes-data-prep-217560

Scope for this turn:
1. Add a deterministic packet producer and candidate-level Opus runner with
   focused tests.
2. Build a new hash-addressed packet generation from the current
   58a4bd2e... queue.
3. Run an offline dry run over the entire universe so incomplete candidates
   receive explicit flagged proposals without provider calls.
4. Dispatch exactly 25 evidence-complete candidate canaries to
   claude-opus-5 with effort=max. Use an aggregate provider budget cap of
   USD 15 and stop safely before any 26th provider call.
5. Verify immutable receipts, hashes, replay behavior, output schemas, and
   that no integration or production artifact changed.

Corrections to your plan:
- The Congress.gov accepted_html page contains only one displayed version.
  For candidates whose inventory declares multiple versions, join the
  GovInfo version collector:
  audits\legfix5\govinfo_bill_xml_versions\runs\full-18440-20260727b
  and verify each accepted receipt and object_path/content_sha256. Parse
  usable legislative text from every official XML object. Never claim
  all-version review from the single Congress.gov page.
- The two summary-settled candidates with zero expected versions are not in
  the 4,116/10,091 finalizable stratum; they must stay flagged without a
  provider call.
- One proposal unit means one candidate with all 19 category slots and every
  discovered membership. Output exactly 19 category-evidence proposals and
  exactly one membership proposal for each discovered membership.
- Model output is proposal-only. Set automated_final_decision=false and a
  non-final adjudication state. Never emit human_ratified or
  reverified_preexisting_project_decision.
- An include proposal requires affirmative official-material nexus evidence.
  An exclude_false_positive proposal requires affirmative false-positive
  evidence and a complete all-version review. Missing, oversized, invalid, or
  ambiguous evidence is flagged.
- Do not infer negative evidence from search membership or term absence.
- Do not weaken the existing culling/integration contracts.
- Use new source/test files where practical. Preserve all pre-existing dirty
  files and unrelated user changes. The existing effort=max patch in
  fec\run_legislation_claude_ambiguity_review.py is an input; do not discard
  it.
- Write only source/tests and a new
  audits\legfix5\opus_adjudication\<hash-addressed-generation> tree. Do not
  write corpus, scoring, junk ledger, rank, integration, sync, or production
  files.

Canary selection must be deterministic and include:
- at least five multi-version candidates;
- at least five candidates with more than one discovered membership;
- only packets under the runner's verified prompt-size ceiling;
- no evidence-incomplete candidate.

Use the repository's focused-test harness rather than pytest. On completion,
return a concise receipt: files changed, tests, packet counts, auto-flag
counts, the 25 canary keys, model/effort, actual calls and usage, disposition
counts, safety assertions, and all remaining blockers. Do not start the full
4,116-candidate provider run in this turn.
