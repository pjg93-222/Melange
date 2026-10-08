# -*- coding: utf-8 -*-
"""G4: the 4 skipped rows + row 66969 + episode-shape checks.  LIVE DB opened READ-ONLY."""
import io, json, sqlite3, sys

DB = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems/social_media.db'
LEDGER = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
          r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\fixN12'
          r'\dry_run_ledger.jsonl')
TARGETS = (69544, 244993, 278454, 278528, 66969, 66973, 245558)

con = sqlite3.connect('file:%s?mode=ro' % DB, uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')

out = io.open(sys.argv[1], 'w', encoding='utf-8', newline='\n')

led = {}
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r['rowid'] in TARGETS:
            led[r['rowid']] = r

for rid in TARGETS:
    row = con.execute('SELECT rowid,member,date,source,chamber,package,nwords,text '
                      'FROM speeches WHERE rowid=?', (rid,)).fetchone()
    out.write('=' * 110 + '\n')
    out.write('ROWID %s | member=%s | date=%s | source=%s | show=%s | nwords=%s\n'
              % (row[0], row[1], row[2], row[3], row[4], row[6]))
    out.write('package=%s\n' % row[5])
    r = led.get(rid)
    if r:
        out.write('LEDGER: skip=%r classes=%s foreign=%s\n'
                  % (r['skip'], r['classes'], r['foreign_classes']))
        out.write('LEDGER kept nwords=%d  kept text=%r\n'
                  % (r['kept']['nwords'], r['kept']['text'][:400]))
        for i, seg in enumerate(r['removed'], 1):
            out.write('  seg %d: class=%s own=%s speaker=%r disp=%s tag=%r\n'
                      % (i, seg['class'], seg['own'], seg['speaker'], seg['disposition'],
                         seg['tag']))
            out.write('         raw[:600]=%s\n' % seg['raw'][:600])
    out.write('--- LIVE TEXT (first 3000 chars) ---\n%s\n' % row[7][:3000])
    if len(row[7]) > 3000:
        out.write('--- LIVE TEXT (last 700 chars) ---\n...%s\n' % row[7][-700:])
    # sibling rows in the same package
    sib = con.execute('SELECT rowid,member,nwords,substr(text,1,220) FROM speeches '
                      'WHERE package=? AND source=? ORDER BY rowid', (row[5], row[3])).fetchall()
    out.write('--- %d rows share this package ---\n' % len(sib))
    for s in sib:
        out.write('   rowid=%-7s %-26s nw=%-5s %s\n' % (s[0], s[1][:26], s[2], s[3]))
    out.write('\n')

# episode shape: are multi-row (member,date,package) groups already normal?
q = ("SELECT COUNT(*) FROM (SELECT member,date,package,COUNT(*) c FROM speeches "
     "WHERE source='INTERVIEW' GROUP BY member,date,package HAVING c>1)")
multi = con.execute(q).fetchone()[0]
tot = con.execute("SELECT COUNT(*) FROM (SELECT member,date,package FROM speeches "
                  "WHERE source='INTERVIEW' GROUP BY member,date,package)").fetchone()[0]
out.write('INTERVIEW (member,date,package) groups: %d total, %d already hold >1 row\n'
          % (tot, multi))
dupt = con.execute("SELECT COUNT(*) FROM (SELECT member,date,package,text,COUNT(*) c FROM speeches "
                   "WHERE source='INTERVIEW' GROUP BY member,date,package,text HAVING c>1)"
                   ).fetchone()[0]
out.write('INTERVIEW (member,date,package,text) duplicate groups today: %d\n' % dupt)
inv = con.execute("SELECT COUNT(*) FROM speeches WHERE source='INTERVIEW' "
                  "AND nwords <> (LENGTH(TRIM(text))-LENGTH(REPLACE(TRIM(text),' ',''))+1)"
                  ).fetchone()[0]
out.write('INTERVIEW rows where nwords != naive space-count: %d (naive check only)\n' % inv)
con.close()
out.close()
print('done')
