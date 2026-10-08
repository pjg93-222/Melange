#!/usr/bin/env python3
"""Extract PDF text in a disposable process controlled by a parent timeout."""

from __future__ import annotations

import argparse
from pathlib import Path

from pypdf import PdfReader


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-pages", type=int, default=250)
    args = parser.parse_args()

    reader = PdfReader(args.input, strict=False)
    pages = []
    for index, page in enumerate(reader.pages):
        if index >= args.max_pages:
            break
        extracted = page.extract_text() or ""
        if extracted.strip():
            pages.append(extracted)
    Path(args.output).write_text("\n".join(pages), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
