# -*- coding: utf-8 -*-
"""N15 W1/W2/W4 (READ-ONLY).  Nothing under fec/ is imported (import == execution).

W1  re-derive, from TODAY's artifacts, the (member, bill, Congress) triples whose
    routing-audit disposition set includes 'official-membership-withdrawn-or-role-superseded'
    and that are STILL displayed in the desk's Bills section.
W2  for each, the OFFICIAL record out of data/legislation/official_membership_movements.json
    (withdrawn flag + date, or the superseding role + date).
W4  mechanical verdict per triple.

Rule transcriptions reused from lane F1 (f1_lib.py, byte-checked against LIVE fec/bill_rules.py)
and lane N5 (n5_lib.py).  Read as text only:
  LIVE\fec\legislation\official_membership_movements.py                (apply_to_desk / eligible)
  LIVE\fec\legislation\build_archive_legislative.py:202-208            (emits the disposition)
  LIVE\fec\legislation\congress_bill_repository.py:141-168             (parse_bill_identity)
"""
import os, sys, json, hashlib, collections

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
os.makedirs(SCRATCH, exist_ok=True)
OUT = []
def W(s=''):
    OUT.append(s)
    print(s)

DISP = 'official-membership-withdrawn-or-role-superseded'


def stamp(path):
    st = os.stat(path)
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    import datetime
    return '%s  %d bytes  mtime=%s  sha256=%s' % (
        os.path.basename(path), st.st_size,
        datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        h.hexdigest())


W('=' * 102)
W('N15 / W1  THE TRIPLES, RE-DERIVED FROM TODAY\'S ARTIFACTS')
W('=' * 102)
for rel in ('member_desk_bundle.json', 'legislation_routing_audit.json',
            'bill_repository_live.json',
            os.path.join('data', 'legislation', 'official_membership_movements.json')):
    W('  input: %s' % stamp(N.P(*rel.split(os.sep))))

# ------------------------------------------------------------------ desk ledger (SHIPPED)
BUNDLE = N.P('member_desk_bundle.json')
with open(BUNDLE, 'rb') as fh:
    D = json.loads(fh.read().decode('utf-8'))
DESK = {}
for m in D.get('members') or []:
    DESK[m.get('name')] = [{'bill': r.get('bill') or '', 'congress': str(r.get('congress') or ''),
                            'role': r.get('role') or '', 'areas': r.get('areas') or [],
                            'title': (r.get('title') or '')[:70]}
                           for r in (m.get('bills') or [])]
MA = D.get('media_audit') or {}
W('  desk bundle: %d members, %d displayed bill rows; media_audit[bill_withdrawn_rows_removed]=%s'
  % (len(DESK), sum(len(v) for v in DESK.values()), MA.get('bill_withdrawn_rows_removed')))
del D

# displayed index: (member, norm_bill, congress) -> displayed row(s)
shown = collections.defaultdict(list)
for m, rows in DESK.items():
    for r in rows:
        shown[(m, N.norm_bill(r['bill']), N.cong(r['congress']))].append(r)

# ------------------------------------------------------------------ routing audit
RA = N.routing_audit()
RES, _names, _bios = N.resolver()
ra_triple = collections.defaultdict(list)
noname = collections.Counter()
for row in RA['rows']:
    mm = row.get('member') or RES.resolve(row.get('member_source'))
    if not mm:
        noname[row.get('disposition')] += 1
        continue
    ra_triple[(mm, N.norm_bill(row.get('bill')), N.cong(row.get('congress')))].append(row)
W('  routing audit: %d rows; declared source_rows=%s selected_events=%s; indexed triples=%d; '
  'rows with no resolvable member=%d %s'
  % (len(RA['rows']), RA['source_rows'], RA['selected_events'], len(ra_triple),
     sum(noname.values()), dict(noname)))
W('  routing disposition histogram: %s'
  % json.dumps(RA['summary']['dispositions'], sort_keys=True))

# ------------------------------------------------------------------ official membership movements
OMDOC = json.load(open(N.P('data', 'legislation', 'official_membership_movements.json'),
                       encoding='utf-8'))
FACTS = OMDOC.get('facts') or []
by_bio = {(r['repository_key'], r['bioguide']): r for r in FACTS}
by_name = {(r['repository_key'], r['member']): r for r in FACTS}
W('  official_membership_movements: schema=%s status=%s checked_at=%s facts=%d additions=%d '
  'unresolved=%d  repository_sha256=%s...'
  % (OMDOC.get('schema'), OMDOC.get('status'), OMDOC.get('checked_at'), len(FACTS),
     len(OMDOC.get('additions') or []), len(OMDOC.get('unresolved') or []),
     str(OMDOC.get('repository_sha256'))[:16]))
_live_sha = hashlib.sha256(open(N.P('bill_repository_live.json'), 'rb').read()).hexdigest()
W('  OM.load gate: repository_sha256 == sha256(bill_repository_live.json)? %s'
  % (OMDOC.get('repository_sha256') == _live_sha))
