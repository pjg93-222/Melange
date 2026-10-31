"""Contract tests use synthetic receipt metadata; no executable is run or signed."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import no_uninstaller_contract as contract


class NoUninstallerContract(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.installer = Path(self.temporary.name) / "Mentat-1.0.22-win-x64.exe"
        self.installer.write_bytes(b"synthetic non-executable artifact")
        self.package = {"version": "1.0.22", "desktopAppConfig": {"appId": "mentat", "desktopUninstaller": False}}
        self.row = {"path": str(self.installer), "sha256": hashlib.sha256(self.installer.read_bytes()).hexdigest(),
                    "status": "Valid", "thumbprint": contract.PIN, "timestamped": True}
        self.receipt = {"schemaVersion": 1, "appId": "mentat", "certificateThumbprint": contract.PIN,
                        "installer": str(self.installer), "desktopUninstaller": False,
                        "uninstallerEvidence": "intentionally-absent", "files": [self.row], "currentFiles": [self.row]}
        self.maps = {"nsis_files": {"$PLUGINSDIR/app-64.7z": object()},
                     "app_files": {"Mentat.exe": object(), "resources/app.asar": object()},
                     "asar_members": {"package.json": {"json": self.package}, "main.cjs": object()}}

    def check(self):
        sidecar = Path(str(self.installer) + ".signatures.json")
        sidecar.write_text(json.dumps(self.receipt), encoding="utf-8")
        return contract.verify_without_uninstaller(installer=self.installer, package_json=self.package, **self.maps)

    def test_explicit_native_contract_binds_receipt_and_outer_bytes(self):
        result = self.check()
        self.assertEqual(result["observedUninstallerFiles"], 0)
        self.assertEqual(result["signingReceiptSha256"], hashlib.sha256(Path(result["signingReceipt"]).read_bytes()).hexdigest())
        self.assertIn("required independently", result["nativeSignatureVerification"])
        self.installer.write_bytes(b"changed installer")
        with self.assertRaisesRegex(contract.ContractRefused, "invalid or stale"):
            self.check()

    def test_all_three_native_identities_are_supported(self):
        for app, main in (("melange", "Melange.exe"), ("mentat", "Mentat.exe"), ("terrier", "Terrier.exe")):
            with self.subTest(app=app):
                self.package["desktopAppConfig"]["appId"] = self.receipt["appId"] = app
                self.maps["app_files"] = {main: object(), "resources/app.asar": object()}
                self.assertEqual(self.check()["appId"], app)

    def test_false_must_be_explicit_and_boolean_in_both_authorities(self):
        for where in ("package", "receipt"):
            for value in (None, True, 0, "false"):
                with self.subTest(where=where, value=value):
                    package, receipt = copy.deepcopy(self.package), copy.deepcopy(self.receipt)
                    target = self.package["desktopAppConfig"] if where == "package" else self.receipt
                    target["desktopUninstaller"] = value
                    with self.assertRaises(contract.ContractRefused):
                        self.check()
                    self.package, self.receipt = package, receipt
        self.receipt["uninstallerEvidence"] = "staged-history-only"
        with self.assertRaisesRegex(contract.ContractRefused, "intentionally-absent"):
            self.check()

    def test_uninstaller_refused_in_every_archive_layer(self):
        names = ["Uninstall Mentat.exe", "deep/UNINSTALL MELANGE.EXE", "nested/unins000.exe",
                 "private/Mentat-1.0.22.__uninstaller.exe", "nested\\old-uninstaller.exe"]
        for scope in self.maps:
            for name in names:
                with self.subTest(scope=scope, name=name):
                    self.maps[scope][name] = object()
                    with self.assertRaisesRegex(contract.ContractRefused, "Unexpected uninstaller"):
                        self.check()
                    del self.maps[scope][name]

    def test_signing_history_cannot_hide_a_generated_uninstaller(self):
        for field in ("files", "currentFiles"):
            with self.subTest(field=field):
                self.receipt[field] = [self.row, dict(self.row, path=str(self.installer.parent / "x.__uninstaller.exe"))]
                with self.assertRaisesRegex(contract.ContractRefused, "history contains"):
                    self.check()
                self.receipt[field] = [self.row]

    def test_wrong_application_distribution_or_installer_receipt_refused(self):
        self.package["desktopAppConfig"]["desktopDistribution"] = "directory-zip"
        with self.assertRaisesRegex(contract.ContractRefused, "another distribution"):
            self.check()
        del self.package["desktopAppConfig"]["desktopDistribution"]
        self.receipt["appId"] = "terrier"
        with self.assertRaisesRegex(contract.ContractRefused, "identity"):
            self.check()
        self.receipt["appId"] = "mentat"
        self.receipt["installer"] = str(self.installer.parent / "other.exe")
        with self.assertRaisesRegex(contract.ContractRefused, "different installer"):
            self.check()

    def test_fresh_owned_outer_signature_evidence_is_required(self):
        for field, value in (("status", "NotSigned"), ("thumbprint", "0" * 40), ("timestamped", False)):
            with self.subTest(field=field):
                saved = self.row[field]
                self.row[field] = value
                with self.assertRaisesRegex(contract.ContractRefused, "invalid or stale"):
                    self.check()
                self.row[field] = saved
        self.receipt["currentFiles"] = [self.row, dict(self.row)]
        with self.assertRaisesRegex(contract.ContractRefused, "Duplicate"):
            self.check()
        self.receipt["currentFiles"] = [dict(self.row, path=str(self.installer.parent / "Mentat.exe"))]
        with self.assertRaisesRegex(contract.ContractRefused, "outer-installer.*missing"):
            self.check()

    def test_omitted_payload_census_is_refused(self):
        for scope in self.maps:
            with self.subTest(scope=scope):
                saved = self.maps[scope]
                self.maps[scope] = {}
                with self.assertRaisesRegex(contract.ContractRefused, "Complete inspected"):
                    self.check()
                self.maps[scope] = saved
        del self.maps["app_files"]["Mentat.exe"]
        with self.assertRaisesRegex(contract.ContractRefused, "missing from inspected"):
            self.check()


if __name__ == "__main__":
    unittest.main()
