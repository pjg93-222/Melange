"""Census of the text-test outcomes in one cross-reference run (read-only).

Usage: python text_census.py <run_dir>
Joins decisions to source_records and prints: contradicted texts per company,
company-named texts, route statuses, own-PAC-as-donor candidates (D4), and
recipient committees resolved through the committee master (D4).
"""
import json, re, sqlite3, sys
from collections import defaultdict

run = sys.argv[1]
con = sqlite3.connect("file:" + run + r"\ledger.sqlite?mode=ro", uri=True)


def tokens(v):
    return " ".join(re.findall(r"[A-Z0-9]+", str(v or "").upper()))


def money(c):
    return f"${c/100:,.2f}"


def stat():
    return dict(rows=0, gross=0)


wanted = {"attribution_contradicted_by_text", "company_named_unverified", "company_attribution_unverified",
          "recipient_connected_organization_resolves_to_company", "role_marker_with_company_named"}
decisions = {}
for sid, pj in con.execute("select source_id, payload_json from decisions"):
    d = json.loads(pj)
    if wanted & set(d["reasons"]) or d.get("attribution_status") in ("recipient_supported", "role_supported"):
        decisions[sid] = d
print("decisions in scope:", len(decisions))
rows = {}
ids = sorted(decisions)
for i in range(0, len(ids), 900):
    chunk = ids[i:i + 900]
    for sid, pj in con.execute("select source_id, payload_json from source_records where source_id in (%s)" % ",".join("?" * len(chunk)), chunk):
        rows.setdefault(sid, json.loads(pj))

contradicted = defaultdict(stat); contradicted_company = defaultdict(stat)
named = defaultdict(stat); named_company = defaultdict(stat)
blank = defaultdict(stat)
status = defaultdict(stat); status_named = defaultdict(stat)
own_pac = defaultdict(stat)
connected = defaultdict(stat)
role = defaultdict(stat)
for sid, d in decisions.items():
    r = rows.get(sid, {})
    amt = abs(int(d["amount_cents"]))
    ent = str(r.get("entity_type") or "").upper()
    company = d["company"]
    text = tokens(r.get("contributor_employer")) if ent == "IND" else tokens(r.get("contributor_name"))
    occ = tokens(r.get("contributor_occupation"))
    reasons = set(d["reasons"])

    def add(s):
        s["rows"] += 1; s["gross"] += amt
    if "attribution_contradicted_by_text" in reasons:
        add(contradicted[(company, ent, text)]); add(contradicted_company[company])
    if "company_named_unverified" in reasons:
        add(named[(company, ent, text)]); add(named_company[company])
        if ent != "IND":
            add(own_pac[(company, ent, text, "has C-id" if re.fullmatch(r"C\d{8}", str(r.get("contributor_id") or "")) else "no C-id", d["bucket"])])
    if "company_attribution_unverified" in reasons:
        add(blank[(company, ent, text or "(blank)")])
    add(status[(d.get("attribution_status"), "named" if "company_named_unverified" in reasons else "unverified" if "company_attribution_unverified" in reasons else "-")])
    if "recipient_connected_organization_resolves_to_company" in reasons:
        add(connected[(company, str(r.get("committee_id") or ""), tokens(r.get("committee_name")))])
    if "role_marker_with_company_named" in reasons:
        add(role[(company, text, occ)])


def show(title, table, limit=None):
    print("\n== " + title + " ==")
    items = sorted(table.items(), key=lambda kv: -kv[1]["gross"])
    for k, s in (items[:limit] if limit else items):
        print(f"  {str(k):110s} rows={s['rows']:6d} gross={money(s['gross']):>16s}")
    print(f"  TOTAL rows={sum(s['rows'] for s in table.values())} gross={money(sum(s['gross'] for s in table.values()))}")


show("attribution_contradicted_by_text per company", contradicted_company)
show("attribution_contradicted_by_text: top texts", contradicted, 60)
show("company_named_unverified per company", named_company)
show("company_named_unverified: top texts", named, 40)
show("company_attribution_unverified (blank / no-employer or recipient-rescued): top texts", blank, 20)
show("attribution_status x text verdict", status)
show("D4 register gap: entity rows naming the company (own PACs/treasury as donors)", own_pac, 40)
show("D4 register gap: recipient committees resolved through the committee master only", connected, 40)
show("role route: top employer/occupation pairs", role, 30)
