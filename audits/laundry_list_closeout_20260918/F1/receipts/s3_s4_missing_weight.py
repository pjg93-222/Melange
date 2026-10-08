# -*- coding: utf-8 -*-
"""Lane F1 / S3 + S4 : missing signed sponsor weight, and the 20260624 regression check.

S3  For the DEFECT class (sponsor is a current roster member, no sponsor-role row exists for the
    scoring cell): is the cell SELECTED into archive_leg.json, and what signed weight is missing?

    The producer's own rules, quoted from the LIVE copies:
      sponsor role weight                LIVE fec\\bill_rules.py:211-219   -> 3.0
      decay                              LIVE fec\\bill_rules.py:190-198   -> 0.8 ** (119 - Congress)
      contribution = sign * w * dw       LIVE fec\\legislation\\build_archive_legislative.py:248
      one event per (member, bill, Congress, category), strongest role wins
                                         LIVE ...build_archive_legislative.py:251, 259-268
      leg[member][category] += contribution
                                         LIVE ...build_archive_legislative.py:269-270

    So the weight a missing sponsor row costs archive_leg.json is
        sign * (3.0 - role_weight(role the member is CURRENTLY credited with)) * dw
    which is the full sign*3.0*dw when the member has no row in that cell at all.
    'sign' and 'dw' are not re-derived here: they are read from the producer's own
    legislation_routing_audit.json rows for the same bill / Congress / effective category.

S4  Did congress_bills_archive_20260624_115822.xlsx carry sponsor rows for those bills?

Writes s3_s4_missing_weight.txt and s3_state.json.
"""
import collections, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f1_lib as L

HERE = os.path.dirname(os.path.abspath(__file__))
P = print


def bar(t):
    P('\n' + '=' * 100)
    P(t)
    P('=' * 100)


ARCH = L.xl(L.SEL_ARCHIVE, 'All Bills')
OLD = L.xl(L.OLD_ARCHIVE, 'All Bills')
NAMES, BIOS = L.roster()
RES = L.Resolver(NAMES, BIOS)
ROSTER_NORM = {L.normalize_name(n): n for n in NAMES}
RA = L.jload('legislation_routing_audit.json')
LEG = L.jload('archive_leg.json')
OMM = L.jload(r'data\legislation\official_membership_movements.json')
S1 = json.load(open(os.path.join(HERE, 's1_state.json'), encoding='utf-8'))
S2 = json.load(open(os.path.join(HERE, 's2_state.json'), encoding='utf-8'))

GA = collections.defaultdict(list)
GB = collections.defaultdict(list)
for i, r in enumerate(ARCH):
    k = L.bill_ident(r['Name'], r['Congress'])
    GA[k].append(i)
    cat = L.canonical_category(r['Section'])
    if cat:
        GB[k + (cat,)].append(i)

# routing-audit rows indexed by (bill_ident, effective_category) and by member
RA_CELL = collections.defaultdict(list)
for row in RA['rows']:
    k = L.bill_ident(row.get('bill'), row.get('congress'))
    RA_CELL[(k, row.get('effective_category'))].append(row)
RA_BILL = collections.defaultdict(list)
for row in RA['rows']:
    RA_BILL[L.bill_ident(row.get('bill'), row.get('congress'))].append(row)

# official membership movements, keyed the way the archive names bills
OMM_FACT = collections.defaultdict(list)
for f in OMM.get('facts', []):
    OMM_FACT[(L.bill_ident(f.get('bill'), f.get('congress')), f.get('member'))].append(f)


def exact_roster_name(raw):
    text = str(raw or '').strip()
    cands = [text]
    if ',' in text:
        left, right = text.split(',', 1)
        cands.insert(0, (right + ' ' + left).strip())
    for c in cands:
        hit = ROSTER_NORM.get(L.normalize_name(c))
        if hit:
            return hit
    return None


def sponsor_of(k):
    cells = sorted({L.clean_sponsor_cell(ARCH[i].get('Sponsor')) for i in GA[k]} - {''})
    for c in cells:
        who = RES.resolve(c) or exact_roster_name(c)
        if who:
            return who, c
    return None, (cells or [''])[0]


