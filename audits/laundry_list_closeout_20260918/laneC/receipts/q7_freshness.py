# Lane C / Q7 : artifact inventory + mtimes. READ-ONLY. stdlib only.
import os, json, datetime, hashlib
ROOT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
PATHS = [
    r"ranks_python.json",
    r"category_stance.json",
    r"dashboard_data.json",
    r"archive_leg.json",
    r"legislation_routing_audit.json",
    r"Moneyball Main Version - Blended.xlsx",
    r"Moneyball Dashboard.html",
    r"cu-member-desk.html",
    r"per_topic_alloc.json",
    r"data\lobbying\per_topic_coalition.json",
    r"data\money\budget_frontier.json",
    r"data\money\budget_frontier_electoral.json",
    r"data\legislation\bill_directions.csv",
    r"data\legislation\bill_overrides.csv",
    r"manual_bill_evidence.csv",
    r"congress_bills_archive_20260624_115822.xlsx",
    r"congress_bills_archive_20260825_115305.xlsx",
    r"Sentinel Bill Ledger.xlsx",
    r"backups\bill_directions.PRE-LEGFIX3.csv",
    r"vote_category_lean.json",
    r".pipeline_run.lock",
]
print("== artifact inventory (live root) ==")
print("%-58s %12s  %-23s %s" % ("path", "bytes", "mtime(local)", "sha256[:16]"))
for rel in PATHS:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print("%-58s %12s  %-23s %s" % (rel, "ABSENT", "-", "-"))
        continue
    st = os.stat(p)
    mt = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    h = "n/a"
    if st.st_size < 200_000_000:
        d = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                d.update(chunk)
        h = d.hexdigest()[:16]
    print("%-58s %12d  %-23s %s" % (rel, st.st_size, mt, h))

print()
print("== glob of congress_bills_archive_*.xlsx, sorted(), as the producer sorts it ==")
import glob
g = sorted(glob.glob(os.path.join(ROOT, "congress_bills_archive_*.xlsx")))
for i, p in enumerate(g):
    print("  [%d] %s" % (i, os.path.basename(p)))
print("  SELECTED by [-1] ->", os.path.basename(g[-1]) if g else "NONE")

print()
print("== excel lock files (~$*) at root ==")
for p in glob.glob(os.path.join(ROOT, "~$*")):
    print("  ", os.path.basename(p))
print("  (none listed above == workbook not held open by Excel)")
