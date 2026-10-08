# -*- coding: utf-8 -*-
"""LANE B P3 (part 2): my hand grades of the 30-window random sample (seed 20260918), exact
Clopper-Pearson intervals, and a separate detector for the CREC roll-call / cosponsor-signature
LIST artefact that turns out to dominate the unguarded population.

GRADING RULE APPLIED: "does the matched name denote the ROSTER MEMBER in this window?"
  member      - yes, the text is about that member
  non-member  - a different person carrying the same name (the P3 defect proper)
  unclear     - cannot tell from the window
A SECOND, INDEPENDENT tag is recorded because it changes the reading of the number:
  list_artefact - the window is a CREC roll-call vote roster or a cosponsor signature block.  The
  person IS the member, so it is NOT a namesake collision, but a vote roster is not a substantive
  reference either; it is a distinct relevance failure living in the same population.

DETECTOR D-P3b (list artefact, measured repo-wide)
  window contains >= 10 DISTINCT roster surnames AND the ratio of roster-surname tokens to all
  word tokens is >= 0.35  -> roll-call / signature list.
READ-ONLY."""
import collections, io, json, os, re, sys, unicodedata
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
SCRATCH = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
           r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
           r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB')
PK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\laneB\receipts')

# --- my grades, keyed by sample index (see receipts/05_p3_namesake.out.txt lines 70-158) ---
GRADES = {
 1:  ('member', 'list_artefact', 'CREC roll-call roster; span straddles "Scott, Austin" / "Scott, David"'),
 2:  ('member', '', '"which is what Adam Schiff has done acting as a investigator"'),
 3:  ('member', '', '"JAMES COMER IS ACTIVELY INVESTIGATING THE HUNTER BIDEN LAPTOP"'),
 4:  ('member', '', '"House impeachment manager Adam Schiff\'s committee"'),
 5:  ('non-member', '', 'Mike Rogers who "just barely lost in the last cycle to Elissa Slotkin" = the '
                        'Michigan Senate candidate, NOT Rep. Mike Rogers (AL). The July namesake shape.'),
 6:  ('member', '', '"The President and Mitch McConnell put huge pressure on these folks"'),
 7:  ('member', 'list_artefact', 'CREC roll-call roster'),
 8:  ('member', '', '"I ASKED CHUCK SCHUMER, GIVE US A SIMPLE SEVEN-WEEK STOPGAP"'),
 9:  ('member', 'list_artefact', 'CREC roll-call roster; "Gonzalez, Vicente Gonzalez-Colon"'),
 10: ('member', '', '"Jon Stewart and Kirsten Gillibrand want you to believe"'),
 11: ('member', 'list_artefact', 'CREC roll-call roster'),
 12: ('member', '', '"Chuck Schumer and Hakeem Jeffries are doing right now"'),
 13: ('member', '', '"the same Mitch McConnell who came to the floor on April 9"'),
 14: ('member', '', '"Today I had a quick conversation with Tim Scott"'),
 15: ('member', '', '"Hakeem Jeffries is here"'),
 16: ('member', '', '"Hakeem Jeffries is sticking with his three years or bust"'),
 17: ('member', '', '"that\'s Ralph Norman. He is always looking for attention."'),
 18: ('member', 'list_artefact', 'CREC cosponsor signature block ending "...Rick Scott."'),
 19: ('member', 'list_artefact', 'CREC signature block ending "United States Senators."'),
 20: ('member', 'list_artefact', 'CREC roll-call roster'),
 21: ('member', '', '"As Chuck Schumer was saying, in politics, in the media"'),
 22: ('member', '', '"Adam Schiff always over-promised and under-delivered"'),
 23: ('member', '', '"Lindsey Graham was -- ... no better friend, no tougher adversary"'),
 24: ('member', 'list_artefact', 'CREC roll-call roster'),
 25: ('member', 'list_artefact', 'CREC cosponsor signature block'),
 26: ('member', '', '"Thomas Massie and I tried to prevent this war in Iran"'),
 27: ('member', '', '"PRE-CHUCK SCHUMER AND THE DEMOCRATS ARE PREVENTING"'),
 28: ('member', '', '"Nancy Pelosi is the one who changed it"'),
 29: ('member', 'list_artefact', 'CREC roll-call roster'),
 30: ('member', '', '"I just don\'t see that Jim Jordan has got a path forward to being the speaker"'),
}


def clopper_pearson(k, n, alpha=0.05):
    """Exact binomial CI without scipy: invert the Beta CDF by bisection on the binomial tail."""
    from math import comb
    def binom_cdf(p, k, n):            # P(X <= k)
        return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    lo, hi = 0.0, 0.0
    if k > 0:                          # solve P(X >= k | p) = alpha/2  ->  1 - cdf(k-1, p) = a/2
        a, b = 0.0, 1.0                # 1-cdf(k-1,p) INCREASES in p: too small -> raise a
        for _ in range(200):
            m = (a + b) / 2
            if 1 - binom_cdf(m, k - 1, n) < alpha / 2: a = m
            else: b = m
        lo = (a + b) / 2
    if k < n:                          # solve P(X <= k) = alpha/2
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if binom_cdf(m, k, n) > alpha / 2: a = m
            else: b = m
        hi = (a + b) / 2
    else:
        hi = 1.0
    return lo, hi


samp = json.load(io.open(os.path.join(PK, '05_p3_sample30_ungraded.json'), encoding='utf-8'))
rows = samp['rows']
POP = samp['population']
for r in rows:
    g, tag, why = GRADES[r['n']]
    r['grade'] = g; r['second_tag'] = tag; r['rationale'] = why
