# Melange application source (release)

Filtered, history-free application source for Melange, published from local Melange worktree branch `claude/sharp-feynman-e85406` at commit `5ef6dbe67b7c4f572a4a215bf384fc5e94554e41` for the four speech-channel kernel test paths (branch `publish/speech-test-no-live-writes-20261020`: the kernel test no longer writes the live stance model, a location-independent input fingerprint, and a regression test for it), from local Melange branch `fix/e2e-20261020` at commit `8a641d9ab60eefde1b29e1f28bb5519a928c002d` for the twenty-four end-to-end fix paths (branch `publish/e2e-pipeline-20261020`: the admissions budget and hold parking, the congress re-derivation, the House Code outage handling and GovInfo statute fallback, the 30-day carry-forward guard, their desk and field-action consumers and tests), from local Melange main at commit `94fe14c7eb49e94a09730deddc193b22df4c9035` for the selected fec debug sweep paths of pull request #14, and at commit `4f381c570875e0b38e92b34118dbadc7ca098748` for the six pull request #17 round 3 paths (refresh_congress_pipeline.py, refresh_sentinel_admissions.py, weekly_refresh.py and their tests); every other path as published by pull requests #15 and #16 (sources `15bc300ca`, `255614003`, `b9d000e1e`). Filter: `ops/release_lib/export.py` rules (roots `fec/`, `requirements.txt`, `ops/`; extension allowlist; 5 MB blob cap; excludes). Paths are kept as in the source (`ops/github` is not remapped to `.github`, so the workflow files under `ops/github` never run here. The two workflows published under `.github/workflows` (`desktop-windows.yml`, `desktop-installer-acceptance.yml`) are carried separately and run on a push to `main` that touches their path filters, or on a manual dispatch).

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
