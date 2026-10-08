# -*- coding: utf-8 -*-
"""measR1d U3 + U4.

U3  DESK.  fec/surfaces/make_member_desk.py:1961-1976 emits ONE footprint item per
    (member, date, package) -- an APPEARANCE RECORD whose title is
      '<network> appearance -- N segment(s) - W words'
    so no row text is displayed there.  Row TEXT reaches the desk by exactly one path:
    _apply_grade() (make_member_desk.py:1933-1943) copies grade['snip'] onto the item, and the
    template renders it as a QUOTATION on the member's record
    (fec/surfaces/templates/make_member_desk_00.tpl:1858  ->  <div class=ev-snip>"..."</div>).
    grade['snip'] comes from data/stance/interviews_cu.csv via _grade_index (:1849-1924).
    So U3 has two measurable exposures: (a) the appearance records' segment/word TALLIES, and
    (b) the <=37 displayed CU passages -- which are the SAME objects U4 scores.

U4  STANCE.  fec/stance/build_media_blend.py:227-259 (LIVE copy) reads
    data/stance/interview_stance_final.csv row-by-row (PASSAGE level), drops neutral/unresolved/
    untiered/uncategorised rows, and adds the survivors to the press pillar at own-source weight
    1.0.  This script re-derives the survivor count and, for every one of the 37 passages, asks
    whether the SCORED WORDS sit after (or inside) a foreign speaker tag.

READ-ONLY: mode=ro sqlite, csv reads, writes only into this packet's receipts dir.
"""
import collections, csv, datetime, io, json, os, re, sqlite3, sys, unicodedata, random

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = LIVE + r'\social_media.db'
SEED = 20260918

src = io.open(os.path.join(HERE, 'U2_row_census.py'), encoding='utf-8').read()
cut = src.index('# ---------------------------------------------------------------- pass 1: lexicon')
H = {'__name__': '_u2'}
exec(compile(src[:cut], 'U2<prelude>', 'exec'), H)
TAG, STOP, tag_parts, is_upper_tag = H['TAG'], H['STOP'], H['tag_parts'], H['is_upper_tag']
allcaps_row, nrm, ROSTER_SUR, fn_compat = H['allcaps_row'], H['nrm'], H['ROSTER_SUR'], H['fn_compat']

AFF = set(json.load(io.open(os.path.join(HERE, 'U2c_all_affected_ids.json'), encoding='utf-8')))
FL = {r['rowid']: r for r in json.load(io.open(os.path.join(HERE, 'U2_flagged_rows.json'), encoding='utf-8'))}
ROSTER = {m['member'] for m in json.load(io.open(LIVE + r'\data\engine\congestion.json', encoding='utf-8'))}

con = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
rows = con.execute("SELECT rowid, member, date, chamber, package, nwords, text FROM speeches "
                   "WHERE source='INTERVIEW'").fetchall()

# ------------------------------------------------------------------ U3
NET = {'transcripts.cnn.com': 'CNN', 'www.cnn.com': 'CNN', 'www.foxnews.com': 'Fox News',
       'foxnews.com': 'Fox News', 'www.ms.now': 'MSNBC / MS NOW', 'ms.now': 'MSNBC / MS NOW',
       'www.msnbc.com': 'MSNBC / MS NOW', 'msnbc.com': 'MSNBC / MS NOW', 'www.npr.org': 'NPR',
       'www.pbs.org': 'PBS', 'www.c-span.org': 'C-SPAN', 'www.nbcnews.com': 'NBC News',
       'www.cbsnews.com': 'CBS News', 'abcnews.go.com': 'ABC News',
       'hughhewitt.com': 'Hugh Hewitt Show', 'www.csis.org': 'CSIS', 'www.cfr.org': 'CFR',
       'www.aspensecurityforum.org': 'Aspen Security Forum'}


