# -*- coding: utf-8 -*-
"""N15 W3 (READ-ONLY): which desk membership source supplied the displayed row for each of the
23, and why OM.apply_to_desk left it in place.  Nothing under fec/ is imported.

The desk's bill ledger is assembled in LIVE\fec\surfaces\make_member_desk.py in this order
(read as text, line numbers from the LIVE file):
  :2117-2145  workbook role sheets   ROLEMAP {'Sponsor Interactions':'sponsor',
              'Original Co-Sponsor Interaction':'original','Co-Sponsor Interactions':'cosponsor'}
  :2146-2164  manual_bill_evidence.csv
  :2170-2174  data/members/{primacy_act,registry_anchor,bank_anchor}_memberships.ndjson
  :2240-2290  collector roster merge (DESK_MEMBERSHIP_SOURCE default 'delta'
              -> data/members/collector_roster_updates.ndjson)
  :2291-2294  sentinel_admissions (remove_managed_desk_rows + append_to_desk)
  :2295-2296  OM.apply_to_desk(bills, OM.load(B))          <-- the pass under test
  :2305-2340  adjudicated per-member withdrawals
  :2351-2367  collapse: one row per (bill, congress), role = min(sponsor<original<cosponsor)
apply_to_desk therefore runs on PRE-COLLAPSE rows: one row per source row per area.
"""
import os, sys, json, csv, collections

N5 = (r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees"
      r"\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\measN5\receipts")
if N5 not in sys.path:
    sys.path.insert(0, N5)
import n5_lib as N                                             # noqa: E402
import f1_lib as F                                             # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SCRATCH = (r"C:\Users\pgoff\AppData\Local\Temp\claude"
           r"\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad"
           r"\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\measN15")
OUT = []
def W(s=''):
    OUT.append(s)
    print(s)

STATE = json.load(open(os.path.join(SCRATCH, 'w1_state.json'), encoding='utf-8'))
DETAIL = STATE['detail']
KEYS = {(d['member'], d['norm_bill'], d['congress']): d for d in DETAIL}
RES, _names, _bios = N.resolver()

W('=' * 102)
W('N15 / W3  WHICH DESK SOURCE SUPPLIED THE DISPLAYED ROW, AND WHY apply_to_desk KEPT IT')
W('=' * 102)

# ---------------------------------------------------------------- what the bundle's own audit says
import re
BUN = N.P('member_desk_bundle.json')
_found = {}
with open(BUN, encoding='utf-8') as fh:
    blob = fh.read(4 << 20)          # the audit blocks sit in the bundle header
for k in ('bill_withdrawn_rows_removed', 'bill_duplicate_rows_collapsed', 'bills_displayed_unique',
          'bill_source_rows', 'bill_manual_rows', 'bill_collector_roster_rows',
          'bill_withdrawal_rules_already_absent'):
    m = re.search(r'"%s"\s*:\s*([0-9]+)' % k, blob)
    _found[k] = int(m.group(1)) if m else None
W('  bundle audit counters (first 4 MB of member_desk_bundle.json):')
for k, v in _found.items():
    W('     %-40s %s' % (k, v))

# ---------------------------------------------------------------- source probes, ROLE-AWARE
SRC = collections.defaultdict(set)          # (member, norm_bill, congress) -> {(tag, canonical_role)}


def add(tag, member_raw, bill, congress, role_raw):
    m = RES.resolve(member_raw) or str(member_raw or '').strip()
    k = (m, N.norm_bill(bill), N.cong(congress))
    if k in KEYS:
        SRC[k].add((tag, F.canonical_role(role_raw)))


# 1. workbook role sheets
SHEET_ROLE = {'Sponsor Interactions': 'sponsor',
              'Original Co-Sponsor Interaction': 'original',
              'Co-Sponsor Interactions': 'cosponsor'}
wb_rows = collections.Counter()
for sheet, role in SHEET_ROLE.items():
    for r in N.sheet_rows(N.P('Moneyball Main Version - Blended.xlsx'), sheet):
        wb_rows[sheet] += 1
        add('workbook:' + sheet, r.get('Member'), r.get('Name'), r.get('Congress'), role)
W('\n  workbook role-sheet rows read: %s' % dict(wb_rows))

# 2. manual csv
_man = 0
for r in N.manual_rows():
    _man += 1
    raw = str(r.get('Role') or '').lower()
    role = 'sponsor' if raw == 'sponsor' else ('original' if 'original' in raw else 'cosponsor')
    add('manual_csv', r.get('Member'), r.get('Bill'), r.get('Congress'), role)
