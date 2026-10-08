# -*- coding: utf-8 -*-
"""N15 W2 code quotes + the NEGATIVE CONTROL for W5 (READ-ONLY, nothing under fec/ imported).

(1) verbatim quotes: the official-record fields, how WITHDRAWN is distinguished from
    ROLE-SUPERSEDED, and the producer lines that emit the disposition.
(2) the 460 unjudgeable displayed rows, split exactly.
(3) the 13 displayed rows the official record is silent about.
(4) NEGATIVE CONTROL: rebuild the PRE-apply_to_desk desk ledger from the same sources
    make_member_desk reads and count the rows that WOULD violate the two conditions.  W5's
    zeros are only meaningful if this number is large.
"""
import os, sys, json, csv, re, collections

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


def quote(rel, lo, hi, label):
    W('\n  --- %s   %s:%d-%d ---' % (label, rel, lo, hi))
    lines = open(N.P(*rel.split('/')), encoding='utf-8').read().splitlines()
    for i in range(lo, hi + 1):
        W('   %4d | %s' % (i, lines[i - 1]))


W('=' * 102)
W('N15 / W2  WHAT THE DISPOSITION MEANS IN CODE (verbatim)')
W('=' * 102)
quote('fec/legislation/official_membership_movements.py', 1, 21,
      'module docstring + the enabled() gate')
quote('fec/legislation/official_membership_movements.py', 40, 57,
      'the RECORD FIELDS: withdrawn is a BOOLEAN off person["withdrawn_date"]; role is the '
      'official role')
quote('fec/legislation/official_membership_movements.py', 60, 91,
      'load() gates + eligible(): ONE predicate covers BOTH withdrawn and role-supersession')
quote('fec/legislation/build_archive_legislative.py', 202, 208,
      'the producer lines that EMIT the disposition')
W('\n  MECHANICS, stated from the quotes above:')
W('   * the official record carries NO "superseded" field.  eligible() (line 89-91) returns False')
W('     on EITHER  fact["withdrawn"] is True  OR  canonical_role(row role) != canonical_role(fact role).')
W('   * build_archive_legislative.py:206-208 collapses both into the SINGLE disposition string')
W('     "official-membership-withdrawn-or-role-superseded", so the string alone cannot tell them apart:')
W('     the only way to separate them is to read fact["withdrawn"] out of the official record.')
W('   * role-supersession in practice = the archive row says "cosponsor" while BILLSTATUS lists the')
W('     person among original_cosponsors (official role "original" -> canonical "original-cosponsor").')
W('   * build() writes withdrawn/withdrawn_date per person (line 43) and only proposes an ADDITION')
W('     when the membership is NOT withdrawn and the role actually changed (line 50-54).')

# ---------------------------------------------------------------- the desk side, exact splits
OMDOC = json.load(open(N.P('data', 'legislation', 'official_membership_movements.json'),
                       encoding='utf-8'))
FACTS = OMDOC.get('facts') or []
by_name = {(r['repository_key'], r['member']): r for r in FACTS}
REPO = json.load(open(N.P('bill_repository_live.json'), encoding='utf-8'))['bills']
with open(N.P('member_desk_bundle.json'), encoding='utf-8') as fh:
    D = json.load(fh)
DESK = {m.get('name'): (m.get('bills') or []) for m in (D.get('members') or [])}
del D

W('')
W('=' * 102)
W('N15 / W5 SUPPORT  THE ROWS apply_to_desk CANNOT JUDGE, AND THE ROWS THE RECORD IS SILENT ABOUT')
W('=' * 102)
kinds = collections.Counter()
silent = []
for member, rows in DESK.items():
    for r in rows:
        nb = N.norm_bill(r.get('bill'))
        key = N.repo_key(nb, r.get('congress'))
        if not key:
            if nb.startswith('LTR'):
                kinds['unparseable: LTR-* sign-on letter'] += 1
            elif 'AMDT' in nb:
                kinds['unparseable: amendment (H.AMDT./S.AMDT.)'] += 1
            else:
                kinds['unparseable: OTHER -> ' + nb] += 1
            continue
        if (key, member) not in by_name:
            silent.append({'member': member, 'bill': r.get('bill'),
                           'congress': str(r.get('congress')), 'key': key,
                           'desk_role': r.get('role'),
                           'key_in_bill_repository_live': key in REPO,
                           'members_in_facts_for_this_key':
                               sorted({f['member'] for f in FACTS if f['repository_key'] == key})[:4]})
for k, n in kinds.most_common():
    W('  %-52s %d' % (k, n))
W('  TOTAL unjudgeable (parse_bill_identity raises -> kept at line 102) = %d' % sum(kinds.values()))
W('\n  displayed rows with a parseable key but NO official fact = %d' % len(silent))
for s in silent:
    W('     %s' % json.dumps(s, ensure_ascii=False))
