"""Verify a signed Melange desktop release installer; never execute installer or payload code.

Derived from the 1.0.16 signing-only verifier (verify_terrier_signed_artifact.py, sha256
1ee631e8...). It keeps that verifier's 15 gate names. 1.0.17 changes shipped code, so the
four byte-identity gates are source-bound here instead:

- A non-PE payload file (and every app.asar member) that differs from the pinned 1.0.16
  baseline must map to a path in `git diff --name-status BASE_PIN HEAD`, derived from git at
  verification time, and its bytes must equal that path at HEAD (deleted paths must be absent).
- Every payload file that maps to a repository path must equal HEAD, changed or not.
- The only other permitted differences are build outputs whose SHA-256 is bound in the build
  receipt (app.asar, the runtime source inventory) and the asar package.json version.
- PE files are compared with their Authenticode table removed; the main executable may change
  only its version strings and its embedded asar integrity hash. Vendor PEs stay byte-identical.

Any other difference fails. Standard library only; run with `python -I`.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile

PIN = "0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30"
APP, APP_NAME = "melange", "Melange"
OLD, NEW = "1.0.16", "1.0.17"
BASE_SHA = "58bc455db6cdfa785d252cdfcdc8ac7b5cd0ad8af0aed8ee78fac1507846a9fc"
BASE_PIN = "46c22a9b4b7020d5db50d7c433eb1d4114910334"
EXPECTED_PES = 545
PLUGINS = {"System.dll", "UAC.dll", "StdUtils.dll", "nsDialogs.dll", "nsExec.dll", "nsis7z.dll", "WinShell.dll"}
MAX_EXPANDED = 8 * 1024 ** 3
RUNTIME = "resources/runtime/" + APP + "/"
# Packaging layout (builder.cjs extraResources, build_runtime.py): payload prefix -> repository prefix.
SOURCE_LAYOUT = ((RUNTIME + "sources/", ""), (RUNTIME + "bootstrap/", "ops/desktop/packaging/"),
                 ("resources/melange-systems-desktop-release.cer", "ops/desktop/client/melange-systems-desktop-release.cer"))
ASAR_ROOT = "ops/desktop/client/"
SOURCE_INVENTORY = RUNTIME + "source-inventory.json"
BUILD_OUTPUTS = {"resources/app.asar", SOURCE_INVENTORY}
GATES = ("pinnedBaselineInstallerMatches", "completedBuildInputsBound", "completePayloadFileSetMatches",
         "allPayloadPeSignaturesValid", "allPreviouslyUnsignedPeApprovedAndTimestamped",
         "previouslyValidVendorFilesByteIdentical", "peOnlyPermittedSignatureAndMainResourceChanges",
         "mainVersionAndAsarIntegrityMatch", "asarMembersByteIdenticalExceptPackageVersion",
         "runtimeSourceFrontendNonPeByteIdentical", "sevenNsisPluginsApprovedTimestampedAndContentBound",
         "mainElevateUninstallerOuterApprovedAndTimestamped", "generatedInstallerVersionsMatch",
         "otherNsisMembersByteIdentical", "inputsUnchangedDuringInspection")
SOURCE_BOUND = "byte-identical to the 1.0.16 baseline, except members that map to a path in git diff BASE_PIN..HEAD and equal HEAD, or build outputs whose SHA-256 is bound in the build receipt"
GATE_SEMANTICS = {
    "asarMembersByteIdenticalExceptPackageVersion": "every asar member " + SOURCE_BOUND + "; package.json may change only its version and add desktopAppConfig keys named in HEAD builder.cjs",
    "runtimeSourceFrontendNonPeByteIdentical": "every non-PE payload file " + SOURCE_BOUND + "; every payload file that maps to a repository path equals HEAD",
    "otherNsisMembersByteIdentical": "every other outer NSIS member " + SOURCE_BOUND,
    "peOnlyPermittedSignatureAndMainResourceChanges": "app-owned PEs equal the baseline with the Authenticode table removed, except the main executable's version strings and asar integrity hash; vendor PEs byte-identical",
}


class Refused(ValueError):
    pass


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def run(argv, timeout=300, env=None):
    result = subprocess.run([str(x) for x in argv], capture_output=True, timeout=timeout, env=env)
    if result.returncode:
        raise Refused("Inspection command failed: " + Path(str(argv[0])).name + ": " + result.stderr.decode("utf-8", "replace")[-1500:])
    return result.stdout


# ---- git-derived allow-list -------------------------------------------------------------

def git(repo, *args):
    return run(["git", "-C", repo, "-c", "core.autocrlf=false", *args], timeout=600)


def resolve_commit(repo, ref):
    return git(repo, "rev-parse", "--verify", ref + "^{commit}").decode().strip()


def changed_paths(repo, base, head):
    """{path: status} from `git diff --no-renames --name-status -z base head`; never hand-written."""
    fields = git(repo, "diff", "--no-renames", "--name-status", "-z", base, head).decode("utf-8").split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    if len(fields) % 2:
        raise Refused("Unparseable git diff output")
    result = {}
    for status, path in zip(fields[0::2], fields[1::2]):
        if status not in ("A", "M", "D", "T"):
            raise Refused("Unexpected git diff status " + status + " for " + path)
        result[path] = status
    return result


def head_contents(repo, head):
    """{path: sha256} of every regular file at head, exported the way the release source is."""
    raw = git(repo, "archive", "--format=tar", head)
    result = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive:
            if member.isfile():
                result[member.name] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    return result


def payload_source(rel):
    for prefix, repo in SOURCE_LAYOUT:
        if prefix.endswith("/") and rel.startswith(prefix):
            return repo + rel[len(prefix):]
        if rel == prefix:
            return repo
    return None


def asar_source(member):
    return None if member == "package.json" or member.startswith("node_modules/") else ASAR_ROOT + member


def source_bound(old, new, changes, head, source_of, bound=None, label="payload"):
    """Compare {name: sha256} maps; return the explained differences or raise.

    A difference passes only as a bound build output (exact hash) or as a source path in
    `changes` whose candidate bytes equal HEAD (or are absent when the path was deleted).
    Every candidate file with a source path must equal HEAD whether or not it changed.
    """
    bound = bound or {}
    rows = []
    for name in sorted(new):
        source = source_of(name)
        if source is not None and name not in bound and new[name] != head.get(source):
            raise Refused("Packaged " + label + " file does not equal release HEAD: " + name)
    for name in sorted(old.keys() | new.keys()):
        before, after = old.get(name), new.get(name)
        if before == after:
            continue
        if name in bound:
            if after is None or after != bound[name]:
                raise Refused("Build output differs from its bound hash: " + name)
            rows.append({"path": name, "basis": "bound-build-output", "before": before, "after": after})
            continue
        source = source_of(name)
        status = changes.get(source) if source is not None else None
        if status is None:
            raise Refused("Unexplained " + label + " difference (not in git diff): " + name)
        if (after is None) != (status == "D"):
            raise Refused("Payload presence disagrees with git status " + status + ": " + name)
        rows.append({"path": name, "basis": "git-diff", "source": source, "gitStatus": status, "before": before, "after": after})
    return rows


# ---- extraction ---------------------------------------------------------------------------

def safe_name(name):
    value = name.replace("\\", "/")
    parts = value.split("/")
    if not value or value.startswith("/") or ":" in value or any(x in ("", ".", "..") for x in parts):
        raise Refused("Unsafe archive member")
    return value


def extract(seven, archive, output, budget):
    listing = run([seven, "l", "-slt", "-ba", archive]).decode("utf-8", "replace").replace("\r\n", "\n")
    total, seen, files = 0, set(), []
    for block in listing.strip().split("\n\n"):
        row = dict(line.split(" = ", 1) for line in block.splitlines() if " = " in line)
        if "Path" not in row:
            continue
        rel = safe_name(row["Path"])
        if rel.casefold() in seen or any(k in row for k in ("Symbolic Link", "Hard Link")):
            raise Refused("Duplicate or linked archive member")
        seen.add(rel.casefold())
        if row.get("Folder") == "+" or row.get("Attributes", "").startswith("D"):
            continue
        size = int(row.get("Size", "0") or "0")
        if size < 0:
            raise Refused("Negative member size")
        total += size
        files.append(rel)
    if total > budget or shutil.disk_usage(output.parent).free < total + 256 * 1024 ** 2:
        raise Refused("Insufficient bounded extraction allowance")
    output.mkdir()
    run([seven, "x", archive, "-o" + str(output), "-y"], timeout=3600)
    actual = tree(output)
    if set(actual) != set(files):
        raise Refused("Extracted paths differ from inspected archive listing")
    actual_total = sum(p.stat().st_size for p in actual.values())
    if actual_total > budget:
        raise Refused("Extracted bytes exceed allowance")
    return actual_total


def tree(root):
    result = {}
    for path in root.rglob("*"):
        info = path.lstat()
        if path.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise Refused("Linked extracted path")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path
    if len({x.casefold() for x in result}) != len(result):
        raise Refused("Case-colliding extracted paths")
    return result


def inspect_files(files):
    """Classify (PE by header, not extension) and hash each file in one open."""
    pes, hashes = set(), {}
    for rel, path in files.items():
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            head = stream.read(4096)
            hasher = hashlib.sha256(head)
            for block in iter(lambda: stream.read(1024 ** 2), b""):
                hasher.update(block)
            if head[:2] == b"MZ" and len(head) >= 64:
                offset = struct.unpack_from("<I", head, 60)[0]
                if offset + 4 <= len(head):
                    signature = head[offset:offset + 4]
                else:
                    stream.seek(offset)
                    signature = stream.read(4)
                if signature == b"PE\0\0":
                    pes.add(rel)
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise Refused("File changed while inspecting: " + rel)
            hashes[rel] = hasher.hexdigest()
    return pes, hashes


# ---- PE comparison ------------------------------------------------------------------------

def pe_layout(raw):
    if raw[:2] != b"MZ" or len(raw) < 64:
        raise Refused("Expected PE image")
    pe = struct.unpack_from("<I", raw, 60)[0]
    if raw[pe:pe + 4] != b"PE\0\0":
        raise Refused("Invalid PE signature")
    optional = pe + 24
    magic = struct.unpack_from("<H", raw, optional)[0]
    if magic not in (0x10B, 0x20B):
        raise Refused("Unknown PE optional header")
    dd = optional + {0x10B: 96, 0x20B: 112}[magic]
    security, checksum = dd + 32, optional + 64
    count = struct.unpack_from("<H", raw, pe + 6)[0]
    section_start = optional + struct.unpack_from("<H", raw, pe + 20)[0]
    sections = []
    for i in range(count):
        at = section_start + i * 40
        virtual_size, rva, size, offset = struct.unpack_from("<IIII", raw, at + 8)
        sections.append((rva, virtual_size, offset, size))
    return checksum, security, dd, sections


def unsigned_body(raw):
    """Bytes before an appended Authenticode table (the whole file when unsigned)."""
    _, security, _, _ = pe_layout(raw)
    table, size = struct.unpack_from("<II", raw, security)
    if (table, size) == (0, 0):
        return raw
    if size < 8 or table + size != len(raw):
        raise Refused("Signature is not an appended certificate table")
    return raw[:table]


def resources(raw):
    _, _, dd, sections = pe_layout(raw)
    def offset(rva):
        for va, vs, ptr, size in sections:
            if va <= rva < va + max(vs, size):
                return ptr + rva - va
        raise Refused("Invalid resource RVA")
    resource_rva = struct.unpack_from("<I", raw, dd + 16)[0]
    if not resource_rva:
        return {}
    root, result, visited = offset(resource_rva), {}, set()
    def visit(at, keys):
        if at in visited or len(keys) > 4:
            raise Refused("Cyclic PE resource directory")
        visited.add(at)
        named, ids = struct.unpack_from("<HH", raw, root + at + 12)
        for i in range(named + ids):
            name, target = struct.unpack_from("<II", raw, root + at + 16 + i * 8)
            if name >> 31:
                pos = root + (name & 0x7fffffff)
                length = struct.unpack_from("<H", raw, pos)[0]
                key = raw[pos + 2:pos + 2 + length * 2].decode("utf-16le")
            else:
                key = name
            path = (*keys, key)
            if target >> 31:
                visit(target & 0x7fffffff, path)
            else:
                rva, length = struct.unpack_from("<II", raw, root + target)
                pos = offset(rva)
                if pos + length > len(raw):
                    raise Refused("Resource outside file")
                result[path] = (pos, raw[pos:pos + length])
    visit(0, ())
    return result


def version_words(version):
    parts = [int(x) for x in version.split(".")]
    parts += [0] * (4 - len(parts))
    if len(parts) != 4 or any(not 0 <= x <= 65535 for x in parts):
        raise Refused("Invalid fixed version")
    return (parts[0] << 16) | parts[1], (parts[2] << 16) | parts[3]


def version_resource(old):
    """Only the documented version strings and the four fixed-version DWORDs."""
    result = bytearray(old.replace(OLD.encode("utf-16le"), NEW.encode("utf-16le")))
    marker = b"\xbd\x04\xef\xfe"
    at = old.find(marker)
    if at < 0 or old.find(marker, at + 1) >= 0:
        raise Refused("Missing unique fixed version record")
    if struct.unpack_from("<IIII", old, at + 8) != (*version_words(OLD), *version_words(OLD)):
        raise Refused("Unexpected baseline main executable version")
    struct.pack_into("<IIII", result, at + 8, *version_words(NEW), *version_words(NEW))
    return bytes(result)


def compare_signed_pe(old_path, new_path, main=False, old_asar=None, new_asar=None):
    """Candidate must be the baseline's unsigned body plus a fresh appended signature."""
    old = unsigned_body(old_path.read_bytes())
    new = new_path.read_bytes()
    c, s, _, _ = pe_layout(old)
    nc, ns, _, _ = pe_layout(new)
    if (c, s) != (nc, ns):
        raise Refused("PE header layout changed: " + str(new_path))
    table, size = struct.unpack_from("<II", new, s)
    if not (len(old) <= table < len(old) + 8 and size >= 8 and table + size == len(new)):
        raise Refused("Signature is not an appended certificate table: " + str(new_path))
    expected = bytearray(old)
    if main:
        old_res, new_res = resources(old), resources(new[:table])
        if old_res.keys() != new_res.keys():
            raise Refused("Main resource set changed")
        version_count = integrity_count = 0
        for key, (pos, payload) in old_res.items():
            new_pos, new_payload = new_res[key]
            if key[0] == 16:
                permitted = version_resource(payload)
                version_count += 1
            elif key[:2] == ("INTEGRITY", "ELECTRONASAR"):
                before = [{"file": "resources\\app.asar", "alg": "SHA256", "value": old_asar}]
                after = [{"file": "resources\\app.asar", "alg": "SHA256", "value": new_asar}]
                if json.loads(payload) != before or json.loads(new_payload) != after:
                    raise Refused("Embedded ASAR integrity is not bound to inspected archive")
                permitted = payload.replace(old_asar.encode(), new_asar.encode())
                integrity_count += 1
            else:
                permitted = payload
            if pos != new_pos or len(payload) != len(new_payload) or new_payload != permitted:
                raise Refused("Unapproved main PE resource change: " + str(key))
            expected[pos:pos + len(payload)] = permitted
        if version_count != 1 or integrity_count != 1:
            raise Refused("Main version/integrity resource missing")
    expected[c:c + 4] = new[c:c + 4]
    expected[s:s + 8] = new[s:s + 8]
    for offset in range(0, len(old), 1024 ** 2):
        before, after = expected[offset:offset + 1024 ** 2], new[offset:min(offset + 1024 ** 2, len(old))]
        if before != after:
            first = next(i for i, pair in enumerate(zip(before, after)) if pair[0] != pair[1])
            raise Refused("PE content changed outside approved resource/signature bytes at offset " + str(offset + first) + ": " + str(new_path))
    if new[len(old):table].strip(b"\0"):
        raise Refused("Nonzero padding before appended PE signature")
    return "authenticode-plus-version-and-asar-integrity" if main else "authenticode-only"


