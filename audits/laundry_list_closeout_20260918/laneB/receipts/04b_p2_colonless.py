# -*- coding: utf-8 -*-
"""LANE B P2 (part 2): COLON-LESS residual speaker tags.

04_p2 anchored on a trailing colon and therefore MISSED the canonical July example: row 196861
reads "... SEN. RICHARD BLUMENTHAL, D-CONN.There's a gra..." -- the upstream turn splitter
dropped the colon, so the tag runs straight into the next turn's prose.

DETECTOR D-P2' (union with D-P2)
  A turn-boundary marker is an ALL-CAPS honorific+name span inside otherwise mixed-case prose:
      (SEN.|REP.|SENATOR|REPRESENTATIVE|CONGRESSMAN|CONGRESSWOMAN|GOV.|PRES.|PRESIDENT|GOVERNOR
       |CHAIRMAN|CHAIRWOMAN|FMR.|AMB.|DR.)  +  1-3 ALL-CAPS name tokens
      + optional party/state tail  , D-CONN. / (D-NY 14TH DISTRICT) / , R-TX
  with NO trailing colon required.  Mixed-case context is required (the row must not be an
  all-caps row) so CREC all-caps headings do not qualify.  Classification of a mention at offset
  pos relative to the FIRST marker B0 is identical to D-P2: pos >= B0 -> wrong speaker; nearest
  preceding marker naming the target -> the July shape.
READ-ONLY. Consumes SCRATCH/refs.jsonl."""
import collections, io, json, os, re, sqlite3, sys, unicodedata
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
SCRATCH = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
           r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
           r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB')
PK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\laneB\receipts')

C = {m['member']: m for m in json.load(io.open(LIVE + r'\data\engine\congestion.json', encoding='utf-8'))}
def nrm(s):
    s = unicodedata.normalize('NFD', s or ''); s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z ]', '', s.lower()).strip()

HON = (r'(?:SEN\.|REP\.|PRES\.|GOV\.|DR\.|FMR\.|AMB\.|SENATOR|REPRESENTATIVE|CONGRESSMAN|'
       r'CONGRESSWOMAN|CHAIRMAN|CHAIRWOMAN|PRESIDENT|GOVERNOR|SPEAKER)')
TAIL = r'(?:\s*,\s*[RDI]-[A-Z][A-Z\.]{1,14}\.?|\s*\([RDI]-[A-Z]{2}[^)]{0,22}\)|\s*\([^)]{1,22}\))?'
NOCOLON = re.compile(HON + r'\s+[A-Z][A-Z\'\.\-]{1,22}(?:\s+[A-Z][A-Z\'\.\-]{1,22}){0,3}' + TAIL)
COLON = re.compile(r'(?:(?<=^)|(?<=[\s>"\u201c\'\(\-\u2014]))((?:' + HON + r'\s+)?'
                   r'[A-Z][A-Z\.\'\-]{1,24}(?:\s+[A-Z][A-Z\.\'\-]{1,24}){0,3}'
                   r'(?:\s*\([^)]{1,18}\))?(?:\s*,\s*[A-Z][A-Z\.\'\- ]{2,40})?)\s*::?')
ANGLE = re.compile(r'>>')
SURNAMES = {nrm(m).split()[-1] for m in C}
STOP = set('''USA GAO DOI EPA FBI CIA NSA DOJ DOD HHS IRS FEMA SNAP CNN FOX MSNBC NPR PBS ABC CBS NBC BBC AP
NATO UN EU WHO CDC NIH FDA SEC FCC FTC HUD VA DHS TSA ICE CBP ATF DEA NASA NOAA USDA DOT FAA GDP CEO ACA
WCNSF KUCB URI NPS DACA GAC SAFE RELIEF ACT BANKING COMMITTEE SENATE HOUSE CONGRESS CAUCUS SUBCOMMITTEE
CHAIR RANKING DEMOCRAT REPUBLICAN MAJORITY MINORITY LEADER WHIP HEALTH UNITS NEXT STEPS TITLE SECTION'''.split())