# ------------------------------------------------ the defect population, grain B
bar('S3-a  DEFECT POPULATION at the grain archive_leg.json actually sums on')
defect = []
for key, idxs in sorted(GB.items()):
    if any(L.canonical_role(ARCH[i]['Role']) == 'sponsor' for i in idxs):
        continue
    base, cat = (key[0], key[1]), key[2]
    who, cell = sponsor_of(base)
    if not who:
        continue
    defect.append({'bill': ARCH[idxs[0]]['Name'], 'congress': base[1], 'cat': cat,
                   'key': base, 'sponsor': who, 'sponsor_cell': cell,
                   'rows_in_cell': len(idxs)})
P('(bill,Congress,category) cells with NO sponsor-role row whose named sponsor IS a roster member: %d'
  % len(defect))
P('   of which the whole bill has no sponsor row anywhere ..... %d'
  % sum(1 for d in defect if not any(L.canonical_role(ARCH[i]['Role']) == 'sponsor'
                                     for i in GA[d['key']])))
P('   of which the bill HAS a sponsor row, but under other categories only ... %d'
  % sum(1 for d in defect if any(L.canonical_role(ARCH[i]['Role']) == 'sponsor'
                                 for i in GA[d['key']])))

# ------------------------------------------------ selection + sign + decay
bar('S3-b  is the cell SELECTED into archive_leg.json, and what does the missing row cost?')
for d in defect:
    cell = RA_CELL.get((d['key'], d['cat']), [])
    sel = [r for r in cell if r['disposition'] == 'selected']
    d['cell_rows_in_audit'] = len(cell)
    d['cell_selected_rows'] = len(sel)
    d['selected'] = bool(sel)
    d['dispositions'] = dict(collections.Counter(r['disposition'] for r in cell))
    signs = sorted({r['sign'] for r in cell if r.get('sign') is not None})
    dws = sorted({round(float(r['decay_weight']), 12) for r in cell if r.get('decay_weight') is not None})
    d['signs'] = signs
    d['decay_weights'] = dws
    d['sign'] = signs[0] if len(signs) == 1 else None
    d['dw'] = dws[0] if len(dws) == 1 else None
    d['direction_mechanism'] = sorted({r.get('direction_mechanism') for r in cell
                                       if r.get('direction_mechanism')})
    # what the member is credited with TODAY in this cell, from the producer's own audit
    mine = [r for r in RA_BILL[d['key']]
            if r.get('member') == d['sponsor'] and r.get('effective_category') == d['cat']]
    d['member_rows_here'] = [(r.get('effective_role') or r.get('source_role'), r['disposition'],
                              r.get('contribution'), r['source_row']) for r in mine]
    cur = [r for r in mine if r['disposition'] == 'selected']
    d['current_contribution'] = round(sum(float(r['contribution']) for r in cur), 12)
    d['current_role'] = (cur[0].get('effective_role') if cur else None)
    d['current_weight'] = L.role_weight(d['current_role']) if cur else 0.0
    if d['selected'] and d['sign'] is not None and d['dw'] is not None:
        d['would_be'] = round(d['sign'] * 3.0 * d['dw'], 12)
        d['missing'] = round(d['sign'] * (3.0 - d['current_weight']) * d['dw'], 12)
    else:
        d['would_be'] = 0.0
        d['missing'] = 0.0
    # official-movement exposure: would a sponsor row even be admitted?
    facts = OMM_FACT.get((d['key'], d['sponsor']), [])
    d['omm_roles'] = sorted({(f.get('role'), bool(f.get('withdrawn'))) for f in facts})
    if not facts:
        d['omm'] = 'no fact -> OM.eligible returns True (sponsor row would be admitted)'
    elif any(L.canonical_role(f.get('role')) == 'sponsor' and not f.get('withdrawn') for f in facts):
        d['omm'] = 'official repository CONFIRMS sponsor, not withdrawn -> admitted'
    else:
        d['omm'] = 'official fact carries a DIFFERENT role/withdrawn -> OM.eligible would REFUSE'

P('%-12s %-4s %-24s %-14s %-4s %-6s %8s %8s %8s'
  % ('bill', 'C', 'category', 'sponsor', 'sel', 'sign', 'decay', 'would-be', 'missing'))
for d in sorted(defect, key=lambda x: -abs(x['missing'])):
    P('%-12s %-4s %-24s %-14s %-4s %-6s %8.4f %+8.3f %+8.3f'
      % (d['bill'], d['congress'], d['cat'], d['sponsor'], 'YES' if d['selected'] else 'no',
         d['sign'] if d['sign'] is not None else '?', d['dw'] or 0.0, d['would_be'], d['missing']))
