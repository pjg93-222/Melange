#!/usr/bin/env python3
"""Build a deterministic text/hint overlay for captured PDF evidence."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from public_history_scraper import evidence_hints, read_ndjson


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(path_value: str, workspace: Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else workspace / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-ledger", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--per-pdf-timeout", type=float, default=15.0)
    args = parser.parse_args()

    capture_ledger = Path(args.capture_ledger).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    workspace = Path(__file__).resolve().parents[2]
    text_root = output_root / "text"
    text_root.mkdir(parents=True, exist_ok=True)

    overlay = output_root / "pdf_text_repair_overlay.ndjson"
    receipt_path = output_root / "pdf_text_repair_overlay_receipt.json"
    existing_repairs = {
        row["url"]: row for row in read_ndjson(overlay)
    } if overlay.exists() else {}
    cached_failures: dict[str, str] = {}
    if receipt_path.exists():
        previous_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        cached_failures = {
            item["url"]: item["reason"]
            for item in previous_receipt.get("failures", [])
        }

    repairs: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    pdf_rows = 0
    pdf_inputs: list[tuple[dict[str, Any], Path]] = []
    for row in read_ndjson(capture_ledger):
        content_type = str(row.get("content_type") or "")
        raw_value = row.get("raw_path")
        if not raw_value:
            continue
        raw_path = resolve(str(raw_value), workspace)
        is_pdf = "pdf" in content_type.lower()
        if not is_pdf and raw_path.exists():
            with raw_path.open("rb") as stream:
                is_pdf = stream.read(5) == b"%PDF-"
        if not is_pdf:
            continue
        pdf_rows += 1
        if row["url"] in existing_repairs:
            repairs.append(existing_repairs[row["url"]])
            continue
        if row["url"] in cached_failures:
            failures.append({"url": row["url"], "reason": cached_failures[row["url"]]})
            continue
        if not raw_path.exists():
            failures.append({"url": row["url"], "reason": "RAW_PATH_MISSING"})
            continue
        pdf_inputs.append((row, raw_path))

    worker_root = output_root / "worker_text"
    worker_root.mkdir(parents=True, exist_ok=True)
    worker_script = Path(__file__).resolve().parent / "extract_pdf_text_worker.py"

    def extract(item: tuple[dict[str, Any], Path]) -> tuple[dict[str, Any], Path, str | None]:
        row, raw_path = item
        target = worker_root / f"{hashlib.sha256(row['url'].encode('utf-8')).hexdigest()}.txt"
        if target.exists():
            return row, target, None
        try:
            subprocess.run(
                [
                    sys.executable,
                    str(worker_script),
                    "--input", str(raw_path),
                    "--output", str(target),
                    "--max-pages", "100",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=args.per_pdf_timeout,
            )
            return row, target, None
        except subprocess.TimeoutExpired:
            return row, target, "EXTRACTION_TIMEOUT"
        except subprocess.CalledProcessError:
            return row, target, "EXTRACTION_FAILED"

    extracted_rows: list[tuple[dict[str, Any], Path]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(extract, item) for item in pdf_inputs]
        for future in as_completed(futures):
            row, target, error = future.result()
            if error:
                failures.append({"url": row["url"], "reason": error})
            else:
                extracted_rows.append((row, target))

    for row, target in sorted(extracted_rows, key=lambda item: item[0]["url"]):
        text = target.read_text(encoding="utf-8")
        text_bytes = text.encode("utf-8")
        text_hash = hashlib.sha256(text_bytes).hexdigest()
        text_path = text_root / f"{text_hash}.txt"
        if not text_path.exists():
            text_path.write_bytes(text_bytes)
        repairs.append({
            "schema_id": "staffer-network-pdf-text-repair-overlay-v1",
            "url": row["url"],
            "text_bytes": len(text_bytes),
            "text_sha256": text_hash,
            "text_path": str(text_path),
            "title": row.get("title"),
            "hints": evidence_hints(text),
            "text_extraction_method": "PYPDF",
            "raw_content_sha256": row.get("content_sha256"),
            "canonical_eligible": False,
        })

    repairs.sort(key=lambda item: item["url"])
    overlay.write_text("".join(compact(row) + "\n" for row in repairs), encoding="utf-8", newline="\n")
    receipt = {
        "schema_id": "staffer-network-pdf-text-repair-overlay-receipt-v1",
        "status": "PASS" if not failures else "PASS_WITH_GAPS",
        "capture_ledger": {"path": str(capture_ledger), "sha256": sha256(capture_ledger)},
        "pdf_capture_count": pdf_rows,
        "repair_count": len(repairs),
        "failure_count": len(failures),
        "failures": failures,
        "canonical_promotions": 0,
        "output": {"path": overlay.name, "bytes": overlay.stat().st_size, "sha256": sha256(overlay)},
    }
    receipt_path.write_text(compact(receipt) + "\n", encoding="utf-8", newline="\n")
    print(compact(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
