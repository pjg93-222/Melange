# Melange application source (release)

Filtered, history-free application source for Melange, published from local Melange branch `main` at commit `d1869477a64d1f02af8a599fa68553900f0bdb4c`. Filter: `ops/release_lib/export.py` rules (roots `fec/`, `requirements.txt`, `ops/`; extension allowlist; 5 MB blob cap; excludes). Paths are kept as in the source (`ops/github` is not remapped to `.github`, so no CI workflows run here).

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
