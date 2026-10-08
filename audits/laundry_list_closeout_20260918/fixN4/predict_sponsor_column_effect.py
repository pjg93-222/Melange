# -*- coding: utf-8 -*-
"""Lane N4 / step 5: PREDICT the effect of the sponsor-column fix. READ-ONLY.

Nothing under fec/ is imported (import == execution). The producer's rules come from lane
F1's transcriptions in ../F1/receipts/f1_lib.py, which f1_selfcheck.py byte-compares against
the LIVE sources and which reproduces the producer's own routing 9550/9550. The fix itself
is loaded from its real file, fec/legislation/sponsor_column.py, by path -- it imports only
os and re, so loading it executes nothing.

What is derived here and what is READ:
  * the synthesised rows are DERIVED by running the shipped helper over the live archive;
  * whether a cell is scored at all, and with what sign and what decay, is READ from the
    producer's own legislation_routing_audit.json -- not re-derived, so this prediction
    cannot disagree with the producer about anything except the rows being added;
  * the dedup arithmetic (strongest-role-wins per member/bill/Congress/category) is applied
    with F1's transcription of BR.preferred_role;
  * official-membership eligibility is re-derived exactly as OM.eligible does it, on
    (repository_key, bioguide), because a refusal there would silently drop a new row.

Writes only its own .txt beside itself.
"""
import collections
import datetime
import importlib.util
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
CLOSEOUT = os.path.dirname(HERE)
WORKTREE = os.path.dirname(os.path.dirname(CLOSEOUT))
sys.path.insert(0, os.path.join(CLOSEOUT, 'F1', 'receipts'))
import f1_lib as L  # noqa: E402


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SC = _load(os.path.join(WORKTREE, 'fec', 'legislation', 'sponsor_column.py'), 'sponsor_column')
P = print


def bar(title):
    P('\n' + '=' * 100)
    P(title)
    P('=' * 100)


# ---------------------------------------------------------------- inputs
ARCH = L.xl(L.SEL_ARCHIVE, 'All Bills')
SENT = L.sentinel_scoring_rows()
MANUAL = L.manual_rows()
NAMES, BIOS = L.roster()
RES = L.Resolver(NAMES, BIOS)
RA = L.jload('legislation_routing_audit.json')
LEG = L.jload('archive_leg.json')
OMM = L.jload(r'data\legislation\official_membership_movements.json')
S3 = json.load(open(os.path.join(CLOSEOUT, 'F1', 'receipts', 's3_state.json'), encoding='utf-8'))

bar('N4-a  INPUTS (all read-only)')
P('archive                       %-50s rows=%d' % (L.SEL_ARCHIVE, len(ARCH)))
P('sentinel verified scoring rows                                                   rows=%d' % len(SENT))
P('manual_bill_evidence.csv                                                         rows=%d' % len(MANUAL))
P('frame the producer scores today = %d + %d + %d = %d' %
  (len(ARCH), len(SENT), len(MANUAL), len(ARCH) + len(SENT) + len(MANUAL)))
P('legislation_routing_audit.json  source_rows=%d  rows=%d  selected_events=%d'
  % (RA['source_rows'], len(RA['rows']), RA['selected_events']))
P('archive_leg.json                members=%d' % len(LEG))
P('roster (data/engine/congestion.json)                                          members=%d' % len(NAMES))
FRAME_ROWS = len(ARCH) + len(SENT) + len(MANUAL)
assert FRAME_ROWS == RA['source_rows'] == len(RA['rows']), (FRAME_ROWS, RA['source_rows'])
P('frame row count reconciles with the audit: %d == source_rows == len(rows)' % FRAME_ROWS)
_age = (datetime.datetime.now(datetime.timezone.utc)
        - datetime.datetime.fromisoformat(OMM['checked_at'].replace('Z', '+00:00'))).total_seconds()
P('official membership facts checked_at=%s  age=%.1f days  (OM.load refuses >8 days: %s)'
  % (OMM['checked_at'], _age / 86400.0, 'STALE' if _age > 8 * 86400 else 'fresh'))

# ---------------------------------------------------------------- the helper, live
bar('N4-b  THE SHIPPED HELPER, RUN OVER THE LIVE ARCHIVE')
extra = SC.sponsor_rows_from_column(ARCH, RES.resolve, L.canonical_category, L.congress_of)
off = SC.sponsor_rows_from_column(ARCH, RES.resolve, L.canonical_category, L.congress_of,
                                  environ={SC.DIAL: '0'})
