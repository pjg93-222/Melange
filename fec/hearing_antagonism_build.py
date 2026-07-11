# -*- coding: utf-8 -*-
"""Refined hearing-antagonism builder (2026-07-10, user refinement). Reads the CACHED turn-sequences
(hearings_seq.db) and computes, per member:
  mm_intr  = interrupts a COLLEAGUE (member cuts off another member's dash-terminated turn)
  mm_xparty= ...the colleague is the other party (cleanest antagonism)
  wit_hostile = member turn ADJACENT to a witness that carries HOSTILE markers (aggressive language /
                blunt correction / hostile interrogation) -- NOT routine procedural time-management
                ('reclaiming my time' is EXCLUDED by design; it inflated senior appropriators in v1)
Confound controls (DW-NOMINATE ideology+extremity, party, minority-fraction, chair-role) via residual.
Emits diagnostics: confound checks, split-half reliability, orthogonality to dominance/visibility/
cooperation, face validity, and an AUDIT DUMP of flagged hostile turns so the lexicon can be judged.
Iterate the lexicon here and re-run in seconds -- no re-download (cache is the point)."""
import sys, os, sqlite3, json, collections, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
from dw_control import load_dw

B = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'

# ---- HOSTILITY LEXICON (pre-specified; member-vs-witness hostility only) ----
INTERROGATE = re.compile(r"\b(yes or no|answer the question|just answer|did you or did you not|"
                         r"answer my question|will you answer|that'?s not what i asked|answer yes or no|"
                         r"i'?m asking you|are you (aware|denying)|isn'?t it true)\b", re.I)
CORRECT = re.compile(r"\b(that'?s (false|not true|incorrect|a lie|not accurate|wrong)|that is false|"
                     r"you'?re (wrong|mistaken|incorrect|lying)|that'?s simply (false|not)|"
                     r"you know that'?s (false|not true))\b", re.I)
AGGRESSIVE = re.compile(r"\b(how dare you|shame on you|you should be ashamed|disgraceful|outrageous|"
                        r"you lied|you failed|reprehensible|you have no business|you don'?t get to|"
                        r"appalling|absolutely unacceptable)\b", re.I)
def is_hostile(t):
    return bool(INTERROGATE.search(t) or CORRECT.search(t) or AGGRESSIVE.search(t))

def load_party():
    import csv
    P = {}; Cj = {m['member']: m for m in json.load(open(B + r'\congestion.json'))}
    bio = {m: Cj[m].get('bioguide') for m in Cj}
    for r in csv.DictReader(open(B + r'\fec\legislators.csv', encoding='utf-8')):
        if r.get('bioguide_id'): P[r['bioguide_id']] = (r.get('party') or '')[:1].upper()
    return {m: P.get(bio.get(m), '?') for m in Cj}

def build():
    DW = load_dw(); PTY = load_party()
    sc = sqlite3.connect(B + r'\hearings_seq.db', timeout=60); sc.execute('PRAGMA query_only=1')
    mc = sqlite3.connect(B + r'\social_media.db', timeout=60); mc.execute('PRAGMA query_only=1')
    chair_of = {p: cm for p, cm in mc.execute("select package, chair_member from hearing_meta")}
    chair_party = {p: cp for p, cp in mc.execute("select package, chair_party from hearing_meta")}

    agg = collections.defaultdict(lambda: collections.Counter())
    byhear = collections.defaultdict(list)          # member -> per-hearing (turns, mm_intr, mm_xparty, wit_hostile)
    minority = collections.defaultdict(lambda: [0, 0])
    audit = collections.defaultdict(list)
    nh = 0
    for pkg, date, seqj in sc.execute("select package, date, seq from hearing_seq"):
        seq = json.loads(seqj); nh += 1
        cp = chair_party.get(pkg, '?')
        per = collections.defaultdict(lambda: collections.Counter())
        for i, turn in enumerate(seq):
            kind = turn[0]
            if kind in ('W', 'C', 'O'): continue           # only member turns are scored
            m = kind; pty = turn[1]; text = turn[3] if len(turn) > 3 else ''
            if chair_of.get(pkg) == m: continue            # skip hearings the member PRESIDED
            per[m]['turns'] += 1
            prev = seq[i - 1] if i > 0 else None
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            # member-vs-member interrupt (colleague cut off)
            if prev and prev[0] not in ('W', 'C', 'O') and prev[2] == 1 and prev[0] != m:
                per[m]['mm_intr'] += 1
                if prev[1] in ('D', 'R') and pty in ('D', 'R') and prev[1] != pty:
                    per[m]['mm_xparty'] += 1
            # member-vs-witness HOSTILE (adjacent to a witness, hostile language)
            adj_wit = (prev and prev[0] == 'W') or (nxt and nxt[0] == 'W')
            if adj_wit and is_hostile(text):
                per[m]['wit_hostile'] += 1
                if len(audit[m]) < 3: audit[m].append(text[:160])
        for m, c in per.items():
            for k, v in c.items(): agg[m][k] += v
            agg[m]['hearings'] += 1
            byhear[m].append((c['turns'], c['mm_intr'], c['mm_xparty'], c['wit_hostile']))
            if cp in ('D', 'R') and PTY.get(m) in ('D', 'R'):
                minority[m][1] += 1; minority[m][0] += (cp != PTY[m])
    sc.close(); mc.close()
    return DW, PTY, agg, byhear, minority, audit, nh

