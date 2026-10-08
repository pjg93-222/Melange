# -*- coding: utf-8 -*-
"""LANE B P2: interview speaker-tag bleed.

CONTEXT ESTABLISHED BY 02b: the `speeches` table is TURN-SEGMENTED -- one speaker's turn per row,
mean INTERVIEW turn 455 chars, zero newlines, zero '>>' in 153,572/153,576 rows.  A window
(text[pos-170:pos+200]) therefore cannot cross a turn boundary UNLESS the upstream turn splitter
failed and left a residual speaker tag inside one row.  That residual tag is the only surviving
mechanism for the July defect, so it is what the detector looks for.

DETECTOR D-P2 (stated precisely)
  A row is CONTAMINATED if its text contains a turn-boundary marker:
    (a) '>>' , or
    (b) a speaker tag  [HONORIFIC] NAME[, ROLE/PARTY]:  where the tag is ALL-CAPS, is not in the
        acronym stoplist, and qualifies as a person by one of: an honorific prefix
        (SEN./REP./PRES./GOV./DR./MR./MS./MRS./FMR./AMB./SENATOR/REPRESENTATIVE/CHAIRMAN/
        CHAIRWOMAN/SPEAKER), OR two or more capitalised word tokens, OR a token equal to a roster
        surname.
  Let B0 = char offset of the FIRST boundary in the row.  The row's attributed speaker owns only
  text[0:B0].  A mention at offset pos is then classified:
    P2-A  pos >= B0                      -> WRONG SPEAKER (the text belongs to a later turn)
    P2-B  P2-A and the nearest preceding tag NAMES the target -> target IS the adjacent turn's
          speaker (the July 'Raskin -> Blumenthal' shape)
    P2-C  the matched name span overlaps a tag span -> the 'mention' is a speaker LABEL, not a
          reference at all
  Offsets: resolve_ref scans ' '+text.lower()+' ', so a mention's offset in `text` is pos-1.
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
SURNAMES = {nrm(m).split()[-1] for m in C}
FIRSTS = {nrm(m).split()[0] for m in C}

STOP = set('''USA GAO DOI FMR EPA FBI CIA NSA DOJ DOD HHS IRS FEMA SNAP WIC CNN FOX MSNBC NPR PBS ABC CBS NBC
BBC AP UPI NATO UN EU WHO CDC NIH FDA SEC FCC FTC FHA HUD VA DHS TSA ICE CBP ATF DEA NASA NOAA USDA DOT FAA
GDP CEO CFO COO CTO PPP ACA CHIP TANF SSI SSDI COLA AMT IRA HSA FSA HMO PPO NIL P.S PS NB RE ETC INC LLC LTD
CO CORP DBA AKA FYI ASAP RSVP TBD TBA NA ND RD ST SEC. NO ID OK DC US U.S U.S.A WCNSF KUCB URI NPS DACA GAC
SAFE RELIEF ACT BILL TITLE SECTION CHAPTER ARTICLE AMENDMENT RESOLUTION BANKING COMMITTEE SENATE HOUSE
CONGRESS CAUCUS SUBCOMMITTEE CHAIR RANKING DEMOCRAT REPUBLICAN MAJORITY MINORITY LEADER WHIP'''.split())
HON = r'(?:SEN\.|REP\.|PRES\.|GOV\.|DR\.|MR\.|MS\.|MRS\.|FMR\.|AMB\.|SENATOR|REPRESENTATIVE|CHAIRMAN|CHAIRWOMAN|SPEAKER|PRESIDENT|GOVERNOR|CONGRESSMAN|CONGRESSWOMAN)'
TAG_RE = re.compile(r'(?:(?<=^)|(?<=[\s>"\u201c\u201d\'\(\-\u2014]))((?:' + HON + r'\s+)?'
                    r'[A-Z][A-Z\.\'\-]{1,24}(?:\s+[A-Z][A-Z\.\'\-]{1,24}){0,3}'
                    r'(?:\s*\([^)]{1,18}\))?(?:\s*,\s*[A-Z][A-Z\.\'\- ]{2,40})?)\s*::?')
ANGLE_RE = re.compile(r'>>')


def qualifies(tag):
    """Is this ALL-CAPS colon-terminated span a PERSON speaker tag (vs an acronym / bill heading)?"""
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
    """Sorted list of (start, end, tag_text) turn-boundary markers in a row."""
    out = []
    for m in ANGLE_RE.finditer(text):
        out.append((m.start(), m.end(), '>>'))
    for m in TAG_RE.finditer(text):
        tag = m.group(1)
        if qualifies(tag):
            out.append((m.start(1), m.end(0), tag))
    out.sort()
    return out


refs = [json.loads(l) for l in io.open(os.path.join(SCRATCH, 'refs.jsonl'), encoding='utf-8')]
art = json.load(io.open(LIVE + r'\member_references.json', encoding='utf-8'))
AE = {(e['a'], e['b']): e for e in art['edges']}

# need the full row text for every speech-derived ref -> fetch only the rows that produced a ref
sids = sorted({r['_sid'] for r in refs if r['src'] in ('INTERVIEW', 'CHRG', 'CREC') and r['_sid'] != ''})
print('distinct speech rows that produced >=1 mention: %d' % len(sids))
con = sqlite3.connect('file:%s?mode=ro' % (LIVE + r'\social_media.db').replace('\\', '/'), uri=True, timeout=180)
con.execute('PRAGMA query_only=ON')
TXT = {}
CH = 900
for i in range(0, len(sids), CH):
    chunk = sids[i:i + CH]
    q = 'SELECT rowid, text FROM speeches WHERE rowid IN (%s)' % ','.join('?' * len(chunk))
    for rid, t in con.execute(q, chunk):
        TXT[rid] = t or ''
con.close()
print('row texts loaded: %d' % len(TXT))

BND = {}
for rid, t in TXT.items():
    b = boundaries(t)
    if b: BND[rid] = b
print('rows with >=1 turn-boundary marker: %d  (%.3f%% of mention-producing rows)' %
      (len(BND), 100.0 * len(BND) / max(1, len(TXT))))
tag_inv = collections.Counter()
for b in BND.values():
    for _, _, tg in b: tag_inv[' '.join(tg.split())[:40]] += 1
print('distinct boundary markers: %d' % len(tag_inv))

hits = []
for r in refs:
    if r['src'] not in ('INTERVIEW', 'CHRG', 'CREC'): continue
    b = BND.get(r['_sid'])
    if not b: continue
    pos = r['_pos'] - 1          # resolve_ref offsets are into ' '+text.lower()+' '
    lit_len = len(r['_lit'])
    B0 = b[0][0]
    inside = any(s <= pos < e for s, e, _ in b) or any(s < pos + lit_len and pos < e for s, e, _ in b)
    if pos < B0 and not inside: continue
    prev = [x for x in b if x[0] <= pos]
    ptag = prev[-1][2] if prev else ''
    tn = nrm(r['b']).split()
    names_target = bool(ptag) and (tn[-1] in nrm(ptag).split() or nrm(ptag).strip() == nrm(r['b']))
    hits.append(dict(r, _B0=B0, _prev_tag=ptag, _names_target=names_target, _inside_tag=inside,
                     _nbound=len(b)))
print()
print('=' * 78)
print('P2 RESULTS')
print('=' * 78)
A = hits
Bsub = [h for h in A if h['_names_target']]
Csub = [h for h in A if h['_inside_tag']]
print('P2-A  mentions downstream of a turn boundary (WRONG SPEAKER) : %d' % len(A))
print('         by source: %s' % dict(collections.Counter(h['src'] for h in A)))
print('P2-B  ...where the nearest preceding tag NAMES the target    : %d   [July Raskin->Blumenthal shape]' % len(Bsub))
print('P2-C  ...where the matched name IS inside a speaker tag      : %d' % len(Csub))
print()
for label, S in (('P2-A', A), ('P2-B', Bsub)):
    ed = {(h['a'], h['b']) for h in S}
    eda = {k for k in ed if k in AE}
    sc = [h for h in S if h['_counted_scored']]
    eds = {(h['a'], h['b']) for h in sc if (h['a'], h['b']) in AE}
    signed = {k for k in eds if AE[k]['pos'] + AE[k]['neg'] > 0}
    print('%s : windows %d | dyads %d | SHIPPED edges %d | windows counted into n_scored %d'
          % (label, len(S), len(ed), len(eda), len(sc)))
    print('       shipped edges with >=1 such SCORED window : %d' % len(eds))
    print('       of those, SIGNED (pos+neg>0)              : %d' % len(signed))
    print('       of those, drawn (n_scored>=2)             : %d' % sum(1 for k in eds if AE[k]['n_scored'] >= 2))
    print('       of those signed AND drawn                 : %d' % sum(1 for k in signed if AE[k]['n_scored'] >= 2))
print()
print('=== up to 15 examples (speaker -> target | source id | 160-char excerpt) ===')
seen = set(); shown = 0
for h in sorted(A, key=lambda x: (not x['_names_target'], not x['_counted_scored'], x['a'])):
    k = (h['a'], h['b'], h['_sid'])
    if k in seen: continue
    seen.add(k)
    ex = ' '.join((h.get('_raw_w') or h['w']).split())[:160]
    print('%2d. %-24s -> %-24s | sid=%-7s src=%s tag=%-22r scored=%s edge_shipped=%s'
          % (shown + 1, h['a'][:24], h['b'][:24], h['_sid'], h['src'][:4], ' '.join(h['_prev_tag'].split())[:22],
             h['_counted_scored'], (h['a'], h['b']) in AE))
    print('      %s' % ex)
    shown += 1
    if shown >= 15: break
print()
print('=== Raskin -> Blumenthal (the named July example) ===')
rb = [r for r in refs if r['a'] == 'Jamie Raskin' and 'Blumenthal' in r['b']]
print('re-derived Raskin->Blumenthal mentions: %d  sources=%s' % (len(rb), dict(collections.Counter(r['src'] for r in rb))))
for r in rb[:6]:
    print('   [%s] sid=%s scored=%s  %s' % (r['src'], r['_sid'], r['_counted_scored'], ' '.join(r['w'].split())[:150]))
k = [kk for kk in AE if kk[0] == 'Jamie Raskin' and 'Blumenthal' in kk[1]]
print('shipped Raskin->Blumenthal edge: %s' % ([ (kk, AE[kk]['net'], AE[kk]['pos'], AE[kk]['neg'], AE[kk]['n_scored'], AE[kk].get('sources')) for kk in k ] or 'ABSENT'))
print()
print('=== boundary-marker inventory (top 60, for audit) ===')
for tg, n in tag_inv.most_common(60):
    print('   %-44r %5d' % (tg, n))
with io.open(os.path.join(PK, '04_p2_examples.json'), 'w', encoding='utf-8') as f:
    json.dump([{k: v for k, v in h.items() if k != '_mentionrow'} for h in A], f, ensure_ascii=False, indent=1)
print()
print('wrote receipts/04_p2_examples.json (%d rows)' % len(A))
print('DONE 04')
