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

# GRANDSTAND / procedural-dominance markers (axis 1, KEPT per user: senior members command the floor).
# 'reclaiming my time' lives HERE (procedural, not antagonism) -- the phrase that inflated Collins is
# the RIGHT signal for a dominance/status axis, wrong for the disagreeableness axis.
PROC = re.compile(r"reclaim\w+ my time|regular order|point of order|regain my time|"
                  r"i control the time|reclaiming the balance|will the gentlem[ae]n yield", re.I)

# Administration party by date (for the hostile-witness POLITICAL control: opposing-admin grilling =
# constituent-grievance performance, not disposition).
ADMIN = [('2017-01-20', '2021-01-20', 'R'), ('2021-01-20', '2025-01-20', 'D')]
def admin_party(date):
    for a, b, p in ADMIN:
        if a <= date < b: return p
    return '?'

def load_seniority():
    """member -> years in office (from voteview first-congress). Senior members grandstand more."""
    import csv
    first = {}
    for r in csv.DictReader(open(B + r'\votes\HSall_members.csv', encoding='utf-8')):
        b = r.get('bioguide_id')
        try: cong = int(r['congress'])
        except (ValueError, TypeError): continue
        if b and (b not in first or cong < first[b]): first[b] = cong
    Cj = {m['member']: m for m in json.load(open(B + r'\congestion.json'))}
    out = {}
    for m in Cj:
        fc = first.get(Cj[m].get('bioguide'))
        if fc: out[m] = 2026 - (1789 + 2 * (fc - 1))   # years since first election
    return out

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
    byhear = collections.defaultdict(list)          # member -> per-hearing (turns, mm, wit_hostile, grand)
    minority = collections.defaultdict(lambda: [0, 0])
    opp = collections.defaultdict(lambda: [0, 0])   # member -> [opp-admin hearings, total] (political control)
    audit = collections.defaultdict(list)
    nh = 0
    for pkg, date, seqj in sc.execute("select package, date, seq from hearing_seq"):
        seq = json.loads(seqj); nh += 1
        cp = chair_party.get(pkg, '?'); ap = admin_party(date)
        per = collections.defaultdict(lambda: collections.Counter())
        for i, turn in enumerate(seq):
            kind = turn[0]
            if kind in ('W', 'C', 'O'): continue           # only member turns are scored
            m = kind; pty = turn[1]; text = turn[3] if len(turn) > 3 else ''
            if chair_of.get(pkg) == m: continue            # skip hearings the member PRESIDED
            per[m]['turns'] += 1
            prev = seq[i - 1] if i > 0 else None
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            # --- GRANDSTAND axis (procedural dominance; interrupting ANYONE + floor-command phrases) ---
            if prev and prev[2] == 1 and prev[0] != m:
                per[m]['all_intr'] += 1
            if PROC.search(text): per[m]['proc'] += 1
            # --- ANTAGONISM axis: member-vs-member interrupt (colleague cut off) ---
            if prev and prev[0] not in ('W', 'C', 'O') and prev[2] == 1 and prev[0] != m:
                per[m]['mm_intr'] += 1
                if prev[1] in ('D', 'R') and pty in ('D', 'R') and prev[1] != pty:
                    per[m]['mm_xparty'] += 1
            # --- ANTAGONISM axis: member-vs-witness HOSTILE (adjacent to witness + hostile language) ---
            adj_wit = (prev and prev[0] == 'W') or (nxt and nxt[0] == 'W')
            if adj_wit and is_hostile(text):
                per[m]['wit_hostile'] += 1
                if ap != '?' and pty in ('D', 'R'):
                    per[m]['wh_opp' if pty != ap else 'wh_aligned'] += 1   # political split
                if len(audit[m]) < 3: audit[m].append(text[:160])
        for m, c in per.items():
            for k, v in c.items(): agg[m][k] += v
            agg[m]['hearings'] += 1
            byhear[m].append((c['turns'], c['mm_intr'] + c['mm_xparty'] + c['wit_hostile'], c['all_intr'] + c['proc']))
            if cp in ('D', 'R') and PTY.get(m) in ('D', 'R'):
                minority[m][1] += 1; minority[m][0] += (cp != PTY[m])
            if ap in ('D', 'R') and PTY.get(m) in ('D', 'R'):
                opp[m][1] += 1; opp[m][0] += (ap != PTY[m])
    sc.close(); mc.close()
    return DW, PTY, agg, byhear, minority, opp, audit, nh

def z(v):
    v = np.array(v, float); s = v.std(); return (v - v.mean()) / s if s > 0 else v * 0
def corr(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); m = ~(np.isnan(a) | np.isnan(b))
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 5 else float('nan')
def resid(y, X):
    X = np.column_stack([np.ones(len(y))] + X); beta, *_ = np.linalg.lstsq(X, y, rcond=None); return y - X @ beta

