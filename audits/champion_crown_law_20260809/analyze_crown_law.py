# -*- coding: utf-8 -*-
"""Crown-law verification: normalized byte-equivalence, member-level board diff
with falsifiable expectations, standalone negative control of the two new
audit checks, and isolation confirmation. Stdlib only; reads artifacts only.

Run from the worktree root:  python audits\\champion_crown_law_20260809\\analyze_crown_law.py
"""
import hashlib
import json
import os
import sys

EV = os.path.dirname(os.path.abspath(__file__))
LIVE_TREE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
LIVE_BOARDS = os.path.join(
    os.environ["LOCALAPPDATA"], "Melange", "lda_rebuild", "derived",
    "champions_v2", "boards.json")
LIVE_BUNDLE = os.path.join(LIVE_TREE, "member_desk_bundle.json")
LIVE_SHA_AT_START = "C160D1A66344EA24ABBFEC5F6911171BAF9ED7045F9B75BD48DC47EF406CA2D6"

SECTORS = ("credit_union", "bank", "crypto", "fintech")
BOARDS = ("champions", "threats", "mixed")

results = []


def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": detail})
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name,
                        (" :: " + detail) if detail else ""))


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def normalized_bytes(doc):
    doc = dict(doc)
    doc.pop("generated_utc", None)
    return (json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=1)
            + "\n").encode("utf-8")


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest().upper()


def row_key(row):
    return row["bioguide"]


def rows_by_id(doc, sector, board):
    return {row_key(r): r for r in doc["sectors"][sector][board]}


base = load(os.path.join(EV, "baseline_boards.json"))
rule = load(os.path.join(EV, "rule_boards.json"))
live = load(LIVE_BOARDS)
bundle = load(LIVE_BUNDLE)

# --- Gate 3: normalized byte-equivalence of baseline vs live artifact -------
check("baseline == live artifact (generated_utc excluded)",
      normalized_bytes(base) == normalized_bytes(live),
      "raw live sha " + sha256(LIVE_BOARDS))

# --- Board-level diff -------------------------------------------------------
moves = {}
changed_rows = []
for sector in SECTORS:
    for board in BOARDS:
        b_rows, r_rows = rows_by_id(base, sector, board), rows_by_id(rule, sector, board)
        removed = sorted(set(b_rows) - set(r_rows))
        added = sorted(set(r_rows) - set(b_rows))
        moves[(sector, board)] = (removed, added)
        for bid in sorted(set(b_rows) & set(r_rows)):
            if (json.dumps(b_rows[bid], sort_keys=True)
                    != json.dumps(r_rows[bid], sort_keys=True)):
                changed_rows.append((sector, board, bid))

cu_removed, cu_added = moves[("credit_union", "threats")]
check("E1a CU threats: exactly Waters removed", cu_removed == ["W000187"],
      "removed=" + ",".join(cu_removed))
backfill = [(b, rows_by_id(rule, "credit_union", "threats")[b]["name"],
             rows_by_id(rule, "credit_union", "threats")[b]["threat"])
            for b in cu_added]
check("E1b CU threats: backfill <= 1 entrant", len(cu_added) <= 1,
      "entrant=" + json.dumps(backfill))
negctl = ["D000563", "B001277", "S000033", "W000817", "B001288"]
present = [b for b in negctl if b in rows_by_id(rule, "credit_union", "threats")]
check("E1c CU threats: Durbin/Blumenthal/Sanders/Warren/Booker retained",
      present == negctl, "present=" + ",".join(present))

mx_removed, mx_added = moves[("credit_union", "mixed")]
waters = rows_by_id(rule, "credit_union", "mixed").get("W000187")
check("E2a CU mixed: exactly Waters added", mx_added == ["W000187"] and not mx_removed,
      "added=%s removed=%s" % (",".join(mx_added), ",".join(mx_removed)))
check("E2b CU mixed Waters row values",
      bool(waters) and waters["tier"] == 1
      and waters["components"]["opposition_att"] == 3
      and waters["components"]["opp_sponsored"] == 1
      and abs(waters["threat"] - 2.484746) < 1e-9,
      json.dumps({k: waters[k] for k in ("tier", "threat")}) if waters else "MISSING")

bk_removed, bk_added = moves[("bank", "threats")]
check("E3a bank threats: exactly Scott removed", bk_removed == ["S001184"],
      "removed=" + ",".join(bk_removed))
