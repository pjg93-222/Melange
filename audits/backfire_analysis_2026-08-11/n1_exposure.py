# -*- coding: utf-8 -*-
"""READ-ONLY N1: member x sector lobbying-exposure matrix from LobbyView raw.

network.csv: lob_id, bioguide_id, year, n_bills (10.9M rows)
clients.csv: lob_id -> client name
sector resolution: sector_spend.ROSTERS (the shipped shared resolver)
"""
import csv, json, os, sys
from collections import defaultdict

sys.path.insert(0, r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec")
from lobbying import sector_spend as SS

RAW = r"C:\Users\pgoff\AppData\Local\Melange\lobbyview\raw"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exposure_matrix.json")

# 1. client -> sector (resolve each unique client name once)
lob_sector = {}
n_clients = 0
with open(os.path.join(RAW, "clients.csv"), encoding="utf-8-sig", newline="") as h:
    for row in csv.DictReader(h):
        n_clients += 1
        name = (row.get("client_name") or row.get("name") or "").strip()
        lob_id = (row.get("lob_id") or "").strip()
        if not name or not lob_id:
            continue
        try:
            matches, _ = SS._match_client(
                {"client": {"name": name}, "filing_year": 2024, "filing_uuid": lob_id},
                SS.DEFAULT_SECTORS,
            )
        except Exception:
            continue
        if matches:
            lob_sector[lob_id] = matches[0]["sector"]
print("clients: %d | sector-resolved lob_ids: %d" % (n_clients, len(lob_sector)))

# 2. stream network.csv, aggregate member x sector
bioguide_member = {}
cong = json.load(open(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\data\engine\congestion.json", encoding="utf-8-sig"))
for row in cong:
    if row.get("bioguide"):
        bioguide_member[row["bioguide"]] = row["member"]

exposure = defaultdict(lambda: defaultdict(float))
years = defaultdict(int)
rows = kept = 0
with open(os.path.join(RAW, "network.csv"), encoding="utf-8-sig", newline="") as h:
    reader = csv.reader(h)
    header = next(reader)
    idx = {name: i for i, name in enumerate(header)}
    li, bi, yi, ni = idx["lob_id"], idx["bioguide_id"], idx["year"], idx["n_bills"]
    for row in reader:
        rows += 1
        sector = lob_sector.get(row[li])
        if not sector:
            continue
        member = bioguide_member.get(row[bi])
        if not member:
            continue
        try:
            n = float(row[ni])
            year = int(row[yi])
        except ValueError:
            continue
        if year < 2021:
            continue
        exposure[member][sector] += n
        years[year] += 1
        kept += 1
print("network rows: %d | kept (sector+member+2021-2026): %d" % (rows, kept))
print("year distribution:", dict(sorted(years.items())))
print("members with any exposure: %d" % len(exposure))

json.dump({m: dict(s) for m, s in exposure.items()}, open(OUT, "w", encoding="utf-8"))
print("wrote", OUT)
