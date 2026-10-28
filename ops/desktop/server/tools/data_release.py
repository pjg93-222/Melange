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
import gzip
import hashlib
import json
import os
import re
import sys
import zipfile
import zlib
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
# Restricted LDA identity corpus (receipt: publication_enabled false, restricted-machine-local) and the
# staffer sections/page that inline it as ODATA/CDATA (GOVERNANCE_MATRIX M-07, D-332; X2). Fail closed: a copy
# of any of these under another name is refused by content hash, and any page carrying the ODATA/CDATA
# islands is refused by content (see select()).
RESTRICTED = [
    # Trailing * takes .gz/.zst/.bak copies; staffer_offices_section.json is public and stays shippable.
    "**/lda-source-native/**", "**/staffer_organisations_section*", "**/staffer_clients_section*",
    "**/staffer-network.html",
    # Derived LDA stores: pending Paul ruling on LDA restriction scope (X2 Q1).
    # Trailing * also takes the -wal/-shm/-journal sidecars, which hold database pages.
    "**/lda_source_catalog_v1.sqlite*", "**/lda_activity_v1.sqlite*", "**/lda_activity_v2.sqlite*",
    "**/lda-identity-candidates*",
]
HARD_DENY = [
    "**/accounts.sqlite3", "**/*.dpapi", "**/keys/**", "**/keys.json", "**/.env*", "**/credentials/**",
    "**/*.pfx", "**/*.pem", ".melange-data-release.json", "__state__/data-download/**",
] + RESTRICTED
# sha256 -> bytes of known restricted files (lda-source-native generation-20260830T231200Z and the
# staffer_{organisations,clients}_section.json builds seen on the owner machine, 2026-10-28). Any member with
# this content is refused whatever its name; restricted files present in the build are added at build time,
# so a new generation's copies are caught too. ponytail: a new section build that is renamed AND absent from
# the build under its own name escapes this list; regenerate the digests when the sections are rebuilt.
RESTRICTED_SHA256 = {
    "2ff6864f8a06e822277083230ab6a59abcc979ca12681e58490c89cb8a85b485": 110195153,
    "81841c810269bf967cb3edc10664dbbad5aa17261089eaa67e4f288c2fcda625": 58789826,
    "363027b2c3fff40331b304c9dd9b1d7bd81691bc9f9915aaf1b8f4acd0a869b7": 430061239,
    "80ac82346c435bb8f1231d9f3425d759ca9a8ae063db879ec104244f9fcd282e": 1928569,
    "0d35902244f02688d9ac961379efee0f96e3cfab1184409a4c93bb0584a1aed2": 2503228,
    "5dfd3bbb16dea6ce940a687b15c74f07e720073d02b559d8000bb33db49dce8c": 2386,
    "d3b2b1a9dea5d5ea9d44a0a1329d51a836c99539518c391b900c8220d847a774": 3892182,
    "06db0d498a9e090bf676e0ceb139a4bc97c3b61bc5ec2f52ab4259ebc8feb3ee": 3892182,
    "c0808b7b7991deda567c6d44bdd6cc479d2a12ec2a00ad7c25d342f38a000a72": 3940057,
    "f085bc383b7a77df591c46315b62be56551f2fe33af0c69f4db88efde5631b0b": 3939693,
}
# The staffer panel's organisations/clients islands (make_staffer_network_html.py, make_combined.py).
# UTF-8/ASCII, plus the UTF-16LE and UTF-16BE (BOM or not) encodings of the same marker, matched on raw bytes.
INLINE_RESTRICTED = re.compile(
    rb"const\s+[oc]data\s*="
    rb"|c\x00o\x00n\x00s\x00t\x00(?:\s\x00)+[oc]\x00d\x00a\x00t\x00a\x00(?:\s\x00)*=\x00"
    rb"|\x00c\x00o\x00n\x00s\x00t(?:\x00\s)+\x00[oc]\x00d\x00a\x00t\x00a(?:\x00\s)*\x00=", re.I)
PAGE_SUFFIXES = (".html", ".htm", ".js", ".mjs", ".cjs")
GZ_LIMIT = 2 * 1024**3  # decompressed bytes read from one .gz page; past this it is excluded (bomb cap)


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
    kept, excluded, restricted = [], [], []
    for rel in sorted(found):
        p, real, link = found[rel]
        if link or _match(rel, HARD_DENY) or _match(real, HARD_DENY) or (_match(rel, deny) and not _match(rel, allow)):
            excluded.append((rel, 0 if link else p.stat().st_size))
            if not link and (_match(rel, RESTRICTED) or _match(real, RESTRICTED)):
                restricted.append(p)
        else:
            kept.append((rel, p))
    # Content checks, so a rename cannot carry restricted data out: hash only where sizes collide.
    # A kept .gz is checked by its decompressed content too, so restricted digests are needed whenever one exists.
    sizes = {p.stat().st_size for _, p in kept}
    any_gz = any(p.name.lower().endswith(".gz") for _, p in kept)
    digests = dict(RESTRICTED_SHA256)
    for p in restricted:
        if p.stat().st_size and (any_gz or p.stat().st_size in sizes):
            digests[sha256_file(p)] = p.stat().st_size
    deny_sizes = set(digests.values()) - {0}
    clean = []
    for rel, p in kept:
        size = p.stat().st_size
        if ((size in deny_sizes and sha256_file(p) in digests) or _gz_restricted(p, digests, max(deny_sizes))
                or _inlines_restricted(p)):
            excluded.append((rel, size))
        else:
            clean.append((rel, p))
    return clean, sorted(excluded)


def _gz_restricted(p: Path, digests: dict, cap: int) -> bool:
    """A .gz whose decompressed content has a restricted digest. Streamed and stopped past ``cap`` (the largest
    restricted size, so nothing bigger can match: the bomb cap). Unreadable gzip fails closed."""
    if not p.name.lower().endswith(".gz"):
        return False
    h, n = hashlib.sha256(), 0
    try:
        with gzip.open(p, "rb") as fh:
            while chunk := fh.read(1 << 20):
                n += len(chunk)
                if n > min(cap, GZ_LIMIT):
                    return False
                h.update(chunk)
    except (OSError, EOFError, zlib.error):
        return True
    return h.hexdigest() in digests


def _inlines_restricted(p: Path) -> bool:
    """A page or script (or its .gz) carrying the staffer ODATA/CDATA islands. Unreadable gzip, or a .gz page
    that inflates past GZ_LIMIT, fails closed."""
    name = p.name.lower()
    if not name.removesuffix(".gz").endswith(PAGE_SUFFIXES):
        return False
    # Streamed, so a ~100 MB page or a .gz bomb never sits in memory. ponytail: a marker whose whitespace run
    # straddles a 1 MiB chunk boundary by more than 4 KiB is missed; the generators emit "const ODATA=".
    tail, n = b"", 0
    try:
        with (gzip.open(p, "rb") if name.endswith(".gz") else p.open("rb")) as fh:
            while chunk := fh.read(1 << 20):
                n += len(chunk)
                if name.endswith(".gz") and n > GZ_LIMIT:
                    return True
                buf = tail + chunk
                if INLINE_RESTRICTED.search(buf):
                    return True
                tail = buf[-4096:]
    except (OSError, EOFError, zlib.error):
        return True
    return False


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