def _net(pkg):                                   # make_member_desk.py:1806-1811, verbatim logic
    if '/washington-journal/' in str(pkg or '').lower():
        return 'Washington Journal'
    mm = re.match(r'https?://([^/]+)/', str(pkg or ''))
    d = mm.group(1).lower() if mm else ''
    return NET.get(d, d or 'broadcast')


ep = collections.defaultdict(lambda: dict(turns=0, words=0, aff_turns=0, aff_words=0, rows=[]))
for rid, mem, dt, cham, pkg, nw, txt in rows:
    k = (mem, (dt or '')[:10], pkg)
    e = ep[k]
    e['turns'] += 1
    e['words'] += int(nw or 0)
    e['rows'].append(rid)
    if rid in AFF:
        e['aff_turns'] += 1
        f = FL.get(rid)
        if f:
            e['aff_words'] += len((txt or '')[f['first_at']:].split())

EP = len(ep)
EP_ROSTER = sum(1 for (m, d, p) in ep if m in ROSTER)
EP_AFF = sum(1 for k, v in ep.items() if v['aff_turns'])
EP_AFF_ROSTER = sum(1 for k, v in ep.items() if v['aff_turns'] and k[0] in ROSTER)
W = sum(v['words'] for v in ep.values())
WA = sum(v['aff_words'] for v in ep.values())
print('=' * 78)
print('U3  DESK -- interview footprint')
print('=' * 78)
print('displayed items = distinct (member,date,package) episodes : %d' % EP)
print('   of those whose member is on the roster                 : %d' % EP_ROSTER)
print('episodes containing >=1 U2-affected row                   : %d  (%.3f%% of items)'
      % (EP_AFF, 100.0 * EP_AFF / EP))
print('   roster-only                                            : %d' % EP_AFF_ROSTER)
print('displayed word total (SUM nwords)                         : %d' % W)
print('words sitting after a foreign tag inside those episodes    : %d  (%.4f%% of displayed words)'
      % (WA, 100.0 * WA / max(1, W)))
memaff = collections.Counter()
memtot = collections.Counter()
for (m, d, p), v in ep.items():
    memtot[m] += 1
    if v['aff_turns']:
        memaff[m] += 1
print('members with >=1 affected displayed item                  : %d of %d members with items'
      % (len(memaff), len(memtot)))
print('worst 12 members (affected items / total items):')
for m, n in memaff.most_common(12):
    print('    %-26s %5d / %5d  (%.1f%%)' % (m[:26], n, memtot[m], 100.0 * n / memtot[m]))
print()
print('NOTE the desk item TITLE is metadata only: '
      "'%s appearance - %d segment%s - %s words' (make_member_desk.py:1971-1972); "
      'no row text is displayed by that path.')

# ------------------------------------------------------------------ U3b/U4: the CU passages
SC = list(csv.DictReader(io.open(LIVE + r'\data\stance\interview_stance_final.csv',
                                encoding='utf-8-sig', newline='')))
TC = list(csv.DictReader(io.open(LIVE + r'\data\stance\interviews_cu.csv',
                                 encoding='utf-8-sig', newline='')))
print()
print('=' * 78)
print('U4  STANCE -- the interview channel of the media blend')
print('=' * 78)
print('interview_stance_final.csv rows: %d   interviews_cu.csv rows: %d' % (len(SC), len(TC)))

SIGN_TXT = io.open(LIVE + r'\fec\stance\build_media_blend.py', encoding='utf-8').read()
m = re.search(r'^SIGN\s*=\s*(\{[^}]*\})', SIGN_TXT, re.M)
print('SIGN table read from build_media_blend.py: %s' % (m.group(1) if m else 'NOT FOUND'))
SIGN = eval(m.group(1)) if m else {}
mc = re.search(r'def own_source_tier_weight\(tier\):.*?\.get\(str\(tier or \'\'\)\.strip\(\)\.lower\(\), 0\.0\)',
               io.open(LIVE + r'\fec\stance\media_rules.py', encoding='utf-8').read(), re.S)
