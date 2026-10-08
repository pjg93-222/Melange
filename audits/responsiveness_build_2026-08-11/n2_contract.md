CONTRACT — responsiveness-surface N2 (registry + producer + tests)
Run: run-20260811T1443271724756Z-ccd0abf0e4 | Lane: codex | Worktree: C:\Users\pgoff\AppData\Local\Temp\claude\cxwt-responsiveness (branch codex/responsiveness-surface)

OBJECTIVE: In the named worktree, materialize the CU ask-registry ledger byte-verbatim and implement the responsiveness_layers producer plus its test suite, exactly per _build_specs/responsiveness_spec_build.md. Display-only surface; no other system behavior changes.

CONSTRAINTS:
1. data/lobbying/industry_ask_registry.ndjson must be an EXACT byte copy of _build_specs/responsiveness_spec_registry.ndjson (sha256 4b7b9301428fc8e7de0aa62a9b200cbd4fb07c92abf4e18bf359500e4017ace3). LF endings. No reformatting, no key reordering.
2. fec/engine/responsiveness_layers.py implements _build_specs/responsiveness_spec_build.md (sha256 267255d2a3780d6aebf6c8a06ba4fedff35304407a748dd4d9b01dcd536da900) exactly. The load-bearing spans are quoted verbatim below; the file is the full authority. No design choices are open to you.
3. House style: mirror fec/engine/primacy_factors.py idioms — encoding boilerplate, atomic write, logging contract, paths.py root resolution.
4. Producer supports --out <path> override for verification runs; default output data/engine/responsiveness_layers.json under the resolved root.
5. NO wall-clock timestamps anywhere in the output artifact (reruns must be byte-identical).
6. Nothing outside the IMPACT ENVELOPE changes. No new dependencies.
7. Real data files (member_desk_bundle.json, data/engine/primacy_factors.json, etc.) may be ABSENT in this worktree (repo-ignored artifacts). Tests use fixtures exclusively. Do NOT attempt a real-data producer run in this worktree.
8. The registry loader validates BEFORE compute; every guard failure is a hard error naming the row.

VERBATIM SPEC SPANS (authority = _build_specs/responsiveness_spec_build.md):
--- eligibility ---
"- status != active  -> NOT counted anywhere except unscored_count
  (status=inactive rows are Paul-struck: fully ignored, not unscored).
- chamber scoped and m.chamber != scope.chamber -> ineligible.
- party scoped and m.party != scope.party -> ineligible.
- committee scoped -> ALWAYS unscored in this pilot (no rosters outside
  finance in corpus) — belt on top of the CISCOMANI row's status.
- service: m must have served congress(v). Source of truth: the service
  data inside data/network/cosponsor_selectivity.json (its definition
  states opportunities are scoped to 'a Congress the member served';
  inspect its schema — 'congresses'/'service_source' keys — and reuse).
  If no per-member service map is extractable, ESCALATE (STOP REPORT)
  rather than inventing a proxy.
- answered(v) = vehicle key present in m.bills with ANY role (sponsor/
  original/cosponsor/signer; initiator's own vehicle counts answered)."
--- capacity ---
"Capacity model (both specs, betas receipted): OLS of
mix.cu_primary ~ [1, fin_member, fin_lead_grade, fin_mem_grade,
agenda_term, senate] over all 533; agenda_term = agenda_credit (linear
spec) or log1p(agenda_credit) (log spec); fin_* from member_desk_src
committee.on containing 'Financial Services' or 'Banking'. Closed-form
normal equations w/ partial pivoting (reference implementation:
audits/backfire_analysis_2026-08-11/n2_models.py ols()). HEADLINE =
linear spec; log spec present in artifact for transparency."
--- receipts ---
"Receipts block: registry_sha256, registry_rows=27, active_rows,
unscored_rows, betas both specs, service_source, in_group_definition,
display_only: true. NO wall-clock timestamp."

ACCEPTANCE CRITERIA:
1. sha256 of data/lobbying/industry_ask_registry.ndjson equals 4b7b9301428fc8e7de0aa62a9b200cbd4fb07c92abf4e18bf359500e4017ace3 (state the computed hash).
2. Producer compiles clean via py_compile.compile(src, cfile=<scratch path>, doraise=True) — no __pycache__ in the worktree.
3. fec/tests/engine/test_responsiveness_layers.py passes under python -m unittest, covering ALL of: loader guards (unknown vehicle-vs-tags, duplicate row, bad scope key, bad status, bad chamber/party values); eligibility negative controls (unscored excluded from denominators, inactive fully ignored, wrong-chamber ineligible, party-scope excludes other party, non-served-congress ineligible); answered semantics (any role, initiator counts); determinism (two fixture runs byte-identical); capacity OLS reproducing hand-computed fixture betas.
4. Full unittest output (exit code + test count) pasted.
5. FILES CHANGED lists exactly the registry, the producer, the test module, and any fixture files — nothing else.

IMPACT ENVELOPE: worktree cxwt-responsiveness ONLY. May create/modify ONLY: data/lobbying/industry_ask_registry.ndjson; fec/engine/responsiveness_layers.py; fec/tests/engine/test_responsiveness_layers.py; fixture files under fec/tests/engine/. Processes: python (py_compile to scratch cfile, unittest). Read-only: _build_specs/*, existing repo files. No git commands ever.

CONFIRMATION CONDITIONS: RECEIPT block first (objective + full enumeration of the 8 constraints AND the 8 INVARIANTS lines + acceptance checks in your own words). HANDSHAKE (READY / READY_WITH_LIMITS / BLOCKED) at execution-turn start. End with the eight labeled lists. STOP REPORT on any ambiguity — especially if _build_specs files are unreadable or the sandbox blocks writes (then: BLOCKED, offer nothing, await instruction).

INVARIANTS (quoted mechanically from the run's pinned ledger record):
- display-only: responsiveness/capacity NEVER enters any score, tier, or rank - desk panel + board chips are presentation
- ranks_python 0/533 after chain; four boards byte-identical except declared responsiveness chip keys and note line
- ask registry rows fable-signed with evidence, row-level Paul override, loader guards (unknown vehicle keys, invalid scope, duplicates rejected)
- unscored vehicles NEVER enter eligibility denominators (W-and-M-scoped CUTAX letter unscored; negative-control test required)
- no manufactured scope: letter scoping carries evidence basis, observed-composition circularity documented for KIMCRAPO/WATERS/SCOTT
- prereg gates any future scoring use; ACU internal rankings unavailable (Paul ruled not shareable) - no criterion-validity claims anywhere
- CU pilot only: registry industry=credit_union rows exclusively this run
- service-map source must be real (cosponsor_selectivity or equivalent) - Codex escalates rather than inventing a proxy
