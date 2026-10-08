# Review packet: legislative-effectiveness shadow lane (Codex worktree f149), assembled 2026-09-11

This folder is the "show me the diff" step that the Codex implementation thread never reached. Everything here was produced read-only from the f149 working tree and the live tree; nothing was applied to the live tree.

Contents:

- `../LEGISLATIVE_EFFECTIVENESS_SHADOW_VALIDATION_2026-09-11.md`: the validation and completion record (provenance, what was built, what the shadow measured, independent verification, production neutrality, limitations, what is not done, how to apply and revert).
- `IMPLEMENTATION_DIFF_2026-09-11.patch`: the implementation's changes to the 11 tracked files, relative to baseline commit `d68ddcda6` (which itself equals the live tree for those files, line endings normalized).
- `NEW_FILES_MANIFEST.txt`: every new module and test file with sha256, plus the carried baseline files and the modified tracked files, each re-verified against the current f149 file.
- `BRAIN_UPDATE_DRAFT_2026-09-11.md`: STATE.md text and an optional DEADENDS entry for Paul to apply to the Project Brain.
- `evidence/`: the reproduction comparison (46 of 50 outputs byte-identical; 4 stdout logs differ by timestamps only), input and code freshness tables, Codex's own audit script output on both generations, the Leg% parity proof (533 of 533), the baseline-allocation-equals-production check, the live-tree drift check, the worktree test results, the prepared Codex contract for registering the six test suites, and the headline shadow numbers.

Outstanding code edit, not done: registering the six new unittest suites in `fec/tests/run_tests.py` `_LANE_MODULES`. The exact edit is in `evidence/prompt.txt` and the validated contract in `evidence/contract.json` (ledger run-id `legeff-runtests-20260911`). Both Codex routes failed on 2026-09-11: the MCP server was refused by the session health check ("stdin is not a terminal"), and one headless `codex exec` attempt (session `01a092ef-1b34-7ef1-8fb0-aa78ac9d6c9a`, 17.96 s) returned "You've hit your usage limit ... try again at Sep 17th, 2026 1:16 PM" before writing anything; `run_tests.py` is unchanged (sha256 b4b5b897c3c0...). Codex's runtime banner showed `model: gpt-6-astra`, `reasoning effort: ultra`, which differs from the codex-executor skill's documented pin (gpt-5.6-sol, xhigh); that reconciliation is Paul's.

Gates that remain Paul's: applying the diff to the live tree (rank-adjacent), re-measuring the kernel and `audit_full` in the live tree afterwards, and every activation decision in section 8 of the plan. The shadow itself changes no production artifact.

Addendum 2026-09-12: after review Paul rejected the results-only board ("it needs to be a combination of primacy, success, amount, and substance") and ruled D-028: board = P x (0.80 + 0.20 x L) with L = 0.35 success + 0.35 amount + 0.30 substance (within-chamber percentiles), Leg% = L; D-026 superseded. The operative contract is ACTIVATION_CONTRACT_2026-09-12_v2.md; v1 is kept as a superseded draft. Evidence for the ruling: evidence/COMPOSITE_BOARDS_118.md, _PART2.md, OUT_OF_SAMPLE_119.md (exploratory, not the yardstick), CHAMPION_SHARE_AND_FLOOR_SWEEP.md, CORTEZ_MASTO_AND_COVERAGE.md.
