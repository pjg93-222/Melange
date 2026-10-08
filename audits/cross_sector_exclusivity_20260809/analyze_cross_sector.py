# -*- coding: utf-8 -*-
"""Cross-sector exclusivity (champion seat yields) verification: board diff with
falsifiable expectations + standalone negative control of the new audit check.
Stdlib only; reads the two evidence artifacts only.
"""
import json
import os
import sys

EV = os.path.dirname(os.path.abspath(__file__))
SECTORS = ("credit_union", "bank", "crypto", "fintech")
BOARDS = ("champions", "threats", "mixed")

EXPECT_STRIPS = {
    "credit_union": {"B001282": "Andy Barr", "S000250": "Pete Sessions"},
    "bank": {"B001277": "Richard Blumenthal", "D000563": "Richard Durbin",
             "S000033": "Bernard Sanders", "W000817": "Elizabeth Warren"},
    "crypto": {"B001288": "Cory Booker"},
    "fintech": {},
}

results = []


def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": detail})
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name,
                        (" :: " + detail) if detail else ""))


def load(name):
    with open(os.path.join(EV, name), encoding="utf-8") as handle:
        return json.load(handle)


def ids(doc, sector, board):
    return [r["bioguide"] for r in doc["sectors"][sector][board]]


base, rule = load("baseline_boards.json"), load("rule_boards.json")

extras_report = {}
for sector in SECTORS:
    b_ch, r_ch = set(ids(base, sector, "champions")), set(ids(rule, sector, "champions"))
    removed = b_ch - r_ch
    added = r_ch - b_ch
    expect = set(EXPECT_STRIPS[sector])
    check("E1 %s champions: expected strips removed" % sector,
          expect <= removed and not (removed - expect - added),
          "removed=%s added(backfill)=%s" % (sorted(removed), sorted(added)))

check("E2 Scott keeps CU + crypto champions seats (crown path)",
      "S001184" in ids(rule, "credit_union", "champions")
      and "S001184" in ids(rule, "crypto", "champions"))

for board in ("threats", "mixed"):
    same = all(
        json.dumps(base["sectors"][s][board], sort_keys=True)
        == json.dumps(rule["sectors"][s][board], sort_keys=True)
        for s in SECTORS)
    check("E3/E4 %s boards byte-identical in all sectors" % board, same)

seen = {}
for sector in SECTORS:
    entries = {e["bioguide"]: e for e in
               rule["receipt"]["sectors"][sector]["cross_sector_exclusions"]}
    for bid, name in EXPECT_STRIPS[sector].items():
        entry = entries.get(bid)
        ok = bool(entry) and entry["routed_to"] == "omitted" and entry["threat_sectors"]
        check("E5 receipt %s: %s stripped + threat_sectors=%s" %
              (sector, name, entry["threat_sectors"] if entry else "-"), ok)
    extras = sorted(set(entries) - set(EXPECT_STRIPS[sector]))
    if extras:
        extras_report[sector] = [
            {"bioguide": b, "name": entries[b]["name"],
             "threat_sectors": entries[b]["threat_sectors"],
             "composite": entries[b]["composite"]} for b in extras]
print("below-cap class-level strips (legitimate, receipt-only):",
      json.dumps(extras_report, sort_keys=True))

surviving_drift = []
for sector in SECTORS:
    b_rows = {r["bioguide"]: r for r in base["sectors"][sector]["champions"]}
    r_rows = {r["bioguide"]: r for r in rule["sectors"][sector]["champions"]}
    for bid in set(b_rows) & set(r_rows):
        if json.dumps(b_rows[bid], sort_keys=True) != json.dumps(r_rows[bid], sort_keys=True):
            surviving_drift.append((sector, bid))
check("E6 surviving champions rows content-identical", not surviving_drift,
      repr(surviving_drift[:5]))

check("E7 rules.cross_sector present in rule, absent in baseline",
      "cross_sector" in rule["receipt"]["rules"]
      and "cross_sector" not in base["receipt"]["rules"])


def audit_cross_check(doc):
    threat_bios = {r["bioguide"] for s in SECTORS for r in doc["sectors"][s]["threats"]}
    return [(s, r["name"]) for s in SECTORS for r in doc["sectors"][s]["champions"]
            if r["bioguide"] in threat_bios]


flags_base = audit_cross_check(base)
expected_names = sorted(
    (s, EXPECT_STRIPS[s][b]) for s in SECTORS for b in EXPECT_STRIPS[s])
check("E8a audit cross-check FLAGS baseline exactly the 7 visible pairs",
      sorted(flags_base) == expected_names, json.dumps(sorted(flags_base)))
check("E8b audit cross-check clean on rule artifact",
      not audit_cross_check(rule), json.dumps(audit_cross_check(rule)))

counts = {which: {b: sum(len(doc["sectors"][s][b]) for s in SECTORS) for b in BOARDS}
          for which, doc in (("baseline", base), ("rule", rule))}
check("E9 totals: champions 134->133, threats 30->30, mixed 110->110",
      counts == {"baseline": {"champions": 134, "threats": 30, "mixed": 110},
                 "rule": {"champions": 133, "threats": 30, "mixed": 110}},
      json.dumps(counts))

ok = all(r["ok"] for r in results)
with open(os.path.join(EV, "diff_receipt.json"), "w", encoding="utf-8") as handle:
    json.dump({"run": "cross_sector_exclusivity_20260809", "all_pass": ok,
               "board_counts": counts, "class_level_extras": extras_report,
               "checks": results}, handle, ensure_ascii=False, sort_keys=True, indent=1)
print("\nALL PASS" if ok else "\nFAILURES PRESENT")
sys.exit(0 if ok else 1)