P('\nper-cell detail:')
for d in sorted(defect, key=lambda x: (x['sponsor'], x['bill'])):
    P('\n  %s (%sth) / %s   sponsor = %s   [Sponsor cell: %s]'
      % (d['bill'], d['congress'], d['cat'], d['sponsor'], d['sponsor_cell']))
    P('     archive rows in this cell = %d ; routing-audit rows = %d ; dispositions = %s'
      % (d['rows_in_cell'], d['cell_rows_in_audit'], d['dispositions']))
    P('     sign = %s (mechanism %s) ; decay = %s' % (d['signs'], d['direction_mechanism'], d['decay_weights']))
    P('     rows the producer already has for %s in this cell: %s'
      % (d['sponsor'], d['member_rows_here'] or 'NONE'))
    P('     currently credited %+.3f as %s -> a sponsor row would credit %+.3f ; MISSING %+.3f'
      % (d['current_contribution'], d['current_role'], d['would_be'], d['missing']))
    P('     official-membership check: %s %s' % (d['omm'], d['omm_roles'] or ''))

# ------------------------------------------------ per-member roll-up
bar('S3-c  MISSING SIGNED WEIGHT per member (top 25 by absolute missing weight)')
per = collections.defaultdict(lambda: {'missing': 0.0, 'cells': []})
for d in defect:
    per[d['sponsor']]['missing'] += d['missing']
    per[d['sponsor']]['cells'].append('%s(%s)/%s %+.2f' % (d['bill'], d['congress'], d['cat'], d['missing']))
order = sorted(per.items(), key=lambda kv: -abs(kv[1]['missing']))
P('%-18s %9s %9s %9s   %s' % ('member', 'missing', 'in leg', 'as pct', 'bills / categories'))
for name, v in order[:25]:
    cats = {d['cat'] for d in defect if d['sponsor'] == name}
    have = sum(LEG.get(name, {}).get(c, 0.0) for c in cats)
    P('%-18s %+9.3f %+9.3f %8s   %s'
      % (name, v['missing'], have,
         ('%.1f%%' % (100.0 * abs(v['missing']) / abs(have)) if have else 'n/a'),
         '; '.join(sorted(v['cells']))))
P('\nmembers affected .............................. %d' % len(per))
P('total missing signed weight (signed sum) ...... %+.3f' % sum(v['missing'] for v in per.values()))
P('total missing signed weight (absolute sum) .... %.3f' % sum(abs(v['missing']) for v in per.values()))
tot_abs = sum(abs(v) for m in LEG.values() for v in m.values())
P('archive_leg.json total absolute weight ........ %.1f  across %d members' % (tot_abs, len(LEG)))
P('missing as a share of the whole matrix ........ %.4f%%'
  % (100.0 * sum(abs(v['missing']) for v in per.values()) / tot_abs))
P('\nper-member per-category view of what the matrix holds vs what is missing:')
for name, v in order:
    for d in sorted((x for x in defect if x['sponsor'] == name), key=lambda x: x['bill']):
        P('   %-14s %-24s archive_leg = %+8.3f   missing %+7.3f   (=%.1f%% of the cell as published)'
          % (name, d['cat'], LEG.get(name, {}).get(d['cat'], 0.0), d['missing'],
             100.0 * abs(d['missing']) / abs(LEG.get(name, {}).get(d['cat'], 0.0))
             if LEG.get(name, {}).get(d['cat'], 0.0) else float('nan')))

# ------------------------------------------------ sanity: the July 12.24 / 6.24 figure
bar('S3-d  CROSS-CHECK against the prior lane (laneC q2c) Tim Scott x Member Business Lending')
ts = [d for d in defect if d['sponsor'] == 'Tim Scott' and d['cat'] == 'Member Business Lending']
P("workbook 'Sponsor Interactions' credits Tim Scott as sponsor on 5 MBL bills totalling 12.24;")
P("laneC receipt q2c_scott_sponsor_trace.txt found 6.24 of that reaches the matrix nowhere.")
P('this lane, measured independently from the archive + routing audit:')
for d in sorted(ts, key=lambda x: x['bill']):
    P('   %-12s C=%-4s missing %+.3f' % (d['bill'], d['congress'], d['missing']))
