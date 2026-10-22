# Desktop data releases (Melange and Mentat)

The installers ship code only. On first launch the backend fetches the app's data from a GitHub
release in the app's own repo. The reader is `packaging/data_release_fetch.py`, started from
`desktop_backend.start_data_release`. The builder is `server/tools/data_release.py`.

## How a release is consumed

- **Repo and tag:** `pjg93-222/Melange` or `pjg93-222/Mentat`. The reader uses the newest **non-draft** release whose tag starts with `data-<app>-` (e.g. `data-mentat-2026-10-21`). Drafts are invisible to it.
- **Manifest (`manifest.json` asset, schema `melange-desktop-data/v1`):**
  `{"schema","app","tag","created","assets":[{"name","bytes","sha256"}],"files":[{"path","bytes","sha256","asset"}],"excluded":[...]}`.
  The reader checks that `schema`, `app` and `tag` match the release, and that each asset's size and SHA-256 match before
  anything is extracted. The zips must hold exactly the files in `files` (no extra, missing or repeated member, no path listed
  twice even by case), and each extracted file must match its `bytes` and SHA-256 before it is moved into place.
- **Download:** HTTPS only, redirects included. Zip parts download, with resume (a server that ignores `Range` restarts the
  part), to `<state>/data-download/<tag>/`. That cache is deleted after a successful extraction; a leftover cache of an
  older tag is deleted before a newer tag downloads. One unauthenticated GitHub API call (`releases?per_page=20`) per launch
  until the marker exists; asset downloads do not count against the 60/hour API limit. A data release older than the 20 newest
  releases of the repo is not seen.
- **One at a time:** an OS lock on `<state>/data-download/.lock` (released when the process exits). A second launch while a
  download runs returns `busy` and writes nothing.
- **Disk space:** before downloading, the reader requires free space for the remaining zips plus every file still to extract
  plus 512 MB (Melange 2026-10-21: about 3.7 GB of zips and 8.7 GB extracted, so about 12.4 GB at peak, counted per volume).
- **Routing:** members are extracted into the data root. Members under `__state__/` go to the state root with the prefix stripped (Melange reads `<state>/Melange` as `MELANGE_LOCAL_ROOT`). The reader refuses absolute paths, drive letters, `..` segments, members that resolve outside their root (including through a junction already in the folder), `__state__/data-download/`, Windows device names (`CON`, `NUL.txt`), names ending in a dot or space, and wildcard or control characters.
- **No overwrites:** existing files are never replaced, except Melange's bootstrap welcome/progress `Moneyball.html`. That page is recognised by the `melange-desktop-empty-workspace-v1` comment in a regular file under 64 KB, so a real dashboard is never mistaken for it. Files that already exist with different content are reported as `kept`.
- **Interrupted extraction:** each file is written to `<name>.data-release-part` and renamed into place after its checksum; the
  part file is removed when a write fails. The main file (Melange `Moneyball.html`, Mentat `reports/`) is written last and the marker
  after everything, so an interrupted run is retried at the next launch and already-correct files are skipped.
  `<state>/data-download/extracting.json` exists from the start of extraction until the marker is written, so Mentat
  resumes even though its `reports/` folder is no longer empty.
- **Marker:** `<data>/.melange-data-release.json` `{"tag","manifestSha256","extractedAt"}`. Once it exists, later launches do nothing.
- **Newer releases:** not applied to an install that has the marker; the mechanism is first-run only. Deleting the marker makes the
  next launch fetch the newest release, but every existing file is still kept, including files from the older release whose content
  changed (they appear in `kept`). Replacing files that still match the older manifest would need the old manifest stored with the
  marker; that is not implemented.
- **Skip rules:** no fetch for Terrier, when `DESKTOP_DATA_RELEASE=off`, when the marker exists, when Melange's
  `Moneyball.html` exists and is not the bootstrap page, or when Mentat's reports folder is redirected away from
  `<data>/reports` or is not empty (unless `extracting.json` shows an interrupted extraction). No matching release ends with status `none`.
- **Env knobs** (set on the client, which passes `DESKTOP_*` through): `DESKTOP_DATA_RELEASE=off` disables the fetch;
  `DESKTOP_DATA_RELEASE_REPO=owner/name` overrides the repo; `DESKTOP_DATA_RELEASE_API=<base>` overrides the API base
  (plain `http://` is accepted only with this set, for tests).
- **Progress:** `<state>/data-download/status.json`. The server starts immediately; data appears when extraction finishes.
  Error text there and on Melange's progress page shows `<data>`, `<state>` and `~` in place of absolute folders.
