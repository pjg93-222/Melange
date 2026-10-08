# -*- coding: utf-8 -*-
"""
D9 STRATIFIED REFIT - READ-ONLY.

Binding plan: D9_STRATIFIED_PREDECLARATION.md
  HEADLINE      = S1 (party-stratified subsample estimates)
  SUPPORTING    = S2 three-way party x exp_B x align_A terms
  MULTIPLICITY  = Holm across 12 interaction terms WITHIN each stratum (D, R separately);
                  Holm across the 12 three-way terms as its own separate family.
  DECISION RULE = three-way survives Holm  ->  that pair's POOLED coefficient is DEPRECATED.

Writes ONLY into the scratchpad. Reads only. Never imports or executes n2_models.py
(importing it would re-run the producer and overwrite the archived artifacts).
"""
import csv, json, math, os, re, sys, hashlib, unicodedata
from collections import Counter

from scipy import stats as _sps

ROOT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
AUD = os.path.join(ROOT, "audits", "backfire_analysis_2026-08-11")
OUT = os.path.dirname(os.path.abspath(__file__))
SECTORS = ("credit_union", "bank", "crypto", "fintech")
ALPHA = 0.05

P_TABLE = os.path.join(AUD, "analysis_table.json")
P_MODELS = os.path.join(AUD, "backfire_models.json")
P_N2 = os.path.join(AUD, "n2_models.py")
P_LEG = os.path.join(ROOT, "fec", "legislators.csv")
P_TIERS = os.path.join(ROOT, "data", "lobbying", "industry_tiers.json")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- archived ols
# VERBATIM from n2_models.py (sha256 pinned below). Closed-form normal equations,
# Gaussian elimination with partial pivoting. Reproduced here so S0 is comparable
# to the committed fit without executing the producer.
def ols(y, X):
    """returns betas, t-stats via normal equations (small k)."""
    n, k = len(y), len(X[0])
    XtX = [[sum(X[i][a]*X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a]*y[i] for i in range(n)) for a in range(k)]
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


def verify_ols_is_verbatim():
    """Guard: the ols() above must be byte-identical to the archived one."""
    src = open(P_N2, encoding="utf-8").read()
    m = re.search(r"^def ols\(y, X\):\n(.*?)^# --- \(1\)", src, re.S | re.M)
    arch = m.group(0).split("# --- (1)")[0].rstrip()
    arch_body = "\n".join(l for l in arch.splitlines() if l.strip() and not l.strip().startswith("#"))
    mine = open(os.path.abspath(__file__), encoding="utf-8").read()
    m2 = re.search(r"^def ols\(y, X\):\n(.*?)^def verify_ols", mine, re.S | re.M)
    my = m2.group(0).split("def verify_ols")[0].rstrip()
    my_body = "\n".join(l for l in my.splitlines() if l.strip() and not l.strip().startswith("#"))
    return arch_body == my_body


def pval(t, df):
    return float(2.0 * _sps.t.sf(abs(t), df))


def holm(pairs):
    """pairs: list of (key, p). Returns {key: holm-adjusted p} (step-down, monotone)."""
    m = len(pairs)
    order = sorted(pairs, key=lambda kv: kv[1])
    adj, run = {}, 0.0
    for i, (k, p) in enumerate(order):
        v = (m - i) * p
        run = max(run, v)
        adj[k] = min(1.0, run)
    return adj


PAIRS = [(a, b) for a in SECTORS for b in SECTORS if a != b]
LAB = {"credit_union": "CU", "bank": "BANK", "crypto": "CRYPTO", "fintech": "FINTECH"}


def design_s0(rows, a, b):
    y = [t["align_%s" % b] for t in rows]
    X = [[1.0, t["exp_%s" % b], t["align_%s" % a],
          t["exp_%s" % b]*t["align_%s" % a], t["senate"], t["log_total_exposure"]] for t in rows]
    return y, X


def design_s2(rows, a, b):
    """S0 + party + every party x term product. R = 1 if Republican else 0."""
    y = [t["align_%s" % b] for t in rows]
    X = []
    for t in rows:
        e, al, R = t["exp_%s" % b], t["align_%s" % a], float(t["R"])
        base = [1.0, e, al, e*al, float(t["senate"]), t["log_total_exposure"]]
        X.append(base + [R] + [R*v for v in base[1:]])
    return y, X