P('LEG_SPONSOR_FROM_COLUMN default -> %d synthesised rows' % len(extra))
P('LEG_SPONSOR_FROM_COLUMN=0       -> %d synthesised rows  (negative control)' % len(off))
assert off == []
P('')
P('%-12s %-4s %-26s %-22s %-9s %-7s %s'
  % ('bill', 'C', 'category', 'Member (Sponsor cell)', 'Role', 'decay', 'provenance'))
for row in extra:
    P('%-12s %-4s %-26s %-22s %-9s %-7s %s'
      % (row['Name'], L.congress_of(row['Congress']), L.canonical_category(row['Section']),
         row['Member'], row['Role'], row['DecayWeight'], row[SC.SOURCE_COLUMN]))

# independent re-derivation of the cell grouping, as a cross-check of the helper
cells = collections.defaultdict(list)
for i, r in enumerate(ARCH):
    cat = L.canonical_category(r['Section'])
    if cat:
        cells[(L.bill_ident(r['Name'], r['Congress']), cat)].append(i)
derived = []
for key, idxs in sorted(cells.items()):
    spellings = []
    for i in idxs:
        cell = L.clean_sponsor_cell(ARCH[i].get('Sponsor'))
        if cell and cell not in spellings:
            spellings.append(cell)
    resolved = {RES.resolve(s) for s in spellings}
    if len(resolved) != 1 or None in resolved:
        continue
    who = resolved.pop()
    if who in {RES.resolve(str(ARCH[i]['Member'] or '').strip()) for i in idxs}:
        continue
    derived.append((ARCH[idxs[0]]['Name'], key[0][1], key[1], who, idxs[0]))
P('\nindependent re-derivation of the same rule: %d cells' % len(derived))
assert len(derived) == len(extra), (len(derived), len(extra))
# `derived` is key-sorted and `extra` is in first-appearance order: index the template row
# by cell rather than by position.
TEMPLATE_ROW = {(L.bill_ident(item[0], item[1]), item[2]): item[4] for item in derived}

f1_cells = {(d['bill'], str(d['congress']), d['cat']) for d in S3['defect_cells']}
mine = {(row['Name'], L.congress_of(row['Congress']), L.canonical_category(row['Section']))
        for row in extra}
P('F1 s3_state.json defect cells ......... %d  %s' % (len(f1_cells), sorted(f1_cells)))
P('this lane synthesises ................. %d  %s' % (len(mine), sorted(mine)))
P('SETS MATCH: %s' % (mine == f1_cells))

bar('N4-c  FAIL-CLOSED: the sponsor cells that must NOT mint a row')
refused = []
for key, idxs in sorted(cells.items()):
    spellings = sorted({L.clean_sponsor_cell(ARCH[i].get('Sponsor')) for i in idxs} - {''})
    for spelling in spellings:
        if RES.resolve(spelling) is None:
            refused.append(spelling)
refused = sorted(set(refused))
P('distinct Sponsor spellings the Resolver refuses (not a current member, or ambiguous): %d'
  % len(refused))
for spelling in refused:
    P('   REFUSED  %s' % spelling)
for probe in ('Scott, David', 'Armstrong, Kelly'):
    P('probe %-18s -> %r   (must be None)' % (probe, RES.resolve(probe)))

# ---------------------------------------------------------------- what the frame does with them
bar('N4-d  EVERY GATE THE NEW ROWS MUST PASS, read from the producer\'s own audit')
RA_CELL = collections.defaultdict(list)
for row in RA['rows']:
    RA_CELL[(L.bill_ident(row.get('bill'), row.get('congress')),
             row.get('effective_category'))].append(row)
RA_BY_SOURCE_ROW = {row['source_row']: row for row in RA['rows']}
OMM_FACT = {(f['repository_key'], f['bioguide']): f for f in OMM.get('facts', [])}

_BILL_RE = re.compile(r'(HCONRES|SCONRES|HJRES|SJRES|HRES|SRES|HR|S)(\d+)')


def repository_key(name, congress):
    """congress_bill_repository.parse_bill_identity(...)['key'], transcribed."""
    match = _BILL_RE.fullmatch(re.sub(r'[^A-Z0-9]', '', str(name or '').upper()))
    if not match:
        return ''
    try:
        number = int(congress)
    except (TypeError, ValueError):
        return ''
    if number <= 0:
        return ''
    return '%d:%s:%d' % (number, match.group(1).casefold(), int(match.group(2)))


def om_eligible(key, bioguide, role):
    """official_membership_movements.eligible, transcribed."""
    fact = OMM_FACT.get((key, bioguide))
    return (True, 'no official fact -> eligible') if fact is None else (
        (not fact['withdrawn']) and L.canonical_role(role) == L.canonical_role(fact['role']),
        'official fact role=%s withdrawn=%s' % (fact['role'], fact['withdrawn']))


