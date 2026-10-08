# -*- coding: utf-8 -*-
"""N15 W5 (READ-ONLY): breadth check over ALL displayed desk bill rows against the official record.
Nothing under fec/ is imported.

For every row in member_desk_bundle.json members[].bills[]:
  key   = parse_bill_identity(bill, congress)['key']                (congress_bill_repository.py:145-168)
  fact  = official_membership_movements.json facts[(key, member)]   (apply_to_desk's own key)
  WITHDRAWN-DISPLAYED  iff fact and fact['withdrawn']
  ROLE-DIFFERS         iff fact and canonical_role(row.role) != canonical_role(fact['role'])
Both are exactly the two conditions apply_to_desk removes on, so a non-zero count is a row the
pass failed to act on.  Rows whose bill does not parse, or that carry no fact, are reported
separately: apply_to_desk cannot judge them.
"""
import os, sys, json, collections

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

W('=' * 102)
W('N15 / W5  BREADTH: EVERY DISPLAYED DESK BILL ROW vs THE OFFICIAL RECORD')
W('=' * 102)

OMDOC = json.load(open(N.P('data', 'legislation', 'official_membership_movements.json'),
                       encoding='utf-8'))
FACTS = OMDOC.get('facts') or []
by_name = {(r['repository_key'], r['member']): r for r in FACTS}
by_bio = {(r['repository_key'], r['bioguide']): r for r in FACTS}
REPO = json.load(open(N.P('bill_repository_live.json'), encoding='utf-8'))['bills']
_names, _bios = N.roster()
W('  official facts=%d (withdrawn=True: %d) ; repository bills=%d ; roster members=%d'
  % (len(FACTS), sum(1 for r in FACTS if r.get('withdrawn')), len(REPO), len(_names)))

with open(N.P('member_desk_bundle.json'), encoding='utf-8') as fh:
    D = json.load(fh)
DESK = {m.get('name'): (m.get('bills') or []) for m in (D.get('members') or [])}
del D
W('  desk bundle: %d members, %d displayed bill rows'
  % (len(DESK), sum(len(v) for v in DESK.values())))
_off_roster = [n for n in DESK if n not in set(_names)]
W('  desk member names NOT in the engine roster: %d %s' % (len(_off_roster), _off_roster[:6]))

tot = collections.Counter()
withdrawn_rows, role_diff_rows, bio_only = [], [], []
unparseable = collections.Counter()
for member, rows in DESK.items():
    bio = _bios.get(member)
    for r in rows:
        tot['rows'] += 1
        key = N.repo_key(r.get('bill'), r.get('congress'))
        if not key:
            tot['unparseable_bill_identity'] += 1
            unparseable[N.norm_bill(r.get('bill'))[:9]] += 1
            continue
        tot['parseable'] += 1
        if key not in REPO:
            tot['repository_key_absent_from_bill_repository_live'] += 1
        f = by_name.get((key, member))
        fb = by_bio.get((key, bio)) if bio else None
        if f is None:
            tot['no_official_fact_by_name'] += 1
            if fb is not None:
                tot['fact_reachable_by_bioguide_but_NOT_by_name'] += 1
                bio_only.append({'member': member, 'bill': r.get('bill'),
                                 'congress': str(r.get('congress')), 'key': key,
                                 'fact_member': fb.get('member'), 'desk_role': r.get('role'),
                                 'fact_role': fb.get('role'), 'withdrawn': bool(fb.get('withdrawn'))})
            continue
        tot['official_fact_present'] += 1
        if f.get('withdrawn'):
            tot['WITHDRAWN_DISPLAYED'] += 1
            withdrawn_rows.append({'member': member, 'bill': r.get('bill'),
                                   'congress': str(r.get('congress')), 'key': key,
                                   'desk_role': r.get('role'),
                                   'withdrawn_date': f.get('withdrawn_date')})
        if F.canonical_role(r.get('role')) != F.canonical_role(f.get('role')):
            tot['ROLE_DIFFERS_FROM_OFFICIAL'] += 1
            role_diff_rows.append({'member': member, 'bill': r.get('bill'),
                                   'congress': str(r.get('congress')), 'key': key,
                                   'desk_role': r.get('role'), 'official_role': f.get('role')})

W('')
for k in ('rows', 'parseable', 'unparseable_bill_identity',
          'repository_key_absent_from_bill_repository_live',
          'official_fact_present', 'no_official_fact_by_name',
          'fact_reachable_by_bioguide_but_NOT_by_name'):
    W('  %-52s %d' % (k, tot[k]))
W('')
W('  *** W5-a  displayed rows whose OFFICIAL record says WITHDRAWN        = %d'
  % tot['WITHDRAWN_DISPLAYED'])
W('  *** W5-b  displayed rows whose role DIFFERS from the official role   = %d'
  % tot['ROLE_DIFFERS_FROM_OFFICIAL'])
for r in withdrawn_rows[:40]:
    W('       WITHDRAWN-DISPLAYED %s' % json.dumps(r, ensure_ascii=False))
for r in role_diff_rows[:40]:
    W('       ROLE-DIFFERS        %s' % json.dumps(r, ensure_ascii=False))
W('  unparseable displayed bill prefixes (apply_to_desk keeps these unjudged): %s'
  % json.dumps(dict(unparseable.most_common(12))))
for r in bio_only[:20]:
    W('       BIOGUIDE-ONLY REACHABLE %s' % json.dumps(r, ensure_ascii=False))

# ---------------------------------------------------------------- the withdrawn facts themselves
W('\n  EVERY fact in the official record with withdrawn=True, and whether the desk shows it:')
shown = {(m, N.repo_key(r.get('bill'), r.get('congress'))): r
         for m, rows in DESK.items() for r in rows}
for f in FACTS:
    if not f.get('withdrawn'):
        continue
    d = shown.get((f['member'], f['repository_key']))
    W('     %-26s %-12s %-11s role=%-10s withdrawn_date=%-11s join=%-11s  desk row: %s'
      % (f['member'][:26], f['bill'], f['repository_key'], f['role'],
         f.get('withdrawn_date') or '-', f.get('join_date') or '-',
         ('DISPLAYED role=%s' % d.get('role')) if d else 'ABSENT from the desk'))

# ---------------------------------------------------------------- role-superseded breadth on the routing side
W('\n  CROSS-CHECK on the routing side (why 1854 rows carry the disposition):')
RA = N.routing_audit()
RES, _n2, _b2 = N.resolver()
kinds = collections.Counter()
for row in RA['rows']:
    if row.get('disposition') != 'official-membership-withdrawn-or-role-superseded':
        continue
    mm = row.get('member') or RES.resolve(row.get('member_source'))
    key = N.repo_key(row.get('bill'), row.get('congress'))
    f = by_name.get((key, mm)) if (key and mm) else None
    if f is None:
        kinds['no fact by name (bioguide-keyed eligible() still fired)'] += 1
    elif f.get('withdrawn'):
        kinds['WITHDRAWN in the official record'] += 1
    else:
        kinds['role superseded: archive role %s -> official %s'
              % (F.canonical_role(row.get('source_role')), F.canonical_role(f.get('role')))] += 1
for k, n in kinds.most_common():
    W('     %-64s rows=%d' % (k, n))

dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'n15_w5_breadth.txt')
with open(dest, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(OUT) + '\nDONE\n')
print('DONE -> %s' % dest)
