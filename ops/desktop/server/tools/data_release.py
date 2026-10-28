"""Package an app data folder into verifiable release artifacts (local only).

Consumer contract (implemented by ops/desktop/packaging/data_release_fetch.py):
the desktop app finds the newest non-draft GitHub release on its own repo whose
tag starts with ``data-<app>-``, fetches ``manifest.json`` first, downloads each
entry of ``assets[]``, verifies ``bytes`` and ``sha256``, extracts members into
the app data root (refusing absolute or ``..`` paths) and writes the marker
``.melange-data-release.json`` ``{"tag","manifestSha256","extractedAt"}`` there.

Manifest schema ``melange-desktop-data/v1``::

    {"schema": "melange-desktop-data/v1", "app": "melange", "tag": "data-melange-2026-10-21",
     "created": "<iso utc>",
     "assets": [{"name": "<zip>", "bytes": N, "sha256": "<hex>"}],
     "files": [{"path": "<rel>", "bytes": N, "sha256": "<hex>", "asset": "<zip>"}],
     "excluded": ["<rel>", ...]}

``--map <relpath>=<absolute path>`` (repeatable) mounts a source folder or single file at ``relpath``
inside a virtual data root alongside ``--data-root``, so a release can be assembled from several folders
without copying them. Deny/allow patterns and member names use the virtual relative path. Members under
``__state__/`` are extracted by the consumer into the app STATE root with that prefix stripped.

This tool never uploads. It prints the ``gh release create`` command for the
owner to run after reviewing EXCLUDED.txt.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path, PurePosixPath

SCHEMA = "melange-desktop-data/v1"
REPOS = {"melange": "pjg93-222/Melange", "mentat": "pjg93-222/Mentat"}
DEFAULT_PART_BYTES = int(1.9 * 1024**3)
DENY = [
    "**/accounts.sqlite3", "**/*.sqlite3-wal", "**/*.sqlite3-shm", "**/*.sqlite-wal",
    "**/*.sqlite-shm", "**/*-journal", "**/*.dpapi", "**/keys/**", "**/keys.json",
    "**/.env*", "**/credentials/**", "**/*secret*", "**/*token*", "**/*.pfx", "**/*.pem",
    "**/session*", "**/cookies*", "**/politico_profile_crawl_*_raw/**", "**/*politico*raw*",
    "**/.cache/**", "**/__pycache__/**", "**/.git/**", "**/node_modules/**",
    ".melange-data-release.json",
]
# Credential stores, the consumer's marker and its download cache: excluded even when --allow names them, and
# also matched against the real absolute path (a --map can mount .../credentials or rename keys.json to anything).
HARD_DENY = [
    "**/accounts.sqlite3", "**/*.dpapi", "**/keys/**", "**/keys.json", "**/.env*", "**/credentials/**",
    "**/*.pfx", "**/*.pem", ".melange-data-release.json", "__state__/data-download/**",
    # Restricted LDA identity corpus (receipt: publication_enabled false, restricted-machine-local) and the
    # staffer sections/page that inline it as ODATA/CDATA (GOVERNANCE_MATRIX M-07, D-332; X2).
    "**/lda-source-native/**", "**/staffer_organisations_section.json", "**/staffer_clients_section.json",
    "**/staffer-network.html",
]


def _match(rel: str, patterns: list[str]) -> bool:
    # fnmatch treats ** like *, which is fine for these path globs; also test every suffix
    # so "**/keys/**" catches "keys/x.json" at the root.
    candidates = {rel, "/" + rel}
    parts = rel.split("/")
    for i in range(len(parts)):
        candidates.add("x/" + "/".join(parts[i:]))
    return any(fnmatch.fnmatch(c, p) for c in candidates for p in patterns)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def map_arg(text: str) -> tuple[str, Path]:
    """``relpath=<absolute path>`` -> (posix relpath, Path); refuses absolute, drive, '.', '..' or empty segments."""
    rel, sep, src = text.partition("=")
    rel = rel.strip().replace("\\", "/")
    parts = rel.split("/")
    if not sep or not rel or rel.startswith("/") or ":" in rel or any(x in ("", ".", "..") for x in parts):
        raise argparse.ArgumentTypeError(f"--map needs <relpath>=<absolute path> with a safe relpath: {text!r}")
    path = Path(src.strip())
    if not path.is_absolute() or not path.exists():
        raise argparse.ArgumentTypeError(f"--map source must be an existing absolute path: {src!r}")
    return rel, path


def _walk(prefix: str, src: Path):
    """(virtual path, file, its real absolute path, is_link). Symlinks and junctions inside a source, files
    or folders, are reported as links and never followed (Path.rglob descends into junctions on Windows)."""
    if src.is_file():
        yield prefix, src, src.as_posix(), False
        return
    stack = [src]
    while stack:
        folder = stack.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                p = Path(entry.path)
                rel = PurePosixPath(p.relative_to(src)).as_posix()
                virtual, real = (f"{prefix}/{rel}" if prefix else rel), p.as_posix()
                if entry.is_symlink() or p.is_junction():
                    yield virtual, p, real, True
                elif entry.is_dir():
                    stack.append(p)
                elif entry.is_file():
                    yield virtual, p, real, False


def select(sources, allow: list[str], deny: list[str]):
    """sources: [(virtual prefix, path)], prefix "" for --data-root. A virtual path claimed twice is an error."""
    found = {}
    for prefix, src in sources:
        for rel, p, real, link in _walk(prefix, src):
            if rel in found:
                raise ValueError(f"virtual path {rel} comes from both {found[rel][0]} and {p}")
            found[rel] = p, real, link
    kept, excluded = [], []
    for rel in sorted(found):
        p, real, link = found[rel]
        if link or _match(rel, HARD_DENY) or _match(real, HARD_DENY) or (_match(rel, deny) and not _match(rel, allow)):
            excluded.append((rel, 0 if link else p.stat().st_size))
        else:
            kept.append((rel, p))
    return kept, excluded


def build(app: str, data_root: Path | None, out: Path, tag: str, allow: list[str], deny: list[str],
          part_bytes: int, maps=()) -> dict:
    sources = ([("", data_root)] if data_root else []) + list(maps)
    if not sources:
        raise ValueError("need --data-root or at least one --map")
    if any(out.resolve() == src.resolve() or out.resolve().is_relative_to(src.resolve()) for _, src in sources):
        raise ValueError("--out must be outside every source folder (a rebuild would package the previous zips)")
    kept, excluded = select(sources, allow, deny)
    out.mkdir(parents=True, exist_ok=True)
    date = tag.rsplit("-", 3)[-3:]
    date = "-".join(date) if len(date) == 3 else dt.date.today().isoformat()
    files, assets = [], []
    part, zf, zpath, used = 0, None, None, 0

    def close():
        nonlocal zf
        if zf is not None:
            zf.close()
            assets.append({"name": zpath.name, "bytes": zpath.stat().st_size, "sha256": sha256_file(zpath)})
            zf = None

    for rel, p in kept:
        size = p.stat().st_size
        if zf is None or (used and used + size > part_bytes):
            close()
            part += 1
            zpath = out / f"{app}-data-{date}-part{part}.zip"
            zf = zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, allowZip64=True, compresslevel=1)
            used = 0
        info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        digest, written = hashlib.sha256(), 0  # one read: a file that changes during the build cannot disagree with its zip member
        with p.open("rb") as fh, zf.open(info, "w", force_zip64=True) as dst:
            while chunk := fh.read(1 << 20):
                digest.update(chunk)
                dst.write(chunk)
                written += len(chunk)
        used += written
        files.append({"path": rel, "bytes": written, "sha256": digest.hexdigest(), "asset": zpath.name})
    close()

    manifest = {
        "schema": SCHEMA, "app": app, "tag": tag,
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "assets": assets, "files": files, "excluded": [rel for rel, _ in excluded],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    sums = [f"{a['sha256']}  {a['name']}" for a in assets]
    sums.append(f"{sha256_file(out / 'manifest.json')}  manifest.json")
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    (out / "EXCLUDED.txt").write_text(
        "\n".join(f"{size:>14}  {rel}" for rel, size in excluded) + "\n", encoding="utf-8")
    (out / "README.md").write_text(
        f"# {app.capitalize()} desktop data ({date})\n\n"
        "Data folder for the desktop app, packaged for automatic download. Sources are public\n"
        "records (FEC filings, congressional and lobbying disclosures). Credentials, account\n"
        "databases, caches and licensed third-party content are excluded; see EXCLUDED.txt in the\n"
        "build folder. `manifest.json` lists every file with its SHA-256; `SHA256SUMS` covers the\n"
        "zips and the manifest. The desktop app downloads, verifies and extracts these on first\n"
        "launch. Nothing here is an installer.\n", encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--app", choices=sorted(REPOS), required=True)
    b.add_argument("--data-root", type=Path)
    b.add_argument("--map", type=map_arg, action="append", default=[], metavar="RELPATH=ABSPATH")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--tag")
    b.add_argument("--allow", action="append", default=[])
    b.add_argument("--deny", action="append", default=[])
    b.add_argument("--part-bytes", type=int, default=DEFAULT_PART_BYTES)
    a = ap.parse_args(argv)
    tag = a.tag or f"data-{a.app}-{dt.date.today().isoformat()}"
    if not tag.startswith(f"data-{a.app}-"):
        ap.error(f"tag must start with data-{a.app}-")
    if not a.data_root and not a.map:
        ap.error("--data-root is required unless at least one --map is given")
    try:
        m = build(a.app, a.data_root.resolve() if a.data_root else None, a.out.resolve(), tag, a.allow,
                  DENY + a.deny, a.part_bytes, [(rel, src.resolve()) for rel, src in a.map])
    except ValueError as error:
        ap.error(str(error))
    total = sum(x["bytes"] for x in m["assets"])
    print(f"{len(m['files'])} files in {len(m['assets'])} asset(s), {total:,} bytes; "
          f"{len(m['excluded'])} excluded (see EXCLUDED.txt)")
    for rel in m["excluded"]:
        print("  excluded:", rel)
    big = [x for x in m["assets"] if x["bytes"] >= 2 * 1024**3]
    if big:
        print("ERROR: asset at or over 2 GiB:", ", ".join(x["name"] for x in big))
        return 2
    out = a.out.resolve()
    print("\nReview EXCLUDED.txt, then upload with:\n"
          f'gh release create {tag} -R {REPOS[a.app]} --prerelease --draft --title "{a.app} data {tag[-10:]}" '
          f'--notes-file "{out / "README.md"}" "{out}\\*.zip" "{out / "manifest.json"}" "{out / "SHA256SUMS"}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
