# -*- coding: utf-8 -*-
"""LANE A / R6 -- TRUE-DUPLICATE CENSUS across media/press channels (read-only).

Two normalisation keys are measured side by side:

  PIPELINE KEY  media_rules.normalized_text() -- lowercase, strip URLs, DELETE every
                non-alphanumeric character, then TRUNCATE TO 120 CHARS.  This is the key the
                engine and the desk actually dedup on.
  AUDIT KEY     casefold + collapse whitespace + strip URLs, NO truncation.  This is the
                "byte-identical normalised text" the audit asks for.

The gap between them is the truncation's false-collision rate: rows the pipeline treats as the
same event that are not in fact the same text.

Classes reported per D-034 (2026-09-16, a0c45a709): a cross-platform twin scoring twice is
RATIFIED; a link-only repeat does not score; same-member/same-platform/same-date byte-identical
repeats are the TRUE-duplicate candidates.
"""
import os, sys, io, csv, json, re, collections, datetime
LIB = r'C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneA\lib'
sys.path.insert(0, LIB)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl
import media_rules as MR
import press_stream as PS
from member_identity import Resolver

ROOT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
print('=' * 100)
print('R6  TRUE-DUPLICATE CENSUS   run', datetime.datetime.now().isoformat(timespec='seconds'))
print('=' * 100)

_url = re.compile(r'https?://\S+')


def audit_key(t):
    """casefold, strip URLs, collapse whitespace -- no truncation."""
    return ' '.join(_url.sub(' ', str(t or '')).casefold().split())


roster = json.load(io.open(os.path.join(ROOT, 'data', 'engine', 'congestion.json'), encoding='utf-8'))
resolver = Resolver([x['member'] for x in roster], {x['member']: x.get('bioguide') for x in roster})

# ---------------- load the social corpus ----------------
SM = os.path.join(ROOT, 'Social Master.xlsx')
wb = openpyxl.load_workbook(SM, read_only=True, data_only=True)
ws = wb['Corpus']
hdr = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
H = {h: i for i, h in enumerate(hdr)}
social = []
for r in ws.iter_rows(min_row=2, values_only=True):
    social.append({'platform': str(r[H['platform']] or ''), 'member_src': r[H['member']],
                   'date': str(r[H['date']] or '')[:10], 'text': str(r[H['text']] or ''),
                   'is_rt': str(r[H['is_rt']] or ''), 'stance': str(r[H['stance']] or ''),
                   'verified': str(r[H['verified_handle']]), 'url': str(r[H['url']] or ''),
                   'source': str(r[H['source']] or '')})
wb.close()
print('Social Master Corpus rows: %d' % len(social))

# resolve members once
for s in social:
    s['member'] = resolver.resolve(s['member_src'])
    s['pk'] = MR.normalized_text(s['text'])
    s['ak'] = audit_key(s['text'])
print('rows with a resolvable member: %d' % sum(1 for s in social if s['member']))

# The population the pipeline actually deduplicates: verified_handle==1 and a resolvable member.
pop = [s for s in social if s['verified'] == '1' and s['member']]
print('dedup population (verified_handle==1 and member resolves): %d' % len(pop))

# ---------------- A. PIPELINE KEY vs AUDIT KEY ----------------
print('\n' + '-' * 100)
print('A.  PIPELINE KEY (normalized_text, 120-char truncation) vs AUDIT KEY (no truncation)')
print('-' * 100)


def groups(items, keyf):
    g = collections.defaultdict(list)
    for it in items:
        g[keyf(it)].append(it)
    return {k: v for k, v in g.items() if len(v) > 1}


pk_groups = groups(pop, lambda s: (s['member'], s['pk']))
ak_groups = groups(pop, lambda s: (s['member'], s['ak']))
pk_surplus = sum(len(v) - 1 for v in pk_groups.values())
ak_surplus = sum(len(v) - 1 for v in ak_groups.values())
print('PIPELINE KEY  (member, normalized_text)  groups=%5d  surplus rows=%5d' % (len(pk_groups), pk_surplus))
print('AUDIT KEY     (member, full normalised)  groups=%5d  surplus rows=%5d' % (len(ak_groups), ak_surplus))