def main():
    DW, PTY, agg, byhear, minority, opp, audit, nh = build()
    MIN = 20
    mem = [m for m in agg if agg[m]['turns'] >= MIN and m in DW]
    SEN = load_seniority()
    BD = json.load(open(B + r'\behavioral_dispositions.json'))['members']
    print('=== TWO-AXIS hearing build | %d hearings cached | %d members (>=%d turns) ===' % (nh, len(mem), MIN))
    tr = np.array([agg[m]['turns'] for m in mem], float)
    def rate(k): return np.array([agg[m][k] for m in mem]) / tr
    ext = np.array([DW[m]['extremity'] for m in mem]); d1 = np.array([DW[m]['dim1'] for m in mem])
    pty = np.array([1.0 if PTY.get(m) == 'R' else 0.0 for m in mem])
    minf = np.array([minority[m][0] / minority[m][1] if minority[m][1] else 0.5 for m in mem])
    oppf = np.array([opp[m][0] / opp[m][1] if opp[m][1] else 0.5 for m in mem])
    sen = np.array([SEN.get(m, np.nan) for m in mem]); sen = np.where(np.isnan(sen), np.nanmean(sen), sen)
    def bdv(k): return np.array([BD.get(m, {}).get(k, np.nan) if isinstance(BD.get(m), dict) else np.nan for m in mem])

    # ---------- AXIS 1: GRANDSTAND (procedural dominance; KEPT, seniority-correlated by design) ----------
    grand = z(rate('all_intr')) + z(rate('proc'))
    print('\n### AXIS 1 -- GRANDSTAND / procedural dominance (the original signal, kept) ###')
    print('  vs seniority(yrs): %+.3f (EXPECT +; senior members command the floor)' % corr(grand, sen))
    print('  vs dominance_z: %+.3f | vs visibility_z: %+.3f' % (corr(grand, bdv('dominance_z')), corr(grand, bdv('visibility_z'))))
    go = sorted(range(len(mem)), key=lambda i: -grand[i])
    print('  top grandstanders: %s' % ', '.join('%s(%s,%dy)' % (mem[i], PTY.get(mem[i]), sen[i]) for i in go[:8]))

    # ---------- AXIS 2: ANTAGONISM (disagreeableness; refined + politically & seniority controlled) ----------
    wh_rate = rate('wit_hostile')
    antag_raw = z(rate('mm_intr')) + z(rate('mm_xparty')) + z(wh_rate)
    print('\n### AXIS 2 -- ANTAGONISM / disagreeableness (member-vs-member + hostile-witness) ###')
    print('  raw confounds: seniority %+.3f | extremity %+.3f | party %+.3f | minority %+.3f | opp-admin %+.3f'
          % (corr(antag_raw, sen), corr(antag_raw, ext), corr(antag_raw, pty), corr(antag_raw, minf), corr(antag_raw, oppf)))
    antag = resid(antag_raw, [sen, ext, d1, pty, minf, oppf])   # controlled disagreeableness
    print('  CONTROLLED (partial seniority+ideology+party+minority+opp-admin):')
    print('    resid vs seniority %+.3f | vs extremity %+.3f | vs opp-admin %+.3f  (all -> ~0 = controls work)'
          % (corr(antag, sen), corr(antag, ext), corr(antag, oppf)))
    print('  --- hostile-witness POLITICAL control (your point 2) ---')
    print('    wit_hostile vs opp-admin fraction: %+.3f (higher = more political/grievance-airing)' % corr(wh_rate, oppf))
    wh_ctrl = resid(wh_rate, [oppf, ext, pty])
    print('    dispositional residual: members hostile ACROSS administrations (top): %s'
          % ', '.join('%s(%s)' % (mem[i], PTY.get(mem[i])) for i in sorted(range(len(mem)), key=lambda i: -wh_ctrl[i])[:6]))
    print('  orthogonality: dominance %+.3f | cooperation %+.3f | reactivity %+.3f'
          % (corr(antag, bdv('dominance_z')), corr(antag, bdv('cooperation_z')), corr(antag, bdv('reactivity_z'))))
    ao = sorted(range(len(mem)), key=lambda i: -antag[i])
    print('  top antagonists (controlled): %s' % ', '.join('%s(%s)' % (mem[i], PTY.get(mem[i])) for i in ao[:8]))

    print('\n### the two axes are distinct: corr(grandstand, antagonism_controlled) = %+.3f ###' % corr(grand, antag))
    print('\n--- reliability (split-half >=4 hearings) ---')
    memR = [m for m in mem if len(byhear[m]) >= 4]
    def half(which, idx):
        out = []
        for m in memR:
            h = byhear[m][which::2]; t = max(sum(x[0] for x in h), 1); out.append(sum(x[idx] for x in h) / t)
        return z(out)
    for nm, idx in [('antagonism', 1), ('grandstand', 2)]:
        r = corr(half(0, idx), half(1, idx)); print('  %-12s n=%d SB=%+.3f' % (nm, len(memR), 2 * r / (1 + r) if r > -1 else float('nan')))
    print('\n--- AUDIT: flagged HOSTILE turns (judge the lexicon) ---')
    for m in sorted(mem, key=lambda m: -agg[m]['wit_hostile'])[:6]:
        print('  %s (%d):' % (m, agg[m]['wit_hostile']))
        for s in audit.get(m, [])[:2]: print('     "%s"' % s)

if __name__ == '__main__':
    main()
