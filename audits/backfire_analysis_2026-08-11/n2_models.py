# -*- coding: utf-8 -*-
"""READ-ONLY N2-N4: alignment/exposure assembly + linear & multivariate tests."""
import csv, json, math, os, sys
from collections import defaultdict

sys.path.insert(0, r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec")
from lobbying import sector_spend as SS

ROOT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
LDA = r"C:\Users\pgoff\AppData\Local\Melange\lda_rebuild\derived\interactions"
SC = os.path.dirname(os.path.abspath(__file__))
SECTORS = ("credit_union", "bank", "crypto", "fintech")

# --- alignment: board scores ---
it = json.load(open(os.path.join(ROOT, r"data\lobbying\industry_tiers.json"), encoding="utf-8"))
align = defaultdict(dict)
for ind in SECTORS:
    for row in it["industries"][ind]["rows"]:
        align[row["member"]][ind] = float(row["score"])
members = sorted(align)
print("members with alignment: %d" % len(members))

# --- bioguide map + chamber ---
bio2m = {}
chamber = {}
for row in it["industries"]["credit_union"]["rows"]:
    if row.get("bioguide"):
        bio2m[row["bioguide"]] = row["member"]
    chamber[row["member"]] = 1 if row["chamber"] == "Senate" else 0

# --- bill -> sponsor members (role-weighted) ---
ROLE_W = {"sponsor": 1.0, "original": 0.5, "cosponsor": 0.25}
bill_members = defaultdict(list)
with open(os.path.join(LDA, "interaction_bill_members.csv"), encoding="utf-8-sig", newline="") as h:
    for row in csv.DictReader(h):
        m = bio2m.get(row["bioguide_id"])
        if m:
            bill_members[row["bill_key"]].append((m, ROLE_W.get(row["role"], 0.25)))

# --- ledger: org-sector lobbying per bill (client resolved once) ---
client_sector = {}
def sector_of(name, year):
    key = name.upper()
    if key in client_sector:
        return client_sector[key]
    try:
        matches, _ = SS._match_client({"client": {"name": name}, "filing_year": year or 2024, "filing_uuid": "x"}, SS.DEFAULT_SECTORS)
        client_sector[key] = matches[0]["sector"] if matches else None
    except Exception:
        client_sector[key] = None
    return client_sector[key]

exposure = defaultdict(lambda: defaultdict(float))
ledger_rows = used = 0
with open(os.path.join(LDA, "interaction_ledger.csv"), encoding="utf-8-sig", newline="") as h:
    for row in csv.DictReader(h):
        ledger_rows += 1
        bk = (row.get("bill_key") or "").strip()
        if not bk or bk not in bill_members:
            continue
        try:
            year = int(row.get("filing_year") or 0)
        except ValueError:
            year = 0
        if year < 2021:
            continue
        sec = sector_of((row.get("client_name") or "").strip(), year)
        if not sec:
            continue
        for m, w in bill_members[bk]:
            exposure[m][sec] += w
        used += 1
print("ledger rows: %d | sector+bill-linked interactions: %d" % (ledger_rows, used))

# --- rhetoric outcome (ordinal) ---
cs = json.load(open(os.path.join(ROOT, "category_stance.json"), encoding="utf-8"))["matrix"]
STANCE_ORD = {"Champion": 3, "Defender": 2, "Ally": 2, "Lean Persuadable": 1, "Persuadable": 1, "Highly Persuadable": 1,
              "True Neutral": 0, "Lean Skeptic": -1, "Skeptic": -2, "Highly Skeptical": -2, "Opponent": -3}
RHET_CAT = {"crypto": "Technology & Emerging", "bank": "Credit Card Mandates", "fintech": "Payments"}

# --- assemble table ---
table = []
for m in members:
    row = {"member": m, "senate": chamber.get(m, 0)}
    tot = sum(exposure[m].values())
    row["log_total_exposure"] = math.log1p(tot)
    for s in SECTORS:
        row["align_%s" % s] = align[m].get(s, 0.0)
        row["exp_%s" % s] = math.log1p(exposure[m].get(s, 0.0))
    for s, cat in RHET_CAT.items():
        lab = (cs.get(m) or {}).get(cat)
        row["rhet_%s" % s] = STANCE_ORD.get(lab) if lab in STANCE_ORD else None
    table.append(row)
json.dump(table, open(os.path.join(SC, "analysis_table.json"), "w", encoding="utf-8"))

# --- stats helpers (pure python) ---
def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs)/n, sum(ys)/n
    sx = math.sqrt(sum((x-mx)**2 for x in xs))
    sy = math.sqrt(sum((y-my)**2 for y in ys))
    if sx == 0 or sy == 0: return 0.0
    return sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / (sx*sy)

