#!/usr/bin/env python3
"""Extract page-delimited text from research PDFs for reproducible review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pypdf import PdfReader


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdfs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    receipts = []
    for source in args.pdfs:
        source = source.resolve()
        reader = PdfReader(source)
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            pages.append(
                f"\n\n===== PDF PAGE {page_number} =====\n\n"
                + (page.extract_text() or "")
            )
        output = args.output_dir / f"{source.stem}.txt"
        output.write_text("".join(pages), encoding="utf-8")
        receipts.append(
            {
                "source": str(source),
                "output": str(output.resolve()),
                "pages": len(reader.pages),
                "characters": sum(len(page) for page in pages),
                "metadata": {
                    str(key): str(value)
                    for key, value in (reader.metadata or {}).items()
                },
            }
        )
    print(json.dumps(receipts, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
