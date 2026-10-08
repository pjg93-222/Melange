# -*- coding: utf-8 -*-
"""Lane F1 / S2 : separate the BENIGN from the DEFECT population among the sponsorless bills.

A sponsor who is not in the current 533-member roster is legitimately absent from the archive's
member rows.  For every sponsorless (bill, Congress) this script names the sponsor from the best
available LOCAL evidence, in this priority order, and records WHICH source answered:

  1. the selected archive's own bill-level 'Sponsor' column
  2. workbook 'Moneyball Main Version - Blended.xlsx' / 'Sponsor Interactions' (Member column)
  3. the older archive congress_bills_archive_20260624_115822.xlsx (sponsor-role rows, then its
     own Sponsor column)
  4. Sentinel Bill Ledger verified scoring rows with a sponsor role
  5. manual_bill_evidence.csv rows with a sponsor role

then classifies:
  SPONSOR-IS-CURRENT-MEMBER-ROW-MISSING  sponsor resolves to a roster member; no sponsor row exists
  SPONSOR-NOT-IN-ROSTER                  a name is known and its surname is absent from the roster
  SPONSOR-UNKNOWN-LOCALLY                no local source names a sponsor, or the name is ambiguous

Also runs a NEGATIVE CONTROL: the re-implemented Resolver is replayed over all 10,181 archive
Member cells and compared with the producer's own resolution in legislation_routing_audit.json.

Writes s2_classify_sponsorless.txt and s2_state.json.
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
WBS = L.xl(L.WORKBOOK, 'Sponsor Interactions')
SENT = L.sentinel_scoring_rows()
MAN = L.manual_rows()
NAMES, BIOS = L.roster()
RES = L.Resolver(NAMES, BIOS)
RA = L.jload('legislation_routing_audit.json')
AUD = {}
for row in RA['rows']:
    AUD.setdefault(row['source_row'], row)
AUDL = [AUD[i + 2] for i in range(len(ARCH))]
S1 = json.load(open(os.path.join(HERE, 's1_state.json'), encoding='utf-8'))

# ------------------------------------------------------- negative control
bar('S2-0  NEGATIVE CONTROL : re-implemented Resolver vs the producer\'s own resolution')
# The producer reaches matchmember() only after seccat() and excluded_bill() pass, and records
# audit['member'] only from that point on (LIVE fec\legislation\build_archive_legislative.py
# 168-179, 188-200).  So 'unknown-section', 'excluded-title' and 'excluded-override' rows carry
# NO member field and are not comparable; 'unmatched-member' means the producer REFUSED.
NO_MEMBER_FIELD = {'unknown-section', 'excluded-title', 'excluded-override'}
agree = dis = skipped = 0
examples = []
skipped_dispositions = collections.Counter()
for i, r in enumerate(ARCH):
    disp = AUDL[i]['disposition']
    if disp in NO_MEMBER_FIELD:
        skipped += 1
        skipped_dispositions[disp] += 1
        continue
    mine = RES.resolve(r['Member'])
    theirs = AUDL[i].get('member')          # None only when disposition == 'unmatched-member'
    if mine == theirs:
        agree += 1
    else:
        dis += 1
        if len(examples) < 10:
            examples.append((str(r['Member']), str(mine), str(theirs), disp))
P('archive Member cells ................................. %d' % len(ARCH))
P('   not comparable (producer never recorded a member) . %d  %s'
  % (skipped, dict(skipped_dispositions)))
P('   comparable ........................................ %d' % (agree + dis))
P('      agree with legislation_routing_audit.json ...... %d' % agree)
P('      disagree ....................................... %d' % dis)
for e in examples:
    P('         source=%-28s mine=%-22s producer=%-22s (%s)' % e)
P('=> the transcribed Resolver is %s'
  % ('FAITHFUL on every comparable row' if dis == 0
     else 'NOT faithful -- treat S2/S3 names as UNKNOWN'))
assert dis == 0, 'resolver parity failed; S2/S3 name-based claims would be unsound'

# ------------------------------------------------------------- indexes
GA = collections.defaultdict(list)
for i, r in enumerate(ARCH):
    GA[L.bill_ident(r['Name'], r['Congress'])].append(i)
SPONSORLESS = [tuple(k.split('|')) for k in S1['grainA_sponsorless']]
SPONSORLESS = [(k[0], k[1]) for k in SPONSORLESS]

OLD_BY = collections.defaultdict(list)
for r in OLD:
    OLD_BY[L.bill_ident(r['Name'], r['Congress'])].append(r)
WB_BY = collections.defaultdict(list)
for r in WBS:
    WB_BY[L.bill_ident(r['Name'], r['Congress'])].append(r)
SENT_BY = collections.defaultdict(list)
for r in SENT:
    SENT_BY[L.bill_ident(r.get('Bill'), r.get('Congress'))].append(r)
MAN_BY = collections.defaultdict(list)
for r in MAN:
    MAN_BY[L.bill_ident(r.get('Bill'), r.get('Congress'))].append(r)

ROSTER_LAST = {L.normalize_name(n).split()[-1] for n in NAMES}
ROSTER_NORM = {L.normalize_name(n): n for n in NAMES}


def exact_roster_name(raw):
    """Decisive membership test that does not depend on the Resolver's ambiguity policy:
    reorder 'Last, First' and ask whether the roster carries that exact normalized name."""
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


def surname_of(raw):
    norm = L.normalize_name(raw)
    if not norm:
        return ''
    toks = norm.split()
    # 'Scanlon, Mary Gay' normalizes to 'scanlon mary gay' -> surname is the FIRST token
    return toks[0] if ',' in str(raw) else toks[-1]


def evidence(k):
    """Return [(source, raw_name)] in priority order."""
    out = []
    cells = sorted({L.clean_sponsor_cell(ARCH[i].get('Sponsor')) for i in GA[k]} - {''})
    for c in cells:
        out.append(('selected-archive Sponsor column', c))
    for r in WB_BY.get(k, []):
        if L.canonical_role(r.get('Role')) == 'sponsor' and str(r.get('Member') or '').strip():
            out.append(("workbook 'Sponsor Interactions' Member", str(r['Member']).strip()))
    for r in OLD_BY.get(k, []):
        if L.canonical_role(r.get('Role')) == 'sponsor' and str(r.get('Member') or '').strip():
            out.append(('older archive 20260624 sponsor-role Member', str(r['Member']).strip()))
    for r in OLD_BY.get(k, []):
        c = L.clean_sponsor_cell(r.get('Sponsor'))
        if c:
            out.append(('older archive 20260624 Sponsor column', c))
    for r in SENT_BY.get(k, []):
        if L.canonical_role(r.get('Role')) == 'sponsor' and str(r.get('Member') or '').strip():
            out.append(('Sentinel verified sponsor row Member', str(r['Member']).strip()))
    for r in MAN_BY.get(k, []):
        if L.canonical_role(r.get('Role')) == 'sponsor' and str(r.get('Member') or '').strip():
            out.append(('manual_bill_evidence sponsor row Member', str(r['Member']).strip()))
    # dedupe keeping first occurrence
    seen = set()
    uniq = []
    for s, n in out:
        if n.casefold() in seen:
            continue
        seen.add(n.casefold())
        uniq.append((s, n))
    return uniq


rows = []
for k in sorted(SPONSORLESS):
    ev = evidence(k)
    res = [(s, n, RES.resolve(n)) for s, n in ev]
    hits = sorted({r for _, _, r in res if r})
    if len(hits) == 1:
        cls, who = 'SPONSOR-IS-CURRENT-MEMBER-ROW-MISSING', hits[0]
    elif len(hits) > 1:
        cls, who = 'SPONSOR-UNKNOWN-LOCALLY', 'AMBIGUOUS:' + '/'.join(hits)
    elif not ev:
        cls, who = 'SPONSOR-UNKNOWN-LOCALLY', ''
    else:
        # The Resolver refuses an ambiguous surname, which is NOT the same as "not a member".
        # Settle it with the decisive test: does the roster carry this exact full name?
        exact = sorted({e for e in (exact_roster_name(n) for _, n in ev) if e})
        if len(exact) == 1:
            cls, who = 'SPONSOR-IS-CURRENT-MEMBER-ROW-MISSING', exact[0]
        elif exact:
            cls, who = 'SPONSOR-UNKNOWN-LOCALLY', 'AMBIGUOUS:' + '/'.join(exact)
        else:
            cls, who = 'SPONSOR-NOT-IN-ROSTER', ev[0][1]
    rows.append({
        'bill': ARCH[GA[k][0]]['Name'], 'congress': k[1], 'key': '%s|%s' % k,
        'member_rows': len(GA[k]),
        'sections': sorted({str(ARCH[i]['Section']) for i in GA[k]}),
        'categories': sorted({L.canonical_category(ARCH[i]['Section']) for i in GA[k]}),
        'sponsor_cell': (sorted({L.clean_sponsor_cell(ARCH[i].get('Sponsor')) for i in GA[k]} - {''}) or [''])[0],
        'evidence': [{'source': s, 'name': n, 'resolves_to': r} for s, n, r in res],
        'class': cls, 'sponsor_member': who,
        'title': str(ARCH[GA[k][0]].get('Title') or ''),
    })

bar('S2-a  CLASSIFICATION of the 53 sponsorless (bill, Congress) in the selected archive')
cnt = collections.Counter(r['class'] for r in rows)
for c in ('SPONSOR-IS-CURRENT-MEMBER-ROW-MISSING', 'SPONSOR-NOT-IN-ROSTER', 'SPONSOR-UNKNOWN-LOCALLY'):
    sub = [r for r in rows if r['class'] == c]
    P('%-40s bills=%-4d member rows=%-6d' % (c, cnt[c], sum(r['member_rows'] for r in sub)))
P('%-40s bills=%-4d member rows=%-6d' % ('TOTAL', len(rows), sum(r['member_rows'] for r in rows)))

P('\nby Congress x class:')
for c in sorted({r['congress'] for r in rows}):
    line = ['C=%s' % c]
    for cls in ('SPONSOR-IS-CURRENT-MEMBER-ROW-MISSING', 'SPONSOR-NOT-IN-ROSTER', 'SPONSOR-UNKNOWN-LOCALLY'):
        line.append('%s=%d' % (cls.split('-')[1][:7], sum(1 for r in rows if r['congress'] == c and r['class'] == cls)))
    P('   ' + '  '.join(line))

P('\nwhich local source answered, for the defect class:')
src = collections.Counter()
for r in rows:
    if r['class'] == 'SPONSOR-IS-CURRENT-MEMBER-ROW-MISSING':
        for e in r['evidence']:
            if e['resolves_to'] == r['sponsor_member']:
                src[e['source']] += 1
                break
for s, n in src.most_common():
    P('   %-46s %d' % (s, n))

bar('S2-b  DEFECT CLASS : sponsor is a current roster member, no sponsor row exists anywhere in the bill')
P('%-14s %-4s %-6s %-22s %-30s %s' % ('bill', 'C', 'rows', 'sponsor (resolved)', 'categories', 'evidence source'))
for r in sorted((x for x in rows if x['class'] == 'SPONSOR-IS-CURRENT-MEMBER-ROW-MISSING'),
                key=lambda x: (x['congress'], x['bill'])):
    e0 = next((e for e in r['evidence'] if e['resolves_to'] == r['sponsor_member']), {'source': '?'})
    P('%-14s %-4s %-6d %-22s %-30s %s' % (r['bill'], r['congress'], r['member_rows'],
                                          r['sponsor_member'], ', '.join(c or '?' for c in r['categories'])[:30],
                                          e0['source']))

bar('S2-c  BENIGN CLASS : named sponsor is not a current member (row legitimately absent)')
P('   "exact roster name" = the decisive test; "surname shared" lists roster members who share')
P('   the surname, i.e. the reason the Resolver alone could not settle the case.')
P('%-14s %-4s %-6s %-30s %-11s %s'
  % ('bill', 'C', 'rows', 'Sponsor cell', 'exact name?', 'roster members sharing the surname'))
for r in sorted((x for x in rows if x['class'] == 'SPONSOR-NOT-IN-ROSTER'),
                key=lambda x: (x['congress'], x['bill'])):
    sur = surname_of(r['sponsor_cell'])
    shared = sorted(n for n in NAMES if L.normalize_name(n).split()[-1] == sur)
    P('%-14s %-4s %-6d %-30s %-11s %s'
      % (r['bill'], r['congress'], r['member_rows'], r['sponsor_cell'][:30],
         'NO' if exact_roster_name(r['sponsor_cell']) is None else 'YES', shared))

bar('S2-d  UNKNOWN-LOCALLY')
for r in sorted((x for x in rows if x['class'] == 'SPONSOR-UNKNOWN-LOCALLY'),
                key=lambda x: (x['congress'], x['bill'])):
    P('%-14s %-4s rows=%-5d cell=%-34s -> %s' % (r['bill'], r['congress'], r['member_rows'],
                                                 r['sponsor_cell'][:34], r['sponsor_member'] or '(no local source)'))

# ------------------------------------------------ the other gap: row present, wrong member
bar('S2-e  CROSS-CHECK : bills where a sponsor-role row EXISTS -- does it carry the named sponsor?')
other = []
for k, idxs in GA.items():
    if k in set(SPONSORLESS):
        continue
    cell = (sorted({L.clean_sponsor_cell(ARCH[i].get('Sponsor')) for i in GA[k]} - {''}) or [''])[0]
    who = RES.resolve(cell)
    if who is None:
        continue
    holders = sorted({RES.resolve(ARCH[i]['Member']) or ('REFUSED:' + str(ARCH[i]['Member']))
                      for i in idxs if L.canonical_role(ARCH[i]['Role']) == 'sponsor'})
    if who not in holders:
        other.append((k, cell, who, holders))
P('(bill,Congress) with a sponsor row whose holder is NOT the person the Sponsor column names .. %d'
  % len(other))
P('%-14s %-4s %-26s %s' % ('bill', 'C', 'Sponsor column resolves to', 'members holding the sponsor role'))
for k, cell, who, holders in sorted(other):
    P('%-14s %-4s %-26s %s' % (ARCH[GA[k][0]]['Name'], k[1], who, holders))
other = [k for k, _, _, _ in other]

with open(os.path.join(HERE, 's2_state.json'), 'w', encoding='utf-8') as fh:
    json.dump({'resolver_control': {'agree': agree, 'disagree': dis},
               'rows': rows,
               'row_present_wrong_member': ['%s|%s' % k for k in other]}, fh, indent=1, sort_keys=True)
P('\nwrote s2_state.json')
