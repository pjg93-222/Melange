# -*- coding: utf-8 -*-
"""LANE A / R8 -- (a) isolate the 120-char truncation, (b) desk press corpus vs engine press
corpus, (c) the press true-duplicate class.  Read-only.

(a) R6 compared the pipeline key against a whitespace/casefold key, which also differs on
    punctuation (curly vs straight apostrophe).  Here a THIRD key -- the pipeline's own
    alphanumeric-only normalisation with NO truncation -- isolates the truncation alone.
(b) The desk displays press from workbook sheet 'Press Release Articles' (3,701 rows); the engine
    scores press from the two tone CSVs (2,679 rows).  Two different populations: measure the
    overlap so "displayed" and "scored" can be reconciled.
(c) Same member + same normalised title + same date + different canonical url = a press item
    ingested twice under two urls.  The (url,identity) turn key cannot see it.
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
print('R8  truncation isolation + press desk/engine overlap   run',
      datetime.datetime.now().isoformat(timespec='seconds'))
print('=' * 100)

_urlrx = re.compile(r'https?://\S+')


def full_alnum(t):
    """media_rules.normalized_text WITHOUT the [:120] truncation."""
    t = _urlrx.sub('', str(t or '').lower())
    return re.sub(r'[^a-z0-9]', '', t)


roster = json.load(io.open(os.path.join(ROOT, 'data', 'engine', 'congestion.json'), encoding='utf-8'))
resolver = Resolver([x['member'] for x in roster], {x['member']: x.get('bioguide') for x in roster})

# ================= (a) TRUNCATION ISOLATION =================
print('\n' + '-' * 100)
print('(a) ISOLATING THE 120-CHAR TRUNCATION  (media_rules.py:76-78)')
print("    def normalized_text(text):  text = re.sub(r'https?://\\S+','',str(text or '').lower())")
print("                                return re.sub(r'[^a-z0-9]','',text)[:120]")
print('-' * 100)
wb = openpyxl.load_workbook(os.path.join(ROOT, 'Social Master.xlsx'), read_only=True, data_only=True)
ws = wb['Corpus']
hdr = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
H = {h: i for i, h in enumerate(hdr)}
pop = []
for r in ws.iter_rows(min_row=2, values_only=True):
    if str(r[H['verified_handle']]) != '1':
        continue
    m = resolver.resolve(r[H['member']])
    if not m:
        continue
    txt = str(r[H['text']] or '')
    pop.append({'member': m, 'platform': str(r[H['platform']] or ''),
                'date': str(r[H['date']] or '')[:10], 'text': txt,
                'stance': str(r[H['stance']] or ''), 'url': str(r[H['url']] or ''),
                'member_src': r[H['member']],
                'pk': MR.normalized_text(txt), 'fk': full_alnum(txt)})
wb.close()
print('dedup population: %d rows' % len(pop))
print('rows whose text exceeds 120 normalised chars (truncation is active): %d'
      % sum(1 for s in pop if len(s['fk']) > 120))


def grp(items, kf):
    g = collections.defaultdict(list)
    for it in items:
        g[kf(it)].append(it)
    return {k: v for k, v in g.items() if len(v) > 1}


pk = grp(pop, lambda s: (s['member'], s['pk']))
fk = grp(pop, lambda s: (s['member'], s['fk']))
print('\nPIPELINE key  (member, normalized_text[:120])  groups=%5d surplus=%5d'
      % (len(pk), sum(len(v) - 1 for v in pk.values())))
print('UNTRUNCATED   (member, full alphanumeric)      groups=%5d surplus=%5d'
      % (len(fk), sum(len(v) - 1 for v in fk.values())))
false_g = {k: v for k, v in pk.items() if len({s['fk'] for s in v}) > 1}
false_rows = sum(len(v) - 1 for v in false_g.values())
print('\nTRUNCATION FALSE COLLISIONS -- pipeline groups whose rows do NOT share the untruncated key:')
print('   groups: %d of %d   surplus rows wrongly treated as the same event: %d'
      % (len(false_g), len(pk), false_rows))
print('   CONSEQUENCE TODAY (CROSSPOST_DEDUP=0): the rows still score, but the desk note')
print('      "also posted on <platform> <date>" is attached to a DIFFERENT statement.')
print('   CONSEQUENCE AT CROSSPOST_DEDUP=1 (the documented revert switch): each of those')
print('      %d rows would be silently dropped as a duplicate of a post it is not.' % false_rows)
ex = sorted(false_g.items(), key=lambda kv: -len(kv[1]))[:6]
for k, v in ex:
    print('\n   %s  rows=%d  platforms=%s  dates=%s'
          % (k[0], len(v), sorted({s['platform'] for s in v}), sorted({s['date'] for s in v})))
    for s in v[:3]:
        print('      len(norm)=%4d  %s' % (len(s['fk']), s['text'][:120].replace('\n', ' ')))
        print('                      ...tail: %s' % s['text'][120:200].replace('\n', ' '))

print('\n-- class census recomputed on the UNTRUNCATED key (non-empty) --')
cls = collections.Counter()
sur = collections.Counter()
true_dups = []
for k, v in fk.items():
    if k[1] == '':
        continue
    plats = {s['platform'] for s in v}
    dates = {s['date'] for s in v}
    if len(plats) > 1:
        lab = 'cross-platform twin (D-034/R9: scores twice, RATIFIED)'
    elif len(dates) == 1:
        lab = 'same member+platform+date == TRUE-DUPLICATE CANDIDATE'
        true_dups.append((k, v))
    else:
        lab = 'same member+platform, different dates (repeat posting)'
    cls[lab] += 1
    sur[lab] += len(v) - 1
print('%-58s %8s %8s' % ('class', 'groups', 'surplus'))
for k in cls:
    print('%-58s %8d %8d' % (k, cls[k], sur[k]))
print('%-58s %8d %8d' % ('TOTAL', sum(cls.values()), sum(sur.values())))

# ================= (b) DESK PRESS vs ENGINE PRESS =================
print('\n' + '-' * 100)
print('(b) DESK PRESS CORPUS vs ENGINE PRESS CORPUS')
print('-' * 100)
WBP = os.path.join(ROOT, 'Moneyball Main Version - Blended.xlsx')
wb = openpyxl.load_workbook(WBP, read_only=True, data_only=True)
pw = wb['Press Release Articles']
ph = {h: i for i, h in enumerate(next(pw.iter_rows(min_row=1, max_row=1, values_only=True)))}
print("sheet 'Press Release Articles' columns: %s" % list(ph))
desk_rows = []
for r in pw.iter_rows(min_row=2, values_only=True):
    desk_rows.append({'member_src': r[ph['member']] if 'member' in ph else None,
                      'bioguide': r[ph['bioguide']] if 'bioguide' in ph else None,
                      'url': str(r[ph['url']] or '') if 'url' in ph else '',
                      'title': str(r[ph['title']] or '') if 'title' in ph else '',
                      'date': str(r[ph['date']] or '')[:10] if 'date' in ph else '',
                      'cats': str(r[ph['categories']] or '') if 'categories' in ph else ''})
wb.close()
print('desk press source rows: %d' % len(desk_rows))
billstatus = [d for d in desk_rows if d['url'].startswith('billstatus:')]
print("   RULE (make_member_desk.py:1664)  if str(pv(r,'url') or '').startswith('billstatus:'):"
      ' press_billstatus_excluded += 1; continue  -> %d' % len(billstatus))
unres = [d for d in desk_rows if not resolver.resolve(d['member_src'], d['bioguide'])]
print('   unresolved member -> %d' % len(unres))
displayed = [d for d in desk_rows
             if resolver.resolve(d['member_src'], d['bioguide']) and not d['url'].startswith('billstatus:')]
print('   DISPLAYED -> %d' % len(displayed))

tone = PS.load_tone_rows()
tone_urls = {PS.canonical_url(t.get('url'), keep_fragment=True) for t in tone}
tone_urls.discard('')
desk_urls = {PS.canonical_url(d['url'], keep_fragment=True) for d in displayed}
desk_urls.discard('')
print('\ndistinct canonical urls -- engine tone rows: %d   desk displayed rows: %d'
      % (len(tone_urls), len(desk_urls)))
both = tone_urls & desk_urls
print('   in BOTH                                  : %d' % len(both))
print('   engine-only (scored, NOT on the desk)     : %d' % len(tone_urls - desk_urls))
print('   desk-only (displayed, engine never sees)  : %d' % len(desk_urls - tone_urls))
eo = sorted(tone_urls - desk_urls)[:6]
do = sorted(desk_urls - tone_urls)[:6]
print('\n   engine-only examples:')
for u in eo:
    print('      %s' % u[:130])
print('   desk-only examples:')
for u in do:
    print('      %s' % u[:130])
# how many engine `used` rows are desk-visible
r1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r1_press_rows.json')
if os.path.exists(r1):
    rows = json.load(io.open(r1, encoding='utf-8'))['rows']
    used = [x for x in rows if x['disposition'] == 'used']
    uu = {PS.canonical_url(x['url'], keep_fragment=True) for x in used}
    print('\n   engine rows with disposition "used": %d  (distinct canonical urls %d)' % (len(used), len(uu)))
    print('      of those urls, present on the desk: %d   absent from the desk: %d'
          % (len(uu & desk_urls), len(uu - desk_urls)))

# ================= (c) PRESS TRUE-DUPLICATE CLASS =================
print('\n' + '-' * 100)
print('(c) PRESS TRUE-DUPLICATE CLASS: same member + same normalised title + same date, 2+ urls')
print('-' * 100)
for t in tone:
    t['member'] = resolver.resolve(t.get('member'), t.get('bioguide'))
    t['tk'] = full_alnum(t.get('title'))
    t['uc'] = PS.canonical_url(t.get('url'), keep_fragment=True)


def pdate(s):
    for f in ('%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y'):
        try:
            return datetime.datetime.strptime((s or '').strip(), f).date().isoformat()
        except ValueError:
            pass
    return ''


for t in tone:
    t['d'] = pdate(t.get('date'))
pt = [t for t in tone if t['member'] and t['tk']]
g = grp(pt, lambda t: (t['member'], t['tk'], t['d']))
print('groups (member, normalised title, date) with 2+ rows: %d   surplus rows: %d'
      % (len(g), sum(len(v) - 1 for v in g.values())))
multi_url = {k: v for k, v in g.items() if len({x['uc'] for x in v}) > 1}
print('   of those, groups spanning 2+ distinct canonical urls: %d   surplus rows: %d'
      % (len(multi_url), sum(len(v) - 1 for v in multi_url.values())))
print('   (a group on ONE url is already collapsed at ingest by the (url,identity) turn key)')
r1rows = {}
if os.path.exists(r1):
    for x in json.load(io.open(r1, encoding='utf-8'))['rows']:
        r1rows[(PS.canonical_url(x['url'], keep_fragment=True), str(x['member_source'] or ''))] = x['disposition']
print('\n   examples (up to 15), with the engine disposition of each row:')
for i, (k, v) in enumerate(sorted(multi_url.items(), key=lambda kv: -len(kv[1]))[:15], start=1):
    print('\n   %2d. %s  date=%s  rows=%d' % (i, k[0], k[2] or '(unparsed)', len(v)))
    print('       title: %s' % (v[0].get('title') or '')[:110])
    for x in v[:6]:
        dsp = r1rows.get((x['uc'], str(x.get('member') and x.get('member') or '')), None)
        dsp = dsp or r1rows.get((x['uc'], str(x.get('member') or '')), '?')
        print('       pv=%-10s stance=%-8s disp=%-18s %s'
              % (str(x.get('press_value'))[:10], str(x.get('stance'))[:8], dsp, x['uc'][:95]))
scoring = 0
for k, v in multi_url.items():
    n = 0
    for x in v:
        dsp = r1rows.get((x['uc'], str(x.get('member') or '')), '?')
        if dsp == 'used':
            n += 1
    if n > 1:
        scoring += 1
print('\n   groups where MORE THAN ONE row has disposition "used" (i.e. scores more than once today): %d'
      % scoring)
print('\nDONE R8')
