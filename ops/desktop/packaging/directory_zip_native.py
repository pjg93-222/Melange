"""Native ZIP compression of a guarded inventory; no program or signing changes."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
import zipfile
import directory_zip as guard


def reorder_directory(archive, expected_names):
    """Move only the inventory central record. All local bytes/offsets stay put."""
    before = guard.physical(archive)
    fd = os.open(archive, os.O_RDWR | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "r+b") as stream:
        guard.require(guard.same_file(before, os.fstat(stream.fileno())), "Archive changed before central reorder")
        stream.seek(max(0, before.st_size - 65557))
        tail_start = stream.tell()
        tail = stream.read()
        end = tail.rfind(b"PK\x05\x06")
        guard.require(end >= 0 and end + 22 <= len(tail), "ZIP end record missing")
        e = struct.unpack_from("<IHHHHIIH", tail, end)
        guard.require(e[1] == e[2] == 0 and e[3] == e[4] and 0 < e[4] < 65535 and e[5] < 0xffffffff and e[6] < 0xffffffff,
                      "Native ZIP must be classic, single-disk ZIP")
        guard.require(end + 22 + e[7] == len(tail) and e[6] + e[5] == tail_start + end and e[5] <= 64 * 1024**2,
                      "Invalid central-directory bounds")
        stream.seek(e[6])
        raw = stream.read(e[5])
        records, names, offset = [], [], 0
        while offset < len(raw):
            guard.require(offset + 46 <= len(raw), "Truncated central record")
            h = struct.unpack_from("<IHHHHHHIIIHHHHHII", raw, offset)
            length = 46 + h[10] + h[11] + h[12]
            guard.require(h[0] == 0x02014b50 and offset + length <= len(raw) and h[13] == 0,
                          "Invalid central record")
            guard.require(not h[3] & 1 and h[4] in (0, 8) and h[8] < 0xffffffff and h[9] < 0xffffffff and h[16] + 30 < e[6],
                          "Unsupported native ZIP member")
            name = raw[offset + 46:offset + 46 + h[10]].decode("utf-8" if h[3] & 0x800 else "cp437")
            guard.safe_path(name)
            kind = stat.S_IFMT(h[15] >> 16)
            guard.require(not h[15] & 0x10 and kind in (0, stat.S_IFREG), "Native ZIP contains a link or directory")
            extra = raw[offset + 46 + h[10]:offset + 46 + h[10] + h[11]]
            position = 0
            while position < len(extra):
                guard.require(position + 4 <= len(extra), "Invalid ZIP extra field")
                tag, size = struct.unpack_from("<HH", extra, position)
                guard.require(tag != 1 and position + 4 + size <= len(extra), "ZIP64 or truncated extra field")
                position += 4 + size
            names.append(name)
            records.append(raw[offset:offset + length])
            offset += length
        guard.require(len(records) == e[4] == len(expected_names) and len(set(names)) == len(names) and set(names) == set(expected_names),
                      "Native ZIP member set differs from inventory")
        index = names.index(guard.INVENTORY)
        ordered = records[index:index + 1] + records[:index] + records[index + 1:]
        rewritten = b"".join(ordered)
        guard.require(len(rewritten) == len(raw), "Central-directory size changed")
        stream.seek(e[6])
        stream.write(rewritten)
        stream.flush()
        os.fsync(stream.fileno())
        after = guard.physical(archive)
        guard.require((before.st_dev, before.st_ino, before.st_size) == (after.st_dev, after.st_ino, after.st_size), "Archive identity changed")
        return {"offset": e[6], "size": e[5], "records": e[4]}


def verify_archive(archive, inventory, encoded):
    """Bind native output to the completed source inventory before any proof."""
    guard.require(archive.stat().st_size <= guard.MAX_ARCHIVE, "Native ZIP exceeds archive limit")
    expected = {row["path"]: row for row in inventory["files"]}
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        names = [item.filename for item in entries]
        guard.require(names[0] == guard.INVENTORY and len(names) == len(expected) + 1 and len(set(names)) == len(names)
                      and set(names) == set(expected) | {guard.INVENTORY}, "Native ZIP inventory order or file set changed")
        guard.require(zipped.read(guard.INVENTORY) == encoded, "Native ZIP inventory bytes changed")
        for item in entries[1:]:
            row = expected[item.filename]
            guard.require(item.compress_type in (0, 8) and not item.flag_bits & 1 and item.file_size == row["size"], "Native ZIP member metadata changed")
            guard.require(item.file_size <= max(1024**2, item.compress_size * guard.MAX_RATIO), "Native ZIP expansion ratio exceeds limit")
            with zipped.open(item) as member:
                digest = hashlib.file_digest(member, "sha256").hexdigest()
            guard.require(digest == row["sha256"], "Native ZIP bytes differ from completed source inventory: " + item.filename)


def build(source, destination, app_id, version, seven_zip):
    from directory_inventory_parallel import inventory_for
    source, destination, seven_zip = Path(source).absolute(), Path(destination).absolute(), Path(seven_zip).resolve(strict=True)
    guard.parent_chain(source)
    guard.parent_chain(destination.parent)
    guard.physical(seven_zip)
    guard.require(destination.suffix.lower() == ".zip" and not destination.is_relative_to(source)
                  and not destination.exists() and not destination.is_symlink(), "Unsafe native ZIP destination")
    implementations = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                       for name in ["directory_zip_native.py", "directory_inventory_parallel.py", "directory_zip.py"]}
    with seven_zip.open("rb") as tool:
        tool_hash = hashlib.file_digest(tool, "sha256").hexdigest()
    inventory, omitted = inventory_for(source, app_id, version, workers=8)
    guard.require(len(inventory["files"]) + 1 < 65535, "Native classic ZIP file-count limit exceeded")
    encoded = json.dumps(inventory, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    guard.require(len(encoded) <= guard.MAX_INVENTORY, "Inventory is too large")
    fd, temporary = tempfile.mkstemp(prefix=".native-directory-zip-", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary)
    listing = temporary.with_suffix(".list")
    listing_identity = None
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(guard.zip_info(guard.INVENTORY), encoded)
        with listing.open("x", encoding="utf-8", newline="\n") as stream:
            info = os.fstat(stream.fileno())
            listing_identity = (info.st_dev, info.st_ino)
            stream.write("".join(row["path"] + "\n" for row in inventory["files"]))
        command = [str(seven_zip), "a", "-tzip", "-mm=Deflate", "-mx=1", "-mmt=4", "-scsUTF-8", "-spd", "-r-", "-y", str(temporary), "@" + str(listing)]
        with (destination.parent / "native-compression.log").open("xb") as log:
            result = subprocess.run(command, cwd=source, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        guard.require(result.returncode == 0, "Native compression failed; see native-compression.log")
        central = reorder_directory(temporary, [guard.INVENTORY, *(row["path"] for row in inventory["files"])])
        verify_archive(temporary, inventory, encoded)
        guard.require(all(hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() == value for name, value in implementations.items()), "Native packager implementation changed")
        os.link(temporary, destination)
    finally:
        if listing_identity and listing.exists():
            info = guard.physical(listing)
            if (info.st_dev, info.st_ino) == listing_identity:
                listing.unlink()
        temporary.unlink(missing_ok=True)
    sha256, sha512 = hashlib.sha256(), hashlib.sha512()
    with destination.open("rb") as archive:
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            sha256.update(chunk)
            sha512.update(chunk)
    evidence = {"schemaVersion": 1, "implementations": implementations, "nativeToolPath": str(seven_zip), "nativeToolSha256": tool_hash,
                "inventorySha256": hashlib.sha256(encoded).hexdigest(), "inventoryWorkers": 8, "compressionThreads": 4,
                "centralDirectory": central, "contentMatchesSourceInventory": True, "packageSha256": sha256.hexdigest()}
    with (destination.parent / "native-zip-evidence.json").open("x", encoding="utf-8") as output:
        json.dump(evidence, output, indent=2)
        output.write("\n")
    return {"path": str(destination), "appId": app_id, "version": version, "platform": "win32", "arch": "x64", "format": "windows-directory-zip-v1", "entrypoint": guard.ENTRYPOINTS[app_id], "name": f"{app_id}-{version}-win32-x64.zip", "size": destination.stat().st_size, "sha256": sha256.hexdigest(), "sha512": base64.b64encode(sha512.digest()).decode(), "fileCount": len(inventory["files"]), "expandedBytes": sum(row["size"] for row in inventory["files"]), "excludedInstallerFiles": omitted}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["source", "output", "seven-zip", "publisher-payload"]:
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--app", required=True, choices=guard.ENTRYPOINTS)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    payload = args.publisher_payload.absolute()
    guard.parent_chain(payload.parent)
    guard.require(not payload.exists() and not payload.is_symlink() and payload != args.output.absolute() and not payload.is_relative_to(args.source.absolute()), "Unsafe publisher payload destination")
    result = build(args.source, args.output, args.app, args.version, args.seven_zip)
    with payload.open("xb") as stream:
        stream.write(guard.publisher_payload(result))
    result["publisherProofPayloadPath"] = str(payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
