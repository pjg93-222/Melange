"""Read-only: summarise named sheets of a Mentat Overview workbook.

Usage: python sheet_summary.py <workbook.xlsx> "Sheet A" "Sheet B" ...
For each sheet: header row number, header list, row count, and per numeric column the sum,
grouped by a Cycle column when one exists. Aggregates only; no row-level output.
"""
import sys
from decimal import Decimal
from collections import defaultdict, Counter
from openpyxl import load_workbook

path = sys.argv[1]
wb = load_workbook(path, read_only=True, data_only=True)
for name in sys.argv[2:]:
    if name not in wb.sheetnames:
        print(f"[{name}] NOT A SHEET"); continue
    ws = wb[name]
    rows = ws.iter_rows(values_only=True)
    header = None; hrow = 0
    for i, row in enumerate(rows, 1):
        vals = [str(v).strip() if v is not None else "" for v in row]
        if sum(1 for v in vals if v) >= 5 and not any(len(v) > 60 for v in vals):
            header = vals; hrow = i; break
        if i > 12: break
    if header is None:
        print(f"[{name}] header NOT FOUND"); continue
    print(f"\n[{name}] header row {hrow} ({len([h for h in header if h])} cols): {header}")
    cyc = next((k for k, h in enumerate(header) if h.lower() == 'cycle'), None)
    sums = defaultdict(lambda: defaultdict(Decimal)); n = Counter(); textcols = defaultdict(Counter)
    for row in rows:
        if row is None or all(v in (None, "") for v in row): continue
        key = str(row[cyc]) if cyc is not None and cyc < len(row) else 'ALL'
        n[key] += 1
        for k, h in enumerate(header):
            if not h or k >= len(row): continue
            v = row[k]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                sums[key][h] += Decimal(str(v))
            elif isinstance(v, str) and len(textcols[h]) < 40:
                textcols[h][v[:40]] += 1
    for key in sorted(n):
        print(f"  cycle={key}: rows {n[key]}")
        for h, s in sums[key].items():
            if abs(s) >= 1000: print(f"     sum {h}: {s:,.2f}")
    for h, c in textcols.items():
        if 1 < len(c) <= 12: print(f"  values of {h}: {dict(c.most_common(12))}")