W('  facts withdrawn=True: %d ; facts by role: %s'
  % (sum(1 for r in FACTS if r.get('withdrawn')),
     json.dumps(dict(collections.Counter(r['role'] for r in FACTS)), sort_keys=True)))

# ------------------------------------------------------------------ W1 selection
cand = {}
for k, rows in ra_triple.items():
    disps = set(r.get('disposition') for r in rows)
    if DISP not in disps:
        continue
    cand[k] = rows
W('\n  triples whose routing dispositions include the string        = %d' % len(cand))
disp_shown = {k: v for k, v in cand.items() if k in shown}
W('  ... of which STILL DISPLAYED on the desk today               = %d' % len(disp_shown))
noselect = {k: v for k, v in disp_shown.items()
            if 'selected' not in set(r.get('disposition') for r in v)}
W('  ... and with NO selected routing row (N5 class-(a) definition) = %d   <== W1 HEADLINE'
  % len(noselect))
W('  ... displayed AND carrying a selected routing row too         = %d' % (len(disp_shown) - len(noselect)))

detail = []
for k in sorted(noselect, key=lambda x: (x[0], x[1], x[2])):
    member, nb, cg = k
    rows = noselect[k]
    dshown = shown[k]
    roles_shown = sorted({F.canonical_role(r['role']) for r in dshown})
    rk = N.repo_key(nb, cg)
    fact = by_name.get((rk, member)) if rk else None
    fact_bio = None
    if rk:
        bio = _bios.get(member)
        fact_bio = by_bio.get((rk, bio))
    src_roles = sorted({'%s/%s' % (r.get('source_section') or '-', F.canonical_role(r.get('source_role')))
                        for r in rows if r.get('disposition') == DISP})
    detail.append({
        'member': member, 'bill': dshown[0]['bill'], 'norm_bill': nb, 'congress': cg,
        'repository_key': rk,
        'dispositions': dict(collections.Counter(r.get('disposition') for r in rows)),
        'routing_rows': [{'disposition': r.get('disposition'),
                          'source_role': F.canonical_role(r.get('source_role')),
                          'effective_role': r.get('effective_role'),
                          'source_section': r.get('source_section'),
                          'source_row': r.get('source_row'),
                          'sign': r.get('sign'),
                          'contribution': r.get('contribution'),
                          'reason': r.get('reason'), 'override_reason': r.get('override_reason')}
                         for r in rows],
        'withdrawn_row_source_roles': src_roles,
        'desk_roles': roles_shown,
        'desk_role_raw': sorted({r['role'] for r in dshown}),
        'desk_rows': len(dshown),
        'desk_title': dshown[0]['title'],
        'desk_areas': sorted({a for r in dshown for a in r['areas']}),
        'fact_by_name': fact, 'fact_by_bioguide': fact_bio,
        'bioguide': _bios.get(member),
    })

W('\n  FULL LIST (W1) -- member / bill / Congress / routing dispositions / role the desk displays')
W('  %-26s %-13s %-5s %-10s %s' % ('member', 'bill', 'cong', 'desk role', 'routing dispositions'))
for d in detail:
    W('  %-26s %-13s %-5s %-10s %s'
      % (d['member'][:26], d['bill'][:13], d['congress'], ','.join(d['desk_roles']),
         '; '.join('%s x%d' % (k, v) for k, v in sorted(d['dispositions'].items()))))

W('\n  displayed-role histogram over the list: %s'
  % json.dumps(dict(collections.Counter(','.join(d['desk_roles']) for d in detail)), sort_keys=True))
W('  Congress histogram: %s'
  % json.dumps(dict(collections.Counter(d['congress'] for d in detail)), sort_keys=True))
W('  role carried by the ROUTING ROW that got the disposition (section/role): %s'
  % json.dumps(dict(collections.Counter(x for d in detail for x in d['withdrawn_row_source_roles'])),
               sort_keys=True))

# ------------------------------------------------------------------ W2 per-triple official record
W('')
W('=' * 102)
W('N15 / W2  THE OFFICIAL RECORD FOR EACH TRIPLE')
W('=' * 102)
W('  official_membership_movements.json fact fields: %s'
  % sorted(FACTS[0].keys()) if FACTS else '  (no facts)')
W('  %-26s %-11s %-9s %-7s %-11s %-11s %-11s'
  % ('member', 'repo_key', 'fact?', 'withdr', 'withdr_date', 'official_role', 'join_date'))
