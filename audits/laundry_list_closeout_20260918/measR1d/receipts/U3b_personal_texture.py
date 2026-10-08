# -*- coding: utf-8 -*-
"""measR1d U3b: the desk's OTHER interview-text surface -- personal texture.

make_member_desk.py:404 loads data/members/member_personal_texture.json and ranks its items with
_PERSONAL_SOURCE_QUALITY (:437-441, 'INTERVIEW': 5).  Unlike the interview footprint (metadata
only) these items carry VERBATIM row text in 'claim' and 'evidence', so this surface can display a
host's sentence as the member's personal detail.  1,059 of the 4,751 items are source='INTERVIEW'.

For each INTERVIEW item this
  (1) runs D-U2 on the item's own claim/evidence text (member = the item's member), and
  (2) pins the item to its speeches row(s) by (member, date, package) + text containment, and
      reports how many land on a U2-affected row.
Seeded (20260918) 20-row graded sample written out.  READ-ONLY.
"""
import collections, csv, io, json, os, re, sqlite3, sys, random

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = LIVE + r'\social_media.db'
SEED = 20260918

src = io.open(os.path.join(HERE, 'U2_row_census.py'), encoding='utf-8').read()
cut = src.index('# ---------------------------------------------------------------- pass 1: lexicon')
H = {'__name__': '_u2'}
exec(compile(src[:cut], 'U2<prelude>', 'exec'), H)
TAG, STOP, tag_parts, is_upper_tag, nrm = H['TAG'], H['STOP'], H['tag_parts'], H['is_upper_tag'], H['nrm']
ROSTER_SUR = H['ROSTER_SUR']

AFF = set(json.load(io.open(os.path.join(HERE, 'U2c_all_affected_ids.json'), encoding='utf-8')))
FL = {r['rowid']: r for r in json.load(io.open(os.path.join(HERE, 'U2_flagged_rows.json'), encoding='utf-8'))}

# SPEAKER_LEX must match U2's; rebuild it from the corpus the same way
con = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
rows = con.execute("SELECT rowid, member, date, package, text FROM speeches WHERE source='INTERVIEW'").fetchall()
con.close()
lex = collections.Counter()
for rid, mem, dt, pkg, txt in rows:
    if not txt or H['allcaps_row'](txt):
        continue
    for m in TAG.finditer(txt):
        tg = m.group(1)
        if not is_upper_tag(tg):
            continue
        hon, up = tag_parts(tg)
        if len(up) >= 2 and not all(w in STOP for w in up):
            last = nrm(up[-1])
            if len(last) >= 3 and up[-1] not in STOP:
                lex[last] += 1
SPEAKER_LEX = set(ROSTER_SUR) | set(lex)


def qualifies(tg):
    hon, up = tag_parts(tg)
    if not up or all(w in STOP for w in up):
        return False
    nonstop = [w for w in up if w not in STOP]
    if hon or len(nonstop) >= 2:
        return True
    return len(up) == 1 and nrm(up[0]) in SPEAKER_LEX


def foreign_tags(text, member):
    out = []
    mp = nrm(member).split()
    msur = mp[-1] if mp else ''
    for m in TAG.finditer(text or ''):
        tg = m.group(1)
        if not is_upper_tag(tg) or not qualifies(tg):
            continue
        hon, up = tag_parts(tg)
        if msur and msur in [nrm(w) for w in up]:
            continue
        out.append((m.start(1), ' '.join(tg.split())))
    return out


BY = collections.defaultdict(list)
for rid, mem, dt, pkg, txt in rows:
    BY[(mem, (dt or '')[:10], pkg)].append((rid, txt or ''))


def nz(s):
    return ' '.join(str(s or '').split()).lower()


D = json.load(io.open(LIVE + r'\data\members\member_personal_texture.json', encoding='utf-8'))
items = []
for mem, v in (D.get('members') or {}).items():
    lst = v if isinstance(v, list) else (v.get('items') or [])
    for it in lst:
        if str(it.get('source') or '').upper() != 'INTERVIEW':
            continue
        items.append((mem, it))
print('personal-texture INTERVIEW items: %d  (of %d items over %d members)'
      % (len(items), sum(len(v if isinstance(v, list) else (v.get('items') or []))
                         for v in (D.get('members') or {}).values()), len(D.get('members') or {})))

