# -*- coding: utf-8 -*-
"""Corrected curly-apostrophe census.

My 05 regex demanded at least one character BETWEEN the leading capital and the U+2019, so
"O’DONNELL" could never match it and the census printed 1.  This is the corrected count.
READ-ONLY: file:...?mode=ro + PRAGMA query_only=ON.
"""
import io
import json
import re
import sqlite3
import sys

LEDGER, DB = sys.argv[1], sys.argv[2]
rows = {}
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if line:
            r = json.loads(line)
            rows[r['rowid']] = r

# an ALL-CAPS speaker tag carrying U+2019, sentence-anchored and colon-terminated
CURLY = re.compile('(?:^|(?<=[.?!])|(?<=--)|(?<=—))\\s*'
                   '[A-Z][A-Z.’‘\'`\\- ]{0,40}’[A-Z][A-Z.’\'`\\- ]{0,40}'
                   '\\s*(?:\\([^)]{1,30}\\))?\\s*:')
ANY_CURLY_CAPS = re.compile('[A-Z]{1,20}’[A-Z]{2,20}')

con = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True)
con.execute('PRAGMA query_only=ON')
tag_ids, any_ids = [], []
for rid, text in con.execute("SELECT rowid,text FROM speeches WHERE source='INTERVIEW'"):
    if not text:
        continue
    if CURLY.search(text):
        tag_ids.append(rid)
    if ANY_CURLY_CAPS.search(text):
        any_ids.append(rid)
con.close()

flagged = set(rows)
trunc = {i for i in rows if not rows[i]['skip']}
res = {
    'INTERVIEW rows with a curly-apostrophe ALL-CAPS TURN TAG (anchored, colon)': len(tag_ids),
    '  of those FLAGGED by v2': len(set(tag_ids) & flagged),
    '  of those TRUNCATED by v2': len(set(tag_ids) & trunc),
    '  of those STILL UNTOUCHED': len(tag_ids) - len(set(tag_ids) & flagged),
    'INTERVIEW rows with ANY curly-apostrophe ALL-CAPS word': len(any_ids),
    'ledger rows whose CUT TAG carries U+2019':
        sum(1 for r in rows.values() if '’' in (r['cut_tag'] or '')),
    'ledger rows with ANY tag carrying U+2019':
        sum(1 for r in rows.values() if any('’' in t['tag'] for t in r['all_tags'])),
}
with io.open(sys.argv[3], 'w', encoding='utf-8', newline='\n') as fh:
    json.dump(res, fh, indent=1, sort_keys=True)
print(json.dumps(res, indent=1, sort_keys=True))
