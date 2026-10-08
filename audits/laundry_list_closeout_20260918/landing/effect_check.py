# Read-only: did each landed fix take effect in the artifacts the chain just wrote?
import json, os, sys, glob
LIVE = sys.argv[1]
def find(name):
    for d in ("", "data/legislation", "data/stance", "data/members", "data/engine", "data/surfaces", "data/press"):
        p = os.path.join(LIVE, d, name)
        if os.path.exists(p): return p
    hits = glob.glob(os.path.join(LIVE, "data", "*", name)); return hits[0] if hits else None
def load(name):
    p = find(name)
    return (json.load(open(p, encoding="utf-8")), p) if p else (None, None)
ra, p = load("legislation_routing_audit.json")
if ra:
    rows = ra.get("rows") if isinstance(ra, dict) else ra
    syn = [r for r in rows if r.get("evidence_source") == "archive-sponsor-column"]
    print("N4 routing audit:", os.path.relpath(p, LIVE), "| rows", len(rows), "| synthesised sponsor rows", len(syn))
    for r in syn: print("    ", r.get("member_source"), "|", r.get("bill"), r.get("congress"), "|", r.get("effective_category") or r.get("source_section"), "|", r.get("disposition"), "| contribution", r.get("contribution"))
al, p = load("archive_leg.json")
if al:
    leg = al.get("leg") or al.get("matrix") or al
    ts = leg.get("Tim Scott") if isinstance(leg, dict) else None
    print("N4 archive_leg Tim Scott / Member Business Lending:", (ts or {}).get("Member Business Lending") if isinstance(ts, dict) else "UNKNOWN-SHAPE", "(was 10.76; predicted 17.00)")
pm, p = load("press_component_meta.json")
if pm:
    t = pm.get("tone_ingest_dedup") or {}
    print("A5 press meta tone_ingest_dedup:", {k: v for k, v in t.items() if k != "duplicate_url_form_rows"})
mr, p = load("member_references.json")
if mr:
    print("R1 member_references: edges", len(mr.get("edges", [])), "| drawn (n_scored>=2)", sum(1 for e in mr.get("edges", []) if (e.get("n_scored") or 0) >= 2), "| admission_filters:", json.dumps((mr.get("admission_filters") or {}).get("excluded")), "| dials", (mr.get("admission_filters") or {}).get("dials"))
db, p = load("member_desk_bundle.json")
if db:
    ma = db.get("media_audit") or (db.get("meta") or {}).get("media_audit") or {}
    led = ma.get("press_source_ledger") or {}
    print("N1a desk press ledger:", {k: v for k, v in led.items() if k != "press_engine_tone_dedup"} or "NOT FOUND in bundle top-level/meta")
    print("     media_audit press keys:", {k: v for k, v in ma.items() if k.startswith("press_") and not isinstance(v, dict)})
for n in ("ranks_python.json", "category_stance.json", "dashboard_data.json", "member_desk_bundle.json", "member_references.json", "Moneyball Dashboard.html", "cu-member-desk.html", "Moneyball.html"):
    q = find(n); 
    if q: 
        import time; print("  mtime %-28s %s" % (n, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(q)))))
