"""Build a plain directory ZIP from a freshly signed win-unpacked tree.

No installer runs, bytes are not modified, and this utility never accesses a
signing key. Release signing/publisher proof and native acceptance happen after
packaging. Only program files belong in the source; user state fails closed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import unicodedata
import zipfile

INVENTORY = "directory-package.json"
ENTRYPOINTS = {"melange": "Melange.exe", "mentat": "Mentat.exe", "terrier": "Terrier.exe"}
MAX_FILES, MAX_TOTAL, MAX_FILE, MAX_INVENTORY = 100_000, 8 * 1024**3, 2 * 1024**3, 16 * 1024**2
MAX_ARCHIVE, MAX_RATIO = 4 * 1024**3, 1000
VERSION = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z")
RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|CLOCK\$|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)", re.I)
PRIVATE_PEM = re.compile(rb"(?m)^-----BEGIN (?P<label>(?:[A-Z0-9]+ )*PRIVATE KEY)-----[ \t]*\r?\n(?P<body>[\s\S]{32,65536}?)^-----END (?P=label)-----[ \t]*(?:\r?\n|$)")


class Refused(ValueError):
    pass


def require(value, message):
    if not value:
        raise Refused(message)


def safe_path(name):
    require(isinstance(name, str) and 0 < len(name.encode("utf-16-le")) // 2 <= 240 and name == unicodedata.normalize("NFC", name), "Invalid package path")
    require(not re.search(r'[\\\x00-\x1f\x7f:<>"|?*]', name) and not name.startswith("/") and not name.endswith("/"), "Unsafe Windows package path")
    for component in name.split("/"):
        require(component not in ("", ".", "..") and not component.endswith((".", " ")) and not RESERVED.match(component), "Unsafe Windows path component")
    return name


def physical(path, directory=False):
    info = path.lstat()
    require(not stat.S_ISLNK(info.st_mode) and (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)), "Linked or nonregular source")
    require(os.path.normcase(str(path.absolute())) == os.path.normcase(str(path.resolve(strict=True))), "Redirected source path")
    if not directory:
        require(info.st_nlink == 1 and info.st_size <= MAX_FILE, "Linked or oversized source file")
    return info


def parent_chain(path):
    for item in (path, *path.parents):
        physical(item, directory=True)


def excluded(name):
    lower = name.lower()
    return (lower in ("resources/elevate.exe", "nsis7z.dll", "app-64.7z", "app-32.7z", "app-arm64.7z")
            or lower.startswith("$pluginsdir/")
            or ("/" not in lower and lower.startswith("uninstall ") and lower.endswith(".exe")))


def refuse_private(name):
    parts = name.lower().split("/")
    base = parts[-1]
    require(not any(p in (".git", ".ssh", ".aws", ".azure", ".codex", ".claude") for p in parts), "Private development directory in package")
    require(parts[0] not in ("state", "userdata", "user data", "profile", "profiles", "logs", "baseline", "updater"), "User state in package")
    own_sources = len(parts) > 4 and parts[:2] == ["resources", "runtime"] and parts[3] == "sources"
    require(not own_sources or "state" not in parts[4:], "Runtime state in package")
    require(base not in (".env", ".secret", "credentials.json", "settings.json", "enrollment.enc", "github-enrollment.enc", "update-state.json", "github-update-state.json"), "Private configuration in package")
    require(not base.startswith(".env."), "Environment configuration in package")
    require(not base.endswith((".pfx", ".p12", ".key")), "Private key in package")
    # Match after-pack.cjs: application sources must not contain runtime state.
    # Third-party runtime databases (PROJ, R, RSQLite) are required program data.
    is_database = base.endswith((".sqlite", ".sqlite3", ".db", "-wal", "-shm", "-journal"))
    require(not is_database or not (own_sources or len(parts) == 1), "Application state database in package")


def same_file(first, second):
    # Windows ChangeTime can advance during antivirus/indexer metadata work on a
    # newly created file. Identity, size, modification time and the independently
    # rechecked content digest bind the bytes without rejecting those reads.
    return (first.st_dev, first.st_ino, first.st_size, first.st_mtime_ns) == (second.st_dev, second.st_ino, second.st_size, second.st_mtime_ns)


def private_pem(data):
    for match in PRIVATE_PEM.finditer(data):
        encoded = b"".join(line.strip() for line in match["body"].splitlines() if b":" not in line)
        if len(encoded) >= 32 and re.fullmatch(rb"[A-Za-z0-9+/]+={0,2}", encoded):
            return True
    return False


def stream_file(file, output=None):
    parent_chain(file.parent)
    before = physical(file)
    digest, count, tail = hashlib.sha256(), 0, b""
    fd = os.open(file, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as source:
        require(same_file(before, os.fstat(source.fileno())), "Source changed before opening")
        while chunk := source.read(1024 * 1024):
            count += len(chunk)
            require(count <= MAX_FILE, "Source grew beyond package limit")
            # Public PEM certificates are allowed; private PEM material is not.
            # Cryptography's public SSH implementation contains marker literals.
            # Match a complete line-anchored PEM block with an encoded body.
            require(not private_pem(tail + chunk), "Private key material in package")
            tail = chunk[-70000:]
            digest.update(chunk)
            if output is not None:
                output.write(chunk)
        require(same_file(before, os.fstat(source.fileno())) and same_file(before, physical(file)), "Source changed during packaging")
    return count, digest.hexdigest()


def inventory_for(source, app_id, version):
    require(app_id in ENTRYPOINTS and isinstance(version, str) and VERSION.fullmatch(version), "Invalid package identity")
    source = Path(source).absolute()
    parent_chain(source)
    records, omitted, aliases, directories, total = [], [], set(), {}, 0
    for current, dirs, filenames in os.walk(source, followlinks=False):
        dirs.sort()
        filenames.sort()
        for directory in dirs:
            relative = (Path(current) / directory).relative_to(source).as_posix()
            safe_path(relative)
            physical(Path(current) / directory, directory=True)
            # Also reject private empty directories instead of silently hiding them.
            refuse_private(relative + "/placeholder")
        for filename in filenames:
            file = Path(current) / filename
            name = safe_path(file.relative_to(source).as_posix())
            physical(file)
            require(name.upper() != INVENTORY.upper(), "Source already contains a directory inventory")
            if excluded(name):
                omitted.append(name)
                continue
            refuse_private(name)
            key = name.upper()
            require(key not in aliases, "Case-insensitive duplicate file")
            aliases.add(key)
            parts = name.split("/")[:-1]
            while parts:
                parent = "/".join(parts)
                require(directories.get(parent.upper(), parent) == parent, "Directory case alias")
                directories[parent.upper()] = parent
                parts.pop()
            size, digest = stream_file(file)
            total += size
            require(total <= MAX_TOTAL and len(records) < MAX_FILES, "Package resource limit exceeded")
            records.append({"path": name, "size": size, "sha256": digest})
    require(not aliases.intersection(directories), "File and directory collision")
    records.sort(key=lambda item: item["path"])
    names = {item["path"] for item in records}
    require(ENTRYPOINTS[app_id] in names and "resources/app.asar" in names, "Incomplete Electron application tree")
    require(any(name.startswith(f"resources/runtime/{app_id}/") for name in names), "Application runtime is missing")
    return {"schemaVersion": 1, "appId": app_id, "version": version, "entrypoint": ENTRYPOINTS[app_id], "files": records}, omitted


def zip_info(name):
    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def build(source, destination, app_id, version):
    source, destination = Path(source).absolute(), Path(destination).absolute()
    require(destination.suffix.lower() == ".zip", "Output must be a ZIP")
    require(not destination.is_relative_to(source), "Output cannot be inside source tree")
    parent_chain(destination.parent)
    require(not destination.exists() and not destination.is_symlink(), "Output already exists")
    inventory, omitted = inventory_for(source, app_id, version)
    encoded = json.dumps(inventory, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    require(len(encoded) <= MAX_INVENTORY, "Inventory is too large")
    fd, temporary = tempfile.mkstemp(prefix=".directory-zip-", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
            archive.writestr(zip_info(INVENTORY), encoded)
            for record in inventory["files"]:
                with archive.open(zip_info(record["path"]), "w", force_zip64=True) as member:
                    size, digest = stream_file(source.joinpath(*record["path"].split("/")), member)
                require((size, digest) == (record["size"], record["sha256"]), "Source changed after inventory")
                member_info = archive.getinfo(record["path"])
                require(size <= max(1024**2, member_info.compress_size * MAX_RATIO), "Member exceeds runtime ZIP expansion ratio")
                require(archive.fp.tell() <= MAX_ARCHIVE, "ZIP exceeds runtime archive limit")
        require(temporary.stat().st_size <= MAX_ARCHIVE, "ZIP exceeds runtime archive limit")
        # Publication is exclusive, even if another process creates destination.
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    sha256, sha512 = hashlib.sha256(), hashlib.sha512()
    with destination.open("rb") as package:
        for chunk in iter(lambda: package.read(1024 * 1024), b""):
            sha256.update(chunk)
            sha512.update(chunk)
    return {"path": str(destination), "appId": app_id, "version": version, "platform": "win32", "arch": "x64", "format": "windows-directory-zip-v1", "entrypoint": ENTRYPOINTS[app_id], "name": f"{app_id}-{version}-win32-x64.zip", "size": destination.stat().st_size, "sha256": sha256.hexdigest(), "sha512": base64.b64encode(sha512.digest()).decode("ascii"), "fileCount": len(inventory["files"]), "expandedBytes": sum(item["size"] for item in inventory["files"]), "excludedInstallerFiles": omitted}


def publisher_payload(descriptor):
    """Exact bytes for the separate local publisher signer; no keys are read."""
    names = ("appId", "version", "platform", "arch", "format", "entrypoint", "name", "size", "sha256", "sha512")
    value = {name: descriptor[name] for name in names}
    return b"MELANGE-DESKTOP-DIRECTORY-ZIP-V1\n" + json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--app", required=True, choices=ENTRYPOINTS)
    parser.add_argument("--version", required=True)
    parser.add_argument("--publisher-payload", type=Path, help="Write canonical bytes for the separate publisher-proof signing step (exclusive output)")
    args = parser.parse_args()
    if args.publisher_payload:
        payload_file = args.publisher_payload.absolute()
        require(not payload_file.is_relative_to(args.source.absolute()), "Publisher payload cannot be inside source tree")
        parent_chain(payload_file.parent)
        require(not payload_file.exists() and not payload_file.is_symlink() and payload_file != args.output.absolute(), "Publisher payload output already exists or conflicts")
    receipt = build(args.source, args.output, args.app, args.version)
    if args.publisher_payload:
        with payload_file.open("xb") as output:
            output.write(publisher_payload(receipt))
        receipt["publisherProofPayloadPath"] = str(payload_file)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