# ---- asar ---------------------------------------------------------------------------------

def asar(path):
    with path.open("rb") as stream:
        lead = stream.read(16)
        first, header_size, _, json_size = struct.unpack("<IIII", lead)
        if first != 4 or not 0 < json_size <= 16 * 1024 ** 2 or header_size < json_size + 8:
            raise Refused("Unsupported ASAR header")
        raw = stream.read(json_size)
        header = json.loads(raw)
        base = 8 + header_size
        result = {}
        def walk(node, prefix=""):
            for name, row in node["files"].items():
                rel = safe_name(prefix + name)
                if "files" in row:
                    walk(row, rel + "/")
                    continue
                if row.get("link") or row.get("unpacked"):
                    raise Refused("Unexpected linked/unpacked ASAR entry")
                offset, size = int(row["offset"]), row["size"]
                if offset < 0 or type(size) is not int or size < 0 or base + offset + size > path.stat().st_size:
                    raise Refused("ASAR entry outside file")
                stream.seek(base + offset)
                data = stream.read(size)
                result[rel] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": size, "head": data[:4]}
                if rel == "package.json":
                    result[rel]["json"] = json.loads(data)
        walk(header)
    return hashlib.sha256(raw).hexdigest(), result


def asar_config_keys(builder_text):
    """Identifiers inside the `desktopAppConfig:{...}` literal of HEAD builder.cjs."""
    at = builder_text.find("desktopAppConfig:{")
    end = builder_text.find("}", at)
    if at < 0 or end < 0:
        raise Refused("desktopAppConfig literal not found in builder.cjs")
    body = builder_text[at + len("desktopAppConfig:{"):end]
    return {part.split(":")[0].strip() for part in body.split(",") if part.strip()}