def ols(y, X):
    """returns betas, t-stats via normal equations (small k)."""
    n, k = len(y), len(X[0])
    XtX = [[sum(X[i][a]*X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a]*y[i] for i in range(n)) for a in range(k)]
    # gaussian elimination
    M = [rowa[:] + [Xty[a]] for a, rowa in enumerate(XtX)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12: return None, None, None
        for r in range(k):
            if r != c:
                f = M[r][c]/M[c][c]
                M[r] = [M[r][j] - f*M[c][j] for j in range(k+1)]
    beta = [M[c][k]/M[c][c] for c in range(k)]
    resid = [y[i] - sum(X[i][j]*beta[j] for j in range(k)) for i in range(n)]
    sse = sum(r*r for r in resid)
    sigma2 = sse / max(n - k, 1)
    # invert XtX via same elimination on identity (small k) - reuse: approximate with diag of inverse via solve per unit vector
    ses = []
    for j in range(k):
        e = [1.0 if a == j else 0.0 for a in range(k)]
        M2 = [rowa[:] + [e[a]] for a, rowa in enumerate(XtX)]
        for c in range(k):
            p = max(range(c, k), key=lambda r: abs(M2[r][c]))
            M2[c], M2[p] = M2[p], M2[c]
            for r in range(k):
                if r != c:
                    f = M2[r][c]/M2[c][c]
                    M2[r] = [M2[r][jj] - f*M2[c][jj] for jj in range(k+1)]
        inv_col = [M2[c][k]/M2[c][c] for c in range(k)]
        ses.append(math.sqrt(max(sigma2 * inv_col[j], 0)))
    tstats = [beta[j]/ses[j] if ses[j] > 0 else 0.0 for j in range(k)]
    r2 = 1 - sse / max(sum((v - sum(y)/n)**2 for v in y), 1e-12)
    return beta, tstats, r2

# --- (1) alignment correlation matrix ---
print()
print("=== 4x4 alignment score correlations (n=%d) ===" % len(table))
for a in SECTORS:
    line = []
    for b in SECTORS:
        r = pearson([t["align_%s" % a] for t in table], [t["align_%s" % b] for t in table])
        line.append("%+.3f" % r)
    print("%-13s %s" % (a, "  ".join(line)))

# --- (2) exposure -> alignment simple correlations ---
print()
print("=== corr(exposure_B, align_B) and cross corr(exposure_B, align_A) ===")
for b in SECTORS:
    line = []
    for a in SECTORS:
        r = pearson([t["exp_%s" % b] for t in table], [t["align_%s" % a] for t in table])
        line.append("%s:%+.3f" % (a[:4], r))
    print("exp_%-12s -> %s" % (b, "  ".join(line)))

# --- (3) THE BACKFIRE MODELS: align_B ~ exp_B * align_A + senate + log_total ---
print()
print("=== multivariate: align_B ~ exp_B + align_A + exp_B*align_A + senate + log_total_exposure ===")
pairs = [(a, b) for a in SECTORS for b in SECTORS if a != b]
results = {}
for a, b in pairs:
    y = [t["align_%s" % b] for t in table]
    X = [[1.0, t["exp_%s" % b], t["align_%s" % a], t["exp_%s" % b]*t["align_%s" % a], t["senate"], t["log_total_exposure"]] for t in table]
    beta, tstat, r2 = ols(y, X)
    if beta is None: continue
    results[(a, b)] = (beta, tstat, r2)
    print("A=%-12s B=%-12s  b_exp=%+.4f(t=%+.1f)  b_alignA=%+.4f(t=%+.1f)  b_INTERACTION=%+.4f(t=%+.1f)  R2=%.3f"
          % (a, b, beta[1], tstat[1], beta[2], tstat[2], beta[3], tstat[3], r2))
json.dump({("%s->%s" % k): {"beta": v[0], "t": v[1], "r2": v[2]} for k, v in results.items()},
          open(os.path.join(SC, "backfire_models.json"), "w", encoding="utf-8"))

# --- (4) rhetoric outcome models where available ---
print()
print("=== rhetoric outcome: rhet_B ~ exp_B * align_A + senate (measured members only) ===")
for a in SECTORS:
    for b in ("crypto", "bank", "fintech"):
        if a == b: continue
        sub = [t for t in table if t["rhet_%s" % b] is not None]
        if len(sub) < 60: continue
        y = [float(t["rhet_%s" % b]) for t in sub]
        X = [[1.0, t["exp_%s" % b], t["align_%s" % a], t["exp_%s" % b]*t["align_%s" % a], t["senate"]] for t in sub]
        beta, tstat, r2 = ols(y, X)
        if beta is None: continue
        if abs(tstat[3]) >= 1.5:
            print("A=%-12s B=%-8s n=%d  b_INTERACTION=%+.4f(t=%+.1f)  R2=%.3f" % (a, b, len(sub), beta[3], tstat[3], r2))
print("(only |t|>=1.5 interactions shown)")
