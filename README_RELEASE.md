# Melange application source (release)

Filtered, history-free application source for Melange, published from local Melange branch `fix/pipeline-health-20261019` at commit `03dc98f3b49231ad034c245be2df5becac642f5f`. Filter: `ops/release_lib/export.py` rules (roots `fec/`, `requirements.txt`, `ops/`; extension allowlist; 5 MB blob cap; excludes). Paths are kept as in the source (`ops/github` is not remapped to `.github`, so the workflow files under `ops/github` never run here. The two workflows published under `.github/workflows` (`desktop-windows.yml`, `desktop-installer-acceptance.yml`) are carried separately and run on a push to `main` that touches their path filters, or on a manual dispatch).

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
