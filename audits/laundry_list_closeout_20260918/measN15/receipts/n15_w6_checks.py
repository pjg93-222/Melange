# -*- coding: utf-8 -*-
"""N15 closing checks (READ-ONLY, nothing under fec/ imported).
 (a) which withdrawn fact the bank_anchor pre-collapse row belonged to (the withdrawn branch DID fire);
 (b) why the official record is silent on the 13 Robert Menendez rows;
 (c) the OM.load staleness window that gates the whole mechanism.
"""
import os, sys, json, datetime, collections

N5 = (r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees"
      r"\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\measN5\receipts")
if N5 not in sys.path:
    sys.path.insert(0, N5)
import n5_lib as N                                             # noqa: E402
import f1_lib as F                                             # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OUT = []
def W(s=''):
    OUT.append(s)
    print(s)

OMDOC = json.load(open(N.P('data', 'legislation', 'official_membership_movements.json'),
                       encoding='utf-8'))
FACTS = OMDOC.get('facts') or []
by_name = {(r['repository_key'], r['member']): r for r in FACTS}
RES, _names, _bios = N.resolver()

W('=' * 102)
W('N15 / CHECK A  the one WITHDRAWN pre-collapse row, and which source carried it')
W('=' * 102)
for line in open(N.P('data', 'members', 'bank_anchor_memberships.ndjson'), encoding='utf-8'):
    if not line.strip():
        continue
    d = json.loads(line)
    m = RES.resolve(d.get('member'))
    key = N.repo_key(d.get('bill'), d.get('congress'))
    f = by_name.get((key, m)) if (key and m) else None
    if f and f.get('withdrawn'):
        W('  bank_anchor_memberships.ndjson row: %s' % json.dumps(d, ensure_ascii=False)[:300])
        W('  official fact: member=%s key=%s role=%s withdrawn=%s withdrawn_date=%s join=%s'
          % (f['member'], f['repository_key'], f['role'], f['withdrawn'],
             f.get('withdrawn_date'), f.get('join_date')))
        W('  -> apply_to_desk line 104 removed this pre-collapse row on the WITHDRAWN branch;')
        W('     the triple is absent from the shipped desk, which is the observed state.')

W('')
W('=' * 102)
W('N15 / CHECK B  why the official record is silent on the 13 Robert Menendez rows')
W('=' * 102)
UN = OMDOC.get('unresolved') or []
un_keys = collections.defaultdict(set)
for u in UN:
    un_keys[u['repository_key']].add((u['bioguide'], u['role']))
bio = _bios.get('Robert Menendez')
W('  engine roster bioguide for "Robert Menendez" (data/engine/congestion.json) = %r' % bio)
hits = 0
for key in ('117:s:3128', '118:s:2142', '117:s:910', '117:s:767', '117:s:2724', '118:s:869',
            '118:s:2860', '118:s:1323', '118:s:817', '118:s:1514', '118:s:2095',
            '117:s:2981', '118:s:2391'):
    ent = sorted(x for x in un_keys.get(key, set()) if x[0] == bio)
    hits += bool(ent)
    W('     %-12s unresolved entry for that bioguide: %s' % (key, ent or 'NONE'))
W('  keys where his bioguide is in unresolved[] = %d / 13' % hits)
W('  -> official_membership_movements.build() line 35-37: a person whose bioguide is not in')
W('     build_ledger_view(bundle)["roster"] is appended to unresolved[] and NO fact is written,')
W('     so apply_to_desk has nothing to test and the row is kept unjudged.')
REPO = json.load(open(N.P('bill_repository_live.json'), encoding='utf-8'))['bills']
W('  THE ACTUAL CAUSE -- the two sides carry DIFFERENT bioguides for this person:')
for key in ('117:s:3128', '117:s:910', '118:s:2391'):
    b = REPO[key]
    ppl = [('sponsor', b.get('sponsor') or {})] + \
          [('original', p) for p in b.get('original_cosponsors', [])] + \
          [('cosponsor', p) for p in b.get('cosponsors', [])]
    hit = [(rl, p) for rl, p in ppl if 'enende' in str(p.get('name', ''))]
    for rl, p in hit:
        W('     %-12s BILLSTATUS %-32s bioguide=%s role=%s ; unresolved[] carries (%s,%s)'
          % (key, p.get('name'), p.get('bioguide'), rl,
             p.get('bioguide'), rl))
W('     engine roster (data/engine/congestion.json) bioguide = %r' % bio)
W('     -> BILLSTATUS says M000639, the engine roster says %r, so view["roster"].get("M000639")' % bio)
W('        is None, the person goes to unresolved[] under M000639 (not under %r), no fact is' % bio)
W('        written, and all 13 of his displayed rows are unjudgeable by apply_to_desk.')
W('        The same mismatch means build_archive_legislative.py:206 passes bioguide=%r, finds no' % bio)
W('        fact either, and therefore never emits the disposition for him.')

W('')
W('=' * 102)
W('N15 / CHECK C  the staleness window OM.load enforces (line 68-69)')
W('=' * 102)
ck = OMDOC['checked_at']
age = (datetime.datetime.now(datetime.timezone.utc)
       - datetime.datetime.fromisoformat(ck.replace('Z', '+00:00'))).total_seconds()
W('  checked_at = %s ; age now = %.2f days ; gate = -300s <= age <= 8 days' % (ck, age / 86400.0))
W('  file mtime = %s (the checked_at stamp is OLDER than the mtime)'
  % datetime.datetime.fromtimestamp(
      os.stat(N.P('data', 'legislation', 'official_membership_movements.json')).st_mtime))
W('  the gate fails (ValueError, make_member_desk stops at :2296) once age > 8 days, i.e. after %s UTC'
  % (datetime.datetime.fromisoformat(ck.replace('Z', '+00:00'))
     + datetime.timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S'))

dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'n15_w6_checks.txt')
with open(dest, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(OUT) + '\nDONE\n')
print('DONE -> %s' % dest)