tal = collections.Counter(r['grade'] for r in rows)
lst = sum(1 for r in rows if r['second_tag'] == 'list_artefact')
print('=' * 78)
print('P3 GRADED SAMPLE (n=30, seed 20260918, population = %d unguarded windows)' % POP)
print('=' * 78)
print('grades: %s' % dict(tal))
for g in ('member', 'non-member', 'unclear'):
    k = tal.get(g, 0)
    lo, hi = clopper_pearson(k, 30)
    print(f'  {g:<11} {k:2d}/30 = {100.0*k/30:5.1f}%   95% CP CI [{100*lo:5.1f}%, {100*hi:5.1f}%]'
          f'   -> {round(POP*lo)}-{round(POP*hi)} of {POP} windows (point {round(POP*k/30)})')
lo, hi = clopper_pearson(lst, 30)
print()
print(f'SECOND TAG  list_artefact  {lst:2d}/30 = {100.0*lst/30:5.1f}%   95% CP CI '
      f'[{100*lo:5.1f}%, {100*hi:5.1f}%]  -> {round(POP*lo)}-{round(POP*hi)} of {POP} (point {round(POP*lst/30)})')
print()
print('the single non-member row:')
for r in rows:
    if r['grade'] == 'non-member':
        print('  [%02d] %s -> %s | literal=%r src=%s sid=%s scored=%s edge_shipped=%s'
              % (r['n'], r['speaker'], r['target'], r['literal'], r['src'], r['sid'], r['scored'], r['edge_shipped']))
        print('       %s' % r['rationale'])
        print('       window: %s' % r['window'][:300])
with io.open(os.path.join(PK, '05b_p3_sample30_GRADED.json'), 'w', encoding='utf-8') as f:
    json.dump({'seed': 20260918, 'population': POP, 'n': 30,
               'grades': dict(tal), 'list_artefact': lst, 'rows': rows}, f, ensure_ascii=False, indent=1)
print()
print('wrote receipts/05b_p3_sample30_GRADED.json')

# ---------------- D-P3b: roll-call / signature list artefact, measured repo-wide ----------------
C = {m['member']: m for m in json.load(io.open(LIVE + r'\data\engine\congestion.json', encoding='utf-8'))}
def nrm(s):
    s = unicodedata.normalize('NFD', s or ''); s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z ]', '', s.lower()).strip()
SUR = {nrm(m).split()[-1] for m in C}
refs = [json.loads(l) for l in io.open(os.path.join(SCRATCH, 'refs.jsonl'), encoding='utf-8')]
art = json.load(io.open(LIVE + r'\member_references.json', encoding='utf-8'))
AE = {(e['a'], e['b']): e for e in art['edges']}


def is_list(w):
    toks = [t for t in re.split(r'[^A-Za-z\'\-]+', w) if len(t) > 1]
    if len(toks) < 12: return False
    hit = [t for t in toks if nrm(t) in SUR]
    return len(set(nrm(t) for t in hit)) >= 10 and len(hit) / len(toks) >= 0.35


for r in refs:
    r['_list'] = is_list(r.get('_raw_w') or r['w'])
L = [r for r in refs if r['_list']]
print()
print('=' * 78)
print('D-P3b  ROLL-CALL / SIGNATURE-LIST ARTEFACT (repo-wide)')
print('=' * 78)
print('mentions whose window is a roster/signature list : %d  (%.1f%% of all %d mentions)'
      % (len(L), 100.0 * len(L) / len(refs), len(refs)))
print('  by source : %s' % dict(collections.Counter(r['src'] for r in L)))
print('  by form   : %s' % dict(collections.Counter(r.get('_form') for r in L)))
sc = [r for r in L if r['_counted_scored']]
eds = {(r['a'], r['b']) for r in sc if (r['a'], r['b']) in AE}
print('  counted into n_scored                         : %d' % len(sc))
print('  SHIPPED edges with >=1 such SCORED window     : %d' % len(eds))
print('  of those SIGNED (pos+neg>0)                   : %d' % sum(1 for k in eds if AE[k]['pos'] + AE[k]['neg'] > 0))
print('  of those drawn (n_scored>=2)                  : %d' % sum(1 for k in eds if AE[k]['n_scored'] >= 2))
bye = collections.defaultdict(list)
for r in refs:
    if r['_counted_scored']: bye[(r['a'], r['b'])].append(r)
allL = [k for k, v in bye.items() if k in AE and v and all(x['_list'] for x in v)]
print('  SHIPPED edges whose ENTIRE scored support is list-artefact : %d' % len(allL))
print('    of those SIGNED : %d   drawn : %d' % (sum(1 for k in allL if AE[k]['pos'] + AE[k]['neg'] > 0),
                                                 sum(1 for k in allL if AE[k]['n_scored'] >= 2)))
print()
print('  overlap with the UNGUARDED population:')
CUEFREE = [r for r in refs if r.get('_form') == 'BARE']
print('    (unguarded computed in 05; here: list-artefact mentions that are BARE-form) : %d'
      % sum(1 for r in L if r.get('_form') == 'BARE'))
print()
print('  10 examples:')
for r in L[:10]:
    print('    %-24s -> %-24s [%s] %s' % (r['a'][:24], r['b'][:24], r['src'][:4],
                                          ' '.join((r.get('_raw_w') or r['w']).split())[:110]))
print('DONE 05b')
