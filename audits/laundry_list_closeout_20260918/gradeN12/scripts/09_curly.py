# -*- coding: utf-8 -*-
import io, json, re, sqlite3, collections, sys
LEDGER = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
          r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\fixN12'
          r'\dry_run_ledger.jsonl')
DB = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems/social_media.db'
rows = []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if line:
            rows.append(json.loads(line))
out = io.open(sys.argv[1], 'w', encoding='utf-8', newline='\n')
def w(s=''):
    out.write(s + '\n')
CURLY = '\u2019'
w('='*100)
w('H4  THE CURLY APOSTROPHE (U+2019) IS NOT IN THE NAME CLASS, SO THE TAG IS CUT IN HALF')
w('    turn_tags.NAMETOK = [A-Z][A-Z.\'`\-]{0,24}: it holds the STRAIGHT quote and the BACKTICK')
w('    (added by the repair for MS NOW) but NOT U+2019, which ABC/this-week writes.')
ends = [r for r in rows if not r['skip'] and r['kept']['text'].rstrip().endswith(CURLY)]
w('    flagged rows whose KEPT text would END on a bare %r : %d' % (CURLY, len(ends)))
for r in sorted(ends, key=lambda x: x['rowid']):
    w('      rowid=%-7s %-24s show=%-12s tag=%-26r kept tail %r'
      % (r['rowid'], r['member'], r['chamber'], r['removed'][0]['tag'][:26],
         r['kept']['text'][-46:]))
frag = collections.Counter()
for r in rows:
    for seg in r['removed']:
        m = re.match(r'^([A-Z]{2,})\b', seg['tag'] or '')
        if m and r['kept']['text'].rstrip().endswith(CURLY):
            frag[m.group(1)] += 1
w('    the half-tags this produces: %s' % dict(frag))
con = sqlite3.connect('file:%s?mode=ro' % DB, uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
flag = {r['rowid'] for r in rows}
PAT = re.compile('[A-Z]' + CURLY + '[A-Z]{2,}\s*(?:\([^)]{1,30}\))?\s*:')
n = nun = 0
ex = []
for rid, txt in con.execute("SELECT rowid,text FROM speeches WHERE source='INTERVIEW'"):
    if txt and PAT.search(txt):
        n += 1
        if rid not in flag:
            nun += 1
            if len(ex) < 10:
                ex.append((rid, PAT.search(txt).group(0)[:34]))
w('    corpus-wide INTERVIEW rows carrying a curly-apostrophe ALL-CAPS tag: %d' % n)
w('    of those, NOT flagged by the migration at all                      : %d' % nun)
w('    unflagged examples: %s' % ex)
con.close()
out.close()
print(io.open(sys.argv[1], encoding='utf-8').read())
