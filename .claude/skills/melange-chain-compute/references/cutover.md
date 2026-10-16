# Engine transition and fallback

Procedure retained from the 2026-10-14 source notes, corrected 2026-10-16.
Historical D-188/D-205 approvals are not authority to activate containers now.
Validate the selected `ops/compute/cutover.py` contract and current task scope.

From the explicit Melange checkout, `python ops/compute/cutover.py show` displays
configured phases. The following are **mutation command shapes**, to use only when
the current task authorizes that specific transition and evidence is verified:

```text
python ops/compute/cutover.py set <chain|collect|office> container
python ops/compute/cutover.py set <chain|collect|office> container --evidence report=<verified-report>
python ops/compute/cutover.py set <chain|collect|office> windows
```

The `report` slot applies to chain/collect; office has two different slots below.
Do not run an example with literal placeholders or use a phase's evidence for another.

| Phase | Default evidence under `audits/compute_parity` | Required result |
|---|---|---|
| chain | `report=chain_parity.json` | PASS, exit code 0, empty failed gates |
| collect | `report=collectors_replay.json` | PASS for the proven collector scope |
| office | `equivalence=office_equivalence.json`, `rank_check=office_rank_check.json` | Equivalent, cells compared > 0; PASS with 533 members and 533 exact ranks |

Check `MELANGE_PARITY_DIR` and `MELANGE_ENGINE_<PHASE>` overrides; environment can
override the file. Do not print arbitrary environment contents. A running refresh
can retain the engine choices read at startup, so transition only between owned
runs. Preserve the tool's fail-closed evidence and event-hash behavior.

`engines.json` is tracked. If an authorized transition changes it, record the exact
diff, evidence SHA256 and rollback state in a scoped commit. Do not import unrelated
worktree edits. A process-only Windows override is temporary and must be restored
after the owned operation; do not persist settings as a diagnostic convenience.

## Scope and prerequisites

- Chain historically covered the weekly `run_pipeline.py` with writer-lease handoff,
  not the daily Congress pipeline. Verify the current call graph before switching.
- Collect covers only the selected `STEP_SERVICE` network collectors. R collectors,
  visible-browser lanes and other host steps were outside that migration. Check
  secret-file mounts, scheduler wiring, cancellation and staging of required stores
  without disclosing keys. A keyless replay does not establish those properties.
- Office uses a workbook view copy, leaving the original workbook and Windows
  reference path intact. The historical implementation treated office as non-gating
  for refresh; inspect current behavior rather than assuming engine state.
- Verify Windows can read container-written receipts and that required lease fixes
  are in the exact selected bytes. PATH_ONLY/EOL_ONLY/ZIP_CONTENT exceptions need
  an applicable accepted disposition; exit 3 is not an unconditional PASS.
- Use the existing authenticated manifest or independently configured trusted image
  digest. An unset source is a failure, not permission to select a local image/tag.

If downstream values move despite a gate, record the inconsistency and stop further
activation. Apply a supported fallback only within existing authorization. Do not
kill a running job or disable trust checks to perform a transition.