_unres = OMDOC.get('unresolved') or []
W('  official record unresolved[] entries (person not on the engine roster) = %d ; sample %s'
  % (len(_unres), json.dumps(_unres[:2], ensure_ascii=False)))

# ---------------------------------------------------------------- NEGATIVE CONTROL
W('')
W('=' * 102)
W('N15 / NEGATIVE CONTROL  PRE-apply_to_desk ROWS THAT VIOLATE THE TWO CONDITIONS')
W('=' * 102)
RES, _names, _bios = N.resolver()
pre = []          # (member, bill_raw, congress, role, source)
SHEET_ROLE = {'Sponsor Interactions': 'sponsor',
              'Original Co-Sponsor Interaction': 'original',
              'Co-Sponsor Interactions': 'cosponsor'}
for sheet, role in SHEET_ROLE.items():
    for r in N.sheet_rows(N.P('Moneyball Main Version - Blended.xlsx'), sheet):
        m = RES.resolve(r.get('Member'))
        if not m:
            continue
        pre.append((m, r.get('Name'), r.get('Congress'), role, 'workbook:' + sheet))
for r in N.manual_rows():
    m = RES.resolve(r.get('Member'))
    if not m:
        continue
    raw = str(r.get('Role') or '').lower()
    role = 'sponsor' if raw == 'sponsor' else ('original' if 'original' in raw else 'cosponsor')
    pre.append((m, r.get('Bill'), r.get('Congress'), role, 'manual_csv'))
for rel, tag in (('data/members/primacy_act_memberships.ndjson', 'primacy_act'),
                 ('data/members/registry_anchor_memberships.ndjson', 'registry_anchor'),
                 ('data/members/bank_anchor_memberships.ndjson', 'bank_anchor'),
                 ('data/members/collector_roster_updates.ndjson', 'collector_roster')):
    for line in open(N.P(*rel.split('/')), encoding='utf-8'):
        if not line.strip():
            continue
        d = json.loads(line)
        m = RES.resolve(d.get('member'))
        if not m:
            continue
        pre.append((m, d.get('bill'), d.get('congress'), d.get('role'), tag))
SA = json.load(open(N.P('data', 'legislation', 'sentinel_admissions.json'), encoding='utf-8'))
for d in (SA.get('memberships') or []):
    m = RES.resolve(d.get('member'))
    if not m:
        continue
    pre.append((m, d.get('bill'), d.get('congress'), d.get('role'), 'sentinel_admissions'))

viol = collections.Counter()
viol_src = collections.Counter()
viol_pairs = collections.Counter()
for m, bill, cg, role, src in pre:
    key = N.repo_key(bill, cg)
    if not key:
        continue
    f = by_name.get((key, m))
    if not f:
        continue
    if f.get('withdrawn'):
        viol['withdrawn'] += 1
        viol_src['withdrawn <- ' + src] += 1
    elif F.canonical_role(role) != F.canonical_role(f.get('role')):
        viol['role-differs'] += 1
        viol_src['role-differs <- ' + src] += 1
        viol_pairs['%s -> official %s' % (F.canonical_role(role), F.canonical_role(f.get('role')))] += 1
W('  pre-collapse candidate rows reconstructed from the desk sources = %d' % len(pre))
W('  rows that WOULD be removed by apply_to_desk (withdrawn)     = %d' % viol['withdrawn'])
W('  rows that WOULD be removed by apply_to_desk (role differs)   = %d' % viol['role-differs'])
W('  TOTAL = %d   <-- had apply_to_desk not run, W5-a/W5-b would report these, not 0'
  % sum(viol.values()))
for k, n in viol_src.most_common():
    W('     %-58s n=%d' % (k, n))
for k, n in viol_pairs.most_common():
    W('     role pair %-46s n=%d' % (k, n))
W('  NOTE: this reconstruction is a SOURCE-PRESENCE probe, not a re-simulation of')
W('  make_member_desk (bill_rules exclusions, overrides and the sentinel remove/append passes are')
W('  not replayed), so it is an UPPER BOUND on the rows the real pass saw.')

# what the bundle itself reports, if the counter is serialised anywhere
hit = None
with open(N.P('member_desk_bundle.json'), encoding='utf-8') as fh:
    while True:
        chunk = fh.read(1 << 22)
        if not chunk:
            break
        m = re.search(r'"bill_withdrawn_rows_removed"\s*:\s*([0-9]+)', chunk)
        if m:
            hit = int(m.group(1))
            break
W('  member_desk_bundle.json "bill_withdrawn_rows_removed" = %s  (None = the media_audit block is '
  'not serialised into the bundle)' % hit)

dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'n15_w2_quotes_and_negcontrol.txt')
with open(dest, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(OUT) + '\nDONE\n')
print('DONE -> %s' % dest)