# how many pipeline-key collisions are NOT audit-key collisions -> truncation false positives
false_collisions = 0
fc_examples = []
for k, v in pk_groups.items():
    aks = {s['ak'] for s in v}
    if len(aks) > 1:
        false_collisions += 1
        if len(fc_examples) < 6:
            fc_examples.append((k[0], [s['text'][:130] for s in v[:2]]))
print('\npipeline-key groups whose members do NOT share the audit key (the 120-char truncation'
      ' merged DIFFERENT texts): %d of %d groups' % (false_collisions, len(pk_groups)))
if fc_examples:
    print('   examples (first 130 chars of two colliding texts):')
    for m, texts in fc_examples:
        print('   %s' % m)
        for t in texts:
            print('      | %s' % t)
# link-only: empty pipeline key
linkonly = [s for s in pop if s['pk'] == '']
print('\nlink-only rows (normalized_text == "" after URL stripping): %d across %d members'
      % (len(linkonly), len({s['member'] for s in linkonly})))
print('   RULE (make_member_desk.py:288-289) if not normalized_text: return (False, "link-only post:'
      ' no scorable text", "")   -> visible, NOT scored')
print('   RULE (build_media_blend.py:106)    elif not _event[1]: nlinkonly+=1; continue          '
      '-> NOT scored by the engine')
print('   platform split of link-only rows: %s'
      % dict(collections.Counter(s['platform'] for s in linkonly).most_common()))

# ---------------- B. CLASSIFY the duplicate groups ----------------
print('\n' + '-' * 100)
print('B.  DUPLICATE CLASSES (audit key, excluding link-only empties)')
print('-' * 100)
ak_real = {k: v for k, v in ak_groups.items() if k[1] != ''}
cls = collections.Counter()
cls_surplus = collections.Counter()
same_plat_same_date = []
same_plat_diff_date = []
cross_plat = []
for k, v in ak_real.items():
    plats = {s['platform'] for s in v}
    dates = {s['date'] for s in v}
    if len(plats) > 1:
        cls['cross-platform twin (D-034: scores twice, RATIFIED)'] += 1
        cls_surplus['cross-platform twin (D-034: scores twice, RATIFIED)'] += len(v) - 1
        cross_plat.append((k, v))
    elif len(dates) == 1:
        cls['same member + same platform + same date  == TRUE-DUPLICATE CANDIDATE'] += 1
        cls_surplus['same member + same platform + same date  == TRUE-DUPLICATE CANDIDATE'] += len(v) - 1
        same_plat_same_date.append((k, v))
    else:
        cls['same member + same platform, DIFFERENT dates (repeat posting)'] += 1
        cls_surplus['same member + same platform, DIFFERENT dates (repeat posting)'] += len(v) - 1
        same_plat_diff_date.append((k, v))
print('%-64s %8s %8s' % ('class', 'groups', 'surplus'))
for k in cls:
    print('%-64s %8d %8d' % (k, cls[k], cls_surplus[k]))
print('%-64s %8d %8d' % ('TOTAL (audit key, non-empty)', sum(cls.values()), sum(cls_surplus.values())))

# ---------------- C. does each class score once or more than once TODAY? ----------------
print('\n' + '-' * 100)
print('C.  DOES EACH CLASS SCORE ONCE OR MORE THAN ONCE TODAY?')
print('-' * 100)
SIGN = {'support': 1, 'oppose': -1, 'neutral': 0}
STACK_PATH = os.path.join(ROOT, 'data', 'stance', 'tweet_stance_final.csv')
with io.open(STACK_PATH, encoding='utf-8-sig', newline='') as fh:
    raw_stack = list(csv.DictReader(fh))
DSTACK = {}
for r in raw_stack:
    DSTACK[(r.get('member') or '', MR.normalized_text(r.get('text')))] = r


def n_scoring_rows(v):
    """how many rows of this group carry a nonzero sign AND scorable text -> score today"""
    n = 0
    for s in v:
        hit = DSTACK.get((str(s['member_src'] or ''), s['pk']))
        stance = str((hit or {}).get('stack_stance') or s['stance'] or 'neutral').lower()
        if stance == 'unrelated':
            continue
        if not MR.route_raw_categories(s['text']):
            continue
        if SIGN.get(stance, 0) == 0:
            continue
        if not s['pk']:
            continue
        n += 1
    return n


