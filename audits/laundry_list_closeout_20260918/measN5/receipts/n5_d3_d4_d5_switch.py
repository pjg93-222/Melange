# -*- coding: utf-8 -*-
"""N5 / D3 + D4 + D5 (READ-ONLY).

D3  classify the 258 archive-only keys from the DESK's side.
D4  simulate pointing the desk at the routing audit's SELECTED rows: rows lost / gained
    vs the SHIPPED member_desk_bundle.json ledger, per member, and the class of every loss.
D5  field coverage: what the desk renders today that the routing audit does not carry.
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n5_lib as N
import f1_lib as F
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
W = print

WBR = N.workbook_role_rows()
ARC = N.archive_rows('sel')
OLD = N.archive_rows('old')
SENT_ALL = N.sentinel_all_rows()
SENT_V = N.sentinel_verified_rows()
MAN = N.manual_rows()
RA = N.routing_audit()
RES, ROSTER, BIOS = N.resolver()
BL = N.bill_live()
DESK = N.shipped_desk_ledger()
LIVE = BL.get('bills') or {}
bio_to_name = {v: k for k, v in BIOS.items() if v}

# ------------------------------------------------------------- key sets
desk_keys = collections.Counter()
for r in WBR:
    desk_keys[N.key4(r.get('Member'), r.get('Name'), r.get('Congress'), r.get('Role'))] += 1
matrix_keys = collections.Counter()
mk_src = collections.defaultdict(set)
for r in ARC:
    k = N.key4(r.get('Member'), r.get('Name'), r.get('Congress'), r.get('Role'))
    matrix_keys[k] += 1
    mk_src[k].add('selected-archive')
for r in SENT_V:
    k = N.key4(r.get('Member'), r.get('Bill'), r.get('Congress'), r.get('Role'))
    matrix_keys[k] += 1
    mk_src[k].add('sentinel-verified')
manual_keys = {N.key4(r.get('Member'), r.get('Bill'), r.get('Congress'), r.get('Role')) for r in MAN}
only_matrix = set(matrix_keys) - set(desk_keys) - manual_keys
W('=' * 102)
W('N5 / D3  THE 258 ARCHIVE-ONLY KEYS, FROM THE DESK SIDE   (reproduced: %d)' % len(only_matrix))
W('=' * 102)

# workbook-side indexes
wb_triple = collections.defaultdict(set)
wb_bill = set()
wb_member = collections.Counter()
wb_member_bill = collections.defaultdict(set)
for r in WBR:
    m = str(r.get('Member') or '').strip()
    b = (N.norm_bill(r.get('Name')), N.cong(r.get('Congress')))
    wb_triple[(m,) + b].add(N.role(r.get('Role')))
    wb_bill.add(b)
    wb_member[m] += 1
    wb_member_bill[m].add(b)

# routing dispositions per triple, plus which frame bucket
SRC = [(0, len(ARC), 'selected-archive'), (len(ARC), len(ARC) + len(SENT_V), 'sentinel-verified'),
       (len(ARC) + len(SENT_V), 10 ** 9, 'manual-csv')]


def bucket(sr):
    i = int(sr) - 2
    for lo, hi, nm in SRC:
        if lo <= i < hi:
            return nm
    return 'UNKNOWN'


ra_triple = collections.defaultdict(list)
for row in RA['rows']:
    mm = row.get('member') or RES.resolve(row.get('member_source'))
    if not mm:
        continue
    ra_triple[(mm, N.norm_bill(row.get('bill')), N.cong(row.get('congress')))].append(
        {'d': row['disposition'], 'role': row.get('effective_role') or N.role(row.get('source_role')),
         'src': bucket(row['source_row']), 'cat': row.get('effective_category'),
         'title': row.get('title'), 'status': row.get('tracker_status'),
         'sign': row.get('sign'), 'srole': N.role(row.get('source_role'))})

sent_triple = collections.defaultdict(list)
for r in SENT_ALL:
    m = RES.resolve(r.get('Member')) if r.get('Member') else None
    if m:
        sent_triple[(m, N.norm_bill(r.get('Bill')), N.cong(r.get('Congress')))].append(r)
old_triple = collections.defaultdict(set)
for r in OLD:
    m = RES.resolve(r.get('Member')) if r.get('Member') else None
    if m:
        old_triple[(m, N.norm_bill(r.get('Name')), N.cong(r.get('Congress')))].add(N.role(r.get('Role')))

# shipped desk index
disp = collections.defaultdict(dict)
for nm, rows in DESK.items():
    for b in rows:
        disp[nm][(N.norm_bill(b['bill']), N.cong(b['congress']))] = b


def live_date(member, bill, congress):
    rk = N.repo_key(bill, congress)
    b = LIVE.get(rk or '')
    if not b:
        return None, False
    bio = BIOS.get(member)
    for f in ('sponsor', 'original_cosponsors', 'cosponsors'):
        v = b.get(f)
        for p in ([v] if isinstance(v, dict) else (v or [])):
            if isinstance(p, dict) and p.get('bioguide') and (
                    p['bioguide'] == bio or bio_to_name.get(p['bioguide']) == member):
                return (p.get('date') or ''), True
    return None, True


# ------------------------------------------------------------------- D3
d3 = collections.Counter()
d3rows = []
for k in sorted(only_matrix):
    raw, bill, c3, rolev = k
    mm = RES.resolve(raw) or raw
    t = (mm, bill, c3)
    wbroles = wb_triple.get((raw, bill, c3)) or wb_triple.get((mm, bill, c3)) or set()
    bill_in_wb = (bill, c3) in wb_bill
    member_in_wb = (raw in wb_member) or (mm in wb_member)
    src = sorted(mk_src[k])
    jd, cached = live_date(mm, bill, c3)
    shownrow = disp.get(mm, {}).get((bill, c3))
    if wbroles:
        cls = 'D3-1 sheets carry the triple under a DIFFERENT role: %s' % sorted(wbroles)
    elif 'sentinel-verified' in src:
        cls = 'D3-2 came from the Sentinel ledger (collector lane), never appended to the sheets'
    elif not bill_in_wb:
        cls = 'D3-4 a bill the role sheets never had'
    elif not member_in_wb:
        cls = 'D3-5 a member the role sheets never had'
    else:
        cls = 'D3-3 sheets have the bill and the member but never this membership row'
    d3[cls] += 1
    d3rows.append({'key': k, 'member': mm, 'class': cls, 'wb_roles': sorted(wbroles),
                   'bill_in_wb': bill_in_wb, 'member_in_wb': member_in_wb, 'frame_src': src,
                   'live_join': jd, 'bill_cached': cached,
                   'displayed_today': bool(shownrow),
                   'displayed_role': (shownrow or {}).get('role'),
                   'routing': dict(collections.Counter(x['d'] for x in ra_triple.get(t, [])))})
W('  by role: %s   by Congress: %s' % (
    dict(collections.Counter(k[3] for k in only_matrix)),
    dict(sorted(collections.Counter(k[2] for k in only_matrix).items()))))
W('  frame source of the 258: %s' % dict(collections.Counter(
    tuple(sorted(mk_src[k])) for k in only_matrix)))
for c, n in d3.most_common():
    W('  %-4d  %s' % (n, c))
W('  ALREADY DISPLAYED on the desk today anyway (via manual csv / primacy sidecars / collector merge): %d / %d'
  % (sum(1 for r in d3rows if r['displayed_today']), len(d3rows)))
W('  displayed role vs archive role: %s' % dict(collections.Counter(
    (r['key'][3], r['displayed_role']) for r in d3rows if r['displayed_today'])))
W('  live BILLSTATUS join date present: %d ; latest=%s ; joined after 2026-08-25=%d'
  % (sum(1 for r in d3rows if r['live_join']),
     max((r['live_join'] for r in d3rows if r['live_join']), default='-'),
     sum(1 for r in d3rows if r['live_join'] and r['live_join'] > '2026-08-25')))
W('  top bills: %s' % collections.Counter(k[1] for k in only_matrix).most_common(10))
W('  examples (up to 12):')
for r in d3rows[:12]:
    W('     %-22s %-13s C%-4s arc_role=%-19s wb_roles=%-22s shown=%-5s src=%-20s live=%s'
      % (r['member'][:22], r['key'][1], r['key'][2], r['key'][3], str(r['wb_roles'])[:22],
         r['displayed_today'], ','.join(r['frame_src'])[:20], r['live_join']))
W('  per-class examples:')
for c in d3:
    ex = [r for r in d3rows if r['class'] == c][:6]
    W('   -- %s' % c)
    for r in ex:
        W('        %-22s %-13s C%-4s arc_role=%-19s shown=%-5s routing=%s'
          % (r['member'][:22], r['key'][1], r['key'][2], r['key'][3], r['displayed_today'],
             str(r['routing'])[:50]))

# =================================================================== D4
W('\n' + '=' * 102)
W('N5 / D4  IF THE DESK READ THE ROUTING AUDIT\'S SELECTED ROWS INSTEAD')
W('=' * 102)
# desk TODAY = shipped bundle, one row per (member, bill, congress)
today = {}
for nm, rows in DESK.items():
    for b in rows:
        today[(nm, N.norm_bill(b['bill']), N.cong(b['congress']))] = b
# routing SELECTED, collapsed the same way (one row per member/bill/congress, strongest role)
sel = {}
for row in RA['rows']:
    if row['disposition'] != 'selected':
        continue
    mm = row.get('member')
    if not mm:
        continue
    t = (mm, N.norm_bill(row.get('bill')), N.cong(row.get('congress')))
    g = sel.setdefault(t, {'roles': set(), 'cats': set(), 'title': row.get('title'),
                           'status': row.get('tracker_status'), 'signs': set(), 'src': set()})
    g['roles'].add(row.get('effective_role') or '')
    if row.get('effective_category'):
        g['cats'].add(row['effective_category'])
    g['signs'].add(row.get('sign'))
    g['src'].add(bucket(row['source_row']))
W('  desk TODAY (shipped bundle)          : %d rows across %d members'
  % (len(today), len({k[0] for k in today})))
W('  routing-audit SELECTED, collapsed    : %d rows across %d members  (8123 selected rows before the (bill,congress) collapse)'
  % (len(sel), len({k[0] for k in sel})))
lost = sorted(set(today) - set(sel))
gained = sorted(set(sel) - set(today))
W('  ROWS LOST  (desk shows, routing-selected does not) = %d' % len(lost))
W('  ROWS GAINED(routing-selected has, desk does not)   = %d' % len(gained))
W('  NET = %+d' % (len(gained) - len(lost)))
W('  lost by role displayed today: %s' % dict(collections.Counter(today[k]['role'] for k in lost)))
W('  lost by Congress: %s' % dict(sorted(collections.Counter(k[2] for k in lost).items())))
W('  gained by routing role: %s' % dict(collections.Counter(
    F.preferred_role(sel[k]['roles']) for k in gained)))
W('  gained by Congress: %s' % dict(sorted(collections.Counter(k[2] for k in gained).items())))

per = collections.defaultdict(lambda: [0, 0])
for k in lost:
    per[k[0]][0] += 1
for k in gained:
    per[k[0]][1] += 1
changed = [m for m, (l, g) in per.items() if l or g]
W('\n  members whose desk bill list would CHANGE AT ALL = %d / %d (%.1f%%)'
  % (len(changed), len(DESK), 100.0 * len(changed) / len(DESK)))
W('  members who would END UP WITH ZERO bills but have >=1 today = %d'
  % sum(1 for m in DESK if DESK[m] and not any(k[0] == m for k in sel)))
W('  TOP 20 members by |net change| (today -> after):')
rows20 = sorted(per.items(), key=lambda x: (-(abs(x[1][1] - x[1][0])), -(x[1][0] + x[1][1]), x[0]))[:20]
W('     %-26s %6s %6s %7s %7s %7s' % ('member', 'today', 'after', 'lost', 'gained', 'net'))
for m, (l, g) in rows20:
    t0 = len(DESK.get(m) or [])
    W('     %-26s %6d %6d %7d %7d %+7d' % (m[:26], t0, t0 - l + g, l, g, g - l))
W('  TOP 20 members by LOST count:')
for m, (l, g) in sorted(per.items(), key=lambda x: (-x[1][0], x[0]))[:20]:
    W('     %-26s today=%-5d lost=%-5d gained=%-4d' % (m[:26], len(DESK.get(m) or []), l, g))

# --------------------------------------------- class of every LOST row
W('\n  CLASS OF EVERY LOST ROW (same taxonomy as D2):')
SIDE = {}
for rel, tag in (('data/members/primacy_act_memberships.ndjson', 'primacy_act'),
                 ('data/members/registry_anchor_memberships.ndjson', 'registry_anchor'),
                 ('data/members/bank_anchor_memberships.ndjson', 'bank_anchor'),
                 ('data/members/collector_roster_updates.ndjson', 'collector_roster'),
                 ('data/members/sentinel_verified_membership_history.ndjson', 'sentinel_history')):
    for line in open(N.P(*rel.split('/')), encoding='utf-8'):
        if not line.strip():
            continue
        r = json.loads(line)
        m = RES.resolve(r.get('member')) or r.get('member')
        SIDE.setdefault((m, N.norm_bill(r.get('bill')), N.cong(r.get('congress'))), set()).add(tag)
for r in MAN:
    m = RES.resolve(r.get('Member')) or r.get('Member')
    SIDE.setdefault((m, N.norm_bill(r.get('Bill')), N.cong(r.get('Congress'))), set()).add('manual_csv')
SA = json.load(open(N.P('data', 'legislation', 'sentinel_admissions.json'), encoding='utf-8'))
for r in (SA.get('memberships') or []):
    m = RES.resolve(r.get('member')) or r.get('member')
    SIDE.setdefault((m, N.norm_bill(r.get('bill')), N.cong(r.get('congress'))), set()).add('sentinel_admissions')
wbt = set()
for r in WBR:
    wbt.add((RES.resolve(r.get('Member')) or str(r.get('Member') or '').strip(),
             N.norm_bill(r.get('Name')), N.cong(r.get('Congress'))))

lost_cls = collections.Counter()
lost_disp = collections.Counter()
lost_src = collections.Counter()
lost_detail = []
for k in lost:
    ra = ra_triple.get(k, [])
    disps = [x['d'] for x in ra]
    if ra:
        cls = 'a  routing holds the triple, non-selected only'
    elif sent_triple.get(k):
        cls = 'c  absent from routing frame, in Sentinel Bill Ledger'
    elif old_triple.get(k):
        cls = 'd  absent from routing+sentinel, in the OLD archive only'
    else:
        cls = 'e  found nowhere else'
    lost_cls[cls] += 1
    for d in set(disps):
        lost_disp[d] += 1
    srcs = set(SIDE.get(k, set()))
    if k in wbt:
        srcs.add('workbook_role_sheets')
    lost_src[tuple(sorted(srcs)) or ('UNATTRIBUTED',)] += 1
    lost_detail.append({'key': k, 'class': cls, 'role_today': today[k]['role'],
                        'dispositions': dict(collections.Counter(disps)),
                        'desk_sources': sorted(srcs)})
for c, n in sorted(lost_cls.items()):
    W('     %-58s n=%d' % (c, n))
W('     disposition strings carried by class-(a) losses:')
for d, n in lost_disp.most_common():
    W('        %-54s triples=%d' % (repr(d), n))
W('     DESK SOURCE that supplied each lost row (why the routing frame never saw it):')
for s, n in lost_src.most_common():
    W('        %-70s n=%d' % (','.join(s), n))
W('     class (c)/(d)/(e) losses in total = %d ; class (a) = %d'
  % (sum(n for c, n in lost_cls.items() if not c.startswith('a')),
     sum(n for c, n in lost_cls.items() if c.startswith('a'))))
W('     CROSS-TAB  class x desk source:')
for kk, n in sorted(collections.Counter(
        (r['class'][0], ','.join(r['desk_sources']) or 'UNATTRIBUTED') for r in lost_detail).items()):
    W('        class %s  x  %-58s n=%d' % (kk[0], kk[1], n))
W('     class-(a) losses split by WHAT the routing audit says (exclusive buckets):')
wd = 'official-membership-withdrawn-or-role-superseded'
a_rows = [r for r in lost_detail if r['class'].startswith('a')]
buckets = collections.Counter()
for r in a_rows:
    ds = set(r['dispositions'])
    if ds == {wd}:
        buckets['withdrawn/role-superseded ONLY (adjudicated removal)'] += 1
    elif wd in ds:
        buckets['withdrawn/role-superseded + a neutral disposition'] += 1
    elif ds & {'neutral-registry', 'neutral-override', 'neutral-manual',
               'neutral-official-evidence'}:
        buckets['neutral-* ONLY (real membership the producer scores 0)'] += 1
    else:
        buckets['other non-selected: %s' % sorted(ds)] += 1
for b, n in buckets.most_common():
    W('        %-62s n=%d' % (b, n))
W('     ALL %d class-(a) losses, verbatim:' % len(a_rows))
for r in sorted(a_rows, key=lambda x: x['key']):
    W('        %-24s %-13s C%-4s role_today=%-11s disp=%s'
      % (r['key'][0][:24], r['key'][1], r['key'][2], r['role_today'],
         sorted(r['dispositions'])))
W('     ALL non-(a) losses that are NOT from a primacy/anchor sidecar:')
for r in sorted([x for x in lost_detail if not x['class'].startswith('a')
                 and not ({'primacy_act', 'registry_anchor', 'bank_anchor'} & set(x['desk_sources']))],
                key=lambda x: x['key']):
    W('        %-24s %-13s C%-4s role_today=%-11s src=%s'
      % (r['key'][0][:24], r['key'][1], r['key'][2], r['role_today'], r['desk_sources']))
W('     lost rows whose bill number is an AMENDMENT (H.Amdt./S.Amdt.): %d of %d'
  % (sum(1 for r in lost_detail if 'AMDT' in r['key'][1]), len(lost_detail)))
W('     examples of NON-(a) losses (up to 20):')
for r in [x for x in lost_detail if not x['class'].startswith('a')][:20]:
    W('        %-24s %-13s C%-4s role=%-11s %-42s src=%s'
      % (r['key'][0][:24], r['key'][1], r['key'][2], r['role_today'], r['class'][:42],
         ','.join(r['desk_sources'])))
W('     examples of class-(a) losses (up to 15):')
for r in [x for x in lost_detail if x['class'].startswith('a')][:15]:
    W('        %-24s %-13s C%-4s role=%-11s disp=%-52s src=%s'
      % (r['key'][0][:24], r['key'][1], r['key'][2], r['role_today'],
         str(r['dispositions'])[:52], ','.join(r['desk_sources'])))

W('\n  WHY EACH GAINED ROW IS ABSENT FROM THE DESK TODAY:')
g_reason = collections.Counter()
for k in gained:
    inwb = k in wbt
    g_reason[('in_workbook_sheets=%s' % inwb, 'frame_src=%s' % ','.join(sorted(
        sel[k]['src'])), 'desk_sidecar=%s' % (','.join(sorted(SIDE.get(k, set()))) or 'none'))] += 1
for kk, n in g_reason.most_common(15):
    W('     %-92s n=%d' % (' | '.join(kk), n))
W('     examples (up to 20):')
for k in gained[:20]:
    W('        %-24s %-13s C%-4s routing_role=%-18s cats=%s'
      % (k[0][:24], k[1], k[2], F.preferred_role(sel[k]['roles']), sorted(sel[k]['cats'])[:2]))

# =================================================================== D5
W('\n' + '=' * 102)
W('N5 / D5  FIELD COVERAGE: WHAT THE DESK RENDERS vs WHAT THE ROUTING AUDIT CARRIES')
W('=' * 102)
W('  desk row fields consumed by the page (make_member_desk_00.tpl:1778-1789 legBody,')
W('  :2058-2078 billCard): role, bill, congress, title, areas, sponsor, ncos, summary, url, action')
fieldfreq = collections.Counter()
for row in RA['rows']:
    fieldfreq.update(row.keys())
W('  routing-audit row fields present at all: %s' % sorted(fieldfreq))
selrows = [r for r in RA['rows'] if r['disposition'] == 'selected']
W('  over the %d SELECTED rows:' % len(selrows))
MAPPED = [('bill', 'bill'), ('congress', 'congress'), ('title', 'title'),
          ('areas', 'effective_category'), ('role', 'effective_role'),
          ('action (latest action)', 'tracker_status'), ('direction (NOT shown today)', 'sign')]
for desk_f, ra_f in MAPPED:
    nonempty = sum(1 for r in selrows if str(r.get(ra_f) or '').strip() != '')
    W('     desk %-28s <- routing %-22s non-empty on %d/%d (%.1f%%)'
      % (desk_f, ra_f, nonempty, len(selrows), 100.0 * nonempty / len(selrows)))
MISSING = ['sponsor', 'ncos (CosponsorCount)', 'summary (bill_summary)', 'url (DetailLink)']
W('  FIELDS THE ROUTING AUDIT DOES NOT CARRY AT ALL (zero rows have them):')
for f in MISSING:
    W('     %s' % f)
# is the audit's title truncated vs the archive's?
arc_title = {}
for r in ARC:
    arc_title[(N.norm_bill(r.get('Name')), N.cong(r.get('Congress')))] = str(r.get('Title') or '')
trunc = same = absent = 0
for r in selrows:
    t = (N.norm_bill(r.get('bill')), N.cong(r.get('congress')))
    a = arc_title.get(t)
    if a is None:
        absent += 1
    elif str(r.get('title') or '') == a:
        same += 1
    else:
        trunc += 1
W('  routing title vs archive Title: identical=%d differs=%d archive-row-absent=%d' % (same, trunc, absent))
W('\n  JOIN COVERAGE for the 4 missing fields over the routing-SELECTED bill universe:')
bills_needed = {(k[1], k[2]) for k in sel}
W('     distinct (bill, congress) the switched desk would render = %d' % len(bills_needed))
srcs = {}
srcs['bill_repository_live.json (title/summary/url/sponsor/cosponsor_count/latest_action)'] = {
    (N.norm_bill(b.get('display') or b.get('title')), N.cong(b.get('congress'))) for b in LIVE.values()}
srcs['bill_repository_live.json BY repo key'] = {N.repo_key(k1, k2) for (k1, k2) in bills_needed}
sent_bill_rows = {(N.norm_bill(r.get('Bill')), N.cong(r.get('Congress'))): r for r in SENT_ALL}
srcs['Sentinel Bill Ledger (Title/Sponsor/Cosponsor Count/Detail Link/Summary)'] = set(sent_bill_rows)
srcs['selected archive All Bills (Sponsor/CosponsorCount/DetailLink/bill_summary)'] = set(arc_title)
srcs['manual_bill_evidence.csv'] = {(N.norm_bill(r.get('Bill')), N.cong(r.get('Congress'))) for r in MAN}
live_by_repo = {b['key'] for b in LIVE.values() if b.get('key')}
hit = sum(1 for (b, c) in bills_needed if N.repo_key(b, c) in live_by_repo)
W('     %-78s covers %d/%d (%.1f%%)' % ('bill_repository_live.json (by <congress>:<type>:<num> key)',
                                        hit, len(bills_needed), 100.0 * hit / len(bills_needed)))
for name in ('Sentinel Bill Ledger (Title/Sponsor/Cosponsor Count/Detail Link/Summary)',
             'selected archive All Bills (Sponsor/CosponsorCount/DetailLink/bill_summary)',
             'manual_bill_evidence.csv'):
    s = srcs[name]
    n = len(bills_needed & s)
    W('     %-78s covers %d/%d (%.1f%%)' % (name, n, len(bills_needed), 100.0 * n / len(bills_needed)))
union = (bills_needed & srcs['selected archive All Bills (Sponsor/CosponsorCount/DetailLink/bill_summary)']) | \
        (bills_needed & srcs['Sentinel Bill Ledger (Title/Sponsor/Cosponsor Count/Detail Link/Summary)']) | \
        {(b, c) for (b, c) in bills_needed if N.repo_key(b, c) in live_by_repo} | \
        (bills_needed & srcs['manual_bill_evidence.csv'])
W('     UNION of those four                                                            covers %d/%d (%.1f%%)'
  % (len(union), len(bills_needed), 100.0 * len(union) / len(bills_needed)))
missing_all = sorted(bills_needed - union)
W('     (bill, congress) with NO join source for sponsor/ncos/summary/url = %d %s'
  % (len(missing_all), missing_all[:12]))
# non-empty rate of those fields in the archive itself
ne = collections.Counter()
for r in ARC:
    for f in ('Sponsor', 'CosponsorCount', 'DetailLink', 'bill_summary'):
        if str(r.get(f) or '').strip() not in ('', 'None', 'nan'):
            ne[f] += 1
W('     archive All Bills non-empty rate: %s of %d rows' % (dict(ne), len(ARC)))

with open(os.path.join(N.SCRATCH, 'd3_d4_state.json'), 'w', encoding='utf-8') as fh:
    json.dump({'d3': d3rows, 'lost': lost_detail,
               'gained': [{'key': k, 'role': F.preferred_role(sel[k]['roles']),
                           'cats': sorted(sel[k]['cats'])} for k in gained],
               'per_member': {m: v for m, v in per.items()}}, fh, ensure_ascii=False, indent=1)
W('\n  [state] %s' % os.path.join(N.SCRATCH, 'd3_d4_state.json'))
W('DONE')
