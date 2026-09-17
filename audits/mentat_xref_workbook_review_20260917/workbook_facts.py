"""Read-only: cycle-sheet totals grouped by Fact Type, plus Master Overview cycle totals.

Usage: python workbook_facts.py <workbook.xlsx>
No writes.
"""
import sys, re
from decimal import Decimal
from collections import Counter, defaultdict
from openpyxl import load_workbook

path = sys.argv[1]
wb = load_workbook(path, read_only=True, data_only=True)
cycle_re = re.compile(r"^\d{4}-\d{4}$")
for name in wb.sheetnames:
    if not cycle_re.match(name):
        continue
    ws = wb[name]
    rows = ws.iter_rows(values_only=True)
    header = None
    for i, row in enumerate(rows, 1):
        vals = [str(v).strip() if v is not None else "" for v in row]
        if "Amount" in vals and "Fact Type" in vals:
            header = vals
            break
        if i > 12:
            break
    if header is None:
        print(f"[{name}] header NOT FOUND")
        continue
    idx = {h: k for k, h in enumerate(header) if h}
    ft = idx["Fact Type"]; a = idx["Amount"]; aa = idx.get("Analysis Amount"); inc = idx.get("Include in Analysis")
    tier = idx.get("Employee Tier"); cat = idx.get("Recipient Category"); gc = idx.get("Gift Count")
    n = Counter(); amt = defaultdict(Decimal); aamt = defaultdict(Decimal); gifts = defaultdict(Decimal)
    tiers = defaultdict(Counter); cats = defaultdict(Counter)
    for row in rows:
        if row is None or a >= len(row) or row[a] is None or row[a] == "":
            continue
        try:
            d = Decimal(str(row[a]))
        except Exception:
            continue
        f = str(row[ft]) if ft < len(row) else ""
        n[f] += 1; amt[f] += d
        if aa is not None and aa < len(row) and row[aa] not in (None, ""):
            try:
                aamt[f] += Decimal(str(row[aa]))
            except Exception:
                pass
        if gc is not None and gc < len(row) and row[gc] not in (None, ""):
            try:
                gifts[f] += Decimal(str(row[gc]))
            except Exception:
                pass
        if tier is not None and tier < len(row):
            tiers[f][str(row[tier])] += 1
        if cat is not None and cat < len(row):
            cats[f][str(row[cat])] += 1
    print(f"\n[{name}]")
    for f, c in n.most_common():
        print(f"  {f!r}: rows {c}  Amount {amt[f]:,.2f}  AnalysisAmount {aamt[f]:,.2f}  GiftCount {gifts[f]:,.0f}")
        print(f"      tiers: {dict(tiers[f].most_common(6))}")
        print(f"      categories: {dict(cats[f].most_common(12))}")

# Master Overview: print rows that look like totals (first 80 rows, first 12 columns)
for sheet in ("Master Overview", "Spending Overview"):
    if sheet not in wb.sheetnames:
        continue
    ws = wb[sheet]
    print(f"\n[{sheet}] first 12 columns of rows containing 'Total' or 'Cycle' or 'Company' (first 80 rows)")
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=80, max_col=12, values_only=True), 1):
        vals = ["" if v is None else str(v) for v in row]
        joined = " | ".join(vals)
        if any(k in joined for k in ("Total", "Cycle", "Company", "Industry", "Average")):
            print(f"  r{i}: {joined[:260]}")
