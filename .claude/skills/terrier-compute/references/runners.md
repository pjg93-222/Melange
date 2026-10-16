# Isolated Terrier builds and optional local runners

Prepared 2026-10-16 from the 2026-10-14 procedure. Run commands only from the
owner-selected checkout and within current scope; validate CLI against selected
`COMPUTE.md` and `tools/compute_build.py`. Placeholder paths are supplied explicitly.

## Build shape

```text
<approved-python> tools/compute_build.py --district <district> --out <new-private-output> --plan
<approved-python> tools/compute_build.py --district <district> --out <new-private-output>
```

Verify the first form is plan-only in the selected version. The second builds.
Do not infer an approved interpreter or output directory from a personal path in
an old handoff. The output must be new/empty, never a live `.local` folder. Preserve
`compute_build_receipt.json` with mode, exact images, run identity and versions.

Historical `TERRIER_COMPUTE` values were `container` (also unset/empty) and `windows`;
invalid modes refused execution. Read current implementation and all applicable
process/user/machine configuration. An unset variable is not proof which runtime
actually ran. A temporary owned-process fallback must restore its prior value.
Do not use `setx` or alter persistent settings as a diagnostic shortcut.

Use `TERRIER_BUILD_IMAGE`/`TERRIER_SCORE_IMAGE` only under the existing trusted
digest contract, otherwise the authenticated release manifest. Do not choose tags,
local images or a new key to bypass refusal.

- Start from `roads` unless the selected step contract explicitly consumes staged
  input stores. Later steps read the same stage; `--inputs <private-data-root>`
  stages only required stores, not a live writable mount.
- Scores needs the existing demo key and walk needs the existing salt. Refuse absent
  inputs, never generate replacements or print them. A Windows output may contain
  `.demo-key`; protect the entire output as private runtime data.
- Do not silently migrate host-only steps, servers or account stores. Scope is the
  selected compute steps; verify their actual dependencies.
- Historical CO-05 parity is not new evidence for OR-05, CT-01 or changed bytes.

## Optional `_build` runners

The old `run_remaining.ps1`, `run_fast.ps1` and `run_nowithhold.ps1` were untracked
local tools. Their absence in public source is expected. Do not fabricate or import
them from an unrelated session. If a current task uses them, review exact bytes,
input/output paths, marks, cleanup and ownership first; retain dated backups for
authorized edits without changing line endings.

The historical step form used `--district <d> --steps <step> --inputs <private-inputs>
--out <new-private-output> --drop-stage`. Inspect stage ownership and cleanup before
using `--drop-stage`. Legacy timeout cleanup targeted every shared project-labelled
container: do not run it alongside another owner or adopt it as a safe stop method.

Do not mix modes midway through one district's ingest/extend/bundle chain without
an accepted input-location transition. Preserve the wrong-ZIP guard: unexpected
ingest/extend ZIP identity must fail; diagnose stale marks or paths rather than
disabling it.

Building does not authorize installation. An in-scope live install must stage,
hash-verify, preserve replaced files and perform its reviewed swap/rollback under
exclusive ownership. A phase-one failure must retain or restore original outputs.
Never overwrite account data or a newer installed source from an older build.

Use bounded reads of existing status/marks/receipts for progress, with private
contents kept local. Absence of a process or a status line does not prove success.