W('  manual_bill_evidence.csv rows read: %d' % _man)

# 3. the three adjudicated sidecars + collector roster + cumulative history
for rel, tag in (('data/members/primacy_act_memberships.ndjson', 'primacy_act'),
                 ('data/members/registry_anchor_memberships.ndjson', 'registry_anchor'),
                 ('data/members/bank_anchor_memberships.ndjson', 'bank_anchor'),
                 ('data/members/collector_roster_updates.ndjson', 'collector_roster'),
                 ('data/members/sentinel_verified_membership_history.ndjson', 'sentinel_history')):
    n = 0
    for line in open(N.P(*rel.split('/')), encoding='utf-8'):
        if not line.strip():
            continue
        n += 1
        r = json.loads(line)
        add(tag, r.get('member'), r.get('bill'), r.get('congress'), r.get('role'))
    W('  %-58s rows read: %d' % (rel, n))

# 4. sentinel admissions
SA = json.load(open(N.P('data', 'legislation', 'sentinel_admissions.json'), encoding='utf-8'))
_sa = 0
for r in (SA.get('memberships') or []):
    _sa += 1
    add('sentinel_admissions', r.get('member'), r.get('bill'), r.get('congress'), r.get('role'))
W('  sentinel_admissions.json memberships: %d' % _sa)

# ---------------------------------------------------------------- per-triple attribution
W('\n  PER-TRIPLE: every source that carries the triple, with the role that source states.')
W('  "kept/removed" is apply_to_desk applied to that pre-collapse row: removed iff the official')
W('  fact is withdrawn OR canonical_role(row) != canonical_role(fact).')
W('')
W('  %-26s %-11s %-5s %-14s %s'
  % ('member', 'bill', 'cong', 'official role', 'source -> role stated [apply_to_desk]'))
agg_supplier = collections.Counter()
agg_removed = collections.Counter()
for d in DETAIL:
    k = (d['member'], d['norm_bill'], d['congress'])
    off = d['official_role']
    srcs = sorted(SRC.get(k, set()))
    parts = []
    supplying = []
    for tag, role in srcs:
        keep = (role == off)
        parts.append('%s=%s[%s]' % (tag.replace('workbook:', 'wb:').replace(' Interaction', '')
                                    .replace(' Interactions', ''), role, 'kept' if keep else 'REMOVED'))
        if keep:
            supplying.append(tag)
        else:
            agg_removed[tag] += 1
    d['sources'] = ['%s=%s' % (t, r) for t, r in srcs]
    d['supplying_sources'] = supplying
    agg_supplier[tuple(supplying) or ('UNATTRIBUTED',)] += 1
    W('  %-26s %-11s %-5s %-14s %s'
      % (d['member'][:26], d['bill'][:11], d['congress'], off, '; '.join(parts) or 'NONE FOUND'))

W('\n  SOURCE(S) that supplied the SURVIVING displayed row (role == official role):')
for s, n in agg_supplier.most_common():
    W('     %-70s n=%d' % (','.join(s), n))
W('  PRE-COLLAPSE rows apply_to_desk REMOVED for these 23 triples, by source:')
for s, n in agg_removed.most_common():
    W('     %-70s n=%d' % (s, n))
W('  triples with NO source found = %d' % sum(1 for d in DETAIL if not d['sources']))
W('  triples where a superseded-role row exists in a desk source = %d / %d'
  % (sum(1 for d in DETAIL if any(r.split('=')[-1] != d['official_role'] for r in d['sources'])),
     len(DETAIL)))

W('\n  WHY apply_to_desk LEFT THE DISPLAYED ROW IN PLACE -- verbatim, '
  r'LIVE\fec\legislation\official_membership_movements.py:94-108:')
for i, line in enumerate(open(N.P('fec', 'legislation', 'official_membership_movements.py'),
                              encoding='utf-8').read().splitlines()[93:108], start=94):
    W('    %3d | %s' % (i, line))
W('  -> by_name is keyed (repository_key, member NAME); for all 23 the fact EXISTS,')
W('     fact["withdrawn"] is False and canonical_role(displayed role) == canonical_role(fact role),')
W('     so the else-branch keeps the row.  The superseded-role duplicate row for the same triple')
W('     is the row apply_to_desk removes, pre-collapse.')

dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'n15_w3_sources.txt')
with open(dest, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(OUT) + '\nDONE\n')
with open(os.path.join(SCRATCH, 'w3_state.json'), 'w', encoding='utf-8') as fh:
    json.dump(DETAIL, fh, ensure_ascii=False, indent=1)
print('DONE -> %s' % dest)