for d in detail:
    f = d['fact_by_name'] or d['fact_by_bioguide']
    if not f:
        W('  %-26s %-11s %-9s %s'
          % (d['member'][:26], d['repository_key'], 'ABSENT',
             '(no official record for this repository_key + member)'))
        continue
    W('  %-26s %-11s %-9s %-7s %-11s %-11s %-11s'
      % (d['member'][:26], d['repository_key'],
         'name' if d['fact_by_name'] else 'bioguide-only',
         str(bool(f.get('withdrawn'))), f.get('withdrawn_date') or '-',
         F.canonical_role(f.get('role')), f.get('join_date') or '-'))
W('  facts found by (repository_key, member NAME) = %d / %d'
  % (sum(1 for d in detail if d['fact_by_name']), len(detail)))
W('  facts found by (repository_key, bioguide)    = %d / %d'
  % (sum(1 for d in detail if d['fact_by_bioguide']), len(detail)))
W('  name-key and bioguide-key disagree on:       %d'
  % sum(1 for d in detail
        if (d['fact_by_name'] or {}).get('bioguide') != (d['fact_by_bioguide'] or {}).get('bioguide')))
_inrepo = json.load(open(N.P('bill_repository_live.json'), encoding='utf-8'))['bills']
W('  repository_key present in bill_repository_live.json: %d / %d'
  % (sum(1 for d in detail if d['repository_key'] in _inrepo), len(detail)))

# ------------------------------------------------------------------ W4 verdicts
W('')
W('=' * 102)
W('N15 / W4  MECHANICAL VERDICT PER TRIPLE')
W('=' * 102)
verd = collections.Counter()
for d in detail:
    f = d['fact_by_name'] or d['fact_by_bioguide']
    desk = set(d['desk_roles'])
    if f is None:
        v = 'UNCLEAR: no official record carries this repository_key + member'
    elif f.get('withdrawn'):
        v = 'DESK-SHOWS-WITHDRAWN'
    else:
        off = F.canonical_role(f.get('role'))
        if desk == {off}:
            v = 'DESK-CORRECT'
        elif off in desk:
            v = 'UNCLEAR: desk shows the official role AND another role (%s)' % ','.join(sorted(desk))
        else:
            v = 'DESK-STALE-ROLE'
    d['verdict'] = v
    verd[v.split(':')[0]] += 1
    d['official_role'] = F.canonical_role((f or {}).get('role')) if f else None
for v, n in sorted(verd.items(), key=lambda x: -x[1]):
    W('  %-24s n=%d' % (v, n))
W('')
W('  %-26s %-13s %-5s %-12s %-12s %-6s %s'
  % ('member', 'bill', 'cong', 'desk role', 'official role', 'withdr', 'verdict'))
for d in sorted(detail, key=lambda x: (x['verdict'], x['member'])):
    f = d['fact_by_name'] or d['fact_by_bioguide']
    W('  %-26s %-13s %-5s %-12s %-12s %-6s %s'
      % (d['member'][:26], d['bill'][:13], d['congress'], ','.join(d['desk_roles']),
         d['official_role'] or '-', str(bool((f or {}).get('withdrawn'))), d['verdict']))

# ------------------------------------------------------------------ the displayed-with-a-selected-row remainder
rest = {k: v for k, v in disp_shown.items() if k not in noselect}
W('\n  FOR CONTEXT -- displayed triples that DO carry a selected routing row = %d' % len(rest))
rest_detail = []
for k in sorted(rest, key=lambda x: (x[0], x[1], x[2])):
    member, nb, cg = k
    rk = N.repo_key(nb, cg)
    f = by_name.get((rk, member)) if rk else None
    roles = sorted({F.canonical_role(r['role']) for r in shown[k]})
    rest_detail.append({'member': member, 'bill': shown[k][0]['bill'], 'congress': cg,
                        'repository_key': rk, 'desk_roles': roles,
                        'official_role': F.canonical_role(f.get('role')) if f else None,
                        'withdrawn': bool((f or {}).get('withdrawn')) if f else None,
                        'dispositions': dict(collections.Counter(r.get('disposition') for r in cand[k]))})
W('  %-26s %-13s %-5s %-12s %-12s %-6s %s'
  % ('member', 'bill', 'cong', 'desk role', 'official role', 'withdr', 'dispositions'))
for d in rest_detail:
    W('  %-26s %-13s %-5s %-12s %-12s %-6s %s'
      % (d['member'][:26], d['bill'][:13], d['congress'], ','.join(d['desk_roles']),
         d['official_role'] or 'NO-FACT', str(d['withdrawn']),
         ','.join(sorted(d['dispositions']))))

state = os.path.join(SCRATCH, 'w1_state.json')
with open(state, 'w', encoding='utf-8') as fh:
    json.dump({'detail': detail, 'rest': rest_detail,
               'counts': {'with_disposition': len(cand), 'displayed': len(disp_shown),
                          'displayed_noselect': len(noselect)}},
              fh, ensure_ascii=False, indent=1)
W('\n  [state] %s' % state)

dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'n15_w1_w2_w4.txt')
with open(dest, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(OUT) + '\nDONE\n')
print('DONE -> %s' % dest)