def allcaps_row(t):
    letters = [c for c in t if c.isalpha()]
    return letters and sum(1 for c in letters if c.isupper()) / len(letters) > 0.85


def qualifies_colon(tag):
    core = re.sub(r'\([^)]*\)', ' ', tag)
    toks = [t for t in re.split(r'[^A-Za-z\.\'\-]+', core) if t]
    if not toks: return False
    has_hon = bool(re.match(r'^(?:' + HON + r')$', toks[0], re.I))
    words = [t for t in toks if not re.match(r'^(?:' + HON + r')$', t, re.I)]
    if not words: return False
    up = [w.strip(".'-").upper() for w in words]
    if all(w in STOP for w in up): return False
    if has_hon: return True
    if any(nrm(w) in SURNAMES for w in up): return True
    if len(up) >= 2 and not any(w in STOP for w in up): return True
    return False


def boundaries(text):
    out = []
    ac = allcaps_row(text)
    for m in ANGLE.finditer(text):
        out.append((m.start(), m.end(), '>>', 'ANGLE'))
    for m in COLON.finditer(text):
        if qualifies_colon(m.group(1)):
            out.append((m.start(1), m.end(0), m.group(1), 'COLON'))
    if not ac:
        for m in NOCOLON.finditer(text):
            out.append((m.start(), m.end(), m.group(0), 'NOCOLON'))
    out.sort()
    # drop NOCOLON markers that duplicate a COLON marker at the same start
    ded, last = [], None
    for s, e, tg, kind in out:
        if last is not None and s == last[0]:
            if kind == 'NOCOLON': continue
        ded.append((s, e, tg, kind)); last = (s, e)
    return ded


refs = [json.loads(l) for l in io.open(os.path.join(SCRATCH, 'refs.jsonl'), encoding='utf-8')]
art = json.load(io.open(LIVE + r'\member_references.json', encoding='utf-8'))
AE = {(e['a'], e['b']): e for e in art['edges']}
sids = sorted({r['_sid'] for r in refs if r['src'] in ('INTERVIEW', 'CHRG', 'CREC') and r['_sid'] != ''})
con = sqlite3.connect('file:%s?mode=ro' % (LIVE + r'\social_media.db').replace('\\', '/'), uri=True, timeout=180)
con.execute('PRAGMA query_only=ON')
TXT = {}
for i in range(0, len(sids), 900):
    ch = sids[i:i + 900]
    for rid, t in con.execute('SELECT rowid, text FROM speeches WHERE rowid IN (%s)' % ','.join('?' * len(ch)), ch):
        TXT[rid] = t or ''
# full-corpus context: how many INTERVIEW rows anywhere carry a colon-less residual tag
full = collections.Counter()
for src, t in con.execute('SELECT source, text FROM speeches'):
    if not t: continue
    full[src + '|rows'] += 1
    if allcaps_row(t): continue
    if NOCOLON.search(t): full[src + '|nocolon_tag'] += 1
con.close()
print('FULL-CORPUS colon-less residual-tag rows:')
for s in ('INTERVIEW', 'CHRG', 'CREC'):
    print('  %-10s %7d of %7d rows  (%.3f%%)' % (s, full[s + '|nocolon_tag'], full[s + '|rows'],
                                                 100.0 * full[s + '|nocolon_tag'] / max(1, full[s + '|rows'])))
BND = {rid: b for rid, b in ((rid, boundaries(t)) for rid, t in TXT.items()) if b}
kinds = collections.Counter(k for b in BND.values() for *_, k in b)
print()
print('mention-producing rows with >=1 marker (UNION detector): %d of %d (%.3f%%)' %
      (len(BND), len(TXT), 100.0 * len(BND) / max(1, len(TXT))))
print('marker kinds: %s' % dict(kinds))