print('own_source_tier_weight (fec/stance/media_rules.py:90-97):')
for ln in (mc.group(0).splitlines() if mc else ['NOT FOUND']):
    print('    %s' % ln)
TIERW = {}
for mm in re.finditer(r"'([a-z_]+)'\s*:\s*([0-9.]+)", mc.group(0) if mc else ''):
    TIERW[mm.group(1)] = float(mm.group(2))
TODAY = datetime.date.today()


def in_use(r):
    sg = SIGN.get((r.get('stance') or '').strip().lower(), 0.0)
    if sg == 0.0:
        return False, 'neutral/unrelated stance (SIGN=0)'
    if (r.get('member') or '') not in ROSTER:
        return False, 'member not on roster'
    try:
        datetime.date.fromisoformat((r.get('date') or '')[:10])
    except Exception:
        return False, 'bad date'
    if TIERW.get((r.get('tier') or '').strip().lower(), 0.0) == 0.0:
        return False, 'tier weight 0 (%r)' % r.get('tier')
    if not [c for c in (r.get('categories') or '').split(';') if c.strip()]:
        return False, 'no categories'
    return True, ''


used = [(i, r) for i, r in enumerate(SC) if in_use(r)[0]]
print('rows that survive build_media_blend\'s filters (the "in use" set): %d' % len(used))
why = collections.Counter(in_use(r)[1] for r in SC if not in_use(r)[0])
for k, v in why.most_common():
    print('    excluded %2d : %s' % (v, k))


def norm(s):
    return ' '.join(str(s or '').split()).lower()


BY = collections.defaultdict(list)
for rid, mem, dt, cham, pkg, nw, txt in rows:
    BY[(mem, (dt or '')[:10])].append((rid, pkg, txt or '', cham))