P('   SUM = %+.3f   %s' % (sum(d['missing'] for d in ts),
                           'MATCHES the 6.24 prior finding' if abs(sum(d['missing'] for d in ts) - 6.24) < 1e-9
                           else 'DOES NOT match 6.24'))

# ------------------------------------------------ S4 regression
bar('S4  REGRESSION CHECK against congress_bills_archive_20260624_115822.xlsx (10,986 rows)')
OLD_A = collections.defaultdict(list)
OLD_B = collections.defaultdict(list)
for r in OLD:
    k = L.bill_ident(r['Name'], r['Congress'])
    OLD_A[k].append(r)
    cat = L.canonical_category(r['Section'])
    if cat:
        OLD_B[k + (cat,)].append(r)
P('older archive rows = %d ; (bill,Congress) groups = %d ; cells = %d'
  % (len(OLD), len(OLD_A), len(OLD_B)))
P('\nDEFECT CELLS  present-in-old / absent-in-old:')
P('%-12s %-4s %-24s %-14s %-11s %-11s %s'
  % ('bill', 'C', 'category', 'sponsor', 'in-old-bill', 'old cell', 'old sponsor-role holders in the cell'))
tab = collections.Counter()
for d in sorted(defect, key=lambda x: (x['congress'], x['bill'])):
    inbill = d['key'] in OLD_A
    cellrows = OLD_B.get(d['key'] + (d['cat'],), [])
    holders = sorted({RES.resolve(r['Member']) or ('REFUSED:' + str(r['Member']))
                      for r in cellrows if L.canonical_role(r['Role']) == 'sponsor'})
    if not inbill:
        verdict = 'BILL-ABSENT-IN-OLD'
    elif d['sponsor'] in holders:
        verdict = 'PRESENT-IN-OLD'
    elif holders:
        verdict = 'OTHER-SPONSOR-IN-OLD'
    else:
        verdict = 'ABSENT-IN-OLD'
    tab[verdict] += 1
    d['old_verdict'] = verdict
    d['old_cell_rows'] = len(cellrows)
    d['old_holders'] = holders
    P('%-12s %-4s %-24s %-14s %-11s %-11s %s'
      % (d['bill'], d['congress'], d['cat'], d['sponsor'],
         'yes' if inbill else 'NO', '%d rows' % len(cellrows), holders or verdict))
P('\ntabulation: %s' % dict(tab))

P('\nALL 53 sponsorless (bill,Congress) -- did the older archive have a sponsor row?')
tab2 = collections.Counter()
for key in sorted(S1['grainA_sponsorless']):
    name, cong = key.rsplit('|', 1)
    k = (name, cong)
    if k not in OLD_A:
        tab2['BILL-ABSENT-IN-OLD'] += 1
    elif any(L.canonical_role(r['Role']) == 'sponsor' for r in OLD_A[k]):
        tab2['SPONSOR-ROW-PRESENT-IN-OLD'] += 1
    else:
        tab2['ALSO-SPONSORLESS-IN-OLD'] += 1
for kk, vv in sorted(tab2.items()):
    P('   %-30s %d' % (kk, vv))
P('\nold-archive sponsor-role rows overall .......... %d / %d'
  % (sum(1 for r in OLD if L.canonical_role(r['Role']) == 'sponsor'), len(OLD)))
P('selected-archive sponsor-role rows overall ..... %d / %d'
  % (sum(1 for r in ARCH if L.canonical_role(r['Role']) == 'sponsor'), len(ARCH)))
oldA_no = [k for k, v in OLD_A.items() if not any(L.canonical_role(r['Role']) == 'sponsor' for r in v)]
P('old archive (bill,Congress) with ZERO sponsor row ... %d / %d  (%.1f%%)'
  % (len(oldA_no), len(OLD_A), 100.0 * len(oldA_no) / len(OLD_A)))

with open(os.path.join(HERE, 's3_state.json'), 'w', encoding='utf-8') as fh:
    json.dump({'defect_cells': [{k: (list(v) if isinstance(v, tuple) else v)
                                 for k, v in d.items()} for d in defect],
               'per_member': {k: v['missing'] for k, v in per.items()},
               'old_tab': dict(tab), 'old_tab_all53': dict(tab2)}, fh, indent=1, default=str)
P('\nwrote s3_state.json')