def z(v):
    v = np.array(v, float); s = v.std(); return (v - v.mean()) / s if s > 0 else v * 0
def corr(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); m = ~(np.isnan(a) | np.isnan(b))
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 5 else float('nan')
def resid(y, X):
    X = np.column_stack([np.ones(len(y))] + X); beta, *_ = np.linalg.lstsq(X, y, rcond=None); return y - X @ beta

def main():
    DW, PTY, agg, byhear, minority, audit, nh = build()
    MIN = 20
    mem = [m for m in agg if agg[m]['turns'] >= MIN and m in DW]
    print('=== REFINED antagonism (member-vs-member + hostile-witness) | %d hearings cached ===' % nh)
    print('members >=%d turns & DW: %d' % (MIN, len(mem)))
    tr = np.array([agg[m]['turns'] for m in mem], float)
    mmi = z(np.array([agg[m]['mm_intr'] for m in mem]) / tr)
    mmx = z(np.array([agg[m]['mm_xparty'] for m in mem]) / tr)
    wh = z(np.array([agg[m]['wit_hostile'] for m in mem]) / tr)
    antag = mmi + mmx + wh
    ext = np.array([DW[m]['extremity'] for m in mem]); d1 = np.array([DW[m]['dim1'] for m in mem])
    pty = np.array([1.0 if PTY.get(m) == 'R' else 0.0 for m in mem])
    minf = np.array([minority[m][0] / minority[m][1] if minority[m][1] else 0.5 for m in mem])
    print('\n--- CONFOUND CHECK ---')
    for nm, v in [('extremity', ext), ('dim1', d1), ('party(R)', pty), ('minority-frac', minf)]:
        print('  antag vs %-14s %+.3f' % (nm, corr(antag, v)))
    print('  antag_resid vs extremity: %+.3f' % corr(resid(antag, [pty, d1, ext, minf]), ext))
    print('\n--- COMPONENT face validity ---')
    for nm, comp in [('mm_intr (colleague)', mmi), ('mm_xparty (cross-aisle)', mmx), ('wit_hostile', wh), ('COMPOSITE', antag)]:
        o = sorted(range(len(mem)), key=lambda i: -comp[i])
        print('  %-24s top: %s' % (nm, ', '.join('%s(%s)' % (mem[i], PTY.get(mem[i])) for i in o[:6])))
    print('\n--- reliability (split-half, >=4 hearings) ---')
    memR = [m for m in mem if len(byhear[m]) >= 4]
    def half(which):
        out = []
        for m in memR:
            h = byhear[m][which::2]; t = max(sum(x[0] for x in h), 1)
            out.append((sum(x[1] for x in h) + sum(x[2] for x in h) + sum(x[3] for x in h)) / t)
        return z(out)
    r = corr(half(0), half(1)); print('  n=%d half-half r=%+.3f SB=%+.3f' % (len(memR), r, 2 * r / (1 + r) if r > -1 else float('nan')))
    print('\n--- orthogonality to existing dispositions ---')
    BD = json.load(open(B + r'\behavioral_dispositions.json'))['members']
    for nm in ['dominance_z', 'visibility_z', 'cooperation_z', 'reactivity_z']:
        dv = [BD.get(m, {}).get(nm) if isinstance(BD.get(m), dict) else None for m in mem]
        print('  antag vs %-14s %+.3f' % (nm, corr(antag, [np.nan if x is None else x for x in dv])))
    print('\n--- AUDIT: sample flagged HOSTILE turns (validate the lexicon) ---')
    top = sorted(mem, key=lambda m: -agg[m]['wit_hostile'])[:6]
    for m in top:
        print('  %s (%d hostile):' % (m, agg[m]['wit_hostile']))
        for s in audit.get(m, [])[:2]: print('     "%s"' % s)

if __name__ == '__main__':
    main()