for label, coll in (('TRUE-DUPLICATE CANDIDATES (same member/platform/date)', same_plat_same_date),
                    ('cross-platform twins (D-034 ratified)', cross_plat),
                    ('same platform, different dates', same_plat_diff_date)):
    multi = 0
    rows_scoring = 0
    for k, v in coll:
        n = n_scoring_rows(v)
        rows_scoring += n
        if n > 1:
            multi += 1
    print('%-56s groups=%5d  groups scoring >1x TODAY=%5d  scoring rows=%5d'
          % (label, len(coll), multi, rows_scoring))
print('\n  NOTE: CROSSPOST_DEDUP default is "0" in BOTH implementations')
print('        (build_media_blend.py:47, make_member_desk.py:256), so every signed row with')
print('        scorable text scores, including a same-platform same-date repeat.')

# ---------------- D. examples of the TRUE-duplicate candidates ----------------
print('\n' + '-' * 100)
print('D.  TRUE-DUPLICATE CANDIDATES -- up to 15 examples')
print('-' * 100)
same_plat_same_date.sort(key=lambda kv: (-len(kv[1]), kv[0][0]))
for i, (k, v) in enumerate(same_plat_same_date[:15], start=1):
    print('\n%2d. member=%s  platform=%s  date=%s  rows=%d  scoring rows TODAY=%d'
          % (i, k[0], v[0]['platform'], v[0]['date'], len(v), n_scoring_rows(v)))
    print('    text: %s' % (v[0]['text'][:170].replace('\n', ' ')))
    for s in v:
        print('      url=%-70s stance=%-8s is_rt=%s source=%s'
              % (s['url'][:70], s['stance'], s['is_rt'], s['source']))

# ---------------- E. PRESS channel duplicates ----------------
print('\n' + '-' * 100)
print('E.  PRESS CHANNEL duplicates (tone rows the engine ingests)')
print('-' * 100)
tone = PS.load_tone_rows()
print('tone rows ingested: %d' % len(tone))
for t in tone:
    t['member'] = resolver.resolve(t.get('member'), t.get('bioguide'))
    t['ak'] = audit_key((t.get('title') or ''))
    t['url_c'] = PS.canonical_url(t.get('url'), keep_fragment=True)
pt = [t for t in tone if t['member']]
print('tone rows with a resolvable member: %d' % len(pt))
g_title = groups(pt, lambda t: (t['member'], t['ak']))
print('\n(member, normalised TITLE) groups>1: %d  surplus rows: %d'
      % (len(g_title), sum(len(v) - 1 for v in g_title.values())))
same_url = 0
diff_url = 0
for k, v in g_title.items():
    if len({x['url_c'] for x in v}) == 1:
        same_url += 1
    else:
        diff_url += 1
print('   of those, groups whose rows share ONE canonical url: %d  (the (url,identity) turn key'
      ' already collapses these at ingest -- see R1)' % same_url)
print('   groups spanning DIFFERENT urls (same member, same headline, different article): %d' % diff_url)
print('\n   top same-title groups:')
for k, v in sorted(g_title.items(), key=lambda kv: -len(kv[1]))[:10]:
    print('      %-24s x%-3d  %s' % (k[0], len(v), (v[0].get('title') or '')[:80]))
    for x in v[:3]:
        print('          %s' % x['url_c'][:110])

# ---------------- F. CROSS-CHANNEL: social text vs press title ----------------
print('\n' + '-' * 100)
print('F.  CROSS-CHANNEL duplicates (social text vs press title, same member)')
print('-' * 100)
soc_keys = collections.defaultdict(list)
for s in pop:
    if s['ak']:
        soc_keys[(s['member'], s['ak'])].append(s)
hits = 0
examples = []
for t in pt:
    if not t['ak']:
        continue
    k = (t['member'], t['ak'])
    if k in soc_keys:
        hits += 1
        if len(examples) < 8:
            examples.append((t['member'], (t.get('title') or '')[:90], t['url_c'][:70],
                             soc_keys[k][0]['platform']))
print('press rows whose normalised title equals one of the same member\'s normalised social texts: %d' % hits)
for m, ti, u, p in examples:
    print('   %-22s [%s] %s' % (m, p, ti))
    print('      press url: %s' % u)
print('\n  NOTE: these are the press/social analogue of a cross-platform twin.  The press channel and')
print('        the social channel are p80-scaled and mixed 50/50, so such a pair contributes on BOTH')
print('        sides of the blend.  No rule in either implementation looks for it.')
print('\nDONE R6')