def check_package(old, new, config_keys):
    if old.get("version") != OLD or new.get("version") != NEW:
        raise Refused("Unexpected package versions")
    if {k: v for k, v in old.items() if k not in ("version", "desktopAppConfig")} != {k: v for k, v in new.items() if k not in ("version", "desktopAppConfig")}:
        raise Refused("Package metadata changed beyond version and application configuration")
    before, after = old.get("desktopAppConfig") or {}, new.get("desktopAppConfig") or {}
    if any(after.get(k, object()) != v for k, v in before.items()):
        raise Refused("Existing desktopAppConfig values changed")
    added = sorted(after.keys() - before.keys())
    if not set(added) <= config_keys:
        raise Refused("desktopAppConfig keys not named in HEAD builder.cjs: " + ", ".join(sorted(set(added) - config_keys)))
    return {k: after[k] for k in added}


# ---- Authenticode -------------------------------------------------------------------------

PS = r'''param([string]$InputList,[string]$OutputFile)
$ErrorActionPreference='Stop'
$items=Get-Content -LiteralPath $InputList -Raw | ConvertFrom-Json
$rows=foreach($item in $items){
 $sig=Get-AuthenticodeSignature -LiteralPath $item.path
 $file=Get-Item -LiteralPath $item.path
 [pscustomobject]@{id=$item.id;bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $item.path -Algorithm SHA256).Hash.ToLowerInvariant();status=[string]$sig.Status;signatureType=[string]$sig.SignatureType;subject=$sig.SignerCertificate.Subject;thumbprint=$sig.SignerCertificate.Thumbprint;timestampSubject=$sig.TimeStamperCertificate.Subject;fileVersion=$file.VersionInfo.FileVersion;productVersion=$file.VersionInfo.ProductVersion}
}
ConvertTo-Json -InputObject @($rows) -Depth 4 | Set-Content -LiteralPath $OutputFile -Encoding utf8
'''


