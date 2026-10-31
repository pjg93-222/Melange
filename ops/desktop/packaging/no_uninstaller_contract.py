"""Explicit native-installer contract; does not replace native signature verification.

Call after independently extracting/inspecting the complete NSIS payload and ASAR.
The caller must still verify every native image, source binding and outer signature.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

PIN = "0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30"
EVIDENCE = "intentionally-absent"


class ContractRefused(ValueError):
    pass


def _require(value, message):
    if not value:
        raise ContractRefused(message)


def uninstaller_name(value):
    """Known generated, installed and copied NSIS uninstaller executable names."""
    name = str(value).replace("\\", "/").rsplit("/", 1)[-1].casefold()
    return name.endswith(".exe") and (
        name.startswith("unins") or name.endswith("__uninstaller.exe") or name == "old-uninstaller.exe"
    )


def _identity(value):
    return os.path.normcase(os.path.abspath(value))


def _digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_without_uninstaller(*, installer, package_json, nsis_files, app_files, asar_members,
                              signing_receipt=None):
    """Verify the opt-in contract using independently observed candidate file sets.

    No path from the signing receipt is opened. Its outer-installer row is bound
    to the explicit input bytes; every other native verdict remains the caller's
    responsibility. Return receipt provenance so the caller can recheck it last.
    """
    installer = Path(installer).absolute()
    _require(installer.suffix.casefold() == ".exe", "No-uninstaller contract requires a native EXE installer")
    _require(isinstance(package_json, dict), "Candidate ASAR package metadata is required")
    config = package_json.get("desktopAppConfig")
    _require(isinstance(config, dict) and config.get("desktopUninstaller") is False,
             "Candidate ASAR must explicitly declare desktopUninstaller:false")
    _require(config.get("desktopDistribution", "native") == "native",
             "No-uninstaller contract does not authorize another distribution")
    app_id = config.get("appId")
    _require(app_id in ("melange", "mentat", "terrier"), "Unsupported native application identity")
    scopes = {"nsis": nsis_files, "app": app_files, "asar": asar_members}
    for scope, files in scopes.items():
        _require(isinstance(files, dict) and bool(files) and all(isinstance(name, str) for name in files),
                 "Complete inspected " + scope + " file map required")
        forbidden = [name for name in files if uninstaller_name(name)]
        _require(not forbidden, "Unexpected uninstaller in " + scope + ": " + ", ".join(forbidden[:8]))
    main = {"melange": "Melange.exe", "mentat": "Mentat.exe", "terrier": "Terrier.exe"}[app_id]
    _require(main in app_files and "resources/app.asar" in app_files and "package.json" in asar_members,
             "Candidate program or ASAR metadata missing from inspected file sets")

    receipt_path = Path(signing_receipt) if signing_receipt else Path(str(installer) + ".signatures.json")
    raw = receipt_path.read_bytes()
    receipt = json.loads(raw.decode("utf-8-sig"))
    _require(isinstance(receipt, dict) and receipt.get("schemaVersion") == 1
             and receipt.get("appId") == app_id and receipt.get("certificateThumbprint") == PIN,
             "Signing receipt identity does not match the native application")
    _require(receipt.get("desktopUninstaller") is False and receipt.get("uninstallerEvidence") == EVIDENCE,
             "Signing receipt must explicitly attest intentionally-absent uninstaller")
    _require(isinstance(receipt.get("installer"), str) and _identity(receipt["installer"]) == _identity(installer),
             "Signing receipt belongs to a different installer")
    for field in ("files", "currentFiles"):
        rows = receipt.get(field)
        _require(isinstance(rows, list) and 0 < len(rows) <= 100000, "Incomplete signing receipt " + field)
        for row in rows:
            _require(isinstance(row, dict) and isinstance(row.get("path"), str) and bool(row["path"]),
                     "Invalid signing receipt row")
            _require(not uninstaller_name(row["path"]), "Signing history contains an uninstaller")
    current = receipt["currentFiles"]
    identities = [_identity(row["path"]) for row in current]
    _require(len(set(identities)) == len(identities), "Duplicate current signature evidence")
    outer = [row for row in current if _identity(row["path"]) == _identity(installer)]
    _require(len(outer) == 1, "Current outer-installer signature evidence is missing")
    row = outer[0]
    _require(row.get("status") == "Valid" and row.get("thumbprint") == PIN
             and row.get("timestamped") is True and row.get("sha256") == _digest(installer),
             "Current outer-installer signature evidence is invalid or stale")
    return {"desktopUninstaller": False, "uninstallerEvidence": EVIDENCE, "appId": app_id,
            "observedUninstallerFiles": 0, "inspectedFileCounts": {key: len(value) for key, value in scopes.items()},
            "signingReceipt": str(receipt_path.absolute()), "signingReceiptSha256": hashlib.sha256(raw).hexdigest(),
            "nativeSignatureVerification": "required independently for the complete native census"}