- **Mentat models:** `app-data/` lands at `<data>/app-data`, the default `MENTAT_APP_DATA_ROOT` (a redirected `appDataRoot` does not
  stop the fetch, and the release's models then sit unused in `<data>/app-data`). Geo layers are not data: they ship in the installer (`runtime-manifest.json` `sourceGlobs`).

## Building one (local only, never uploads)

Run from the repo root with Python 3.12. `--map rel=ABS` (repeatable) mounts a folder or file at `rel` inside a virtual
data root, so nothing is copied; deny/allow patterns use the virtual path. Symlinks and junctions inside a source are listed in
`EXCLUDED.txt` and not followed. `--out` must be outside every source. The two builds from 2026-10-21:

```powershell
# Mentat; $M = the Mentat checkout's mentat folder, $OUT = a new output folder outside it
python -I ops\desktop\server\tools\data_release.py build --app mentat --tag data-mentat-2026-10-21 `
  --out $OUT `
  --map inputs=$M\inputs --map app-data=$M\app\data `
  --map forecast=$M\forecast
```

```bash
# Melange, clean build (-> ...\data-release-melange-2026-10-21-clean); S = live checkout, L = local staffer_network
python -I -X utf8 ops/desktop/server/tools/data_release.py build --app melange --tag data-melange-2026-10-21 --out "$OUT" \
 --map "Moneyball.html=$S\\Moneyball.html" --map "audits/staffer_live_runtime=$S\\audits\\staffer_live_runtime" \
 --map "data/engine=$S\\data\\engine" --map "fec/surfaces=$S\\fec\\surfaces" \
 --map "__state__/Melange/staffer_network/live_catalog=$L\\live_catalog" \
 --map "__state__/Melange/staffer_network/normalized=$L\\normalized" \
 --map "__state__/Melange/staffer_network/raw/littlesis=$L\\raw\\littlesis" \
 --deny 'audits/staffer_live_runtime/backups/**' --deny '**/*.bak' --deny '**/*.log' --deny '**/*.err' --deny '**/*.tmp' \
 --deny '**/*.pre-heal-*' --deny '**/STABILIZATION_*' --deny '**/restart_watch_*' --deny '**/stabilization_chain_plan.txt' \
 --deny '**/*.ps1' --deny '**/identity_reference_cache/**' \
 --allow 'audits/staffer_live_runtime/identity_reference_v1.sqlite-wal' \
 --allow 'audits/staffer_live_runtime/identity_reference_v1.sqlite-shm'
```

Output: `<app>-data-<date>-partN.zip` (each under 1.9 GiB, `--part-bytes`), `manifest.json`, `SHA256SUMS`, `EXCLUDED.txt`, `README.md`.
`--allow <glob>` overrides `--deny` and the soft defaults, never the hard denylist below; keep it to exact paths (above: the identity index's WAL/SHM).

## Publishing

1. Read `EXCLUDED.txt` and spot-check the manifest for anything below that slipped through.
2. Run the `gh release create` line the build prints: `gh release create <tag> -R pjg93-222/<App> --prerelease --draft
   --title "<app> data <date>" --notes-file <out>\README.md <out>\*.zip <out>\manifest.json <out>\SHA256SUMS`.
3. Un-draft it (`gh release edit <tag> -R <repo> --draft=false`). Until then no app sees it. To retract a release, re-draft or delete it. Installs that already extracted it keep their files.

## Excluded by policy

Hard denylist (`HARD_DENY`; `--allow` cannot override it, and it is also matched against each file's real absolute path, so a
`--map` cannot rename or mount these in): account databases (`accounts.sqlite3`), DPAPI blobs, `keys/`, `keys.json`, `.env*`,
`credentials/`, `.pfx`/`.pem` files, the marker and `__state__/data-download/`.
Soft defaults (`DENY`; an exact-path `--allow` after review can re-include one): anything named `*secret*`, `*token*`, `session*` or
`cookies*` (congressional `session_*` data can match), licensed third-party content (raw Politico Pro crawls, `*politico*raw*`; never
allow these), caches, `__pycache__`, `.git`, `node_modules`, and SQLite journals.
Beyond the defaults, the Melange build also excluded backups, logs, scratch files and operator scripts. Donor records, reports and
user state stay out of Mentat releases, as `dataPolicy` in `runtime-manifest.json` requires. Only publish public-record data.

## How this differs from Terrier's GitHub district data

Terrier does not use this mechanism (`launch` ignores it). Its district data lives in `pjg93-222/Geo` and is addressed by a
**signed pointer/catalogue** that the owner prepares with the protected release key (`packaging/prepare_github_district_catalogue.py`).
The **Electron client** (`client/github-districts.cjs`) downloads and verifies the data into a **separate cache** and passes it
to the backend with `--github-district-data`. `terrier_district.validate_github_runtime` then validates the cache read-only, and
updates apply when the district is reopened. Melange/Mentat use an unsigned release manifest instead. The integrity
check there is size plus SHA-256 over HTTPS from the app's own repo. The **backend** extracts once, in place, into the data root.