out = []
for i, (srow, trow) in enumerate(zip(SC, TC)):
    mem, day = trow.get('member'), (trow.get('date') or '')[:10]
    ptext = (trow.get('text') or '').strip()
    pn = norm(ptext)
    probe = pn[len(pn) // 3:len(pn) // 3 + 60]
    cand = BY.get((mem, day), [])
    # pin to package exactly as _grade_index does (probe against GROUP_CONCAT per package)
    bypkg = collections.defaultdict(list)
    for rid, pkg, txt, cham in cand:
        bypkg[pkg].append((rid, txt, cham))
    pkgs = [p for p, lst in bypkg.items() if probe and probe in norm(' '.join(t for _, t, _ in lst))]
    # which ROWS does the passage overlap?  slide 40-char probes of the passage over each row
    ov = []
    for p in pkgs:
        for rid, txt, cham in bypkg[p]:
            nt = norm(txt)
            hits = sum(1 for j in range(0, max(1, len(pn) - 40), 40) if pn[j:j + 40] in nt)
            if hits:
                ov.append((rid, p, txt, cham, hits))
    # (a) does the PASSAGE ITSELF contain a foreign tag?
    ptags = []
    for mm2 in TAG.finditer(ptext):
        tg = mm2.group(1)
        if not is_upper_tag(tg):
            continue
        hon, up = tag_parts(tg)
        if not up or all(w in STOP for w in up):
            continue
        mp = nrm(mem).split()
        if mp and mp[-1] in [nrm(w) for w in up]:
            continue
        ptags.append((mm2.start(1), ' '.join(tg.split())))
    # (b) does the passage START at or after the row's first foreign tag?
    after = []
    for rid, p, txt, cham, hits in ov:
        if rid not in FL:
            continue
        b0 = FL[rid]['first_at']
        first_probe = pn[:40]
        pos = norm(txt).find(first_probe) if first_probe else -1
        nb0 = len(norm(txt[:b0]))
        after.append(dict(rowid=rid, first_tag=FL[rid]['first_tag'], tag_at_norm=nb0,
                          passage_at_norm=pos, starts_after=(pos >= nb0 - 2 and pos >= 0)))
    out.append(dict(i=i + 1, member=mem, date=day, stance=(srow.get('stance') or ''),
                    tier=(srow.get('tier') or ''), cats=(srow.get('categories') or ''),
                    in_use=in_use(srow)[0], in_use_why=in_use(srow)[1],
                    pkgs=pkgs, npkgs=len(pkgs),
                    overlap_rows=[r[0] for r in ov], overlap_affected=[r[0] for r in ov if r[0] in AFF],
                    passage_tags=ptags, after=after, nchars=len(ptext), text=ptext))

print()
print('%-3s %-24s %-10s %-9s %-5s %-5s %-6s %-6s %s' %
      ('#', 'member', 'date', 'stance', 'use', 'pkgs', 'rows', 'affrow', 'VERDICT'))
bad = []
for r in out:
    v = 'CLEAN'
    if r['passage_tags']:
        v = 'FOREIGN TAG INSIDE PASSAGE'
    elif any(a['starts_after'] for a in r['after']):
        v = 'PASSAGE AFTER A FOREIGN TAG'
    elif r['overlap_affected']:
        v = 'row affected, passage before tag'
    elif not r['overlap_rows']:
        v = 'UNPINNED (no row overlap)'
    r['verdict'] = v
    if v.startswith('FOREIGN') or v.startswith('PASSAGE AFTER'):
        bad.append(r)
    print('%-3d %-24s %-10s %-9s %-5s %-5d %-6d %-6d %s' %
          (r['i'], r['member'][:24], r['date'], r['stance'][:9], 'Y' if r['in_use'] else 'n',
           r['npkgs'], len(r['overlap_rows']), len(r['overlap_affected']), v))
print()
print('SCORED PASSAGES CONTAMINATED BY FOREIGN SPEECH: %d of %d (%d of the %d in-use rows)'
      % (len(bad), len(out), sum(1 for r in bad if r['in_use']), len(used)))
for r in bad:
    print()
    print('  #%d %s %s  stance=%s tier=%s in_use=%s' % (r['i'], r['member'], r['date'],
                                                        r['stance'], r['tier'], r['in_use']))
    print('     tags in passage: %s' % r['passage_tags'])
    print('     rows: %s   affected: %s' % (r['overlap_rows'], r['overlap_affected']))
    for a in r['after']:
        print('     row %s first_tag=%r tag@%d passage@%d starts_after=%s'
              % (a['rowid'], a['first_tag'], a['tag_at_norm'], a['passage_at_norm'], a['starts_after']))
    print('     passage: %s' % ' '.join(r['text'].split())[:420])

with io.open(os.path.join(HERE, 'U4_passage_audit.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print()
print('wrote U4_passage_audit.json')

# seeded 20 of the DISPLAYED excerpts (U3 asks for 20; the whole displayed set is 37 so all are
# graded above -- this writes the seeded 20 subset as the required sample artifact)
pinned = [r for r in out if r['pkgs']]
rnd = random.Random(SEED)
s20 = rnd.sample(sorted(pinned, key=lambda r: r['i']), 20) if len(pinned) >= 20 else pinned
p = os.path.join(HERE, 'U3_displayed_excerpt_sample20_GRADED.csv')
with io.open(p, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['n', 'passage_idx', 'member', 'date', 'stance', 'in_use', 'packages',
                'overlap_rows', 'affected_rows', 'GRADE', 'text'])
    for j, r in enumerate(s20, 1):
        w.writerow([j, r['i'], r['member'], r['date'], r['stance'], int(r['in_use']),
                    ' | '.join(r['pkgs']), ' '.join(map(str, r['overlap_rows'])),
                    ' '.join(map(str, r['overlap_affected'])), r['verdict'],
                    ' '.join(r['text'].split())])
print('wrote U3_displayed_excerpt_sample20_GRADED.csv (%d of %d pinned passages)' % (len(s20), len(pinned)))
con.close()
print('DONE U3U4')