def signatures(items, output):
    script, paths, receipt = output / "inspect-signatures.ps1", output / "signature-inputs.json", output / "signatures.json"
    script.write_text(PS, encoding="utf-8")
    write_json(paths, [{"id": key, "path": str(path)} for key, path in items.items()])
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    env = dict(os.environ, PSModulePath=r"C:\Windows\System32\WindowsPowerShell\v1.0\Modules;C:\Program Files\WindowsPowerShell\Modules")
    # Process-only policy for this generated, read-only inspection script. It does not
    # change machine or user policy and executes no extracted application code.
    run([powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script, "-InputList", paths, "-OutputFile", receipt], timeout=1800, env=env)
    rows = json.loads(receipt.read_text(encoding="utf-8-sig"))
    if len(rows) != len(items) or {x["id"] for x in rows} != set(items):
        raise Refused("Signature census incomplete")
    return {x["id"]: x for x in rows}


def required_owner(row):
    if (row["status"] != "Valid" or row.get("signatureType") != "Authenticode" or row["thumbprint"] != PIN
            or "DigiCert" not in (row.get("timestampSubject") or "")):
        raise Refused("Expected valid, DigiCert-timestamped approved publisher: " + row["id"])


def bind_completed_build(path, build_inputs, report):
    raw = path.read_bytes()
    result = json.loads(raw.decode("utf-8-sig"))
    if (result.get("exitCode") != 0 or result.get("sourcePin") != build_inputs.get("packagingSource") or
            result.get("sourceClean") is not True or result.get("inputsUnchanged") is not True):
        raise Refused("Completed build failed or inputs/source changed")
    report["buildResultSha256"] = hashlib.sha256(raw).hexdigest()
    return result