hits = []
for r in refs:
    if r['src'] not in ('INTERVIEW', 'CHRG', 'CREC'): continue
    b = BND.get(r['_sid'])
    if not b: continue
    pos = r['_pos'] - 1
    ll = len(r['_lit'])
    B0 = b[0][0]
    inside = any(s < pos + ll and pos < e for s, e, _, _ in b)
    if pos < B0 and not inside: continue
    prev = [x for x in b if x[0] <= pos]
    ptag = prev[-1][2] if prev else ''
    pkind = prev[-1][3] if prev else ''
    tn = nrm(r['b']).split()
    names_target = bool(ptag) and (tn[-1] in nrm(ptag).split())
    hits.append(dict(r, _prev_tag=ptag, _kind=pkind, _names_target=names_target, _inside_tag=inside))

print()
print('=' * 78)
print('P2 UNION RESULTS (D-P2 colon  OR  D-P2\' colon-less)')
print('=' * 78)
A = hits
Bs = [h for h in A if h['_names_target']]
Cs = [h for h in A if h['_inside_tag']]
print('P2-A  mentions downstream of a turn boundary : %d   by source %s' % (len(A), dict(collections.Counter(h['src'] for h in A))))
print('        by marker kind: %s' % dict(collections.Counter(h['_kind'] for h in A)))
print('P2-B  nearest marker NAMES the target        : %d' % len(Bs))
print('P2-C  matched name IS inside a marker        : %d' % len(Cs))
for label, S in (('P2-A', A), ('P2-B', Bs)):
    ed = {(h['a'], h['b']) for h in S}
    eda = {k for k in ed if k in AE}
    sc = [h for h in S if h['_counted_scored']]
    eds = {(h['a'], h['b']) for h in sc if (h['a'], h['b']) in AE}
    signed = {k for k in eds if AE[k]['pos'] + AE[k]['neg'] > 0}
    print()
    print('%s : windows %d | dyads %d | SHIPPED edges %d | windows in n_scored %d' % (label, len(S), len(ed), len(eda), len(sc)))
    print('      shipped edges with >=1 SCORED contaminated window : %d' % len(eds))
    print('      of those SIGNED (pos+neg>0)                       : %d' % len(signed))
    print('      of those drawn (n_scored>=2)                      : %d' % sum(1 for k in eds if AE[k]['n_scored'] >= 2))
    print('      SIGNED and drawn                                  : %d' % sum(1 for k in signed if AE[k]['n_scored'] >= 2))
print()
print('=== 15 examples (speaker -> target | source id | 160-char excerpt) ===')
seen = set(); n = 0
for h in sorted(A, key=lambda x: (not x['_names_target'], not x['_counted_scored'], x['a'])):
    k = (h['a'], h['b'], h['_sid'])
    if k in seen: continue
    seen.add(k)
    print('%2d. %-23s -> %-23s | sid=%-7s %s | marker=%r [%s] scored=%s shipped=%s' %
          (n + 1, h['a'][:23], h['b'][:23], h['_sid'], h['src'][:4], ' '.join(h['_prev_tag'].split())[:30],
           h['_kind'], h['_counted_scored'], (h['a'], h['b']) in AE))
    print('      %s' % ' '.join((h.get('_raw_w') or h['w']).split())[:160])
    n += 1
    if n >= 15: break
print()
print('=== Raskin -> Blumenthal now caught? ===')
rb = [h for h in A if h['a'] == 'Jamie Raskin' and 'Blumenthal' in h['b']]
print('caught: %s' % bool(rb))
for h in rb:
    print('  sid=%s marker=%r kind=%s names_target=%s scored=%s' % (h['_sid'], h['_prev_tag'], h['_kind'], h['_names_target'], h['_counted_scored']))
    print('  window: %s' % ' '.join((h.get('_raw_w') or h['w']).split())[:200])
with io.open(os.path.join(PK, '04b_p2_union_examples.json'), 'w', encoding='utf-8') as f:
    json.dump(A, f, ensure_ascii=False, indent=1)
print()
print('wrote receipts/04b_p2_union_examples.json (%d rows)' % len(A))
print('DONE 04b')
