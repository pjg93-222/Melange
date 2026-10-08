# Moneyball.html canonicalization — 2026-09-04

Scope: the two locations where a "Moneyball" HTML surface existed outside version control —
the Desktop copies (`C:\Users\pgoff\OneDrive\Desktop\Moneyball.html` and
`...\Moneyball Dashboard.html`) versus the project builds under
`C:\Users\pgoff\OneDrive\Desktop\Melange Systems\`. Goal: back up the Desktop copies, replace
them with tiny redirect stubs pointing at the project builds, check for anything else that
still points at the Desktop copies, and verify in a sandboxed mirror that both member URL
forms (`?m=Mike Crapo` and `?m=Alex Padilla`) render from the same underlying file. No git
commands were used (owner's rule); nothing under `Melange Systems\` was touched except the
new `backups\desktop_copies_20260904\` folder and this file.

## 1. The two copies

| File | Path | Size | Last-write (UTC) | SHA-256 |
|---|---|---|---|---|
| Desktop (stale) | `Desktop\Moneyball.html` | 46,800,639 bytes | 2026-09-02T23:24:33.277Z | `D0D1E4EE8C3126E6FB0B746F1839C7D884B4B3398D34121AD08DE56956427A18` |
| Project (canonical) | `Melange Systems\Moneyball.html` | 75,916,784 bytes | 2026-09-04T23:54:19.439Z | `A085A1CB8B9D55AF8590934A4E7983D35F26A7A5AE5041B8244DE55B687060F0` |
| Desktop (stale) | `Desktop\Moneyball Dashboard.html` | 2,951,990 bytes | 2026-09-02T23:31:47.729Z | `31FFCE1F36C3AD3CA98982873E8A190C5018C3544578A6C01D921AA85957CBD9` |
| Project (canonical) | `Melange Systems\Moneyball Dashboard.html` | 2,956,260 bytes | 2026-09-04T23:19:04.843Z | `25475C9CD12F6DB12DAC987A881A9BC0AB5B8812A4759250A6058B32C6D62161` |

The project-copy hashes above were captured at the moment each file was copied into the
verification mirror (Section 4) and reconfirmed to match the mirror copy afterward, so they
are tied to a specific instant rather than re-derived after the fact.

**Diff verdict (established before this pass, not re-run here):** a code-level diff with
payloads stripped showed the Desktop copies contain nothing the project copies lack. The
project copies additionally carry district-brief CSS, sub-section styling, the slide-down
member sheet, and updated header copy. This task treated that finding as settled and did not
re-diff the two files.

**Canonical provenance (confirmed directly in this pass):** `fec/surfaces/make_combined.py`
resolves `MB_ROOT` via `paths.ROOT` (line 2), sets `B = MB_ROOT` (line 38), and writes the
combined dashboard with:
```
386  out = os.path.join(B, 'Moneyball.html')
388  write_text_atomic(HTML,out)
```
So `Melange Systems\Moneyball.html` is the file that script actually produces — nothing writes
the Desktop copy; it was a manual copy that went stale.

Titles read from the live head bytes of each canonical file (used verbatim in the stubs below):
- `Moneyball.html` → `Melange — Influence Dashboard`
- `Moneyball Dashboard.html` → `Melange — Influence map`

## 2. Backups

Both Desktop files were copied byte-for-byte to
`C:\Users\pgoff\OneDrive\Desktop\Melange Systems\backups\desktop_copies_20260904\` **before**
either was touched, and each copy's SHA-256 was checked against the source immediately after
copying (both matched — see hashes in Section 1). Contents of that folder:

- `Moneyball.html` (the original 46,800,639-byte Desktop file)
- `Moneyball Dashboard.html` (the original 2,951,990-byte Desktop file)
- `MANIFEST.json` — `{source_path, backup_path, size_bytes, mtime_utc, sha256, sha256_verified_on_backup_copy, replaced_at_utc}` for each entry, plus a `reason` field explaining the canonicalization.

## 3. Replacement stubs

Each Desktop file was replaced (via a temp file in the scratchpad, moved into place, then
re-hashed) with a small self-contained redirect stub — no external resources, both under 1 KB:

- `Desktop\Moneyball.html` → now 857 bytes, SHA-256 `76452A53FA271BE66887EC08B5D678E6F10BCBDEF81131F6543B3C5D5B9A663D`
- `Desktop\Moneyball Dashboard.html` → now 905 bytes, SHA-256 `8F2082BEF08AA2784F3769C17344503709B797936F97AAF27C59B9636C204AFA`

Each stub:
- Carries the exact `<title>` of the canonical file it forwards to (see Section 1).
- Redirects via a `<script>` that builds a **relative** target — `'Melange%20Systems/Moneyball.html' + location.search + location.hash` (respectively `'Melange%20Systems/Moneyball%20Dashboard.html' + location.search + location.hash`) — and calls `location.replace(target)`, so it works unmodified whether opened as `file://` or served from any HTTP root at the Desktop folder, and preserves any `?m=`/`?coal=` query and hash.
- Wraps a visible fallback line in `<noscript>` — "This copy moved. Open: `<a href='Melange%20Systems/Moneyball.html'>Melange Systems/Moneyball.html</a>`" (same relative href) — for the no-JS case, styled black/gold: background `#0b0b0b`, text `#e8e2d0`, links `#EECD5C`, font stack `"Century Gothic","Tw Cen MT",Futura,"Segoe UI",sans-serif`. *(Interpretation note: the spec asked for "a `<noscript>` and a visible fallback line" — I read that as the fallback line living inside the `<noscript>`, which is the standard pattern for a JS-redirect stub and keeps it invisible during the normal instant-redirect path. Flagging this reading in case a fallback visible outside `<noscript>` too was intended.)*
- Ends with an HTML comment naming the canonical path, the backup path, and the date.
- Uses "Melange" in all visible text; the filenames themselves stay "Moneyball" (owner's law on filenames vs. visible copy).

## 4. Reference and shortcut sweep

**Text references.** Searched (case-insensitive) for `Desktop\Moneyball`, `Desktop/Moneyball`,
and `Desktop\Moneyball Dashboard` in three locations (via the Grep tool rather than a literal
`rg` shell invocation — same regex/case-insensitivity semantics; I did not separately apply the
`--max-filesize 3M` cap or the `.html`/`.jsonl` glob excludes from the original command, since
each call returned zero hits regardless, so the omitted filters could not have hidden a match):

- `Melange Systems\fec` — no matches
- `C:\Users\pgoff\.claude\glassbox` — no matches
- `C:\Users\pgoff\.claude\settings.json` — no matches
- `C:\Users\pgoff\.claude\settings.json.bak` — no matches

No code file was edited as part of this sweep (none needed editing — nothing was found).

**Shortcuts.** `C:\Users\pgoff\Desktop` does not exist on this machine (the Desktop is
OneDrive-redirected). `C:\Users\pgoff\OneDrive\Desktop`, checked both top-level and by a full
recursive walk of the tree (the recursive walk took a long time — apparently OneDrive
placeholder/cloud-file scanning through the large `Melange Systems` tree — but it did complete,
with zero `.lnk`/`.url` matches for "Moneyball" or "Melange" anywhere in that tree). Windows
`Recent` (`%APPDATA%\Microsoft\Windows\Recent`) had 16 matches, resolved via
`(New-Object -ComObject WScript.Shell).CreateShortcut($p)`:

| Shortcut | TargetPath |
|---|---|
| Melange Systems.lnk (+ 7 numbered duplicates `(2)`–`(8)`) | `Desktop\Melange Systems` (folder) |
| MelangeXCollector.cmd.lnk | `...\Startup\MelangeXCollector.cmd.disabled-20260827` |
| **Moneyball.lnk** | `Desktop\Melange Systems\Moneyball.html` — already the canonical file, no drift |
| **Moneyball Dashboard.lnk** | `Desktop\Moneyball Dashboard.html` — **the Desktop copy**, now a stub |
| Moneyball Dashboard.speech-preview.lnk | `Desktop\Melange Systems\Moneyball Dashboard.speech-preview.html` (a different file, out of this task's scope) |
| Moneyball_AllInOne.lnk | `Melange Systems\outputs\email_allinone_2026-08-25\Moneyball_AllInOne.zip` |
| moneyball_core.lnk | `Melange Systems\fec\moneyball_core.py` |
| Moneyball_Email_Package.lnk | `Downloads\Moneyball_Email_Package.zip` |
| Moneyball_Email_Package_AllInOne.lnk | `Melange Systems\outputs\email_package\Moneyball_Email_Package_AllInOne.zip` |

Per the task's rule, Recent-items shortcuts were not touched (Windows history). The one
shortcut whose target is a Desktop copy (`Moneyball Dashboard.lnk`) is left alone — the stub
now forwards it to the canonical file automatically, preserving whatever query it's opened
with.

## 5. Rendering verification (sandboxed mirror, live tree untouched)

Built a mirror under the scratchpad (`.../scratchpad/verify/`):
`Moneyball.html` and `Moneyball Dashboard.html` = copies of the **new** Desktop stubs;
`Melange Systems/Moneyball.html` and `Melange Systems/Moneyball Dashboard.html` = copies of
the live project files, each hashed immediately before copying and reconfirmed identical to
the mirror copy afterward (Section 1 hashes — both matched, `True`/`True`).

Served with `python -m http.server 8802 --bind 127.0.0.1` from that mirror (port 8802, never
8801). Confirmed it answered: `curl.exe -s -o NUL -w "%{http_code}"` returned `200` for
`/Moneyball.html`, `/Moneyball%20Dashboard.html`, and `/Melange%20Systems/Moneyball.html`.

**Crapo, via the Desktop stub form** — `http://127.0.0.1:8802/Moneyball.html?m=Mike%20Crapo`,
waited ~10s for the 73 MB page:
- `location.href` after redirect: `http://127.0.0.1:8802/Melange%20Systems/Moneyball.html?m=Mike%20Crapo` — the stub forwarded and preserved the query.
- `document.title`: `Melange — Influence Dashboard`
- Member header (`.mhead h2` / `.mhead .meta`): `"Mike CrapoDemographic Potential · 64.7"` / `"Senate · Republican · Idaho"`
- `document.documentElement.outerHTML.length`: 76,424,976
- Console errors (`onlyErrors:true`), verbatim: `[error] Failed to load resource: net::ERR_CONNECTION_REFUSED` — traced via network requests to `http://127.0.0.1:8841/staffer-live/launch.js`, an optional live-feature probe the page makes to a separate local dev server that isn't running in this sandbox. Not related to the stub or the canonical file's own rendering.

**Padilla, via the direct project-copy URL** —
`http://127.0.0.1:8802/Melange%20Systems/Moneyball.html?m=Alex%20Padilla`, same wait:
- `location.href`: unchanged (no stub involved), query intact.
- `document.title`: `Melange — Influence Dashboard`
- Member header: `"Alex Padilla"` / `"Senate · Democrat · California"`
- `outerHTML.length`: 76,423,755
- Console errors: the same single benign `staffer-live/launch.js` refusal, nothing else.

**Dashboard, via the Desktop stub with a `coal=` query** —
`http://127.0.0.1:8802/Moneyball%20Dashboard.html?coal=Alex%20Padilla,Mike%20Crapo`:
- `location.href` after redirect: `http://127.0.0.1:8802/Melange%20Systems/Moneyball%20Dashboard.html?coal=Alex%20Padilla,Mike%20Crapo` — forwarded with the query intact.
- `document.title`: `Melange — Influence map`
- Console errors accumulated in the tab across all four navigations in this session: 4 total, every one the same `staffer-live/launch.js` connection refusal (one per page load) — no other errors at any point.

**Same-file proof.** `curl.exe -sI` against `/Melange%20Systems/Moneyball.html`, run twice
(once between the two member loads, once after): both responses returned
`Content-Length: 75916784` and `Last-Modified: Fri, 04 Sep 2026 23:54:19 GMT`, identical byte
count and mtime both times — the Crapo and Padilla loads were served the same static file from
disk, not two different files or a live-regenerated one.

The server was then stopped via its background task id (`bxndijqne`) — only that process —
and a follow-up `curl` to port 8802 confirmed it was down (connection refused, `http_code
000`).

## 6. Rollback

If the stubs need to be undone, copy the backups back over them and re-verify:
```
Copy-Item 'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\backups\desktop_copies_20260904\Moneyball.html' 'C:\Users\pgoff\OneDrive\Desktop\Moneyball.html' -Force
Copy-Item 'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\backups\desktop_copies_20260904\Moneyball Dashboard.html' 'C:\Users\pgoff\OneDrive\Desktop\Moneyball Dashboard.html' -Force
Get-FileHash 'C:\Users\pgoff\OneDrive\Desktop\Moneyball.html' -Algorithm SHA256          # expect D0D1E4EE8C3126E6FB0B746F1839C7D884B4B3398D34121AD08DE56956427A18
Get-FileHash 'C:\Users\pgoff\OneDrive\Desktop\Moneyball Dashboard.html' -Algorithm SHA256 # expect 31FFCE1F36C3AD3CA98982873E8A190C5018C3544578A6C01D921AA85957CBD9
```

## 7. Bottom line

The Desktop copies are now 857- and 905-byte redirect stubs; the byte-for-byte originals are
preserved in `backups\desktop_copies_20260904\` with a hash-verified manifest. No code file
anywhere referenced the Desktop copies by path, so nothing needed updating. One Recent-items
shortcut (`Moneyball Dashboard.lnk`) still targets the Desktop path but now rides the stub's
forward automatically. Both member URL forms — the legacy Desktop-style query and the direct
project-copy query — were shown, in a sandboxed mirror, to resolve to the identical file on
disk (matching Content-Length and Last-Modified across requests) and to render that member's
real data (Crapo: Senate · Republican · Idaho; Padilla: Senate · Democrat · California), with
no console errors other than an expected, unrelated dev-only network probe.