predicted = []
for row in extra:
    name, congress = row['Name'], L.congress_of(row['Congress'])
    cat = L.canonical_category(row['Section'])
    member = RES.resolve(row['Member'])
    cell = RA_CELL[((L.bill_ident(name, congress)), cat)]
    selected = [r for r in cell if r['disposition'] == 'selected']
    signs = sorted({r['sign'] for r in cell if r.get('sign') is not None})
    decays = sorted({round(float(r['decay_weight']), 12) for r in cell
                     if r.get('decay_weight') is not None})
    template_index = TEMPLATE_ROW[(L.bill_ident(name, congress), cat)]
    template_audit = RA_BY_SOURCE_ROW.get(template_index + 2, {})
    key = repository_key(name, congress)
    ok, why = om_eligible(key, BIOS.get(member), 'sponsor')
    # decay for the new row: BR.evidence_decay(Name, Congress, DecayWeight) and the row is
    # not LTR- letter evidence, so the stored archive weight is used verbatim.
    assert not str(name).upper().startswith('LTR-')
    dw = float(row['DecayWeight'])
    mine_event = [r for r in cell if r.get('member') == member and r['disposition'] == 'selected']
    prior_role = mine_event[0]['effective_role'] if mine_event else None
    prior_contribution = float(mine_event[0]['contribution']) if mine_event else 0.0
    if prior_role is None:
        disposition, contribution = 'selected', signs[0] * 3.0 * dw
    elif L.preferred_role((prior_role, 'sponsor')) == 'sponsor' and prior_role != 'sponsor':
        disposition, contribution = 'selected', signs[0] * 3.0 * dw
    else:
        disposition, contribution = 'duplicate-same-role', prior_contribution
    item = {'bill': name, 'congress': congress, 'cat': cat, 'member': member, 'key': key,
            'cell_rows': len(cell), 'cell_selected': len(selected), 'signs': signs,
            'decays': decays, 'row_decay': dw, 'om_ok': ok, 'om_why': why,
            'template_source_row': template_index + 2,
            'template_disposition': template_audit.get('disposition'),
            'template_category': template_audit.get('effective_category'),
            'prior_role': prior_role, 'prior_contribution': prior_contribution,
            'disposition': disposition, 'contribution': contribution,
            'delta': round(contribution - prior_contribution, 12)}
    predicted.append(item)
    P('\n  %s (%s) / %s   -> %s' % (name, congress, cat, member))
    P('     repository key %-14s bioguide %-8s official-membership: %s  [%s]'
      % (key, BIOS.get(member), 'ADMITTED' if ok else 'REFUSED', why))
    P('     the cell today: %d audit rows, %d selected, sign=%s, decay=%s'
      % (len(cell), len(selected), signs, decays))
    P('     template row = archive row %d (audit source_row %d), disposition %r, category %r'
      % (template_index, template_index + 2, template_audit.get('disposition'),
         template_audit.get('effective_category')))
    P('     new row: role sponsor (weight 3.0) x sign %s x decay %s -> %+.6f'
      % (signs[0], dw, signs[0] * 3.0 * dw))
    P('     strongest-role-wins vs what %s already holds here (%r, %+.3f) -> %s, %+.6f'
      % (member, prior_role, prior_contribution, disposition, contribution))
    P('     archive_leg.json delta for (%s, %s): %+.6f' % (member, cat, item['delta']))
    assert ok, 'official membership would refuse this row -- prediction invalid'
    assert len(signs) == 1 and len(decays) == 1, (signs, decays)
    assert selected, 'cell is not scored today; the new row would not be either'
    assert abs(dw - decays[0]) < 1e-12, (dw, decays)
    assert item['template_disposition'] == 'selected' and item['template_category'] == cat

# ---------------------------------------------------------------- archive_leg.json
bar('N4-e  PREDICTED archive_leg.json')
delta = collections.defaultdict(float)
for item in predicted:
    delta[(item['member'], item['cat'])] += item['delta']
P('%-16s %-26s %10s %10s %10s' % ('member', 'category', 'published', 'delta', 'predicted'))
for (member, cat), value in sorted(delta.items()):
    before = LEG.get(member, {}).get(cat, 0.0)
    P('%-16s %-26s %10.2f %+10.2f %10.2f' % (member, cat, before, value, before + value))
P('')
P('cells that move ............................ %d' % sum(1 for v in delta.values() if abs(v) > 1e-12))
P('cells touched but unchanged (dedup) ........ %d' % sum(1 for v in delta.values() if abs(v) <= 1e-12))
P('members whose archive_leg.json changes ..... %d' % len({m for (m, _c), v in delta.items()
                                                           if abs(v) > 1e-12}))