S2_NAMES = ["intercept", "exp_B", "align_A", "exp_B:align_A", "senate", "log_total_exp",
            "R", "R:exp_B", "R:align_A", "R:exp_B:align_A", "R:senate", "R:log_total_exp"]
IX_THREEWAY = 9
IX_INTER = 3


def main():
    rep = {}
    rep["inputs"] = [{"path": p, "sha256": sha256(p)} for p in (P_TABLE, P_MODELS, P_N2, P_LEG, P_TIERS)]
    rep["ols_verbatim_vs_archive"] = verify_ols_is_verbatim()

    table = json.load(open(P_TABLE, encoding="utf-8"))
    archived = json.load(open(P_MODELS, encoding="utf-8"))
    rep["n_table"] = len(table)

    # ------------------------------------------------------ S0 GATE
    s0 = {}
    devs = []
    for a, b in PAIRS:
        y, X = design_s0(table, a, b)
        beta, t, r2 = ols(y, X)
        key = "%s->%s" % (a, b)
        s0[key] = {"beta": beta, "t": t, "r2": r2, "n": len(y), "df": len(y) - 6}
        ar = archived[key]
        for i in range(6):
            devs.append(abs(beta[i] - ar["beta"][i]))
            devs.append(abs(t[i] - ar["t"][i]))
        devs.append(abs(r2 - ar["r2"]))
    rep["s0_max_abs_deviation"] = max(devs)
    rep["s0_reproduced"] = max(devs) < 1e-9
    rep["s0"] = {k: {"b_inter": v["beta"][IX_INTER], "t_inter": v["t"][IX_INTER],
                     "p_inter": pval(v["t"][IX_INTER], v["df"]), "r2": v["r2"], "n": v["n"]}
                 for k, v in s0.items()}
    if not rep["s0_reproduced"]:
        rep["STOP"] = "S0 did not reproduce; downstream untrustworthy."
        json.dump(rep, open(os.path.join(OUT, "d9_stratified_results.json"), "w", encoding="utf-8"), indent=1)
        print(json.dumps(rep, indent=1)); return

    # ------------------------------------------------------ PARTY JOIN
    tiers = json.load(open(P_TIERS, encoding="utf-8"))
    m2b = {}
    for ind in SECTORS:
        for r in tiers["industries"][ind]["rows"]:
            if r.get("bioguide"):
                m2b[r["member"]] = r["bioguide"]
    leg = list(csv.DictReader(open(P_LEG, encoding="utf-8-sig")))
    b2p = {r["bioguide_id"]: r["party"] for r in leg}

    def nrm(s):
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        return re.sub(r"[^a-z ]", "", s.lower()).strip()

    idx = [{}, {}, {}, {}]
    for r in leg:
        idx[0].setdefault(nrm(r["full_name"]), []).append(r)
        idx[1].setdefault(nrm(r["first_name"] + " " + r["last_name"]), []).append(r)
        if r["nickname"]:
            idx[2].setdefault(nrm(r["nickname"] + " " + r["last_name"]), []).append(r)
        idx[3].setdefault(nrm(r["first_name"].split()[0] + " " + r["last_name"]), []).append(r)

    join = Counter()
    unresolved = []
    for t in table:
        m = t["member"]
        if m in m2b and m2b[m] in b2p:
            t["party"] = b2p[m2b[m]]; t["join_via"] = "bioguide"; join["bioguide"] += 1; continue
        k = nrm(m)
        got = None
        for lvl, d in enumerate(idx):
            h = d.get(k)
            if h and len(h) == 1:
                got = (h[0], "name_l%d" % lvl); break
        if got is None:
            k2 = nrm(m.split()[0] + " " + " ".join(m.split()[1:]))
            for lvl, d in enumerate(idx):
                h = d.get(k2)
                if h and len(h) == 1:
                    got = (h[0], "name_l%d" % lvl); break
        if got is None:
            t["party"] = None; t["join_via"] = None; unresolved.append(m); join["UNRESOLVED"] += 1
        else:
            t["party"] = got[0]["party"]; t["join_via"] = got[1]; join[got[1]] += 1

    rep["join"] = {"by_method": dict(join), "unresolved_members": unresolved,
                   "joined": len(table) - len(unresolved), "rate": (len(table) - len(unresolved)) / len(table)}
    rep["party_distribution_joined"] = dict(Counter(t["party"] for t in table))
    rep["party_distribution_legislators_csv"] = dict(Counter(r["party"] for r in leg))

    for t in table:
        t["R"] = 1 if t["party"] == "Republican" else 0

    dems = [t for t in table if t["party"] == "Democrat"]
    reps = [t for t in table if t["party"] == "Republican"]
    inds = [t for t in table if t["party"] == "Independent"]
    unk = [t for t in table if t["party"] is None]
    rep["strata_n"] = {"Democrat": len(dems), "Republican": len(reps),
                       "Independent_EXCLUDED_from_stratification": len(inds),
                       "Independent_members": [t["member"] for t in inds],
                       "unjoined_EXCLUDED": len(unk), "unjoined_members": [t["member"] for t in unk]}

    # ------------------------------------------------------ S1 HEADLINE
    s1 = {}
    for name, sub in (("Democrat", dems), ("Republican", reps)):
        raw = {}
        for a, b in PAIRS:
            y, X = design_s0(sub, a, b)
            beta, t, r2 = ols(y, X)
            key = "%s->%s" % (a, b)
            df = len(y) - 6
            raw[key] = {"n": len(y), "df": df, "b": beta[IX_INTER], "t": t[IX_INTER],
                        "p_raw": pval(t[IX_INTER], df), "r2": r2}
        adj = holm([(k, v["p_raw"]) for k, v in raw.items()])
        for k in raw:
            raw[k]["p_holm"] = adj[k]
            raw[k]["holm_sig"] = adj[k] < ALPHA
        s1[name] = raw
    rep["s1"] = s1

    # ------------------------------------------------------ S2 SUPPORTING
    def fit_s2(rows, tag):
        raw = {}
        for a, b in PAIRS:
            y, X = design_s2(rows, a, b)
            beta, t, r2 = ols(y, X)
            key = "%s->%s" % (a, b)
            if beta is None:
                raw[key] = {"singular": True}; continue
            df = len(y) - 12
            raw[key] = {"n": len(y), "df": df, "b3": beta[IX_THREEWAY], "t3": t[IX_THREEWAY],
                        "p_raw": pval(t[IX_THREEWAY], df), "r2": r2}
        adj = holm([(k, v["p_raw"]) for k, v in raw.items()])
        for k in raw:
            raw[k]["p_holm"] = adj[k]
            raw[k]["holm_sig"] = adj[k] < ALPHA
        return raw

    s2_primary = fit_s2([t for t in table if t["party"] is not None], "primary")
    s2_sens = fit_s2(dems + reps, "sens_no_independents")
    rep["s2_primary_note"] = ("R=1 Republican else 0; the %d Independents sit in the reference "
                             "cell with Democrats, per the pre-declaration ('they remain in S0 "
                             "and S2 where party enters as a dummy')." % len(inds))
    rep["s2"] = s2_primary
    rep["s2_sensitivity_drop_independents"] = s2_sens
    rep["s2_sensitivity_agrees"] = all(s2_primary[k]["holm_sig"] == s2_sens[k]["holm_sig"] for k in s2_primary)

    # ------------------------------------------------------ DECISION RULE
    dep, stand = [], []
    for a, b in PAIRS:
        k = "%s->%s" % (a, b)
        (dep if s2_primary[k]["holm_sig"] else stand).append(k)
    rep["decision_rule"] = {"alpha": ALPHA,
                            "pooled_DEPRECATED": dep,
                            "pooled_STANDS": stand}

    # ------------------------------------------------------ EXPECTATION
    crypto_out = ["credit_union->crypto", "bank->crypto", "fintech->crypto"]
    crypto_fault = ["crypto->credit_union", "crypto->bank", "crypto->fintech"]
    exp = {"crypto_as_outcome": {}, "crypto_faultline": {}}
    for k in crypto_out:
        d, r = s1["Democrat"][k], s1["Republican"][k]
        exp["crypto_as_outcome"][k] = {
            "threeway_holm_sig": s2_primary[k]["holm_sig"], "threeway_p_holm": s2_primary[k]["p_holm"],
            "D_b": d["b"], "D_p_holm": d["p_holm"], "R_b": r["b"], "R_p_holm": r["p_holm"],
            "opposite_signed": (d["b"] > 0) != (r["b"] > 0),
            "D_pos_R_neg": d["b"] > 0 and r["b"] < 0}
    for k in crypto_fault:
        d, r = s1["Democrat"][k], s1["Republican"][k]
        exp["crypto_faultline"][k] = {
            "D_b": d["b"], "D_p_holm": d["p_holm"], "D_sig": d["holm_sig"],
            "R_b": r["b"], "R_p_holm": r["p_holm"], "R_sig": r["holm_sig"]}
    exp["pred_A_all3_threeway_sig"] = all(exp["crypto_as_outcome"][k]["threeway_holm_sig"] for k in crypto_out)
    exp["pred_B_all3_D_pos_R_neg"] = all(exp["crypto_as_outcome"][k]["D_pos_R_neg"] for k in crypto_out)
    exp["pred_C_faultline_D_sig_count"] = sum(1 for k in crypto_fault if exp["crypto_faultline"][k]["D_sig"])
    exp["pred_C_faultline_R_nonsig_count"] = sum(1 for k in crypto_fault if not exp["crypto_faultline"][k]["R_sig"])
    rep["expectation"] = exp

    json.dump(rep, open(os.path.join(OUT, "d9_stratified_results.json"), "w", encoding="utf-8"), indent=1)

    # ------------------------------------------------------ PRINT
    W = print
    W("=" * 100)
    W("S0 GATE: max |deviation| vs backfire_models.json = %.3e  -> %s"
      % (rep["s0_max_abs_deviation"], "REPRODUCED" if rep["s0_reproduced"] else "FAILED"))
    W("ols() byte-identical to archived n2_models.py ols(): %s" % rep["ols_verbatim_vs_archive"])
    W("join: %d/%d = %.4f  methods=%s  unresolved=%s"
      % (rep["join"]["joined"], len(table), rep["join"]["rate"], dict(join), unresolved))
    W("party (joined 533): %s" % rep["party_distribution_joined"])
    W("party (legislators.csv 537): %s" % rep["party_distribution_legislators_csv"])
    W("strata: D=%d R=%d I=%d(EXCLUDED from stratification) unjoined=%d"
      % (len(dems), len(reps), len(inds), len(unk)))
    W("Independents excluded: %s" % rep["strata_n"]["Independent_members"])
    W("")
    W("=" * 100)
    W("S1 HEADLINE - stratified interaction exp_B x align_A   (Holm within each stratum, m=12)")
    W("%-26s | %-32s | %-32s" % ("A->B", "DEMOCRAT (n=%d)" % len(dems), "REPUBLICAN (n=%d)" % len(reps)))
    W("%-26s | %9s %7s %8s %-5s| %9s %7s %8s %-5s" % ("", "b", "t", "p_holm", "sig", "b", "t", "p_holm", "sig"))
    W("-" * 100)
    for a, b in PAIRS:
        k = "%s->%s" % (a, b)
        d, r = s1["Democrat"][k], s1["Republican"][k]
        W("%-26s | %+9.4f %+7.2f %8.4f %-5s| %+9.4f %+7.2f %8.4f %-5s"
          % (k, d["b"], d["t"], d["p_holm"], "*" if d["holm_sig"] else "", r["b"], r["t"], r["p_holm"], "*" if r["holm_sig"] else ""))
    W("")
    W("=" * 100)
    W("S2 SUPPORTING - three-way R x exp_B x align_A  (Holm across the 12-term family)")
    W("%-26s %10s %8s %10s %10s %5s   %10s" % ("A->B", "b3", "t3", "p_raw", "p_holm", "sig", "pooled_b"))
    W("-" * 100)
    for a, b in PAIRS:
        k = "%s->%s" % (a, b)
        v = s2_primary[k]
        W("%-26s %+10.4f %+8.2f %10.5f %10.5f %5s   %+10.4f"
          % (k, v["b3"], v["t3"], v["p_raw"], v["p_holm"], "*" if v["holm_sig"] else "", rep["s0"][k]["b_inter"]))
    W("")
    W("sensitivity (drop 3 Independents, n=%d) agrees with primary on Holm survival: %s"
      % (len(dems) + len(reps), rep["s2_sensitivity_agrees"]))
    W("")
    W("DECISION RULE (alpha=%.2f): pooled DEPRECATED -> %s" % (ALPHA, dep or "NONE"))
    W("                            pooled STANDS     -> %s" % (stand or "NONE"))
    W("")
    W("EXPECTATION CHECK")
    W(json.dumps(exp, indent=1))


if __name__ == "__main__":
    main()
