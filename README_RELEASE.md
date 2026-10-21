# Melange application source (release)

Filtered, history-free application source for Melange. The baseline is the published tree of `main`: every path is published from one recorded source, and `FILTER_REPORT.txt` and `SOURCE_PROVENANCE.json` name the source of each increment. The latest increments: local Melange main at commit `39715eae00f5dec9274b4643fd7fca9d655cb6a0` for fec/engine/build_competitiveness.py, and at commit `c1ab75e3f27adafb98f5ce2e3e32a48d3dc98c23` for fec/lobbying/cosponsor_forecast.py; local Melange branch `claude/small-tooling-20261020` at commit `ed64156ff37e2536469cd1130174b0d5ee6dcd16` for the other six small-tooling paths (ops/vps/cloud-init.yaml, ops/VPS.md, ops/tests/test_compose_policy.py, fec/moneyball_core.py and two tests; fec/tests/run_tests.py is merged with main's version, Addendum 36); local Melange worktree branch `claude/sharp-feynman-e85406` at commit `5ef6dbe67b7c4f572a4a215bf384fc5e94554e41` for the four speech-channel kernel test paths (pull request #23); local Melange branch `fix/e2e-20261020` at commit `8a641d9ab60eefde1b29e1f28bb5519a928c002d` for the twenty-four end-to-end fix paths (pull request #22); local Melange main at commit `94fe14c7eb49e94a09730deddc193b22df4c9035` for the selected fec debug sweep paths of pull request #14, and at commit `4f381c570875e0b38e92b34118dbadc7ca098748` for the six pull request #17 round 3 paths; the desktop paths published by pull requests #13, #19, #21 and #24 (for example ops/desktop/client/updater.cjs from #19, ops/desktop/server/test_invites.py from #21 and ops/desktop/server/test_crash_dummy.py from #24); every other path as published by pull requests #15 and #16 (sources `15bc300ca`, `255614003`, `b9d000e1e`). Filter: `ops/release_lib/export.py` rules (roots `fec/`, `requirements.txt`, `ops/`; extension allowlist; 5 MB blob cap; excludes). Paths are kept as in the source (`ops/github` is not remapped to `.github`, so the workflow files under `ops/github` never run here. The two workflows published under `.github/workflows` (`desktop-windows.yml`, `desktop-installer-acceptance.yml`) are carried separately and run on a push to `main` that touches their path filters, or on a manual dispatch).

See `SOURCE_PROVENANCE.json` and `FILTER_REPORT.txt`.

## Building the Windows app

```
python ops/desktop/packaging/build_runtime.py --app melange --source <repo root>
cd ops/desktop/client
npm ci
set DESKTOP_APP_ID=melange
set DESKTOP_GITHUB_REPOSITORY=pjg93-222/Melange
npm run build
```
