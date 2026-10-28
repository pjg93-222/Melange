"""Independently inspect a native Windows release; never execute its payload.

The build controller supplies frozen client/source exports and its gated staging
tree. This verifier compares actual archive bytes to those inputs, independently
enumerates every PE header, and obtains fresh Windows signature verdicts.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import ctypes
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys

HERE = Path(__file__).resolve().parent
PRODUCTS = {"melange": "Melange", "mentat": "Mentat", "terrier": "Terrier"}
REPOSITORIES = {"melange": "pjg93-222/melange", "mentat": "pjg93-222/mentat", "terrier": "pjg93-222/geo"}
RESERVE = 32 * 1024 ** 3
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
    for file in files.values():
        physical(file)
    pes, hashes = legacy.inspect_files(files)
    return files, pes, {name: {"sha256": hashes[name], "size": file.stat().st_size} for name, file in files.items()}


def extract(seven, archive, destination, budget):
    physical(destination.parent, True)
    listing = legacy.run([seven, "l", "-slt", "-ba", archive]).decode("utf-8", "strict").replace("\r\n", "\n")
    names, aliases, total = set(), set(), 0
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
        size = int(row.get("Size", "0") or "0")
        require(size >= 0, "Negative archive member size")
        total += size
        names.add(name)
    require(total <= budget and shutil.disk_usage(destination.parent).free - total >= RESERVE,
            "Extraction would exceed its bound or32GiB reserve")
    destination.mkdir()
    owned = destination.stat()
    legacy.run([seven, "x", archive, "-o" + str(destination), "-y"], timeout=1800)
    after = physical(destination, True)
    require((owned.st_dev, owned.st_ino) == (after.st_dev, after.st_ino), "Inspection root was replaced")
    files = legacy.tree(destination)
    require(set(files) == names, "Extracted paths differ from inspected archive listing")
    require(sum(file.stat().st_size for file in files.values()) == total, "Extracted byte count differs from archive listing")
    return total


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


def verify_sources(*, app, version, program_files, program_map, members, client, staged, trust):
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
    build_inputs = {name: snapshot(client / name)[-1] for name in BUILD_INPUTS}
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
    return {"clientFiles": expected_client, "runtimeSources": staged_map, "runtimeBootstrap": expected_boot,
            "nativeBuildInputs": build_inputs, "publicReleaseCertificate": program_map["resources/" + certificate],
            "sourceManifests": {"releaseFiles": legacy.digest(client / "release-files.cjs"),
                                "buildRuntime": legacy.digest(packaging / "build_runtime.py"),
                                "stagedSources": legacy.digest(staged_inventory_path)}}, package


def native_census(*, installer, program_directory, app_files, app_pes, app_map, nsis_files, nsis_pes, nsis_map, receipt):
    """Bind every header-detected native file to fresh build signature evidence."""
    current = receipt.get("currentFiles") or []
    require(len({identity(row["path"]) for row in current}) == len(current), "Duplicate current signature records")
    expected = {}
    for row in current:
        file = Path(row["path"])
        if identity(file) == identity(installer):
            continue
        try:
            rel = file.relative_to(program_directory).as_posix()
        except ValueError as error:
            raise Refused("Current signature row escapes signed program tree") from error
        require(rel in app_pes and row.get("sha256") == app_map[rel]["sha256"], "Current program signature bytes/census differ: " + rel)
        expected[rel] = row
    require(set(expected) == app_pes, "Native header census differs from complete build signature receipt")
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
    for sha in (args.client_commit, args.source_commit):
        require(re.fullmatch(r"[0-9a-f]{40}", sha), "Frozen commit identity required")
    require(re.fullmatch(r"\d+\.\d+\.\d+", args.version), "Stable native version required")
    output, installer = Path(args.output).absolute(), Path(args.installer).absolute()
    program, client, staged = (Path(value).absolute() for value in (args.program_directory, args.client, args.staged_sources))
    seven = Path(args.seven_zip).resolve(strict=True)  # known tool cache may have a legitimate parent redirect
    trust, receipt_path = Path(args.trust_descriptor).absolute(), Path(args.signing_receipt).absolute()
    for folder in (program, client, staged, output.parent):
        physical(folder, True)
    if args.source:
        physical(Path(args.source), True)
    require(not output.exists(), "Inspection output must be fresh")
    output.mkdir()
    paths = [installer, receipt_path, trust, seven, Path(__file__), HERE / "verify_signed_release.py", HERE / "no_uninstaller_contract.py"]
    inputs = {str(file): snapshot(file) for file in paths}
    reference_files, reference_pes, reference = scan(program)
    report = {"schemaVersion": 1, "status": "failed", "appId": args.app, "version": args.version,
              "clientCommit": args.client_commit, "sourceCommit": args.source_commit,
              "originalSourceExport": args.source,
              "frozenExportBinding": "exports and gated stage supplied by the release controller; actual packaged bytes compared independently",
              "installerSha256": inputs[str(installer)][-1], "inputs": {name: row[-1] for name, row in inputs.items()},
              "runtimeExecution": "not performed", "recipientPolicyAcceptance": "not tested"}
    with locked_input(installer), locked_input(seven):
        preflight = output / "preflight"
        preflight.mkdir()
        legacy.required_owner(legacy.signatures({"installer": installer}, preflight, preserve_execution_policy=True)["installer"])
        outer, extracted = output / "nsis", output / "app"
        used = extract(seven, installer, outer, MAX_EXPANDED)
        archives = list(outer.rglob("app-64.7z"))
        require(len(archives) == 1, "Exactly one native x64 application payload required")
        used += extract(seven, archives[0], extracted, MAX_EXPANDED - used)
        app_files, app_pes, app_map = scan(extracted)
        nsis_files, nsis_pes, nsis_map = scan(outer)
        same_tree(app_map, reference, "Complete signed application")
        require(app_pes == reference_pes, "Native classification differs from signed program tree")
        asar_header_hash, members = legacy.asar(app_files["resources/app.asar"])
        verify_asar_integrity(app_files[PRODUCTS[args.app] + ".exe"], asar_header_hash)
        source_evidence, package = verify_sources(app=args.app, version=args.version, program_files=app_files,
            program_map=app_map, members=members, client=client, staged=staged, trust=trust)
        absence = contract.verify_without_uninstaller(installer=installer, package_json=package,
            nsis_files=nsis_files, app_files=app_files, asar_members=members, signing_receipt=receipt_path)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        items, expected = native_census(installer=installer, program_directory=program, app_files=app_files,
            app_pes=app_pes, app_map=app_map, nsis_files=nsis_files, nsis_pes=nsis_pes, nsis_map=nsis_map, receipt=receipt)
        native = output / "native"
        native.mkdir()
        print(json.dumps({"phase": "complete-native-signature-census", "appId": args.app, "files": len(items)}), flush=True)
        rows = legacy.signatures(items, native, preserve_execution_policy=True)
        check_verdicts(rows, items, expected, app_map, nsis_map, args.app, args.version)
        require(rows["installer"]["sha256"] == report["installerSha256"], "Outer installer changed during signature verification")
        same_tree(scan(extracted)[2], app_map, "Final extracted application")
        same_tree(scan(outer)[2], nsis_map, "Final NSIS container")
        same_tree(scan(program)[2], reference, "Final signed program input")
        final_sources, _ = verify_sources(app=args.app, version=args.version, program_files=app_files,
            program_map=app_map, members=legacy.asar(app_files["resources/app.asar"])[1], client=client, staged=staged, trust=trust)
        require(final_sources == source_evidence, "Frozen source inputs changed during verification")
        for file, before in inputs.items():
            require(snapshot(file) == before, "Verification input changed: " + file)
        report.update(status="passed", payloadFileCount=len(app_files), payloadPeCount=len(app_pes),
            nsisPluginCount=len(NATIVE_PLUGINS), completeNativeCount=len(items), extractedBytes=used,
            nsisPluginContract={"electronBuilderVersion": "26.15.3", "mode": "assisted-per-user-without-uninstaller", "files": sorted(NATIVE_PLUGINS)},
            embeddedAsarIntegrityVerified=True, asarHeaderSha256=asar_header_hash,
            completeNativeCensus=True, desktopUninstaller=False,
            noUninstaller=absence, sourceEvidence=source_evidence, applicationFiles=app_map, nsisFiles=nsis_map,
            nativeSignatureRows=rows, inputFilesUnchanged=True)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", choices=PRODUCTS, required=True)
    for name in ("version", "installer", "signing-receipt", "program-directory", "client", "staged-sources",
                 "client-commit", "source-commit", "trust-descriptor", "seven-zip", "output", "report"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--source", help="Original frozen source export (provenance; transformed bytes use --staged-sources)")
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