def bound_outputs(*documents):
    bound = {}
    for document in documents:
        for name, value in (document.get("boundBuildOutputs") or {}).items():
            if name not in BUILD_OUTPUTS or name in bound:
                raise Refused("Unexpected or duplicate bound build output: " + name)
            bound[name] = value
    if set(bound) != BUILD_OUTPUTS:
        raise Refused("Build receipt does not bind every build output")
    return bound


# ---- verification -------------------------------------------------------------------------

def verify(args, report):
    candidate, baseline, output, seven = map(Path, (args.installer, args.baseline, args.output, args.seven_zip))
    repo = str(Path(args.repo).resolve())
    report.update({"appId": APP, "expectedVersion": NEW, "baselineVersion": OLD,
                   "candidate": str(candidate), "candidateSha256": digest(candidate), "candidateBytes": candidate.stat().st_size,
                   "baselineSha256": digest(baseline), "verifierSha256": digest(__file__), "sevenZipSha256": digest(seven)})
    if report["baselineSha256"] != BASE_SHA:
        raise Refused("Baseline installer is not the pinned accepted release")
    build_inputs_path = Path(args.build_inputs) if args.build_inputs else candidate.parents[2] / "build-inputs.json"
    build_result_path = build_inputs_path.with_name("build-result.json")
    build_inputs = json.loads(build_inputs_path.read_text(encoding="utf-8-sig"))
    head, base = resolve_commit(repo, args.head), resolve_commit(repo, BASE_PIN)
    if (build_inputs.get("app") != APP or build_inputs.get("version") != NEW or
            build_inputs.get("baselineInstallerSHA256") != BASE_SHA or build_inputs.get("packagingSource") != head or
            build_inputs.get("basePin") != base or Path(build_inputs["root"]).resolve() != candidate.parents[2].resolve()):
        raise Refused("Build input is not bound to this candidate and release HEAD")
    report.update({"buildInputsSha256": digest(build_inputs_path), "packagingSource": head, "basePin": base,
                   "applicationSource": build_inputs.get("applicationSource")})
    build_result = bind_completed_build(build_result_path, build_inputs, report)
    bound = bound_outputs(build_inputs, build_result)
    changes = changed_paths(repo, base, head)
    head_files = head_contents(repo, head)
    report["gitDiff"] = {"command": "git diff --no-renames --name-status " + base + " " + head, "paths": len(changes),
                         "sha256": hashlib.sha256(json.dumps(changes, sort_keys=True).encode()).hexdigest()}
    budget = MAX_EXPANDED
    roots = {}
    for label, installer in (("baseline", baseline), ("candidate", candidate)):
        container = output / label
        container.mkdir()
        nsis, app = container / "nsis", container / "app"
        budget -= extract(seven, installer, nsis, budget)
        archives = list(nsis.rglob("app-64.7z"))
        if len(archives) != 1:
            raise Refused("Exactly one x64 app payload required")
        budget -= extract(seven, archives[0], app, budget)
        roots[label] = (nsis, app)
        print(json.dumps({"event": "inspection-progress", "phase": label + "-extracted", "appRoot": str(app)}), flush=True)
    old_nsis, old_app = roots["baseline"]
    new_nsis, new_app = roots["candidate"]
    old_files, new_files = tree(old_app), tree(new_app)
    old_pes, old_hashes = inspect_files(old_files)
    new_pes, new_hashes = inspect_files(new_files)
    if old_pes != new_pes or len(new_pes) != EXPECTED_PES:
        report["peAdded"], report["peRemoved"] = sorted(new_pes - old_pes), sorted(old_pes - new_pes)
        raise Refused("Payload PE closure differs from pinned baseline")
    report["payloadAdded"] = sorted(new_files.keys() - old_files.keys())
    report["payloadRemoved"] = sorted(old_files.keys() - new_files.keys())
    # Non-PE payload (app.asar is a bound build output; its members are checked below).
    nonpe_old = {k: v for k, v in old_hashes.items() if k not in old_pes}
    nonpe_new = {k: v for k, v in new_hashes.items() if k not in new_pes}
    payload_rows = source_bound(nonpe_old, nonpe_new, changes, head_files, payload_source, bound)
    inventory = json.loads(new_files[SOURCE_INVENTORY].read_text(encoding="utf-8"))
    packaged_sources = sorted(k[len(RUNTIME + "sources/"):] for k in new_files if k.startswith(RUNTIME + "sources/"))
    if sorted(inventory) != packaged_sources:
        raise Refused("Runtime source inventory does not list exactly the packaged sources")
    old_plugins, new_plugins = tree(old_nsis / "$PLUGINSDIR"), tree(new_nsis / "$PLUGINSDIR")
    if {x for x in old_plugins if x.endswith(".dll")} != PLUGINS or {x for x in new_plugins if x.endswith(".dll")} != PLUGINS:
        raise Refused("Unexpected NSIS plugin closure")
    old_uninstaller, new_uninstaller = list(old_nsis.rglob("Uninstall " + APP_NAME + ".exe")), list(new_nsis.rglob("Uninstall " + APP_NAME + ".exe"))
    if len(old_uninstaller) != 1 or len(new_uninstaller) != 1:
        raise Refused("Generated uninstaller missing/ambiguous")
    items = {"candidate/installer": candidate, "baseline/installer": baseline,
             "candidate/uninstaller": new_uninstaller[0], "baseline/uninstaller": old_uninstaller[0]}
    for label, files in (("baseline", old_files), ("candidate", new_files)):
        items.update({label + "/app/" + rel: files[rel] for rel in sorted(new_pes)})
    for label, files in (("baseline", old_plugins), ("candidate", new_plugins)):
        items.update({label + "/plugin/" + rel: files[rel] for rel in sorted(PLUGINS)})
    print(json.dumps({"event": "inspection-progress", "phase": "native-signature-census", "files": len(items)}), flush=True)
    sig = signatures(items, output)
    for rel in new_pes:
        if sig["baseline/app/" + rel]["sha256"] != old_hashes[rel] or sig["candidate/app/" + rel]["sha256"] != new_hashes[rel]:
            raise Refused("PE changed between byte census and signature inspection: " + rel)
    main_name = APP_NAME + ".exe"
    for key in ("candidate/installer", "candidate/uninstaller", "candidate/app/" + main_name, "candidate/app/resources/elevate.exe"):
        required_owner(sig[key])
    for key in ("candidate/installer", "candidate/uninstaller", "candidate/app/" + main_name):
        if sig[key]["fileVersion"] not in (NEW, NEW + ".0") or sig[key]["productVersion"] not in (NEW, NEW + ".0"):
            raise Refused("New executable version missing: " + key)
    old_asar_hash, old_asar = asar(old_files["resources/app.asar"])
    new_asar_hash, new_asar = asar(new_files["resources/app.asar"])
    if any(m["head"][:2] == b"MZ" for m in new_asar.values()):
        raise Refused("ASAR carries a PE candidate member")
    config_keys = asar_config_keys(git(repo, "show", head + ":ops/desktop/client/builder.cjs").decode("utf-8"))
    added_config = check_package(old_asar["package.json"]["json"], new_asar["package.json"]["json"], config_keys)
    asar_rows = source_bound({k: v["sha256"] for k, v in old_asar.items() if k != "package.json"},
                             {k: v["sha256"] for k, v in new_asar.items() if k != "package.json"},
                             changes, head_files, asar_source, label="asar")
    checks, preserved, owned_identical, signed = [], 0, 0, 0
    for rel in sorted(new_pes):
        before, after = sig["baseline/app/" + rel], sig["candidate/app/" + rel]
        owned_before = before["status"] == "Valid" and before["thumbprint"] == PIN
        if before["status"] == "Valid" and not owned_before:
            if after["status"] != "Valid" or after["sha256"] != before["sha256"] or after["thumbprint"] != before["thumbprint"]:
                raise Refused("Previously valid vendor image changed: " + rel)
            mode = "vendor-byte-identical"
            preserved += 1
        elif owned_before or before["status"] == "NotSigned":
            required_owner(after)
            if after["sha256"] == before["sha256"]:
                mode = "approved-byte-identical"
                owned_identical += 1
            else:
                mode = compare_signed_pe(old_files[rel], new_files[rel], rel == main_name, old_asar_hash, new_asar_hash)
                signed += 1
        else:
            raise Refused("Baseline has unexpected invalid signature: " + rel)
        checks.append({"path": rel, "comparison": mode, "sha256": after["sha256"], "baselineSha256": before["sha256"],
                       "signerThumbprint": after["thumbprint"], "signatureType": after["signatureType"], "timestampSubject": after["timestampSubject"]})
    if not any(x["path"] == main_name and x["comparison"] == "authenticode-plus-version-and-asar-integrity" for x in checks):
        raise Refused("Main executable version and asar integrity were not compared")
    for rel in sorted(PLUGINS):
        required_owner(sig["candidate/plugin/" + rel])
        if sig["candidate/plugin/" + rel]["sha256"] != sig["baseline/plugin/" + rel]["sha256"]:
            compare_signed_pe(old_plugins[rel], new_plugins[rel])
    old_outer, new_outer = tree(old_nsis), tree(new_nsis)
    skip = lambda rel: rel.endswith("/app-64.7z") or rel.endswith("/Uninstall " + APP_NAME + ".exe") or rel.startswith("$PLUGINSDIR/") and rel.rsplit("/", 1)[-1] in PLUGINS
    outer_rows = source_bound({k: digest(v) for k, v in old_outer.items() if not skip(k)},
                              {k: digest(v) for k, v in new_outer.items() if not skip(k)},
                              changes, head_files, lambda _: None, label="NSIS")
    if (digest(candidate) != report["candidateSha256"] or digest(baseline) != BASE_SHA or
            digest(build_inputs_path) != report["buildInputsSha256"] or digest(build_result_path) != report["buildResultSha256"]):
        raise Refused("Installer or build receipt changed during inspection")
    report.update({"status": "passed", "payloadPeCount": len(new_pes), "newlySignedOrResignedPayloadPeCount": signed,
                   "approvedByteIdenticalPeCount": owned_identical, "unchangedVendorPeCount": preserved,
                   "nsisPluginCount": len(PLUGINS), "payloadFileCount": len(new_files),
                   "vendorCatalogSignatureCount": sum(x["comparison"] == "vendor-byte-identical" and x["signatureType"] == "Catalog" for x in checks),
                   "asarMembersCompared": len(new_asar), "asarHeaderSha256": new_asar_hash, "asarAddedConfiguration": added_config,
                   "candidateAsarSha256": new_hashes["resources/app.asar"], "candidateMainSha256": new_hashes[main_name],
                   "boundBuildOutputs": bound, "sourceBoundPayloadChanges": payload_rows, "sourceBoundAsarChanges": asar_rows,
                   "sourceBoundNsisChanges": outer_rows, "payloadPeChecks": checks,
                   "generatedUninstaller": sig["candidate/uninstaller"], "outerInstaller": sig["candidate/installer"],
                   "maxExtractionBytes": MAX_EXPANDED, "extractedBytes": MAX_EXPANDED - budget,
                   "checks": {key: True for key in GATES}, "gateSemantics": GATE_SEMANTICS,
                   "generatedPackagingException": "Outer NSIS and generated uninstaller are rebuilt, not byte-equal to baseline. Their approved signer, timestamp and new version are verified.",
                   "runtimeExecution": "not performed", "recipientPolicyAcceptance": "not tested"})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", required=True)
    parser.add_argument("--baseline", required=True, help="The 1.0.16 installer (sha256 " + BASE_SHA + ")")
    parser.add_argument("--output", required=True, help="Fresh non-existent work directory")
    parser.add_argument("--repo", required=True, help="Git repository holding the release HEAD and the base pin")
    parser.add_argument("--head", required=True, help="Release HEAD; must equal build-inputs packagingSource")
    parser.add_argument("--build-inputs")
    parser.add_argument("--seven-zip", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).absolute()
    if output.exists():
        parser.error("output must not already exist")
    output.mkdir()
    report = {"schemaVersion": 1, "status": "failed", "checkedUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "checks": {key: False for key in GATES}}
    try:
        verify(args, report)
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
    write_json(output / "verification.json", report)
    print(json.dumps({k: report[k] for k in ("status", "candidateSha256", "payloadPeCount", "nsisPluginCount", "error") if k in report}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
