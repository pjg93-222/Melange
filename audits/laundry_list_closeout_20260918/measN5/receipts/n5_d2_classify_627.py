# -*- coding: utf-8 -*-
"""N5 / D2 (READ-ONLY): classify the 627 workbook-role-sheet-only keys.

Reproduces lane C's fork set first (q2b_fork_size.py), then assigns every key to
exactly one class with this PRECEDENCE (stated so the cross-tab can be re-sliced):

  (b) the routing audit holds the same (member, bill, Congress) with a SELECTED row
      -- the bill survives a switch, only the role badge can change.
  (a) the routing audit holds the triple but EVERY row on it is non-selected
      (withdrawn / role-superseded / excluded / neutral / unmatched) -- a switch
      removes the row and the removal is adjudicated.
  (c) triple absent from the routing audit (= absent from the producer's frame) but
      present in Sentinel Bill Ledger.xlsx.
  (d) triple absent from routing audit and sentinel, present in the OLDER archive.
  (e) found nowhere else -- workbook-only residue.

Also prints the raw (in-routing x disposition x in-sentinel x in-old-archive) cross-tab.
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n5_lib as N
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

W = print


def dump(obj, name):
    p = os.path.join(N.SCRATCH, name)
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=True)
    W('  [state] %s' % p)


# ------------------------------------------------------------------ inputs
WBR = N.workbook_role_rows()
ARC = N.archive_rows('sel')
OLD = N.archive_rows('old')
SENT_ALL = N.sentinel_all_rows()
SENT_V = N.sentinel_verified_rows()
MAN = N.manual_rows()
RA = N.routing_audit()
RES, ROSTER, BIOS = N.resolver()
BL = N.bill_live()

W('=' * 102)
W('N5 / D2  CLASSIFY THE 627 WORKBOOK-ONLY KEYS')
W('=' * 102)
W('workbook role-sheet rows      = %d  (%s)' % (len(WBR), dict(collections.Counter(
    r['__sheet__'] for r in WBR))))
W('selected archive rows         = %d   old archive rows = %d' % (len(ARC), len(OLD)))
W('sentinel ledger rows          = %d   verified+eligible membership = %d' % (len(SENT_ALL), len(SENT_V)))
W('manual_bill_evidence rows     = %d' % len(MAN))
W('routing audit rows            = %d  (declared source_rows=%s, selected_events=%s)'
  % (len(RA['rows']), RA['source_rows'], RA['selected_events']))
W('  frame arithmetic check: %d archive + %d sentinel-verified + %d manual = %d  (audit says %d) -> %s'
  % (len(ARC), len(SENT_V), len(MAN), len(ARC) + len(SENT_V) + len(MAN), RA['source_rows'],
     'MATCH' if len(ARC) + len(SENT_V) + len(MAN) == RA['source_rows'] else 'MISMATCH'))

# --------------------------------------------------- reproduce lane C's fork
desk_keys = collections.Counter()
key_to_wbrows = collections.defaultdict(list)
for r in WBR:
    k = N.key4(r.get('Member'), r.get('Name'), r.get('Congress'), r.get('Role'))
    desk_keys[k] += 1
    key_to_wbrows[k].append(r)
matrix_keys = collections.Counter()
for r in ARC:
    matrix_keys[N.key4(r.get('Member'), r.get('Name'), r.get('Congress'), r.get('Role'))] += 1
for r in SENT_V:
    matrix_keys[N.key4(r.get('Member'), r.get('Bill'), r.get('Congress'), r.get('Role'))] += 1
manual_keys = {N.key4(r.get('Member'), r.get('Bill'), r.get('Congress'), r.get('Role')) for r in MAN}
only_desk = set(desk_keys) - set(matrix_keys) - manual_keys
only_matrix = set(matrix_keys) - set(desk_keys) - manual_keys
W('\nREPRODUCTION: only-in-workbook = %d (lane C: 627) ; only-in-archive = %d (lane C: 258) -> %s'
  % (len(only_desk), len(only_matrix),
     'MATCH' if (len(only_desk), len(only_matrix)) == (627, 258) else 'MISMATCH'))
W('  by role: %s ; by Congress: %s' % (
    dict(collections.Counter(k[3] for k in only_desk)),
    dict(sorted(collections.Counter(k[2] for k in only_desk).items()))))

# --------------------------------------------- routing-audit triple index
SRC_BUCKETS = [(0, len(ARC), 'selected-archive'),
               (len(ARC), len(ARC) + len(SENT_V), 'sentinel-verified'),
               (len(ARC) + len(SENT_V), 10 ** 9, 'manual-csv')]


def bucket_of(source_row):
    idx = int(source_row) - 2
    for lo, hi, name in SRC_BUCKETS:
        if lo <= idx < hi:
            return name
    return 'UNKNOWN'


ra_triple = collections.defaultdict(list)
ra_unresolved = collections.Counter()
for row in RA['rows']:
    mm = row.get('member')
    if not mm:
        mm = RES.resolve(row.get('member_source'))
        if not mm:
            ra_unresolved[str(row.get('member_source'))] += 1
            continue
    t = (mm, N.norm_bill(row.get('bill')), N.cong(row.get('congress')))
    ra_triple[t].append({'disposition': row['disposition'],
                         'source_role': N.role(row.get('source_role')),
                         'effective_role': row.get('effective_role'),
                         'effective_category': row.get('effective_category'),
                         'source': bucket_of(row['source_row']),
                         'reason': row.get('reason') or row.get('override_reason') or '',
                         'source_row': row['source_row']})
W('\nrouting-audit triples indexed = %d ; rows whose member_source did not resolve = %d %s'
  % (len(ra_triple), sum(ra_unresolved.values()), dict(ra_unresolved)))

# ------------------------------------------------------- other-source indexes
sent_triple = collections.defaultdict(list)
for r in SENT_ALL:
    m = RES.resolve(r.get('Member')) if r.get('Member') else None
    if not m:
        continue
    sent_triple[(m, N.norm_bill(r.get('Bill')), N.cong(r.get('Congress')))].append(r)
old_triple = collections.defaultdict(list)
for r in OLD:
    m = RES.resolve(r.get('Member')) if r.get('Member') else None
    if not m:
        continue
    old_triple[(m, N.norm_bill(r.get('Name')), N.cong(r.get('Congress')))].append(r)
arc_triple = collections.defaultdict(list)
for r in ARC:
    m = RES.resolve(r.get('Member')) if r.get('Member') else None
    if not m:
        continue
    arc_triple[(m, N.norm_bill(r.get('Name')), N.cong(r.get('Congress')))].append(r)

# ------------------------------------------------------ live BILLSTATUS dates
live = BL.get('bills') or {}
bio_to_name = {v: k for k, v in BIOS.items() if v}


def live_join(member, bill, congress):
    """(date, withdrawn_date, role_in_billstatus, bill_present) from bill_repository_live."""
    rk = N.repo_key(bill, congress)
    if not rk or rk not in live:
        return None, None, None, False
    b = live[rk]
    bio = BIOS.get(member)
    for field, rolename in (('sponsor', 'sponsor'),
                            ('original_cosponsors', 'original-cosponsor'),
                            ('cosponsors', 'cosponsor')):
        v = b.get(field)
        people = [v] if isinstance(v, dict) else (v or [])
        for p in people:
            if not isinstance(p, dict):
                continue
            pb = p.get('bioguide')
            if (pb and bio and pb == bio) or (pb and bio_to_name.get(pb) == member):
                return p.get('date') or '', p.get('withdrawn_date') or '', rolename, True
    return None, None, None, True


# ---------------------------------------------------------------- classify
NONSELECTED_ORDER = ['official-membership-withdrawn-or-role-superseded', 'excluded-title',
                     'excluded-override', 'neutral-registry', 'neutral-override',
                     'neutral-manual', 'neutral-official-evidence', 'unknown-section',
                     'unmatched-member', 'duplicate-lower-role', 'duplicate-same-role']
classes = collections.defaultdict(list)
detail = {}
unresolved_members = collections.Counter()
for k in sorted(only_desk):
    raw_member, bill, congress, rolev = k
    mm = RES.resolve(raw_member)
    if not mm:
        unresolved_members[raw_member] += 1
    t = (mm or raw_member, bill, congress)
    ra_rows = ra_triple.get(t, [])
    disps = [x['disposition'] for x in ra_rows]
    wrows = key_to_wbrows[k]
    jd, wd, lrole, bill_in_live = live_join(mm or raw_member, bill, congress)
    rec = {'key': k, 'member': mm or raw_member, 'triple_in_routing': bool(ra_rows),
           'routing_dispositions': dict(collections.Counter(disps)),
           'routing_selected_roles': sorted({x['effective_role'] for x in ra_rows
                                             if x['disposition'] == 'selected' and x['effective_role']}),
           'routing_sources': sorted({x['source'] for x in ra_rows}),
           'routing_reasons': sorted({x['reason'] for x in ra_rows if x['reason']}),
           'in_selected_archive_triple': bool(arc_triple.get(t)),
           'archive_roles': sorted({N.role(r.get('Role')) for r in arc_triple.get(t, [])}),
           'in_sentinel': bool(sent_triple.get(t)),
           'sentinel_status': sorted({(str(r.get('Record Type')), str(r.get('Review Status')),
                                       str(r.get('Scoring Eligible')), N.role(r.get('Role')),
                                       str(r.get('Join Date') or ''))
                                      for r in sent_triple.get(t, [])}),
           'in_old_archive': bool(old_triple.get(t)),
           'old_archive_roles': sorted({N.role(r.get('Role')) for r in old_triple.get(t, [])}),
           'wb_sheets': sorted({r['__sheet__'] for r in wrows}),
           'wb_rows': sorted(r['__row__'] for r in wrows),
           'wb_last_action': sorted({str(r.get('LastAction') or '') for r in wrows}),
           'wb_title': (wrows[0].get('Title') if wrows else ''),
           'live_bill_cached': bill_in_live, 'live_join_date': jd,
           'live_withdrawn_date': wd, 'live_role': lrole}
    if 'selected' in disps:
        cls = 'b'
    elif ra_rows:
        cls = 'a'
    elif sent_triple.get(t):
        cls = 'c'
    elif old_triple.get(t):
        cls = 'd'
    else:
        cls = 'e'
    rec['class'] = cls
    classes[cls].append(rec)
    detail[' | '.join(k)] = rec

W('\n' + '=' * 102)
W('D2 CLASSIFICATION (627 keys, one class each)')
W('=' * 102)
LABELS = {'a': '(a) routing audit holds the triple, EVERY row non-selected (withdrawn/superseded/ineligible)',
          'b': '(b) routing audit SELECTS the triple under a different role (bill survives a switch)',
          'c': '(c) triple absent from the producer frame, present in Sentinel Bill Ledger.xlsx',
          'd': '(d) absent from routing+sentinel, present in the OLDER 20260624 archive only',
          'e': '(e) found nowhere else -- workbook-only residue'}
for c in 'abcde':
    W('  %-3s n=%-5d %s' % (c, len(classes[c]), LABELS[c]))
W('  TOTAL = %d' % sum(len(classes[c]) for c in 'abcde'))
if unresolved_members:
    W('  !! member names in the 627 that the producer Resolver cannot resolve: %s' % dict(unresolved_members))

for c in 'abcde':
    rows = classes[c]
    if not rows:
        continue
    W('\n' + '-' * 102)
    W('CLASS %s  n=%d  %s' % (c, len(rows), LABELS[c]))
    W('-' * 102)
    W('  distinct members=%d  distinct bills=%d  by Congress=%s  by workbook role=%s'
      % (len({r['member'] for r in rows}), len({r['key'][1] for r in rows}),
         dict(sorted(collections.Counter(r['key'][2] for r in rows).items())),
         dict(collections.Counter(r['key'][3] for r in rows))))
    W('  top bills: %s' % collections.Counter(r['key'][1] for r in rows).most_common(12))
    if c == 'a':
        dd = collections.Counter()
        for r in rows:
            for d, n in r['routing_dispositions'].items():
                dd[d] += 1
        W('  DISPOSITION STRINGS on the matching routing-audit rows (triples carrying each):')
        for d, n in dd.most_common():
            W('     %-52s triples=%d' % (repr(d), n))
        rs = collections.Counter()
        for r in rows:
            for x in r['routing_reasons']:
                rs[x] += 1
        if rs:
            W('  reason / override_reason strings: %s' % rs.most_common(10))
        W('  routing source bucket: %s' % collections.Counter(
            tuple(r['routing_sources']) for r in rows).most_common())
    if c == 'b':
        W('  routing SELECTED effective_role vs workbook role:')
        for pair, n in collections.Counter(
                (r['key'][3], tuple(r['routing_selected_roles'])) for r in rows).most_common():
            W('     workbook=%-18s routing_selected=%-28s n=%d' % (pair[0], str(pair[1]), n))
    if c == 'c':
        st = collections.Counter()
        for r in rows:
            for s in r['sentinel_status']:
                st[s] += 1
        W('  SENTINEL status columns (Record Type, Review Status, Scoring Eligible, Role, Join Date):')
        for s, n in st.most_common(20):
            W('     %-100s n=%d' % (str(s), n))
    if c == 'd':
        W('  old-archive roles on the triple: %s' % collections.Counter(
            tuple(r['old_archive_roles']) for r in rows).most_common())
    W('  examples (up to 10):')
    for r in rows[:10]:
        W('     %-22s %-14s C%-4s wb=%-18s | routing=%-46s | arc_roles=%-22s sent=%s old=%s | live_date=%s wd=%s'
          % (r['member'][:22], r['key'][1], r['key'][2], r['key'][3],
             str(r['routing_dispositions'])[:46], str(r['archive_roles'])[:22],
             r['in_sentinel'], r['in_old_archive'], r['live_join_date'], r['live_withdrawn_date']))

# ------------------------------------------------------------- cross-tab
W('\n' + '=' * 102)
W('RAW CROSS-TAB (re-sliceable): in_routing x in_selected_archive_triple x in_sentinel x in_old_archive')
W('=' * 102)
ct = collections.Counter((r['triple_in_routing'], r['in_selected_archive_triple'],
                          r['in_sentinel'], r['in_old_archive'])
                         for c in 'abcde' for r in classes[c])
for k, n in sorted(ct.items(), key=lambda x: -x[1]):
    W('  routing=%-5s sel_archive=%-5s sentinel=%-5s old_archive=%-5s  n=%d' % (k + (n,)))

# ------------------------------------------------------------ DATE EVIDENCE
W('\n' + '=' * 102)
W('D2 DATE EVIDENCE for when the 627 workbook rows were appended')
W('=' * 102)
allrows = [r for c in 'abcde' for r in classes[c]]
W('\n1) APPEND ORDER inside each role sheet (rows are 1-based; header is row 1).')
sheet_tot = collections.Counter(r['__sheet__'] for r in WBR)
for sn in N.ROLE_SHEETS:
    idx = sorted(i for r in allrows for i in r['wb_rows'] if sn in r['wb_sheets'])
    if not idx:
        W('   %-34s no 627-rows' % sn)
        continue
    tot = sheet_tot[sn] + 1
    W('   %-34s sheet data rows=%-6d 627-rows here=%-5d min=%-6d median=%-6d max=%-6d '
      '| in LAST 10%% of the sheet=%d' % (sn, sheet_tot[sn], len(idx), idx[0],
                                          idx[len(idx) // 2], idx[-1],
                                          sum(1 for i in idx if i > tot - sheet_tot[sn] * 0.10)))
    # where do the OTHER (non-627) rows sit?
    other = sorted(r['__row__'] for r in WBR if r['__sheet__'] == sn
                   and N.key4(r.get('Member'), r.get('Name'), r.get('Congress'), r.get('Role')) not in only_desk)
    if other:
        W('      non-627 rows in the same sheet: min=%d median=%d max=%d'
          % (other[0], other[len(other) // 2], other[-1]))

W('\n2) BILLSTATUS cosponsorship DATE from bill_repository_live.json (updated_at=%s).'
  % BL.get('updated_at'))
have = [r for r in allrows if r['live_join_date']]
W('   bill cached in the live repository      : %d / %d' % (sum(1 for r in allrows if r['live_bill_cached']), len(allrows)))
W('   member found on that bill with a date   : %d' % len(have))
W('   member found with a WITHDRAWN date      : %d' % sum(1 for r in allrows if r['live_withdrawn_date']))
W('   join-date histogram by month:')
for ym, n in sorted(collections.Counter((r['live_join_date'] or '')[:7] for r in have).items()):
    W('      %-10s n=%d' % (ym, n))
W('   joined AFTER the selected archive snapshot 2026-08-25 : %d'
  % sum(1 for r in have if r['live_join_date'] > '2026-08-25'))
W('   joined AFTER the older archive snapshot    2026-06-24 : %d'
  % sum(1 for r in have if r['live_join_date'] > '2026-06-24'))
W('   by class:')
for c in 'abcde':
    h = [r for r in classes[c] if r['live_join_date']]
    W('      class %s: dated=%-5d  min=%-12s max=%-12s  after-08-25=%-4d withdrawn=%d'
      % (c, len(h), min((r['live_join_date'] for r in h), default='-'),
         max((r['live_join_date'] for r in h), default='-'),
         sum(1 for r in h if r['live_join_date'] > '2026-08-25'),
         sum(1 for r in classes[c] if r['live_withdrawn_date'])))

W('\n3) SENTINEL LEDGER Join Date where the triple is in the ledger (any status).')
jd = collections.Counter()
for r in allrows:
    for s in r['sentinel_status']:
        if s[4]:
            jd[s[4][:10]] += 1
W('   distinct join dates: %s' % (jd.most_common(20) or 'none'))

W('\n4) FILE-LEVEL timestamps (context, not per-row):')
for rel in ('Moneyball Main Version - Blended.xlsx', N.SEL_ARCHIVE, N.OLD_ARCHIVE,
            'Sentinel Bill Ledger.xlsx', 'legislation_routing_audit.json',
            'bill_repository_live.json', 'member_desk_bundle.json'):
    p = N.P(rel)
    import datetime
    W('   %-46s mtime=%s size=%d' % (rel,
      datetime.datetime.fromtimestamp(os.path.getmtime(p)).isoformat(sep=' ')[:19],
      os.path.getsize(p)))


# ==================================================================== D2-bis
# The decisive question: does any of the 627 actually ADD a bill row to the desk,
# or is it collapsed / filtered away before display?
W('\n' + '=' * 102)
W('D2-bis  DO THE 627 SURVIVE INTO THE DESK PAGE?')
W('=' * 102)
W("make_member_desk.py:2325-2343 collapses each member's ledger to ONE row per (bill, congress)")
W("keeping the most specific role (sponsor > original > cosponsor).  So a workbook-only")
W("'cosponsor' key whose 'original-cosponsor' twin is ALSO in the sheets adds nothing.")
twin = 0
notwin = []
for r in allrows:
    raw, bill, c3, rolev = r['key']
    if rolev != 'cosponsor':
        notwin.append(r)
        continue
    if (raw, bill, c3, 'original-cosponsor') in desk_keys or (raw, bill, c3, 'sponsor') in desk_keys:
        twin = twin + 1
        r['collapsed_by_stronger_workbook_twin'] = True
    else:
        r['collapsed_by_stronger_workbook_twin'] = False
        notwin.append(r)
W('  627 keys whose STRONGER-role twin is also in the workbook role sheets (collapse eats them) = %d' % twin)
W('  627 keys with NO stronger twin in the sheets = %d' % len(notwin))
for r in notwin:
    W('     %-22s %-14s C%-4s wb=%-12s class=%s routing=%s'
      % (r['member'][:22], r['key'][1], r['key'][2], r['key'][3], r['class'],
         str(r['routing_dispositions'])[:40]))

# what the SHIPPED desk actually displays for each of the 627 triples
DESK = N.shipped_desk_ledger()
disp = collections.defaultdict(dict)
for nm, rows in DESK.items():
    for b in rows:
        disp[nm][(N.norm_bill(b['bill']), N.cong(b['congress']))] = b
shown = collections.Counter()
shown_role = collections.Counter()
for r in allrows:
    t = (r['key'][1], r['key'][2])
    b = disp.get(r['member'], {}).get(t)
    r['displayed_on_desk'] = bool(b)
    r['displayed_role'] = (b or {}).get('role')
    shown[(r['class'], bool(b))] += 1
    if b:
        shown_role[(r['key'][3], b['role'])] += 1
W('\n  SHIPPED member_desk_bundle.json (mtime 2026-09-18 02:35) -- is the (member,bill,congress) shown?')
for k in sorted(shown):
    W('     class %s  displayed=%-5s n=%d' % (k[0], k[1], shown[k]))
W('     displayed role vs the 627 workbook role: %s' % dict(shown_role))
W('  -> distinct displayed (member,bill,congress) rows the 627 map onto = %d'
  % len({(r['member'], r['key'][1], r['key'][2]) for r in allrows if r['displayed_on_desk']}))

# class (e) sanity: is the BILL in the archive at all (for anybody)?
W('\n  class (e) bill presence elsewhere:')
arc_bills = {(N.norm_bill(r.get('Name')), N.cong(r.get('Congress'))) for r in ARC}
old_bills = {(N.norm_bill(r.get('Name')), N.cong(r.get('Congress'))) for r in OLD}
sent_bills = {(N.norm_bill(r.get('Bill')), N.cong(r.get('Congress'))) for r in SENT_ALL}
for r in classes['e']:
    t = (r['key'][1], r['key'][2])
    W('     %-22s %-12s C%-4s | bill in sel_archive=%-5s old_archive=%-5s sentinel=%-5s live_repo=%-5s '
      '| displayed=%s role=%s'
      % (r['member'][:22], t[0], t[1], t in arc_bills, t in old_bills, t in sent_bills,
         r['live_bill_cached'], r['displayed_on_desk'], r['displayed_role']))

dump({'classes': {c: [r['key'] for r in classes[c]] for c in 'abcde'},
      'detail': detail}, 'd2_state.json')
W('\nDONE')
