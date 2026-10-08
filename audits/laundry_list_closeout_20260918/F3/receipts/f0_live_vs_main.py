# F3 r0: verify the task's live-vs-main premise with line-ending normalization.
# READ-ONLY. Uses `git show` (a read-only git command) into memory only.
import subprocess, hashlib, os, sys, datetime

WT   = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\unfinished-work-handoff-a3bbad"
LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"

CANDIDATES = [
    "fec/stance/per_category_stance.py",
    "fec/stance/build_media_blend.py",
    "fec/stance/press_stream.py",       # task named this path
    "fec/press_stream.py",              # actual live path
    "fec/stance/workbook_stance_views.py",
    "fec/moneyball_core.py",
    "fec/surfaces/build_dashboard_bundle.py",
    "fec/stance/media_rules.py",
    "fec/stance/stance_rules.py",
    "fec/stance/press_stance_stack.py",
    "fec/stance/overall_stance_policy.py",
    "fec/stance/adjudicated_corroboration.py",
    "fec/stance/say_do_gap.py",
    "fec/stance/resolve_attribution_domain.py",
]

def norm(b):
    # normalize CRLF/CR -> LF and strip a UTF-8 BOM so the comparison measures CONTENT
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

print("=" * 100)
print("F3 r0  LIVE vs main @HEAD, line-ending normalized   run %s" % datetime.datetime.now().isoformat(timespec="seconds"))
print("=" * 100)
rev = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
print("HEAD = %s\n" % rev)
print("%-46s %-9s %-9s %s" % ("path", "in main", "in LIVE", "verdict"))
print("-" * 100)
for rel in CANDIDATES:
    g = subprocess.run(["git", "-C", WT, "show", "HEAD:%s" % rel], capture_output=True)
    in_main = (g.returncode == 0)
    lp = os.path.join(LIVE, rel.replace("/", os.sep))
    in_live = os.path.isfile(lp)
    if in_main and in_live:
        mb = norm(g.stdout)
        with open(lp, "rb") as fh:
            lb = norm(fh.read())
        if mb == lb:
            v = "IDENTICAL (content)"
        else:
            ml, ll = mb.decode("utf-8", "replace").split("\n"), lb.decode("utf-8", "replace").split("\n")
            import difflib
            nd = sum(1 for d in difflib.unified_diff(ml, ll, n=0) if d[:1] in "+-" and d[:3] not in ("+++", "---"))
            v = "DIFFERS  (%d changed lines; main %d ln / live %d ln)" % (nd, len(ml), len(ll))
    elif in_main and not in_live:
        v = "main-only (NOT on disk live)"
    elif in_live and not in_main:
        v = "LIVE-only (untracked / not in main)"
    else:
        v = "absent both"
    print("%-46s %-9s %-9s %s" % (rel, in_main, in_live, v))

print("\n-- sha256 of the LIVE files this lane pins line numbers to --")
for rel in ["fec/stance/per_category_stance.py", "fec/stance/build_media_blend.py",
            "fec/press_stream.py", "fec/stance/workbook_stance_views.py",
            "fec/surfaces/build_dashboard_bundle.py", "fec/moneyball_core.py",
            "fec/stance/media_rules.py", "fec/stance/stance_rules.py"]:
    lp = os.path.join(LIVE, rel.replace("/", os.sep))
    if os.path.isfile(lp):
        with open(lp, "rb") as fh:
            raw = fh.read()
        st = os.stat(lp)
        print("   %-46s %s  %8d B  mtime %s  lines(raw)=%d"
              % (rel, hashlib.sha256(raw).hexdigest()[:16], st.st_size,
                 datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                 raw.count(b"\n") + (0 if raw.endswith(b"\n") else 1)))
print("\nDONE F3 r0")
