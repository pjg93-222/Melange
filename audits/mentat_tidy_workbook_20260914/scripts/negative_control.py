"""Negative control: corrupt one receipt in a COPY of the staging store and prove
the writer refuses to publish.

Copies `stage/tidy-cu.sqlite`, adds $1.00 to exactly one
`contributions.analysis_amount`, runs the real writer against the copy, and
records the exit code, the absence of any output file, and the failing
Data Quality rows. The pristine store and the published mock are untouched.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = HERE / "stage" / "tidy-cu.sqlite"
COPY = HERE / "stage" / "tidy-cu-corrupt.sqlite"
OUT = HERE / "out" / "NEGATIVE CONTROL (should not exist).xlsx"
DATABASE = (r"C:\Users\pgoff\Mentat\mentat\.cache\repair-20260908-databases"
            r"\credit_union.db")
PAYLOAD = (r"C:\Users\pgoff\Mentat\mentat\.cache\industry-report\credit_union"
           r"\industry_data-f9e956354525acb0.json")
RECEIPT = (r"C:\Users\pgoff\Mentat\mentat\.cache\industry-report\credit_union"
           r"\workbook_manifest_all_cycles.json")


def main():
    for path in (OUT, Path(str(OUT) + ".receipt.json")):
        path.unlink(missing_ok=True)
    shutil.copy2(SOURCE, COPY)
    connection = sqlite3.connect(COPY)
    with connection:
        victim = connection.execute(
            "SELECT source_id, cycle_label, company, analysis_amount FROM contributions "
            "WHERE include_in_analysis = 1 ORDER BY source_id LIMIT 1").fetchone()
        connection.execute(
            "UPDATE contributions SET analysis_amount = analysis_amount + 1.0 "
            "WHERE source_id = ?", (victim[0],))
    connection.close()
    print(f"corrupted source_id {victim[0]} ({victim[1]}, {victim[2]}): "
          f"analysis_amount {victim[3]} -> {victim[3] + 1.0}")

    completed = subprocess.run(
        [sys.executable, str(HERE / "build_tidy_workbook.py"),
         "--staging", str(COPY), "--out", str(OUT), "--database", DATABASE,
         "--database-sha256",
         "f9e956354525acb069cae220eb8d1538c479eea1bf23df1b3154adee8f416686",
         "--payload", PAYLOAD, "--overview-receipt", RECEIPT],
        capture_output=True, text=True, cwd=str(HERE))
    print(f"\nwriter exit code: {completed.returncode}")
    print("stdout:", completed.stdout.strip() or "(empty)")
    print("stderr:")
    print(completed.stderr.strip())
    print(f"\noutput workbook exists: {OUT.exists()}")
    print(f"pending files left behind: "
          f"{[p.name for p in OUT.parent.glob('*.pending-*')]}")
    receipt_path = Path(str(OUT) + ".receipt.json")
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text())
        failures = [c for c in receipt["checks"]
                    if c["severity"] == "fail" and not c["passed"]]
        print(f"receipt ok={receipt['ok']} sha256={receipt['sha256']}")
        print(f"failing Data Quality rows: {len(failures)}")
        for row in failures:
            print(f"  {row['check_id']}: {row['detail']}")
        passed_w7 = [c for c in receipt["checks"]
                     if c["check_id"] == "database_amount_and_rows" and c["passed"]]
        print(f"W7 database_amount_and_rows rows still passing: {len(passed_w7)} "
              f"(expected: the corruption touched analysis_amount, not amount)")
    COPY.unlink(missing_ok=True)
    return 0 if completed.returncode == 2 and not OUT.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
