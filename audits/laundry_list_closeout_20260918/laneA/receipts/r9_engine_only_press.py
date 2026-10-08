# -*- coding: utf-8 -*-
"""LANE A / R9 -- why 293 engine-scored press urls are absent from the desk sheet.  Read-only.

R8 found 293 canonical urls that the engine ingests but the workbook sheet 'Press Release
Articles' (the desk's press source) does not carry, and that 221 of the engine's 1,387 `used`
rows are among them.  Hypothesis: the refresh stream (data/stance/press_refresh_tone.csv, added
2026-09-16) never reached the workbook sheet, so the desk's press display is one corpus behind.
"""
import os, sys, io, json, collections, datetime
LIB = r'C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneA\lib'
sys.path.insert(0, LIB)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl
import press_stream as PS
from member_identity import Resolver

ROOT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
print('=' * 100)
print('R9  engine-only press urls: source attribution   run',
      datetime.datetime.now().isoformat(timespec='seconds'))
print('=' * 100)

roster = json.load(io.open(os.path.join(ROOT, 'data', 'engine', 'congestion.json'), encoding='utf-8'))
resolver = Resolver([x['member'] for x in roster], {x['member']: x.get('bioguide') for x in roster})

rows = json.load(io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     'r1_press_rows.json'), encoding='utf-8'))['rows']
by_url_src = {}
for x in rows:
    by_url_src.setdefault(PS.canonical_url(x['url'], keep_fragment=True), set()).add(x['src'])

wb = openpyxl.load_workbook(os.path.join(ROOT, 'Moneyball Main Version - Blended.xlsx'),
                            read_only=True, data_only=True)
pw = wb['Press Release Articles']
ph = {h: i for i, h in enumerate(next(pw.iter_rows(min_row=1, max_row=1, values_only=True)))}
desk_urls = set()
desk_all = 0
for r in pw.iter_rows(min_row=2, values_only=True):
    desk_all += 1
    u = str(r[ph['url']] or '')
    if u.startswith('billstatus:'):
        continue
    if not resolver.resolve(r[ph['member']], r[ph['bioguide']]):
        continue
    c = PS.canonical_url(u, keep_fragment=True)
    if c:
        desk_urls.add(c)
wb.close()
print('desk sheet rows: %d   displayed distinct canonical urls: %d' % (desk_all, len(desk_urls)))

engine_urls = set(by_url_src)
only = engine_urls - desk_urls
print('engine distinct canonical urls: %d' % len(engine_urls))
print('engine-only urls: %d' % len(only))
src = collections.Counter()
for u in only:
    s = by_url_src[u]
    src['+'.join(sorted(s))] += 1
print('\nengine-only urls by TONE SOURCE FILE:')
for k, v in src.most_common():
    print('   %-20s %6d' % (k, v))
print('\nall engine urls by tone source file:')
allsrc = collections.Counter('+'.join(sorted(by_url_src[u])) for u in engine_urls)
for k, v in allsrc.most_common():
    print('   %-20s %6d' % (k, v))

used = {PS.canonical_url(x['url'], keep_fragment=True): x for x in rows if x['disposition'] == 'used'}
missing_used = {u: used[u] for u in used if u not in desk_urls}
print('\nengine rows with disposition "used": %d   of those ABSENT from the desk sheet: %d'
      % (len(used), len(missing_used)))
msrc = collections.Counter('+'.join(sorted(by_url_src[u])) for u in missing_used)
print('   those %d by tone source file: %s' % (len(missing_used), dict(msrc.most_common())))
print('\n   sample of scored-but-not-displayed press items:')
for u in sorted(missing_used)[:12]:
    x = missing_used[u]
    print('      [%s] %-24s %s' % (x['src'], str(x['member_source'])[:24], u[:108]))
print('\n   the %d "refresh" urls are supplemental rows added to the engine feed on 2026-09-16'
      ' (data/stance/press_refresh_tone.csv, mtime 2026-09-16 23:44).' % src.get('refresh', 0))
print('   base-file urls absent from the desk sheet: %d -- these are NOT explained by the refresh'
      % src.get('base', 0))
print('\nDONE R9')
