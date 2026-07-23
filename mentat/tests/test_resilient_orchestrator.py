from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    PROJECT_ROOT
    / "tools"
    / "parallel"
    / "Start-MentatResilientIndustryReports.ps1"
)
POWERSHELL = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)


@unittest.skipUnless(POWERSHELL.is_file(), "Windows PowerShell is unavailable")
class ResilientOrchestratorTests(unittest.TestCase):
    def test_powershell_parser_accepts_script(self) -> None:
        command = (
            "$text=Get-Content -LiteralPath "
            f"'{str(SCRIPT).replace(chr(39), chr(39) * 2)}' -Raw;"
            "$tokens=$null;$errors=$null;"
            "[void][Management.Automation.Language.Parser]::ParseInput("
            "$text,[ref]$tokens,[ref]$errors);"
            "if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1}"
        )
        result = subprocess.run(
            [
                str(POWERSHELL),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            cwd=PROJECT_ROOT.parent,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_plan_only_counts_numbered_keys_and_comma_industries(self) -> None:
        environment = os.environ.copy()
        environment.pop("FEC_API_KEY", None)
        environment.pop("FEC_API_KEYS", None)
        for name in list(environment):
            if name.startswith("FEC_API_KEY_"):
                environment.pop(name)
        environment["FEC_API_KEY_1"] = "synthetic-key-one"
        environment["FEC_API_KEY_2"] = "synthetic-key-two"
        result = subprocess.run(
            [
                str(POWERSHELL),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT),
                "-Industries",
                "Fintech,Crypto",
                "-PlanOnly",
            ],
            cwd=PROJECT_ROOT.parent,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["industries"], ["Fintech", "Crypto"])
        self.assertEqual(plan["recovery_workers"], 1)
        self.assertEqual(plan["resources"]["key_count"], 2)
        self.assertGreaterEqual(plan["resources"]["effective_api_lanes"], 1)
        self.assertLessEqual(plan["resources"]["effective_api_lanes"], 2)
        self.assertEqual(plan["resources"]["fanout_max_parallel"], 0)
        self.assertEqual(
            plan["resources"]["allocation_mode"],
            "live_auto_each_industry",
        )
        self.assertIn("workbook generators overlap", plan["strategy"])

    def test_plan_only_rejects_more_than_six_industries(self) -> None:
        environment = os.environ.copy()
        environment["FEC_API_KEY"] = "synthetic-key"
        result = subprocess.run(
            [
                str(POWERSHELL),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT),
                "-Industries",
                "A,B,C,D,E,F,G",
                "-PlanOnly",
            ],
            cwd=PROJECT_ROOT.parent,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("at most six industries", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
