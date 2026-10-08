# -*- coding: utf-8 -*-
"""F3 shared helpers.

CONTRACT: nothing under LIVE\fec is ever imported or executed.  Constants are lifted out of the
LIVE source by AST literal-parsing (no module execution), and the few tiny pure functions the
audit needs are REIMPLEMENTED here with a citation to the LIVE lines they mirror.
"""
import ast, os, io, json, hashlib, unicodedata, re, collections

LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def module_constants(rel):
    """AST-parse a LIVE .py file and return {name: python literal} for module-level assignments
    whose value is a literal (or a dict whose keys may be earlier literal names).  NO EXECUTION."""
    path = os.path.join(LIVE, rel.replace("/", os.sep))
    src = io.open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        tgt = node.targets[0]
        if not isinstance(tgt, ast.Name):
            continue
        try:
            out[tgt.id] = ast.literal_eval(node.value)
            continue
        except (ValueError, TypeError, SyntaxError):
            pass
        # dict whose keys may be Name references to constants already captured
        if isinstance(node.value, ast.Dict):
            d, ok = {}, True
            for k, v in zip(node.value.keys, node.value.values):
                try:
                    kk = ast.literal_eval(k)
                except (ValueError, TypeError, SyntaxError):
                    if isinstance(k, ast.Name) and k.id in out:
                        kk = out[k.id]
                    else:
                        ok = False
                        break
                try:
                    vv = ast.literal_eval(v)
                except (ValueError, TypeError, SyntaxError):
                    ok = False
                    break
                d[kk] = vv
            if ok:
                out[tgt.id] = d
    return out


_MR = None
def media_rules():
    """Constants of LIVE fec/stance/media_rules.py, AST-lifted."""
    global _MR
    if _MR is None:
        _MR = module_constants("fec/stance/media_rules.py")
    return _MR


def nfc(v):
    """Mirror of LIVE fec/stance/per_category_stance.py:15-16."""
    return unicodedata.normalize("NFC", str(v)) if v is not None else v


def normalized_text(text):
    """Mirror of LIVE fec/stance/media_rules.py:76-78."""
    text = re.sub(r"https?://\S+", "", str(text or "").lower())
    return re.sub(r"[^a-z0-9]", "", text)[:120]


def normalize_signed_extrema(values):
    """Mirror of LIVE fec/stance/media_rules.py:174-189."""
    clean = {m: float(v or 0.0) for m, v in values.items()}
    pmax = max((v for v in clean.values() if v > 0.0), default=0.0)
    nmax = abs(min((v for v in clean.values() if v < 0.0), default=0.0))
    return {m: (v / pmax if v > 0.0 and pmax else v / nmax if v < 0.0 and nmax else 0.0)
            for m, v in clean.items()}


def general_exclusion_ledger(values):
    """Mirror of LIVE fec/stance/media_rules.py:192-201."""
    return {m: {"general": float(v), "applied_to_policy_domains": False,
                "reason": "residual General Credit Union evidence has no evidenced policy domain"}
            for m, v in values.items() if abs(float(v or 0.0)) > 1e-12}


# --- the two hand-maintained lists the stance path depends on, transcribed with citations -----
# LIVE fec/stance/per_category_stance.py:28-31
CATS = [('Examination & Supervision', 5), ('CU Capital Requirements', 6), ('NCUA Budget & Insurance', 7),
        ('Interchange', 8), ('Payments', 9), ('Technology & Emerging', 10), ('Fraud Prevention', 11),
        ('Data Privacy & Cyber', 12), ('Charter Modernization', 13), ('Defense CU Issues', 14),
        ('Field of Membership', 15), ('CU Tax Status', 16), ('CDFI Fund', 17), ('CFPB', 19),
        ('Credit Card Mandates', 20), ('TCPA', 21), ('Member Business Lending', 22),
        ('Mortgage & Housing', 23)]
# LIVE fec/moneyball_core.py:94-95
COLS = list(range(5, 24))
ALL_COLS = COLS + [24]
# LIVE fec/stance/per_category_stance.py:36
DEFENSIVE = {'Interchange', 'Credit Card Mandates', 'CU Tax Status'}


def verify_transcriptions():
    """Fail loudly if a transcribed literal has drifted from the LIVE source."""
    mr = media_rules()
    problems = []
    if len(mr.get("RAW_TO_STANCE", {})) != 18:
        problems.append("RAW_TO_STANCE is %d entries, expected 18" % len(mr.get("RAW_TO_STANCE", {})))
    if set(mr["RAW_TO_STANCE"].values()) != {c for c, _ in CATS}:
        problems.append("RAW_TO_STANCE targets != transcribed CATS names")
    src = io.open(os.path.join(LIVE, "fec", "stance", "per_category_stance.py"), encoding="utf-8").read()
    for name, _ in CATS:
        if ("'%s'" % name) not in src:
            problems.append("cats name %r not found in per_category_stance.py" % name)
    if "COLS=list(range(5,24))" not in io.open(os.path.join(LIVE, "fec", "moneyball_core.py"), encoding="utf-8").read().replace(" ", ""):
        problems.append("moneyball_core COLS literal drifted")
    return problems
