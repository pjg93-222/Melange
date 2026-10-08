import pandas as pd, re
p = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congress_bills_archive_20260624_115822.xlsx"
ab = pd.read_excel(p, sheet_name="All Bills")
def norm(s):
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())
abn = ab["Name"].map(norm)
print("=== S.2704 rows ===")
print(ab[abn=="S2704"][["Section","Role","Member","Name","Title","Congress","DecayWeight"]].to_string())

# max bill numbers per chamber per congress
pat = re.compile(r"^(H\.R\.|S\.|H\.RES\.|S\.RES\.|H\.J\.RES\.|S\.J\.RES\.|H\.CON\.RES\.|S\.CON\.RES\.)(\d+)$", re.I)
rows=[]
for nm, cong in zip(ab["Name"].astype(str), ab["Congress"]):
    mm = pat.match(nm.strip())
    if mm: rows.append((mm.group(1).upper(), int(mm.group(2)), cong))
df = pd.DataFrame(rows, columns=["prefix","num","congress"])
print()
print("=== max bill number by prefix x congress ===")
print(df.groupby(["congress","prefix"])["num"].agg(["max","count"]).to_string())
print()
print("=== distinct Name formats not matching pattern (sample) ===")
bad = [n for n in ab["Name"].astype(str).unique() if not pat.match(n.strip())]
print("unmatched distinct:", len(bad), bad[:20])
