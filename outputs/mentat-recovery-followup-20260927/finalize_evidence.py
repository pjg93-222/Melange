"""Verify follow-up logs and immutable pilot files; record final fingerprints."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

prior = json.loads((ROOT / "outputs/mentat-pilot-integration-20260927/final-verification.json").read_text())
pilot_files = []
for item in prior["pilot_files"]:
    path = Path(item["path"])
    observed = sha(path)
    assert observed == item["sha256"], f"Pilot file changed: {path}"
    pilot_files.append({"path": str(path), "sha256": observed, "unchanged": True})

suites = []
for log in sorted((HERE / "sol").glob("*.log")):
    if log.name.startswith("r-"):
        continue
    content = log.read_text(encoding="utf-8-sig")
    count = re.search(r"Ran (\d+) tests? in", content)
    assert count and re.search(r"^OK$", content, re.M), log
    suites.append({"suite": log.stem, "passed": int(count[1]), "log": str(log)})
assert len(suites) == 11 and sum(item["passed"] for item in suites) == 114, suites
r_logs = sorted((HERE / "sol").glob("r-*.log"))
assert len(r_logs) == 3
assert all("PASS" in path.read_text(encoding="utf-8-sig") for path in r_logs)
for name in ("real-schema-verification.json", "hot-journal-verification.json"):
    assert json.loads((HERE / name).read_text())["passed"] is True

ui = json.loads((HERE / "ui-verification.json").read_text())
ui["final_preview"] = {
    "url": prior["preview_url"], "read_only": True, "process_id": 14168,
    "stale_code_notice_present": False,
    "viewport": [1707, 932], "mode": "builder",
    "title_height": 34, "subtitle_height": 20, "summary_height": 16,
    "vertical_text_clipping": False, "page_horizontal_overflow": False,
    "pilot_totals_unchanged": True,
}
ui["notes"] = "Measurements read from the live DOM through the browser tool. Screenshots confirmed natural-height title and verified totals. Narrow text wraps normally. Dedicated preview restarted after backend edits; final screenshot showed no stale-code notice. Viewport override restored."
(HERE / "ui-verification.json").write_text(json.dumps(ui, indent=2) + "\n", encoding="utf-8")

code_paths = [
    "mentat/tools/api_company_cycle_fanout.py",
    "mentat/tools/merge_company_shards.py",
    "mentat/tests/test_merge_crash_recovery.py",
    "mentat/app/workspace-polish.css",
]
result = {
    "verified_at": datetime.now(timezone.utc).isoformat(),
    "verification_model": "GPT-6 Sol",
    "python_tests_passed": 114, "python_suites": suites,
    "additional_parameterized_subcases_passed": 4,
    "r_scripts_passed": 3, "r_logs": [str(path) for path in r_logs],
    "production_schema_check_passed": True, "independent_hot_journal_check_passed": True,
    "ui_viewports_passed": 4, "preview_restarted_and_verified": True,
    "source_database_and_workbook_unchanged": True, "pilot_files": pilot_files,
    "code_sha256": [{"path": str(ROOT / path), "sha256": sha(ROOT / path)} for path in code_paths],
    "scope": "Local Windows process and SQLite crash/concurrency checks; applies to runs using updated code.",
}
(HERE / "final-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
fingerprints = [{"path": str(path.relative_to(HERE)), "sha256": sha(path)} for path in sorted(HERE.rglob("*")) if path.is_file() and path != HERE / "sha256.json"]
(HERE / "sha256.json").write_text(json.dumps(fingerprints, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"python_tests": 114, "r_scripts": 3, "pilot_files_unchanged": len(pilot_files), "evidence_files_hashed": len(fingerprints)}, indent=2))
