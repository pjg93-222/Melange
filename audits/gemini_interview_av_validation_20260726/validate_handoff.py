#!/usr/bin/env python3
"""Fail-closed validation for the machine-prepared human annotation packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "validation_manifest_150.json"
RECEIPTS = HERE / "media_receipts_150.json"
MEDIA = HERE / "media"
STORYBOARDS = HERE / "storyboards"
DEFAULT_WORKBOOK = (
    HERE
    / "outputs"
    / "019fa014-1de3-7111-a692-280ee4652bbd"
    / "interview_av_validation_150.xlsx"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    args = parser.parse_args()
    errors = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = manifest.get("items", [])
    case_ids = [row["case_id"] for row in items]
    if len(items) != 150 or len(set(case_ids)) != 150:
        errors.append("manifest must contain 150 unique cases")
    if manifest.get("production_consumers") != 0:
        errors.append("manifest production_consumers must remain zero")
    receipts = json.loads(RECEIPTS.read_text(encoding="utf-8"))
    if receipts.get("manifest_sha256") != sha256_file(MANIFEST):
        errors.append("media receipts do not match frozen manifest")
    receipt_by_id = {row["case_id"]: row for row in receipts.get("items", [])}
    for case_id in case_ids:
        receipt = receipt_by_id.get(case_id)
        media = MEDIA / f"{case_id}.mp4"
        storyboard = STORYBOARDS / f"{case_id}.jpg"
        if not receipt or receipt.get("status") not in {
            "downloaded_verified",
            "existing_verified",
        }:
            errors.append(f"{case_id}: missing verified receipt")
        elif not media.is_file():
            errors.append(f"{case_id}: media missing")
        elif receipt.get("sha256") != sha256_file(media):
            errors.append(f"{case_id}: media hash mismatch")
        if not storyboard.is_file():
            errors.append(f"{case_id}: storyboard missing")
    if not args.workbook.is_file():
        errors.append(f"workbook missing: {args.workbook}")
    else:
        try:
            with zipfile.ZipFile(args.workbook) as archive:
                if "xl/workbook.xml" not in archive.namelist():
                    errors.append("workbook is not a valid xlsx package")
        except zipfile.BadZipFile:
            errors.append("workbook is not a valid zip/xlsx file")
    result = {
        "status": "PASS" if not errors else "FAIL",
        "case_count": len(items),
        "verified_receipts": sum(
            row.get("status") in {"downloaded_verified", "existing_verified"}
            for row in receipt_by_id.values()
        ),
        "media_files": len(list(MEDIA.glob("V*.mp4"))),
        "storyboards": len(list(STORYBOARDS.glob("V*.jpg"))),
        "workbook": str(args.workbook),
        "errors": errors[:50],
        "error_count": len(errors),
    }
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
