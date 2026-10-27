"""Build local signed directory-ZIP engineering candidates from frozen Git commits.

This command never publishes or launches an application. Native UI, update smoke,
security and redistribution acceptance remain separate release gates.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import uuid

HERE = Path(__file__).resolve().parent
APPS = {"melange": "Melange", "mentat": "Mentat", "terrier": "Geo"}
PIN = "0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30"
SUBJECT = "CN=Melange Systems Desktop Release (self-signed)"
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
GIB = 1024**3


class Refused(ValueError):
    pass


def require(value, message):
    if not value:
        raise Refused(message)


def digest(file):
    with Path(file).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def tree_bytes(root):
    root = physical(root)
    size = 0
    for base, directories, files in os.walk(root, followlinks=False):
        for name in directories:
            physical(Path(base) / name)
        for name in files:
            info = (Path(base) / name).lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "Linked or special runtime input")
            size += info.st_size
    return size


def runtime_budget(config):
    return config["runtime"]["inputBytes"] if config["runtime"] else max(3 * GIB // 4, config.get("runtimeBaselineBytes", 2 * GIB) * 3 // 2)


def peak_reserve(config):
    # Reused: runtime + unpacked app + worst-case ZIP. Fresh also holds a venv.
    copies = 3 if config["runtime"] else 4
    return copies * (runtime_budget(config) + GIB // 2) + config["source"]["exportBytes"] + GIB


def physical(path):
    path = Path(path).absolute()
    for current in (path, *path.parents):
        require(not current.is_symlink() and not current.is_junction(), "Linked build path")
    require(path.resolve(strict=True) == path, "Noncanonical build path")
    return path


def json_write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def git(repo, *args, missing=False):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, stdin=subprocess.DEVNULL)
    if missing and result.returncode:
        return None
    require(result.returncode == 0, "Git operation failed: " + result.stderr.decode("utf-8", "replace")[-1000:])
    return result.stdout


def source_identity(value, app):
    require(isinstance(value, dict) and isinstance(value.get("commit"), str) and re.fullmatch(r"[0-9a-f]{40}", value["commit"]), "A frozen full commit is required")
    repo, commit = physical(value["path"]), value["commit"]
    require(git(repo, "rev-parse", "--verify", commit + "^{commit}").decode().strip() == commit, "Source commit is unavailable locally")
    origin = git(repo, "config", "--get", "remote.origin.url").decode().strip()
    require(re.fullmatch(r"(?:https://github\.com/|git@github\.com:)pjg93-222/" + APPS[app] + r"(?:\.git)?/?", origin, re.I), "Unexpected source repository")
    records = [row.split(b"\t", 1)[0].split() for row in git(repo, "ls-tree", "-rzl", commit).split(b"\0") if row]
    export_bytes = sum(int(row[3]) for row in records if row[3] != b"-")
    return {"path": str(repo), "commit": commit, "repository": "pjg93-222/" + APPS[app], "exportBytes": export_bytes,
            "checkoutDirty": bool(git(repo, "status", "--porcelain", "--untracked-files=no").strip()), "exportDirty": False}


def committed_json(source, relative):
    return json.loads(git(source["path"], "show", source["commit"] + ":" + relative))


def dependency_reuse(app, source, runtime, manifest):
    runtime = physical(runtime)
    provenance = json.loads((runtime / "source-provenance.json").read_text(encoding="utf-8"))
    require(provenance.get("repository", "").lower() == source["repository"].lower(), "Runtime provenance belongs to another app")
    commit = next((provenance.get(key) for key in ("commit", "reviewedBase") if re.fullmatch(r"[0-9a-f]{40}", provenance.get(key, "")) and git(source["path"], "cat-file", "-e", provenance[key] + "^{commit}", missing=True) is not None), None)
    require(commit, "Runtime provenance commit is unavailable; rebuild dependencies")
    hashes = {}
    for name in [manifest["requirements"], "requirements.lock.txt"]:
        old = git(source["path"], "show", commit + ":" + name, missing=True)
        new = git(source["path"], "show", source["commit"] + ":" + name, missing=True)
        require(old == new, app + " dependency requirements changed: " + name + "; omit runtime to rebuild from pinned constraints")
        hashes[name] = hashlib.sha256(new).hexdigest() if new is not None else None
    require((runtime / "python/python.exe").is_file(), "Reusable Python is missing")
    status = json.loads((runtime / "runtime-status.json").read_text(encoding="utf-8"))
    require(status.get("appId") == app and status.get("missingNativeRuntimes") == [], "Reusable runtime is incomplete")
    for name in manifest["nativeRuntimes"]:
        require((runtime / "native" / name).is_dir(), "Reusable native runtime is missing: " + name)
    return {"path": str(runtime), "inputBytes": tree_bytes(runtime), "provenance": provenance, "requirements": hashes,
            "dependencyInventorySha256": digest(runtime / "dependency-inventory.json"), "runtimeStatusSha256": digest(runtime / "runtime-status.json")}


def plan(spec):
    require(spec.get("schemaVersion") == 1 and re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", spec.get("version", "")), "Invalid candidate version")
    require(isinstance(spec.get("apps"), dict) and spec["apps"] and set(spec["apps"]) <= set(APPS), "Invalid app selection")
    tooling = source_identity(spec["tooling"], "melange")
    require(committed_json(tooling, "ops/desktop/client/package.json")["version"] == spec["version"], "Frozen client version differs from candidate version")
    manifest = committed_json(tooling, "ops/desktop/packaging/runtime-manifest.json")
    apps = {}
    for app, value in spec["apps"].items():
        source = source_identity(value["source"], app)
        reuse = dependency_reuse(app, source, value["runtime"], manifest["apps"][app]) if value.get("runtime") else None
        require(reuse or not manifest["apps"][app]["nativeRuntimes"], "A fresh native runtime build needs explicit reviewed native inputs")
        apps[app] = {"source": source, "runtime": reuse, "runtimeBaselineBytes": tree_bytes(value["runtimeSizeBaseline"]) if value.get("runtimeSizeBaseline") else 2 * GIB}
    return {"schemaVersion": 1, "version": spec["version"], "tooling": tooling, "apps": apps,
            "publicationAllowed": False, "appExecution": "not-requested", "sourceMode": "git-archive-frozen-commits"}


def inventory(root):
    root = physical(root)
    rows = []
    for file in sorted(root.rglob("*")):
        physical(file)
        if file.is_file():
            require(file.stat().st_nlink == 1, "Hardlinked build input")
            rows.append({"path": file.relative_to(root).as_posix(), "size": file.stat().st_size, "sha256": digest(file)})
    return rows


def export_commit(source, destination):
    destination.mkdir()
    process = subprocess.Popen(["git", "-C", source["path"], "-c", "core.autocrlf=false", "-c", "core.eol=lf", "archive", "--format=tar", source["commit"]], stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            for member in archive:
                require(member.isdir() or member.isfile(), "Git export contains a link or special file")
                archive.extract(member, destination, filter="data")
        # Streaming tar stops at its end marker. Drain Git's remaining block
        # padding before waiting, otherwise a small Windows pipe can deadlock.
        while process.stdout.read(65536):
            pass
        require(process.wait() == 0, "Git archive failed")
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.kill()
            process.wait()
    return inventory(destination)


class Build:
    def __init__(self, prepared, root, artifacts, python, free_floor_gib=32):
        self.plan, self.root, self.artifacts, self.python = prepared, Path(root).absolute(), Path(artifacts).absolute(), Path(python).absolute()
        self.floor = free_floor_gib * GIB
        self.environment = {key: value for key, value in os.environ.items() if not key.upper().startswith(("DESKTOP_", "CSC_", "WIN_CSC_")) and key.upper() not in {"PSMODULEPATH", "NODE_OPTIONS", "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "ELECTRON_RUN_AS_NODE", "ELECTRON_BUILDER_NSIS_DIR", "ELECTRON_BUILDER_NSIS_RESOURCES_DIR"}}

    def space(self, additional=0):
        require(shutil.disk_usage(self.root).free >= self.floor + additional, "Build would cross configured free-space floor")

    def call(self, label, command, cwd=None, env=None, reserve=0):
        self.space(reserve)
        print(json.dumps({"step": label}), flush=True)
        command = [str(x) for x in command]
        command[0] = shutil.which(command[0]) or command[0]
        with (self.root / "logs" / (label + ".log")).open("xb") as output:
            output.write((subprocess.list2cmdline(command) + "\n").encode())
            result = subprocess.run(command, cwd=cwd, env=env or self.environment, stdout=output, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        require(result.returncode == 0, label + " failed; see logs/" + label + ".log")
        self.space()

    def remove(self, relative):
        target = self.root / relative
        require(target != self.root and target.is_relative_to(self.root), "Cleanup target escaped private build root")
        if target.exists():
            physical(target)
            require(self.root.stat().st_ino == self.root_identity, "Build directory identity changed")
            require(json.loads((self.root / "owner.json").read_text())["id"] == self.owner, "Build ownership changed")
            shutil.rmtree(target)

    def run(self):
        require(os.name == "nt" and not os.environ.get("CI") and not os.environ.get("GITHUB_ACTIONS"), "Local Windows build required")
        require(len(str(self.root)) <= 70 and not self.root.exists(), "Use a fresh short build root (at most 70 characters)")
        physical(self.root.parent)
        require(not self.artifacts.is_relative_to(self.root), "Artifacts must survive scratch cleanup outside the build root")
        self.root.mkdir()
        physical(self.root)
        self.owner = uuid.uuid4().hex
        self.root_identity = self.root.stat().st_ino
        json_write(self.root / "owner.json", {"id": self.owner, "purpose": "local-directory-candidate"})
        for folder in ["logs", "src", "runtime", "build", "signing", "verify", "venv"]:
            (self.root / folder).mkdir()
        json_write(self.root / "plan.json", self.plan)
        self.space(self.plan["tooling"]["exportBytes"] + 2 * GIB)
        tools = self.root / "src" / "tooling"
        tool_inventory = export_commit(self.plan["tooling"], tools)
        json_write(self.root / "tooling-source-inventory.json", tool_inventory)
        client, packaging = tools / "ops/desktop/client", tools / "ops/desktop/packaging"
        self.call("desktop-npm-ci", ["npm", "ci", "--no-fund"], cwd=client, reserve=2 * GIB)
        self.artifacts.mkdir(parents=True, exist_ok=True)
        physical(self.artifacts)
        completed = {}
        for app, config in self.plan["apps"].items():
            self.space(peak_reserve(config))
            shares_tools = config["source"]["repository"] == self.plan["tooling"]["repository"] and config["source"]["commit"] == self.plan["tooling"]["commit"]
            source = tools if shares_tools else self.root / "src" / app
            source_inventory = tool_inventory if shares_tools else export_commit(config["source"], source)
            json_write(self.root / (app + "-source-inventory.json"), source_inventory)
            if app == "terrier" and (source / "frontend/package.json").is_file():
                self.call(app + "-frontend-ci", ["npm", "ci", "--no-fund"], cwd=source / "frontend", reserve=2 * GIB)
                self.call(app + "-frontend-build", ["npm", "run", "build"], cwd=source / "frontend", reserve=GIB)
            runtime = self.root / "runtime" / app
            if config["runtime"]:
                self.space(config["runtime"]["inputBytes"])
                original = Path(config["runtime"]["path"])
                shutil.copytree(original, runtime, ignore=lambda folder, names: {name for name in names if Path(folder) == original and name in {"sources", "bootstrap"}})
                (runtime / "sources").mkdir()
                python = runtime / "python/python.exe"
                mode = ["--sync-sources-only"]
            else:
                venv = self.root / "venv" / app
                self.call(app + "-venv", [self.python, "-I", "-m", "venv", venv], reserve=GIB // 4)
                python = venv / "Scripts/python.exe"
                self.call(app + "-pip", [python, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "--require-hashes", "--only-binary=:all:", "--no-deps", "-r", packaging / (app + "-runtime.constraints.txt")], reserve=2 * runtime_budget(config) + GIB // 2)
                self.call(app + "-pip-check", [python, "-m", "pip", "check"])
                mode = []
            self.call(app + "-runtime", [python, "-B", packaging / "build_runtime.py", "--app", app, "--source", source, *mode, "--build-root", self.root / "build", "--runtime-root", self.root / "runtime"], cwd=tools, reserve=runtime_budget(config) + GIB // 4)
            status = json.loads((runtime / "runtime-status.json").read_text())
            require(status["missingNativeRuntimes"] == [], "Native runtime inputs missing")
            # A copied provenance record describes only the reusable dependencies;
            # all shipped application/bootstrap bytes are regenerated above.
            old_provenance = runtime / "source-provenance.json"
            if old_provenance.exists():
                old_provenance.unlink()
            provenance = {"schemaVersion": 1, "app": app, "repository": config["source"]["repository"], "commit": config["source"]["commit"],
                          "sourceCommit": config["source"]["commit"], "toolingCommit": self.plan["tooling"]["commit"], "dirty": False,
                          "sourceExportInventorySha256": digest(self.root / (app + "-source-inventory.json")),
                          "toolingExportInventorySha256": digest(self.root / "tooling-source-inventory.json"), "dependencyReuse": {key: value for key, value in config["runtime"].items() if key != "path"} if config["runtime"] else None,
                          "publication": "engineering-candidate-not-approved"}
            json_write(old_provenance, provenance)
            output = self.artifacts / app
            output.mkdir()
            json_write(output / "source-provenance.json", provenance)
            json_write(output / "runtime-source-inventory.json", {"sources": inventory(runtime / "sources"), "bootstrap": inventory(runtime / "bootstrap")})
            signing = self.root / "signing" / app
            signing.mkdir()
            env = {**self.environment, "DESKTOP_APP_ID": app, "DESKTOP_DISTRIBUTION": "directory-zip", "DESKTOP_RUNTIME_ROOT": str(self.root / "runtime"), "DESKTOP_DIST_ROOT": str(signing / "dist"), "DESKTOP_SIGNING_ROOT": str(signing), "DESKTOP_SIGNING_CERT_SHA1": PIN, "WINDOWS_PUBLISHER_NAME": SUBJECT,
                   "DESKTOP_UPDATE_PROVIDER": "github", "DESKTOP_GITHUB_REPOSITORY": config["source"]["repository"], "DESKTOP_ACCESS_TRUST": str(packaging / "desktop-access-trust.public.json")}
            self.call(app + "-electron", ["npm", "run", "build", "--", "--win", "--x64", "--publish", "never"], cwd=client, env=env, reserve=tree_bytes(runtime) + GIB)
            unpacked = signing / "dist" / app / "win-unpacked"
            require((unpacked.with_name(unpacked.name + ".signatures.json")).is_file(), "Directory signing receipt missing")
            shutil.copy2(unpacked.with_name(unpacked.name + ".signatures.json"), output / "build-signatures.json")
            # Run the frozen packager, never the caller's potentially dirty file.
            package = output / (app + "-" + self.plan["version"] + "-win32-x64.zip")
            self.call(app + "-zip", [self.python, "-B", packaging / "directory_zip.py", "--app", app, "--version", self.plan["version"], "--source", unpacked, "--output", package, "--publisher-payload", output / "publisher-payload.json"], reserve=tree_bytes(unpacked) + GIB // 4)
            text = (self.root / "logs" / (app + "-zip.log")).read_text(encoding="utf-8")
            descriptor = json.loads(text[text.index("{\n"):])
            json_write(output / "package.json", descriptor)
            self.call(app + "-publisher-proof", [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", packaging / "sign_directory_package.ps1", "-PayloadFile", output / "publisher-payload.json", "-OutputFile", output / "publisher-proof.json"])
            self.remove(Path("signing") / app)
            self.remove(Path("runtime") / app)
            self.remove(Path("build") / app)
            self.remove(Path("venv") / app)
            self.space(descriptor["expandedBytes"] + GIB)
            self.call(app + "-verify", ["node", packaging / "verify_directory_release.cjs", client, output, self.root, self.plan["version"]], cwd=client)
            self.remove(Path("verify") / app)
            self.remove(Path("src") / app)
            receipt = {"schemaVersion": 1, "appId": app, "version": self.plan["version"], "sourceCommit": provenance["sourceCommit"], "toolingCommit": provenance["toolingCommit"], "package": descriptor,
                       "sourceInventorySha256": digest(output / "runtime-source-inventory.json"), "nativeVerificationSha256": digest(output / "native-verification.json"), "publisherProofSha256": digest(output / "publisher-proof.json"),
                       "publicationAllowed": False, "acceptanceNotRun": ["isolated-packaged-app-smoke", "automatic-update-smoke", "security-gate", "dependency-and-redistribution-review", "recipient-ThreatLocker-policy"], "completedAt": dt.datetime.now(dt.timezone.utc).isoformat()}
            json_write(output / "engineering-receipt.json", receipt)
            completed[app] = receipt
        json_write(self.root / "completed.json", completed)
        return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--python312", type=Path, required=True)
    parser.add_argument("--free-floor-gib", type=int, default=32)
    parser.add_argument("--build", action="store_true", help="Perform the local build; default only validates frozen inputs")
    args = parser.parse_args()
    require(args.free_floor_gib >= 32, "Free-space floor must be at least 32 GiB")
    prepared = plan(json.loads(args.spec.read_text(encoding="utf-8")))
    if args.build:
        print(json.dumps(Build(prepared, args.root, args.artifacts, args.python312, args.free_floor_gib).run(), indent=2))
    else:
        print(json.dumps(prepared, indent=2))


if __name__ == "__main__":
    main()