check("E3b bank threats: Barr + Sessions retained",
      all(b in rows_by_id(rule, "bank", "threats") for b in ("B001282", "S000250")),
      "count %d -> %d, added=%s" % (len(rows_by_id(base, "bank", "threats")),
                                    len(rows_by_id(rule, "bank", "threats")),
                                    ",".join(bk_added) or "none"))

bm_removed, bm_added = moves[("bank", "mixed")]
scott = rows_by_id(rule, "bank", "mixed").get("S001184")
check("E4 bank mixed: exactly Scott added, opposition_att >= 3",
      bm_added == ["S001184"] and not bm_removed and bool(scott)
      and scott["components"]["opposition_att"] >= 3,
      "opposition_att=%s" % (scott["components"]["opposition_att"] if scott else "MISSING"))

quiet = [(s, b) for s in ("crypto", "fintech") for b in BOARDS
         if moves[(s, b)] != ([], [])]
check("E5 crypto + fintech boards unchanged", not quiet, repr(quiet))

champ_moves = [(s,) + moves[(s, "champions")] for s in SECTORS
               if moves[(s, "champions")] != ([], [])]
check("E6 champions boards unchanged in all sectors", not champ_moves, repr(champ_moves))

exp_receipt = {"credit_union": [("W000187", "mixed")], "bank": [("S001184", "mixed")],
               "crypto": [], "fintech": []}
got_receipt = {s: [(e["bioguide"], e["routed_to"])
                   for e in rule["receipt"]["sectors"][s]["crown_threat_exclusions"]]
               for s in SECTORS}
check("E7a receipts: crown_threat_exclusions exactly Waters(CU)+Scott(bank), routed mixed",
      got_receipt == exp_receipt, json.dumps(got_receipt))
check("E7b receipts: rules.champion_exclusivity present + baseline lacks it",
      "champion_exclusivity" in rule["receipt"]["rules"]
      and "champion_exclusivity" not in base["receipt"]["rules"])
check("E8 no retained row changed anywhere", not changed_rows, repr(changed_rows[:5]))

# --- Standalone negative control of the two audit checks --------------------
def audit_check_1(doc):
    return [(s, r["name"]) for s in SECTORS for r in doc["sectors"][s]["threats"]
            if int(r.get("tier") or 0) == 1]


def audit_check_2(doc):
    crowns = {str((m.get("bio") or {}).get("bioguide") or "").strip()
              for m in bundle["members"] if int(m.get("tier") or 0) == 1}
    crowns.discard("")
    return [(s, r["name"]) for s in SECTORS for r in doc["sectors"][s]["threats"]
            if r["bioguide"] in crowns]


flag1_base, flag2_base = audit_check_1(base), audit_check_2(base)
flag1_rule, flag2_rule = audit_check_1(rule), audit_check_2(rule)
expected_flags = [("credit_union", "Maxine Waters"), ("bank", "Tim Scott")]
check("NC1 audit check 1 FLAGS baseline exactly Waters(CU)+Scott(bank)",
      sorted(flag1_base) == sorted(expected_flags), json.dumps(flag1_base))
check("NC2 audit check 2 FLAGS baseline exactly Waters(CU)+Scott(bank)",
      sorted(flag2_base) == sorted(expected_flags), json.dumps(flag2_base))
check("NC3 both audit checks PASS clean on rule artifact",
      not flag1_rule and not flag2_rule,
      json.dumps({"c1": flag1_rule, "c2": flag2_rule}))

# --- Isolation --------------------------------------------------------------
check("ISO live artifact untouched (sha unchanged since run start)",
      sha256(LIVE_BOARDS) == LIVE_SHA_AT_START)

ok = all(r["ok"] for r in results)
receipt = {
    "run": "champion_crown_law_20260809",
    "all_pass": ok,
    "board_counts": {
        "baseline": {b: sum(len(base["sectors"][s][b]) for s in SECTORS) for b in BOARDS},
        "rule": {b: sum(len(rule["sectors"][s][b]) for s in SECTORS) for b in BOARDS},
    },
    "cu_threat_backfill_entrant": backfill,
    "checks": results,
}
with open(os.path.join(EV, "diff_receipt.json"), "w", encoding="utf-8") as handle:
    json.dump(receipt, handle, ensure_ascii=False, sort_keys=True, indent=1)
print("\nALL PASS" if ok else "\nFAILURES PRESENT")
sys.exit(0 if ok else 1)