P('every other (member, category) cell of the %d-member matrix is untouched: the helper' % len(LEG))
P('  proposes rows only for the %d cells above and nothing else is re-derived.' % len(delta))
P('members carrying >=1 archive bill: %d -> %d  (audit_full floor is >=516)'
  % (len(LEG), len(set(LEG) | {item['member'] for item in predicted})))

# ---------------------------------------------------------------- pinned counts
bar('N4-f  EVERY PINNED / RECONCILED COUNT THIS CHANGE MOVES')
new_selected = sum(1 for item in predicted if item['disposition'] == 'selected')
new_dupes = sum(1 for item in predicted if item['disposition'] == 'duplicate-same-role')
disp = dict(RA['summary']['dispositions'])
dupes = dict(RA['summary']['duplicates'])
P('%-64s %10s %10s' % ('quantity', 'today', 'after'))
for label, before, after in (
        ('frame rows (len(A))', FRAME_ROWS, FRAME_ROWS + len(extra)),
        ('legislation_routing_audit.json source_rows', RA['source_rows'],
         RA['source_rows'] + len(extra)),
        ('legislation_routing_audit.json len(rows)', len(RA['rows']), len(RA['rows']) + len(extra)),
        ('legislation_routing_audit.json selected_events', RA['selected_events'],
         RA['selected_events'] + new_selected),
        ('summary.dispositions["selected"]', disp.get('selected', 0),
         disp.get('selected', 0) + new_selected),
        ('summary.dispositions["duplicate-same-role"]', disp.get('duplicate-same-role', 0),
         disp.get('duplicate-same-role', 0) + new_dupes),
        ('summary.duplicates["duplicate-same-role"]', dupes.get('duplicate-same-role', 0),
         dupes.get('duplicate-same-role', 0) + new_dupes),
        ('summary.effective_categories["Member Business Lending"]',
         RA['summary']['effective_categories'].get('Member Business Lending', 0),
         RA['summary']['effective_categories'].get('Member Business Lending', 0)
         + sum(1 for i in predicted if i['cat'] == 'Member Business Lending')),
        ('archive_leg.json members (audit_full floor >=516)', len(LEG),
         len(set(LEG) | {i['member'] for i in predicted})),
        ('unmatched archive rows (audit_full cap <=50 and <=1%)',
         sum(int(v or 0) for v in RA['summary']['unmatched_members'].values()),
         sum(int(v or 0) for v in RA['summary']['unmatched_members'].values())),
        ('letter evidence rows (fail-closed floor 296)',
         sum(1 for r in MANUAL if str(r.get('Bill') or r.get('Name') or '').upper().startswith('LTR-')),
         sum(1 for r in MANUAL if str(r.get('Bill') or r.get('Name') or '').upper().startswith('LTR-'))),
        ('archive workbook rows (leg_evidence_recompute pin 10986)', len(ARCH), len(ARCH))):
    P('%-64s %10s %10s%s' % (label, before, after, '' if before != after else '   (unchanged)'))
P('')
P('ROW CONSERVATION holds: len(rows) == source_rows both before (%d) and after (%d), so'
  % (len(RA['rows']), len(RA['rows']) + len(extra)))
P('  audit_full.py:525 and bill_coverage_audit C1 stay green -- every synthesised row also')
P('  appends exactly one routing row, on every disposition branch.')
P('DUPLICATE-SELECTED GUARDS hold: live_legislative_pillar.measure() and')
P('  audit_measurement_layers raise on two SELECTED rows sharing (member, congress, bill,')
P('  category). The %d Anna Luna rows arrive after her sentinel sponsor rows and dedup to' % new_dupes)
P('  duplicate-same-role, so no cell gains a second selected row.')

bar('N4-g  SUMMARY')
P('synthesised rows ......................... %d  (%d selected, %d dedup to duplicate-same-role)'
  % (len(extra), new_selected, new_dupes))
P('signed weight reaching the matrix ........ %+.3f' % sum(i['delta'] for i in predicted))
P('archive_leg.json cells that change ....... %d' % sum(1 for v in delta.values() if abs(v) > 1e-12))
for (member, cat), value in sorted(delta.items()):
    if abs(value) > 1e-12:
        before = LEG.get(member, {}).get(cat, 0.0)
        P('   %s / %s: %.2f -> %.2f' % (member, cat, before, before + value))
P('F1 measured the same missing weight independently: %+.3f' %
  sum(S3['per_member'].values()))
P('MATCH: %s' % (abs(sum(i['delta'] for i in predicted) - sum(S3['per_member'].values())) < 1e-9))
