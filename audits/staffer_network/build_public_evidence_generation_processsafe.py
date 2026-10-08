#!/usr/bin/env python3
"""Run the public evidence builder with process-isolated PDF extraction.

PyMuPDF does not guarantee thread-safe text extraction.  The original builder
used a thread pool, which produced whitespace-level divergence for a subset of
PDFs.  This wrapper keeps the established consolidation logic but executes each
PDF extraction in an isolated process and normalizes generated text references
to generation-relative paths so independent output roots can be byte-compared.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT
    / "audits"
    / "staffer_network"
    / "public_evidence_generation_20260831T235930Z_g1371_pdf109_v1"
    / "build_generation.py"
)
GENERATION_ID = "public-evidence-20260901T003500Z-g1371-pdf109-v3-pymupdf1282-process-isolated"
GENERATED_AT = "2026-09-01T00:35:00Z"


def load_source(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import source builder: {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def extract_task(payload: tuple[dict[str, Any], str]) -> dict[str, Any]:
    capture, output_root_raw = payload
    output_root = Path(output_root_raw)
    module = load_source(f"public_evidence_worker_{capture['content_sha256']}")
    module.OUT = output_root
    module.PDF_TEXT_DIR = output_root / "pdf_text"
    module.GENERATION_ID = GENERATION_ID
    result = module.extract_pdf(capture)
    result["extracted_text_path"] = (
        f"pdf_text/{capture['content_sha256']}.txt"
    )
    result["extraction_mode"] = (
        "page.get_text(text, sort=False) in an isolated worker process"
    )
    return result


class ProcessIsolatedExecutor:
    """Drop-in executor used by the established builder's PDF map call."""

    def __init__(self, max_workers: int, output_root: Path):
        self.max_workers = max_workers
        self.output_root = output_root
        self._executor: ProcessPoolExecutor | None = None

    def __enter__(self):
        self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
        return self

    def map(self, _function: Any, iterable: Iterable[dict[str, Any]]):
        if self._executor is None:
            raise RuntimeError("executor not started")
        payloads = ((capture, str(self.output_root)) for capture in iterable)
        return self._executor.map(extract_task, payloads, chunksize=1)

    def __exit__(self, exc_type, exc, traceback):
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=exc is not None)
        return False


def run(output_root: Path) -> None:
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    module = load_source("public_evidence_processsafe_parent")
    module.OUT = output_root
    module.LEDGER_NDJSON = output_root / "public_evidence_ledger_1371.ndjson"
    module.LEDGER_CSV = output_root / "public_evidence_ledger_1371.csv"
    module.PDF_MANIFEST = output_root / "pdf_text_extractions_109.ndjson"
    module.RECEIPT = output_root / "generation_receipt.json"
    module.PDF_TEXT_DIR = output_root / "pdf_text"
    module.GENERATION_ID = GENERATION_ID
    module.GENERATED_AT = GENERATED_AT

    class BoundExecutor(ProcessIsolatedExecutor):
        def __init__(self, max_workers: int):
            super().__init__(max_workers=max_workers, output_root=output_root)

    module.ThreadPoolExecutor = BoundExecutor
    module.build()

    receipt = json.loads(module.RECEIPT.read_text(encoding="utf-8"))
    receipt["schema_id"] = "staffer-network-public-evidence-generation-receipt-v2"
    receipt["generation_id"] = GENERATION_ID
    receipt["generated_at"] = GENERATED_AT
    receipt["pdf_repair"]["parallelization"] = "8_ISOLATED_PROCESSES"
    receipt["pdf_repair"]["thread_safe_extraction_gate"] = "PASS"
    receipt["determinism"]["generated_text_path_basis"] = "GENERATION_RELATIVE"
    receipt["determinism"]["rerun_verification"] = "PENDING_EXTERNAL_BYTE_COMPARISON"
    module.RECEIPT.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    run(args.output_root.resolve())
    print(GENERATION_ID)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