res = []
tagc = collections.Counter()
for mem, it in items:
    ev = (it.get('evidence') or '')
    cl = (it.get('claim') or '')
    ft_ev = foreign_tags(ev, mem)
    ft_cl = foreign_tags(cl, mem)
    pkg = it.get('locator') or it.get('url') or ''
    day = (it.get('date') or '')[:10]
    cands = BY.get((mem, day, pkg), [])
    hit_rows = []
    probe = nz(ev)[:60]
    for rid, txt in cands:
        if probe and probe in nz(txt):
            hit_rows.append(rid)
    aff = [r for r in hit_rows if r in AFF]
    for _, t in ft_ev:
        tagc[t] += 1
    res.append(dict(member=mem, date=day, package=pkg, category=it.get('category'),
                    display_eligible=bool(it.get('display_eligible')),
                    narrative_eligible=bool(it.get('narrative_eligible')),
                    tags_in_evidence=ft_ev, tags_in_claim=ft_cl,
                    rows=hit_rows, affected_rows=aff, evidence=ev, claim=cl))

WT = [r for r in res if r['tags_in_evidence'] or r['tags_in_claim']]
WA = [r for r in res if r['affected_rows']]
DE = [r for r in res if r['display_eligible']]
DEWT = [r for r in WT if r['display_eligible']]
NE = [r for r in res if r['narrative_eligible']]
NEWT = [r for r in WT if r['narrative_eligible']]
print()
print('items whose DISPLAYED text contains a foreign speaker tag : %d  (%.2f%%)'
      % (len(WT), 100.0 * len(WT) / max(1, len(res))))
print('   of those, display_eligible=True                        : %d' % len(DEWT))
print('   of those, narrative_eligible=True                      : %d' % len(NEWT))
print('items pinned to a U2-affected speeches row                : %d' % len(WA))
print('display_eligible INTERVIEW items overall                  : %d' % len(DE))
print('narrative_eligible INTERVIEW items overall                : %d' % len(NE))
print('items that could not be pinned to any row                 : %d' % sum(1 for r in res if not r['rows']))
print()
print('most frequent foreign tags inside displayed personal-texture text:')
for t, n in tagc.most_common(15):
    print('   %4d  %s' % (n, t[:60]))
print()
print('members affected: %d' % len({r['member'] for r in WT}))
print()
print('=== every item whose displayed text carries a foreign tag (up to 25 shown) ===')
for i, r in enumerate(sorted(WT, key=lambda x: (x['member'], x['date']))[:25], 1):
    print('%2d. %-24s %s %-18s display=%s narrative=%s tags=%s'
          % (i, r['member'][:24], r['date'], str(r['category'])[:18], r['display_eligible'],
             r['narrative_eligible'], [t for _, t in (r['tags_in_evidence'] or r['tags_in_claim'])]))
    ev = ' '.join(r['evidence'].split())
    a = (r['tags_in_evidence'] or r['tags_in_claim'])[0][0]
    print('     ...%s  >>>  %s...' % (ev[max(0, a - 120):a], ev[a:a + 220]))

with io.open(os.path.join(HERE, 'U3b_personal_texture_hits.json'), 'w', encoding='utf-8') as f:
    json.dump(WT, f, ensure_ascii=False, indent=1)
rnd = random.Random(SEED)
pool = sorted(res, key=lambda r: (r['member'], r['date'], r['category'] or ''))
s20 = rnd.sample(pool, 20)
with io.open(os.path.join(HERE, 'U3b_personal_sample20_GRADED.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['n', 'member', 'date', 'category', 'display_eligible', 'rows', 'affected_rows',
                'foreign_tags', 'GRADE', 'evidence'])
    for j, r in enumerate(s20, 1):
        ft = [t for _, t in (r['tags_in_evidence'] + r['tags_in_claim'])]
        w.writerow([j, r['member'], r['date'], r['category'], int(r['display_eligible']),
                    ' '.join(map(str, r['rows'])), ' '.join(map(str, r['affected_rows'])),
                    ' | '.join(ft), 'FOREIGN-SPEECH-PRESENT' if ft else 'CLEAN',
                    ' '.join(r['evidence'].split())])
print()
print('wrote U3b_personal_texture_hits.json (%d), U3b_personal_sample20_GRADED.csv' % len(WT))
print('DONE U3b')
