"""Independently inspect a native Windows release; never launch its native payload.

The build controller supplies frozen client/source exports and its gated staging
tree. This verifier compares actual archive bytes to those inputs, independently
enumerates every PE header, and obtains fresh Windows signature verdicts. The
source-bound Node contract-construction check creates no backend, UI or profile.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
from concurrent.futures import ThreadPoolExecutor
import ctypes
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PRODUCTS = {"melange": "Melange", "mentat": "Mentat", "terrier": "Terrier"}
REPOSITORIES = {"melange": "pjg93-222/melange", "mentat": "pjg93-222/mentat", "terrier": "pjg93-222/geo"}
GIB = 1024 ** 3
RESERVE = 32 * GIB
MAX_EXPANDED = 8 * 1024 ** 3
# Reviewed electron-builder26.15.3 assisted, per-user native include graph:
# installer.onInit/mutex -> System/UAC; common isUpdated -> StdUtils;
# PAGE_INSTALL_MODE -> nsDialogs (the current-user skip happens at runtime);
# CHECK_APP_RUNNING -> nsExec; extractUsing7za -> nsis7z; shortcuts -> WinShell.
# Removing uninstaller generation/calls does not remove any of these branches.
# A future template/config change must review this contract and its actual census.
NATIVE_PLUGINS = frozenset({"System.dll", "UAC.dll", "StdUtils.dll", "nsDialogs.dll",
                            "nsExec.dll", "nsis7z.dll", "WinShell.dll"})
BUILD_INPUTS = ("builder.cjs", "nsis-no-uninstaller.cjs", "nsis-no-uninstaller-extract.nsh", "installer.nsh")
BUILTIN_BUILD_INPUTS = ("builder.cjs", "build-plugin-free.cjs", "plugin-free-installer.nsi", "release-signing.cjs")
INSTALLER_FORMATS = ("legacy-nsis-v1", "builtin-nsis-v1")
NSIS_MEMBERS = frozenset("$PLUGINSDIR/" + name for name in (*NATIVE_PLUGINS, "modern-wizard.bmp", "app-64.7z"))


def load_helper(name):
    spec = importlib.util.spec_from_file_location("native_release_" + name, HERE / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


legacy = load_helper("verify_signed_release")
contract = load_helper("no_uninstaller_contract")
Refused = legacy.Refused


def require(value, message):
    if not value:
        raise Refused(message)


def identity(path):
    return os.path.normcase(os.path.abspath(path))


def physical(path, directory=False):
    path = Path(path).absolute()
    info = path.lstat()
    require(not path.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400,
            "Redirected verification path: " + str(path))
    require(path.is_dir() if directory else path.is_file() and info.st_nlink == 1,
            "Private physical file/directory required: " + str(path))
    require(identity(path.resolve(strict=True)) == identity(path), "Verification path traverses a redirect")
    return info


def snapshot(path):
    info = physical(path)
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, legacy.digest(path)


@contextlib.contextmanager
def locked_input(path):
    """On Windows deny replacement and writes while 7-Zip/Windows reads input."""
    before = snapshot(path)
    handle = None
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                           ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        create.restype = ctypes.c_void_p
        handle = create(str(Path(path).absolute()), 0x80000000, 1, None, 3, 0x80, None)
        require(handle not in (None, ctypes.c_void_p(-1).value), "Could not lock verification input")
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    try:
        require(snapshot(path) == before, "Input changed before inspection lock")
        yield before
        require(snapshot(path) == before, "Input changed during inspection")
    finally:
        if handle is not None:
            kernel.CloseHandle(handle)


def scan(directory):
    physical(directory, True)
    files = legacy.tree(Path(directory))
    # Windows final-path checks and small reads have substantial per-file
    # latency. Bound concurrency while preserving every physical-path check,
    # header classification, hash, and before/after stat invariant. No verdict
    # is cached, and callers still repeat their independent final comparisons.
    def inspect(item):
        name, file = item
        physical(file)
        native, hashes = legacy.inspect_files({name: file})
        return name, bool(native), {"sha256": hashes[name], "size": file.stat().st_size}
    pes, mapping = set(), {}
    with ThreadPoolExecutor(max_workers=16) as pool:
        for name, native, value in pool.map(inspect, files.items()):
            if native:
                pes.add(name)
            mapping[name] = value
    return files, pes, mapping


def reference_overlays(files, pes, mapping, app, *, executable=None, asar=None):
    """Map the two explicit build overlays without duplicating a signed runtime.

    Every mapped input stays a physical, single-link file. The final archive is
    still extracted independently and compared to this exact merged reference.
    """
    files, pes, mapping = dict(files), set(pes), dict(mapping)
    for relative, source in ((PRODUCTS[app] + ".exe", executable), ("resources/app.asar", asar)):
        if source is None:
            continue
        require(relative in files, "Overlay has no corresponding program member")
        file = Path(source).absolute()
        physical(file)
        native, hashes = legacy.inspect_files({relative: file})
        require(native == ({relative} if relative.endswith(".exe") else set()), "Overlay native classification differs")
        files[relative] = file
        pes.discard(relative)
        pes.update(native)
        mapping[relative] = {"sha256": hashes[relative], "size": file.stat().st_size}
    return files, pes, mapping


def source_overlays(files, pes, mapping, app, version, manifest_file, client_commit, source_commit):
    """Independently bind the narrowly reviewed non-native source replacements.

    The original base stays untouched. Actual extracted sources and bootstrap
    still have to equal the separately gated source tree and frozen tooling.
    """
    if manifest_file is None:
        return files, pes, mapping, {}, None
    manifest_file = Path(manifest_file).absolute()
    require(physical(manifest_file).st_size <= 65536, "Source overlay manifest is too large")
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, "Duplicate source overlay property")
            value[key] = item
        return value
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    require(isinstance(manifest, dict) and set(manifest) == {"schemaVersion", "appId", "version", "clientCommit", "sourceCommit", "files"}
            and type(manifest["schemaVersion"]) is int and manifest["schemaVersion"] == 1
            and manifest["appId"] == app and manifest["version"] == version
            and manifest["clientCommit"] == client_commit and manifest["sourceCommit"] == source_commit
            and all(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{40}", value) for value in (client_commit, source_commit)),
            "Source overlay identity differs from frozen release")
    rows = manifest["files"]
    require(isinstance(rows, list) and 1 <= len(rows) <= 5, "Invalid source overlay member count")
    prefix = "resources/runtime/" + app + "/"
    allowed = {prefix + name for name in ("bootstrap/terrier_standalone.py", "bootstrap/module_application_inventory.py",
                                          "source-inventory.json", "source-provenance.json")}
    if app == "terrier":
        allowed.add(prefix + "sources/server/research/street_views.py")
    root = manifest_file.parent / "files"
    overlay_files, overlay_pes, overlay_map = scan(root)
    require(not overlay_pes, "Source overlays cannot contain native images")
    files, pes, mapping = dict(files), set(pes), dict(mapping)
    seen, inputs = set(), {}
    for row in rows:
        require(isinstance(row, dict) and set(row) == {"path", "bytes", "sha256"}, "Invalid source overlay member")
        name = row["path"]
        require(isinstance(name, str) and name in allowed and name not in seen and name in files and name not in pes
                and type(row["bytes"]) is int and 0 <= row["bytes"] <= 16 * 1024**2
                and isinstance(row["sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", row["sha256"]),
                "Invalid source overlay member")
        seen.add(name)
        require(overlay_map.get(name) == {"sha256": row["sha256"], "size": row["bytes"]}, "Source overlay bytes differ")
        source = overlay_files[name]
        with source.open("rb") as stream:
            require(stream.read(2) != b"MZ", "Source overlays cannot contain native images")
        files[name], mapping[name] = source, overlay_map[name]
        inputs[str(source)] = snapshot(source)
    require(set(overlay_files) == seen, "Source overlay file inventory is not closed")
    inputs[str(manifest_file)] = snapshot(manifest_file)
    return files, pes, mapping, inputs, {"path": str(manifest_file), "sha256": inputs[str(manifest_file)][-1],
        "clientCommit": client_commit, "sourceCommit": source_commit, "files": rows}


def source_provenance(*, app, version, client_commit, source_commit, staged, program_map, original_reference, origin_proof=None):
    """Bind packaged provenance to the independent gated stage and source origins."""
    expected = staged.parent / "source-provenance.json"
    info = physical(expected)
    prefix = "resources/runtime/" + app + "/"
    expected_hash = legacy.digest(expected)
    require(program_map.get(prefix + "source-provenance.json") == {"sha256": expected_hash, "size": info.st_size},
            "Packaged source provenance differs from gated provenance")
    value = json.loads(expected.read_text(encoding="utf-8"))
    require(isinstance(value, dict) and value.get("schemaVersion") == 1 and value.get("app") == app
            and value.get("version") == version and value.get("sourceCommit") == source_commit
            and value.get("commonClientCommit") == value.get("bootstrapCommit") == client_commit,
            "Source provenance differs from frozen identities")
    previous = original_reference.get(prefix + "source-provenance.json")
    require(previous is not None and value.get("previousRuntimeProvenanceSha256") == previous["sha256"],
            "Source provenance does not bind retained provenance")
    origin = value.get("sourceOrigin")
    require(isinstance(origin, dict), "Explicit retained/composite source origin required")
    sources = {name[len(prefix + "sources/"):]: row for name, row in program_map.items() if name.startswith(prefix + "sources/")}
    retained = {name[len(prefix + "sources/"):]: row for name, row in original_reference.items() if name.startswith(prefix + "sources/")}
    require(set(sources) == set(retained), "Source overlay changed the retained source closure")
    proof_hash = None
    if app != "terrier":
        require(origin.get("kind") == "retained-verified-export" and origin.get("baseSourceCommit") == source_commit
                and origin.get("sourceFileCount") == len(sources) and sources == retained,
                "Retained source provenance differs from exact base sources")
    else:
        require(origin_proof is not None, "Terrier composite source origin proof is required")
        proof_path = Path(origin_proof).absolute()
        physical(proof_path)
        proof_hash = legacy.digest(proof_path)
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
        require(origin.get("kind") == proof.get("provenanceKind") == "composite-retained-export-plus-exact-git-override"
                and proof.get("status") == "passed" and origin.get("proofSha256") == proof_hash
                and proof.get("overrideSourceCommit") == source_commit
                and origin.get("baseSourceCommit") == proof.get("baseSourceCommit")
                and origin.get("sharedBootstrapSourceCommit") == proof.get("sharedBootstrapCommit")
                and proof.get("changedGitPaths") == ["server/research/street_views.py"],
                "Terrier composite source origin identity differs")
        rows = proof.get("files")
        require(isinstance(rows, list) and len(rows) == len(sources), "Incomplete composite source origins")
        seen, counts = set(), {"git-blob": 0, "retained-approved-export-not-tracked-in-git": 0}
        for row in rows:
            name = row.get("path")
            require(name in sources and name not in seen and row.get("origin") in counts
                    and row.get("matchesPublished30Native") is True
                    and retained[name] == {"sha256": row.get("baseSha256"), "size": row.get("bytes")},
                    "Composite source origin differs from retained base")
            seen.add(name)
            counts[row["origin"]] += 1
            size = proof["override"]["bytes"] if name == "server/research/street_views.py" else row["bytes"]
            require(sources[name] == {"sha256": row.get("effectiveSha256"), "size": size},
                    "Composite source origin differs from packaged source")
        for field, count in (("sourceFileCount", len(sources)), ("gitBackedFileCount", counts["git-blob"]),
                             ("retainedExportFileCount", counts["retained-approved-export-not-tracked-in-git"])):
            require(origin.get(field) == proof.get(field) == count, "Composite source origin counts differ")
    return {"sha256": expected_hash, "kind": origin["kind"], "originProofSha256": proof_hash,
            "sourceFileCount": len(sources)}


def reader_capabilities(seven):
    info = legacy.run([seven, "i"]).decode("utf-8", "strict")
    require(re.search(r"\bNsis\s+nsis\b", info, re.IGNORECASE), "A full NSIS-capable 7-Zip reader is required")
    return {"nsis": True, "formatSelection": "explicit Nsis outer, 7z inner"}


def extract(seven, archive, destination, budget, *, reserve=RESERVE, archive_format="7z", expected_files=None):
    physical(destination.parent, True)
    require(archive_format in ("Nsis", "7z"), "Unsupported inspection archive format")
    if expected_files is not None:
        require(archive_format == "Nsis" and isinstance(expected_files, dict) and bool(expected_files),
                "Direct NSIS inspection requires a complete signed program reference")
        require(all(isinstance(name, str) and legacy.safe_name(name) == name
                    and not any(part.casefold() == "$pluginsdir" for part in name.split("/"))
                    and isinstance(value, dict) and type(value.get("size")) is int and value["size"] >= 0
                    for name, value in expected_files.items()), "Invalid direct NSIS program reference")
    listing = legacy.run([seven, "l", "-t" + archive_format, "-slt", "-ba", archive]).decode("utf-8", "strict").replace("\r\n", "\n")
    names, aliases, sizes, total = set(), set(), {}, 0
    for block in listing.strip().split("\n\n"):
        row = dict(line.split(" = ", 1) for line in block.splitlines() if " = " in line)
        if "Path" not in row:
            continue
        name = legacy.safe_name(row["Path"])
        require(name.casefold() not in aliases and not any(key in row for key in ("Symbolic Link", "Hard Link")), "Linked/aliased archive member")
        aliases.add(name.casefold())
        require(len(aliases) <= 200000, "Archive file count exceeds inspection bound")
        if row.get("Folder") == "+" or row.get("Attributes", "").startswith("D"):
            continue
        value = row.get("Size", "")
        require(value.isdecimal() or archive_format == "Nsis" and value == "", "Missing or invalid archive member size")
        size = int(value) if value else None
        sizes[name] = size
        total += size or 0
        names.add(name)
    # NSIS omits unpacked sizes for compressed plugin/resource members. Its
    # reviewed nine-member closure and bounded reservation avoid interpreting
    # unknown as zero; inner7z still requires every exact declared byte count.
    if expected_files is not None:
        require(names == set(expected_files), "Direct NSIS member set differs from signed program reference")
        require(all(size is None or size == expected_files[name]["size"] for name, size in sizes.items()),
                "Direct NSIS declared size differs from signed program reference")
        # NSIS can omit unpacked sizes. Reserve the complete authenticated build
        # reference, then require every extracted byte count and hash to match it.
        bound = sum(value["size"] for value in expected_files.values())
    elif archive_format == "Nsis":
        require(names == NSIS_MEMBERS, "NSIS member set differs from reviewed native template")
        bound = min(budget, Path(archive).stat().st_size * 2 + 64 * 1024 ** 2)
    else:
        bound = total
    require(reserve >= 16 * GIB and total <= bound <= budget and shutil.disk_usage(destination.parent).free - bound >= reserve,
            "Extraction would exceed its bound or selected desktop workspace reserve")
    destination.mkdir()
    owned = destination.stat()
    legacy.run([seven, "x", "-t" + archive_format, archive, "-o" + str(destination), "-y"], timeout=1800)
    after = physical(destination, True)
    require((owned.st_dev, owned.st_ino) == (after.st_dev, after.st_ino), "Inspection root was replaced")
    files = legacy.tree(destination)
    require(set(files) == names, "Extracted paths differ from inspected archive listing")
    actual = {name: file.stat().st_size for name, file in files.items()}
    require(all(actual[name] == size for name, size in sizes.items() if size is not None), "Extracted byte count differs from archive listing")
    if expected_files is not None:
        require(actual == {name: value["size"] for name, value in expected_files.items()},
                "Direct NSIS extracted sizes differ from signed program reference")
    require(expected_files is not None or archive_format != "Nsis" or all(size <= 8 * 1024 ** 2 for name, size in actual.items() if name != "$PLUGINSDIR/app-64.7z"),
            "NSIS plugin/resource exceeds its inspection bound")
    used = sum(actual.values())
    require(used <= bound and shutil.disk_usage(destination.parent).free >= reserve, "Extracted bytes exceed bound or desktop workspace reserve")
    return used


def same_tree(actual, expected, label):
    require(actual == expected, label + " file census or bytes differ")


def verify_asar_integrity(main, header_hash):
    entries = [payload for key, (_offset, payload) in legacy.resources(main.read_bytes()).items()
               if key[:2] == ("INTEGRITY", "ELECTRONASAR")]
    require(len(entries) == 1 and json.loads(entries[0]) ==
            [{"file": "resources\\app.asar", "alg": "SHA256", "value": header_hash}],
            "Main executable ASAR integrity differs from inspected archive")


def literal_assignment(file, name):
    for node in ast.parse(Path(file).read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            result = ast.literal_eval(node.value)
            require(isinstance(result, (tuple, list)) and all(isinstance(item, str) and legacy.safe_name(item) == item for item in result), "Invalid frozen file manifest")
            require(len(set(result)) == len(result), "Duplicate frozen bootstrap input")
            return list(result)
    raise Refused("Frozen manifest assignment missing: " + name)


def client_manifest(client):
    text = (client / "release-files.cjs").read_text(encoding="utf-8")
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    found = re.search(r"module\.exports\s*=\s*Object\.freeze\(\s*(\[[\s\S]*?\])\s*\)", text)
    require(found, "Unsupported frozen client file manifest")
    files = ast.literal_eval(found[1])
    require(isinstance(files, list) and all(isinstance(name, str) and legacy.safe_name(name) == name for name in files), "Invalid frozen client manifest")
    require(len(set(files)) == len(files), "Duplicate frozen client input")
    return files


def asar_member_bytes(archive, name):
    """Read one already-censused member without executing or extracting client code."""
    name = legacy.safe_name(name)
    with Path(archive).open("rb") as stream:
        lead = stream.read(16)
        require(len(lead) == 16, "Truncated contract ASAR header")
        first, header_size, _, json_size = struct.unpack("<IIII", lead)
        require(first == 4 and 0 < json_size <= 16 * 1024**2 and header_size >= json_size + 8,
                "Unsupported contract ASAR header")
        node = json.loads(stream.read(json_size))
        for part in name.split("/"):
            node = node.get("files", {}).get(part)
            require(isinstance(node, dict) and not node.get("link") and not node.get("unpacked"),
                    "Missing or redirected compiled ASAR inventory")
        require("files" not in node and type(node.get("size")) is int and 0 < node["size"] <= 2 * 1024**2,
                "Invalid compiled ASAR inventory size")
        offset = int(node.get("offset", -1))
        require(offset >= 0 and 8 + header_size + offset + node["size"] <= Path(archive).stat().st_size,
                "Compiled ASAR inventory lies outside archive")
        stream.seek(8 + header_size + offset)
        raw = stream.read(node["size"])
        require(len(raw) == node["size"], "Truncated compiled ASAR inventory")
        return raw


def compiled_module_tables(*, app, javascript, python, program_map, config):
    """Join both compiled authorities to the actual packaged program, not its source inventory."""
    text = javascript.decode("utf-8-sig")
    matches = list(re.finditer(r"\bconst\s+APPLICATION_SPECS\s*=\s*freeze\(\s*", text))
    require(len(matches) == 1, "Compiled JavaScript module table is missing or ambiguous")
    js, end = json.JSONDecoder().raw_decode(text, matches[0].end())
    require(re.fullmatch(r"\s*\);\s*module\.exports\s*=\s*Object\.freeze\(\{APPLICATION_SPECS\}\);\s*",
                         text[end:]), "Compiled JavaScript module table is not a closed literal")
    def literal(node):
        if isinstance(node, ast.Call):
            require(isinstance(node.func, ast.Name) and node.func.id == "MappingProxyType"
                    and len(node.args) == 1 and not node.keywords,
                    "Compiled Python module table contains executable selectors")
            return literal(node.args[0])
        if isinstance(node, ast.Dict):
            keys = [literal(key) for key in node.keys]
            require(all(type(key) is str for key in keys) and len(set(keys)) == len(keys),
                    "Compiled Python module table has duplicate or invalid keys")
            return dict(zip(keys, (literal(value) for value in node.values)))
        if isinstance(node, (ast.Tuple, ast.List)):
            return [literal(value) for value in node.elts]
        if isinstance(node, ast.Constant) and type(node.value) in (str, int, bool, type(None)):
            return node.value
        raise Refused("Compiled Python module table is not a closed literal")
    assignments = [node.value for node in ast.parse(python.decode("utf-8-sig")).body
                   if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                       and target.id == "APPLICATION_SPECS" for target in node.targets)]
    require(len(assignments) == 1, "Compiled Python module table is missing or ambiguous")
    py = literal(assignments[0])
    require(js == py and isinstance(js, dict) and set(js) == {"melange", "mentat"},
            "Packaged JavaScript/Python compiled module tables disagree")
    spec = js[app]
    fields = {"schemaVersion", "appId", "contractId", "programFingerprint", "programFiles",
              "requiredKinds", "publicReaders", "privateBoundaries", "startupTimeoutMs"}
    require(isinstance(spec, dict) and set(spec) == fields and type(spec["schemaVersion"]) is int
            and spec["schemaVersion"] == 1 and spec["appId"] == app
            and spec["contractId"] == app + ".public-data.v1", "Invalid compiled application identity")
    files = spec["programFiles"]
    require(isinstance(files, list) and 0 < len(files) <= 512, "Invalid compiled program table")
    seen, total = set(), 0
    for row in files:
        require(isinstance(row, dict) and set(row) == {"root", "path", "bytes", "sha256"}
                and row["root"] in ("source", "bootstrap") and isinstance(row["path"], str)
                and 0 < len(row["path"]) <= 400
                and all(re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9._-]{0,127}", part)
                        and not part.endswith(".") for part in row["path"].split("/"))
                and type(row["bytes"]) is int and 0 <= row["bytes"] <= 16 * 1024**2
                and isinstance(row["sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", row["sha256"]),
                "Invalid compiled program descriptor")
        key = row["root"] + "/" + row["path"].lower()
        require(key not in seen and not row["path"].endswith(("module_application_inventory.py", "module-application-inventory.cjs")),
                "Duplicate or recursive compiled program descriptor")
        seen.add(key)
        total += row["bytes"]
        prefix = "resources/runtime/" + app + ("/sources/" if row["root"] == "source" else "/bootstrap/")
        require(program_map.get(prefix + row["path"]) == {"size": row["bytes"], "sha256": row["sha256"]},
                "Compiled program descriptor differs from actual packaged bytes: " + key)
    require(total <= 64 * 1024**2, "Compiled program table exceeds native budget")
    ordered = sorted(files, key=lambda row: (row["root"], row["path"]))
    fingerprint = hashlib.sha256(json.dumps(ordered, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(fingerprint == spec["programFingerprint"], "Compiled program fingerprint differs from its literal table")
    modes = config.get("desktopPublicData", {})
    require(isinstance(modes, dict), "Packaged public data mode is invalid")
    mode = modes.get(app)
    require(mode in (None, "paged-v1") and (mode != "paged-v1" or app == "melange"),
            "Unsupported packaged public data mode")
    paged = app == "melange" and mode == "paged-v1"
    access_mode = config.get("desktopAccessMode", "managed")
    authentication = config.get("desktopAuthentication", "password")
    require(access_mode in ("standalone", "managed") and authentication in ("windows", "password")
            and (authentication != "windows" or access_mode == "standalone"),
            "Invalid packaged module authentication mode")
    return {"status": "passed", "appId": app, "programFingerprint": fingerprint,
            "programFileCount": len(files), "programBytes": total,
            "javascriptSha256": hashlib.sha256(javascript).hexdigest(),
            "pythonSha256": hashlib.sha256(python).hexdigest(),
            "publicDataMode": mode, "accessMode": access_mode, "authentication": authentication,
            "contractId": "melange.public-data.pages.v1" if paged else spec["contractId"],
            "requiredKinds": ["melange.official-payroll-pages.v1"] if paged else spec["requiredKinds"],
            "literalTablesEqual": True, "matchesActualPackagedProgram": True}


def compiled_module_runtime(*, app, client, extracted, expected):
    """Construct the real, byte-bound client contract without launching an application or backend."""
    script = r'''
const fs=require('node:fs'),path=require('node:path');
const request=JSON.parse(fs.readFileSync(0,'utf8'));
const {Runtime}=require(path.join(request.client,'runtime.cjs'));
const {withCompiledApplicationContract}=require(path.join(request.client,'module-data-startup.cjs'));
const {createRuntimeModuleBoundary}=require(path.join(request.client,'module-data-runtime-boundary.cjs'));
const runtime=new Runtime(request.app,request.profile,request.resources,{allowStandalone:request.accessMode==='standalone',authentication:request.authentication});
const result=withCompiledApplicationContract(request.app,{runtime,resources:request.resources,publicDataMode:request.mode},(contract,proof)=>{
 if(!contract)throw new Error('Packaged application contract is unsupported');
 const boundary=createRuntimeModuleBoundary({appId:request.app,profile:request.profile,contract,constructionProof:proof,
   getRuntime:()=>runtime,getSelected:()=>({}),authorize:async()=>{throw new Error('Acceptance never authorizes a launch');}});
 if(!boundary||boundary.supportsContract(contract)!==true||boundary.supportsContract(contract)!==true)throw new Error('Packaged native boundary rejects its contract');
 return {status:'passed',contractId:contract.contractId,programFingerprint:contract.programFingerprint,
   programFileCount:contract.programFiles.length,requiredKinds:contract.requiredKinds,boundarySupported:true};
});
process.stdout.write(JSON.stringify(result));
'''
    node = shutil.which("node")
    require(node is not None, "Node is required for the packaged application-contract acceptance")
    request = {"app": app, "client": str(client), "resources": str(extracted / "resources"),
               "profile": str(extracted.parent / "unused-module-acceptance-profile"),
               "mode": expected["publicDataMode"], "accessMode": expected["accessMode"],
               "authentication": expected["authentication"]}
    result = subprocess.run([node, "-e", script], input=json.dumps(request).encode(), capture_output=True,
                            timeout=120, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    require(result.returncode == 0, "Actual packaged application contract/native boundary is unsupported")
    value = json.loads(result.stdout)
    require(value.get("status") == "passed" and value.get("boundarySupported") is True
            and all(value.get(key) == expected[key] for key in ("contractId", "programFingerprint", "programFileCount", "requiredKinds")),
            "Actual packaged application contract differs from compiled-table acceptance")
    return {**value, "scope": "Real byte-bound packaged client contract and Runtime roots; no backend/UI/profile writes",
            "clientSource": "Frozen client bytes already matched to actual ASAR by verify_sources",
            "programRoots": "Actual extracted native program"}


def verify_sources(*, app, version, program_files, program_map, members, client, staged, trust, installer_format="legacy-nsis-v1"):
    require(installer_format in INSTALLER_FORMATS, "Unsupported native installer format")
    names = client_manifest(client)
    own = {name for name in members if not name.startswith("node_modules/")}
    require(own == set(names), "ASAR application member set differs from frozen client manifest")
    expected_client = {}
    for name in names:
        physical(client / name)
        expected_client[name] = legacy.digest(client / name)
        if name != "package.json":
            require(members[name]["sha256"] == expected_client[name], "ASAR source differs from frozen client: " + name)
    require(not any(value["head"][:2] == b"MZ" for value in members.values()), "ASAR contains a native image")
    package = members["package.json"]["json"]
    original = json.loads((client / "package.json").read_text(encoding="utf-8"))
    require(package.get("version") == version == original.get("version") and package.get("name") == app + "-desktop"
            and package.get("main") == "main.cjs" and package.get("dependencies") == original.get("dependencies"), "Packaged application identity/dependencies differ")
    config = package.get("desktopAppConfig") or {}
    require(config.get("appId") == app and config.get("desktopUninstaller") is False
            and config.get("windowsPublisherName") == "CN=Melange Systems Desktop Release (self-signed)", "Native application configuration differs")
    update = config.get("desktopUpdateSource") or {}
    require(update.get("provider") == "github" and str(update.get("repository", "")).lower() == REPOSITORIES[app]
            and update.get("distribution", "native") == "native", "Native GitHub receiver configuration differs")
    require(config.get("desktopAccessTrust") == json.loads(trust.read_text(encoding="utf-8")), "Packaged public trust differs from frozen descriptor")
    require(re.search(r"const\s+PUBLISHER_PIN_ENFORCE\s*=\s*true\s*;", (client / "native-signature.cjs").read_text()), "Publisher pin is not enforced")
    build_names = list(BUILTIN_BUILD_INPUTS if installer_format == "builtin-nsis-v1" else BUILD_INPUTS)
    # Historical direct builds predate the production wrapper. Bind that wrapper
    # whenever the frozen source's production entry point invokes it.
    if installer_format == "builtin-nsis-v1" and "build-native.cjs" in str(original.get("scripts", {}).get("build", "")):
        build_names.append("build-native.cjs")
    build_inputs = {name: snapshot(client / name)[-1] for name in build_names}
    certificate = "melange-systems-desktop-release.cer"
    cert_info = physical(client / certificate)
    require(program_map.get("resources/" + certificate) == {"sha256": legacy.digest(client / certificate), "size": cert_info.st_size},
            "Packaged public release certificate differs from frozen client")
    staged_files, _, staged_map = scan(staged)
    staged_inventory_path = staged.parent / "source-inventory.json"
    physical(staged_inventory_path)
    staged_inventory = json.loads(staged_inventory_path.read_text(encoding="utf-8"))
    require(isinstance(staged_inventory, list) and sorted(staged_inventory) == sorted(staged_files), "Gated source inventory differs from its actual files")
    prefix = "resources/runtime/" + app + "/"
    actual_sources = {name[len(prefix + "sources/"):]: value for name, value in program_map.items() if name.startswith(prefix + "sources/")}
    same_tree(actual_sources, staged_map, "Gated runtime sources")
    inventory = json.loads(program_files[prefix + "source-inventory.json"].read_text(encoding="utf-8"))
    require(isinstance(inventory, list) and sorted(inventory) == sorted(staged_files), "Packaged source inventory differs from gated sources")
    packaging = client.parent / "packaging"
    boot = literal_assignment(packaging / "build_runtime.py", "BOOTSTRAP_FILES")
    expected_boot = {}
    for name in boot:
        info = physical(packaging / name)
        expected_boot[name] = {"sha256": legacy.digest(packaging / name), "size": info.st_size}
    actual_boot = {name[len(prefix + "bootstrap/"):]: value for name, value in program_map.items() if name.startswith(prefix + "bootstrap/")}
    same_tree(actual_boot, expected_boot, "Frozen runtime bootstrap")
    module_table = {"status": "not-applicable", "reason": "district-application-or-legacy-client"}
    if app in ("melange", "mentat"):
        name = "module-application-inventory.cjs"
        python_name = prefix + "bootstrap/module_application_inventory.py"
        declares_modules = name in members or python_name in program_files
        needs_modules = config.get("desktopAccessMode") == "standalone" and config.get("desktopAuthentication") == "windows"
        if declares_modules or needs_modules:
            require(name in members and python_name in program_files,
                    "Packaged application is missing its compiled module declarations")
            javascript = asar_member_bytes(program_files["resources/app.asar"], name)
            require(hashlib.sha256(javascript).hexdigest() == members[name]["sha256"],
                    "Compiled ASAR module declaration changed during inspection")
            module_table = compiled_module_tables(app=app, javascript=javascript,
                python=program_files[python_name].read_bytes(), program_map=program_map, config=config)
    return {"clientFiles": expected_client, "runtimeSources": staged_map, "runtimeBootstrap": expected_boot,
            "nativeBuildInputs": build_inputs, "publicReleaseCertificate": program_map["resources/" + certificate],
            "compiledModuleTable": module_table,
            "sourceManifests": {"releaseFiles": legacy.digest(client / "release-files.cjs"),
                                "buildRuntime": legacy.digest(packaging / "build_runtime.py"),
                                "stagedSources": legacy.digest(staged_inventory_path)}}, package


def native_census(*, installer, program_directory, app_files, app_pes, app_map, nsis_files, nsis_pes, nsis_map, receipt,
                  installer_format="legacy-nsis-v1", reference_files=None):
    """Bind every header-detected native file to fresh build signature evidence."""
    require(installer_format in INSTALLER_FORMATS, "Unsupported native installer format")
    current = receipt.get("currentFiles") or []
    require(len({identity(row["path"]) for row in current}) == len(current), "Duplicate current signature records")
    expected = {}
    for row in current:
        file = Path(row["path"])
        if identity(file) == identity(installer):
            continue
        if "payloadRelativePath" in row:
            rel = row["payloadRelativePath"]
            require(isinstance(rel, str) and legacy.safe_name(rel) == rel, "Invalid payload relative signature path")
        else:
            try:
                rel = file.relative_to(program_directory).as_posix()
            except ValueError as error:
                raise Refused("Current signature row escapes signed program tree") from error
        source = (reference_files or {}).get(rel, Path(program_directory) / rel)
        require(identity(file) == identity(source), "Current signature row does not identify its actual reference input")
        require(rel not in expected, "Duplicate native payload signature mapping")
        require(rel in app_pes and row.get("sha256") == app_map[rel]["sha256"], "Current program signature bytes/census differ: " + rel)
        expected[rel] = row
    require(set(expected) == app_pes, "Native header census differs from complete build signature receipt")
    if installer_format == "builtin-nsis-v1":
        require(receipt.get("installerFormat") == installer_format and receipt.get("installerPlugins") == [],
                "Build signature receipt must declare the zero-plugin installer format")
        require(nsis_map == app_map and nsis_pes == app_pes and set(nsis_files) == set(app_files)
                and not any(part.casefold() == "$pluginsdir" for name in nsis_files for part in name.split("/")),
                "Direct NSIS census differs from complete program or contains installer plugins")
        plugins = set()
    else:
        plugins = {"$PLUGINSDIR/" + name for name in NATIVE_PLUGINS}
        require(nsis_pes == plugins, "Outer NSIS native census differs from the exact seven reviewed native plugins")
    items = {"installer": installer, **{"app/" + rel: app_files[rel] for rel in sorted(app_pes)},
             **{"plugin/" + rel: nsis_files[rel] for rel in sorted(plugins)}}
    history = receipt.get("files") or []
    for rel, row in expected.items():
        require(row.get("status") == "Valid", "Build recorded an invalid native signature")
        if row.get("thumbprint") != legacy.PIN:
            prior = [old for old in history if identity(old.get("path", "")) == identity(row["path"])]
            require(prior and all(old.get("status") == "Valid" and old.get("thumbprint") == row.get("thumbprint")
                and old.get("preserved") is True and old.get("signed") is False
                and old.get("beforeSha256") == old.get("sha256") == row["sha256"] for old in prior),
                "Original vendor image was not preserved byte-for-byte: " + rel)
    for rel in plugins:
        require(any(Path(row.get("path", "")).name.casefold() == Path(rel).name.casefold()
                    and row.get("sha256") == nsis_map[rel]["sha256"] and row.get("status") == "Valid"
                    and row.get("thumbprint") == legacy.PIN for row in history), "NSIS plugin differs from signed private toolset: " + rel)
    return items, expected


def check_verdicts(rows, items, expected, app_map, nsis_map, app, version):
    require(set(rows) == set(items), "Fresh native signature census is incomplete")
    for key, row in rows.items():
        require(row.get("status") == "Valid", "Native signature is not Valid: " + key)
        if key.startswith("app/"):
            rel = key[4:]
            require(row.get("sha256") == app_map[rel]["sha256"] and row.get("thumbprint") == expected[rel].get("thumbprint"), "Native file or signer changed: " + key)
            if row.get("thumbprint") == legacy.PIN:
                legacy.required_owner(row)
        else:
            legacy.required_owner(row)
            if key.startswith("plugin/"):
                require(row.get("sha256") == nsis_map[key[7:]]["sha256"], "NSIS plugin bytes changed during signature inspection")
        if key in ("installer", "app/" + PRODUCTS[app] + ".exe", "app/resources/elevate.exe"):
            legacy.required_owner(row)
        if key in ("installer", "app/" + PRODUCTS[app] + ".exe"):
            require(row.get("fileVersion") in (version, version + ".0") and row.get("productVersion") in (version, version + ".0"), "Native executable version differs")


def verify(args):
    require(os.name == "nt", "Actual native release verification requires Windows")
    installer_format = getattr(args, "installer_format", "legacy-nsis-v1")
    require(installer_format in INSTALLER_FORMATS, "Unsupported native installer format")
    reserve = free_floor_gib(args.free_floor_gib) * GIB
    for sha in (args.client_commit, args.source_commit):
        require(re.fullmatch(r"[0-9a-f]{40}", sha), "Frozen commit identity required")
    require(re.fullmatch(r"\d+\.\d+\.\d+", args.version), "Stable native version required")
    output, installer = Path(args.output).absolute(), Path(args.installer).absolute()
    program, client, staged = (Path(value).absolute() for value in (args.program_directory, args.client, args.staged_sources))
    overlays = {"executable": getattr(args, "app_executable", None), "asar": getattr(args, "app_asar", None)}
    source_overlay = getattr(args, "source_overlay", None)
    require(installer_format == "builtin-nsis-v1" or not (any(overlays.values()) or source_overlay), "Reference overlays require the built-in installer format")
    if source_overlay:
        overlay_root = Path(source_overlay).absolute().parent
        require(not overlay_root.is_relative_to(program) and not program.is_relative_to(overlay_root),
                "Source overlay must be outside the retained base")
    seven = Path(args.seven_zip).resolve(strict=True)  # known tool cache may have a legitimate parent redirect
    tool_inputs = [seven]
    if seven.with_suffix(".dll").exists():
        tool_inputs.append(seven.with_suffix(".dll"))
    # Reject the limited7za reader before any large program scan or extraction.
    with contextlib.ExitStack() as locks:
        for file in tool_inputs:
            locks.enter_context(locked_input(file))
        reader = reader_capabilities(seven)
    trust, receipt_path = Path(args.trust_descriptor).absolute(), Path(args.signing_receipt).absolute()
    for folder in (program, client, staged, output.parent):
        physical(folder, True)
    if args.source:
        physical(Path(args.source), True)
    require(not output.exists(), "Inspection output must be fresh")
    output.mkdir()
    paths = [installer, receipt_path, trust, *tool_inputs, Path(__file__), HERE / "verify_signed_release.py", HERE / "no_uninstaller_contract.py",
             *(Path(value).absolute() for value in overlays.values() if value)]
    if source_overlay:
        paths.append(staged.parent / "source-provenance.json")
        if getattr(args, "source_origin_proof", None):
            paths.append(Path(args.source_origin_proof).absolute())
    inputs = {str(file): snapshot(file) for file in paths}
    reference_files, reference_pes, reference = scan(program)
    original_reference = dict(reference)
    reference_files, reference_pes, reference = reference_overlays(reference_files, reference_pes, reference, args.app, **overlays)
    reference_files, reference_pes, reference, source_inputs, source_binding = source_overlays(
        reference_files, reference_pes, reference, args.app, args.version, source_overlay, args.client_commit, args.source_commit)
    inputs.update(source_inputs)
    report = {"schemaVersion": 1, "status": "failed", "appId": args.app, "version": args.version,
              "clientCommit": args.client_commit, "sourceCommit": args.source_commit,
              "originalSourceExport": args.source,
              "frozenExportBinding": "exports and gated stage supplied by the release controller; actual packaged bytes compared independently",
              "installerSha256": inputs[str(installer)][-1], "inputs": {name: row[-1] for name, row in inputs.items()},
              "freeFloorGiB": args.free_floor_gib,
              "archiveReader": reader, "installerFormat": installer_format,
              "referenceOverlays": {name: str(Path(value).absolute()) for name, value in overlays.items() if value},
              "sourceOverlay": source_binding,
              "runtimeExecution": "not performed", "recipientPolicyAcceptance": "not tested"}
    with locked_input(installer), contextlib.ExitStack() as locks:
        for file in tool_inputs:
            locks.enter_context(locked_input(file))
        preflight = output / "preflight"
        preflight.mkdir()
        legacy.required_owner(legacy.signatures({"installer": installer}, preflight, preserve_execution_policy=True)["installer"])
        if installer_format == "builtin-nsis-v1":
            # The container directly holds the program. Extract/census once;
            # there are no install-time plugin DLLs or nested payload archive.
            outer = extracted = output / "app"
            used = extract(seven, installer, extracted, MAX_EXPANDED, reserve=reserve,
                           archive_format="Nsis", expected_files=reference)
            app_files, app_pes, app_map = scan(extracted)
            nsis_files, nsis_pes, nsis_map = app_files, app_pes, app_map
        else:
            outer, extracted = output / "nsis", output / "app"
            used = extract(seven, installer, outer, MAX_EXPANDED, reserve=reserve, archive_format="Nsis")
            archives = list(outer.rglob("app-64.7z"))
            require(len(archives) == 1, "Exactly one native x64 application payload required")
            used += extract(seven, archives[0], extracted, MAX_EXPANDED - used, reserve=reserve)
            app_files, app_pes, app_map = scan(extracted)
            nsis_files, nsis_pes, nsis_map = scan(outer)
        same_tree(app_map, reference, "Complete signed application")
        require(app_pes == reference_pes, "Native classification differs from signed program tree")
        asar_header_hash, members = legacy.asar(app_files["resources/app.asar"])
        verify_asar_integrity(app_files[PRODUCTS[args.app] + ".exe"], asar_header_hash)
        source_evidence, package = verify_sources(app=args.app, version=args.version, program_files=app_files,
            program_map=app_map, members=members, client=client, staged=staged, trust=trust, installer_format=installer_format)
        provenance_binding = source_provenance(app=args.app, version=args.version, client_commit=args.client_commit,
            source_commit=args.source_commit, staged=staged, program_map=app_map, original_reference=original_reference,
            origin_proof=getattr(args, "source_origin_proof", None)) if source_overlay else None
        absence = contract.verify_without_uninstaller(installer=installer, package_json=package,
            nsis_files=nsis_files, app_files=app_files, asar_members=members, signing_receipt=receipt_path)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        items, expected = native_census(installer=installer, program_directory=program, app_files=app_files,
            app_pes=app_pes, app_map=app_map, nsis_files=nsis_files, nsis_pes=nsis_pes, nsis_map=nsis_map, receipt=receipt,
            installer_format=installer_format, reference_files=reference_files)
        native = output / "native"
        native.mkdir()
        print(json.dumps({"phase": "complete-native-signature-census", "appId": args.app, "files": len(items)}), flush=True)
        rows = legacy.signatures(items, native, preserve_execution_policy=True)
        check_verdicts(rows, items, expected, app_map, nsis_map, args.app, args.version)
        module_acceptance = None
        compiled = source_evidence["compiledModuleTable"]
        if compiled["status"] == "passed":
            print(json.dumps({"phase": "actual-compiled-module-contract", "appId": args.app,
                              "publicDataMode": compiled["publicDataMode"]}), flush=True)
            module_acceptance = compiled_module_runtime(app=args.app, client=client,
                extracted=extracted, expected=compiled)
        require(rows["installer"]["sha256"] == report["installerSha256"], "Outer installer changed during signature verification")
        same_tree(scan(extracted)[2], app_map, "Final extracted application")
        if outer != extracted:
            same_tree(scan(outer)[2], nsis_map, "Final NSIS container")
        same_tree(scan(program)[2], original_reference, "Final signed program input")
        if source_overlay:
            _, _, final_reference, final_source_inputs, final_binding = source_overlays(
                reference_files, reference_pes, reference, args.app, args.version, source_overlay, args.client_commit, args.source_commit)
            require(final_reference == reference and final_source_inputs == source_inputs and final_binding == source_binding,
                    "Source overlay changed during verification")
        final_sources, _ = verify_sources(app=args.app, version=args.version, program_files=app_files,
            program_map=app_map, members=legacy.asar(app_files["resources/app.asar"])[1], client=client, staged=staged, trust=trust,
            installer_format=installer_format)
        require(final_sources == source_evidence, "Frozen source inputs changed during verification")
        if source_overlay:
            require(source_provenance(app=args.app, version=args.version, client_commit=args.client_commit,
                source_commit=args.source_commit, staged=staged, program_map=app_map, original_reference=original_reference,
                origin_proof=getattr(args, "source_origin_proof", None)) == provenance_binding,
                "Source provenance changed during verification")
        for file, before in inputs.items():
            require(snapshot(file) == before, "Verification input changed: " + file)
        plugins = [] if installer_format == "builtin-nsis-v1" else sorted(NATIVE_PLUGINS)
        report.update(status="passed", payloadFileCount=len(app_files), payloadPeCount=len(app_pes),
            nsisPluginCount=len(plugins), completeNativeCount=len(items), extractedBytes=used,
            nsisPluginContract={"format": installer_format, "mode": "builtin-per-user-without-uninstaller" if not plugins else "assisted-per-user-without-uninstaller", "files": plugins},
            embeddedAsarIntegrityVerified=True, asarHeaderSha256=asar_header_hash,
            completeNativeCensus=True, desktopUninstaller=False,
            noUninstaller=absence, sourceEvidence=source_evidence, applicationFiles=app_map, nsisFiles=nsis_map,
            compiledModuleAcceptance=module_acceptance,
            sourceProvenance=provenance_binding,
            nativeSignatureRows=rows, inputFilesUnchanged=True)
    return report


def free_floor_gib(value):
    # Per-run desktop workspace bound, not the unrelated DE-076 data transaction.
    value = int(value)
    if value < 16:
        raise argparse.ArgumentTypeError("--free-floor-gib must be at least 16")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", choices=PRODUCTS, required=True)
    for name in ("version", "installer", "signing-receipt", "program-directory", "client", "staged-sources",
                 "client-commit", "source-commit", "trust-descriptor", "seven-zip", "output", "report"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--source", help="Original frozen source export (provenance; transformed bytes use --staged-sources)")
    parser.add_argument("--app-executable", help="Explicit signed main-executable overlay used by the built-in installer")
    parser.add_argument("--app-asar", help="Explicit ASAR overlay used by the built-in installer")
    parser.add_argument("--source-overlay", help="Closed, replacement-only source/bootstrap overlay manifest; vendor/native changes are forbidden")
    parser.add_argument("--source-origin-proof", help="Independent composite origin proof required for a Terrier source overlay")
    parser.add_argument("--installer-format", choices=INSTALLER_FORMATS, default="legacy-nsis-v1",
                        help="explicit native payload layout; builtin layout forbids external installer plugins")
    parser.add_argument("--free-floor-gib", type=free_floor_gib, default=32,
                        help="desktop workspace reserve in GiB (at least 16; default 32)")
    args = parser.parse_args(argv)
    report_path = Path(args.report).absolute()
    physical(report_path.parent, True)
    require(not report_path.exists(), "Verification report already exists")
    try:
        report = verify(args)
    except Exception as error:
        report = {"schemaVersion": 1, "status": "failed", "appId": args.app, "version": args.version,
                  "error": type(error).__name__ + ": " + str(error), "inspectionRetained": args.output}
    report["checkedUtc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "report": str(report_path), "error": report.get("error")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
