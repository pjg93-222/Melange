# -*- coding: utf-8 -*-
"""Lane F1 / S1 : sponsor-role census of the SELECTED bill archive.  READ-ONLY.

Q: for every (bill, Congress) in congress_bills_archive_20260825_115305.xlsx 'All Bills',
   is there at least one row whose canonical role is 'sponsor'?

Grain A = (bill, Congress)                      -- the question as asked
Grain B = (bill, Congress, canonical category)  -- the grain archive_leg.json actually sums on
          (producer event_key, LIVE build_archive_legislative.py:251)

Also: the archive DOES carry a bill-level 'Sponsor' column.  How often does the person it
names have no sponsor-role member row?

Writes s1_sponsor_row_census.txt (this transcript) and s1_state.json (machine state for S2-S4).
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


# ------------------------------------------------------------------ inputs
ARCH = L.xl(L.SEL_ARCHIVE, 'All Bills')
NAMES, BIOS = L.roster()
RES = L.Resolver(NAMES, BIOS)
RA = L.jload('legislation_routing_audit.json')
LEG = L.jload('archive_leg.json')

bar('S1  INPUTS')
P('selected archive              %s   rows=%d' % (L.SEL_ARCHIVE, len(ARCH)))
P('roster (data/engine/congestion.json)                members=%d' % len(NAMES))
P('legislation_routing_audit.json  source=%s' % RA['source'])
P('   source_rows=%d selected_events=%d  (archive %d + sentinel %d + manual 371 = %d)'
  % (RA['source_rows'], RA['selected_events'], len(ARCH), RA['sentinel_verified_rows'],
     len(ARCH) + RA['sentinel_verified_rows'] + 371))
P('archive_leg.json members=%d' % len(LEG))

# link archive row i (0-based) to routing audit row source_row == i+2
RA_BY_SR = {}
for row in RA['rows']:
    RA_BY_SR.setdefault(row['source_row'], []).append(row)
link_ok = link_bad = 0
for i, r in enumerate(ARCH):
    cand = RA_BY_SR.get(i + 2) or []
    if len(cand) == 1 and str(cand[0].get('bill') or '') == str(r['Name'] or '') \
       and str(cand[0].get('source_section') or '') == str(r['Section'] or '') \
       and str(cand[0].get('member_source') or '') == str(r['Member'] or ''):
        link_ok += 1
    else:
        link_bad += 1
P('\nrouting-audit linkage  archive row i <-> audit source_row i+2 : %d agree / %d disagree'
  % (link_ok, link_bad))
assert link_bad == 0, 'routing audit linkage broken; every downstream number would be unsound'
AUD = [RA_BY_SR[i + 2][0] for i in range(len(ARCH))]

# ------------------------------------------------------------------ grains
GA = collections.defaultdict(list)          # (bill,congress) -> [i]
for i, r in enumerate(ARCH):
    GA[L.bill_ident(r['Name'], r['Congress'])].append(i)

# whitespace-insensitive cross-check of the bill half of the key
GA_WS = collections.defaultdict(set)
for k in GA:
    GA_WS[(''.join(k[0].split()), k[1])].add(k)
collapse = {k: v for k, v in GA_WS.items() if len(v) > 1}
P('grain A  (bill,Congress) groups = %d ; whitespace-variant collisions = %d %s'
  % (len(GA), len(collapse), sorted(collapse.values())[:4] if collapse else ''))


def roles(idxs):
    return collections.Counter(L.canonical_role(ARCH[i]['Role']) for i in idxs)


SPONSORLESS_A = {k: v for k, v in GA.items() if roles(v)['sponsor'] == 0}

bar('S1-a  GRAIN A : (bill, Congress) with >=1 member row and ZERO sponsor-role rows')
P('bills (bill,Congress) in the selected archive ..................... %d' % len(GA))
P('   of which >=1 sponsor-role row ................................. %d' % (len(GA) - len(SPONSORLESS_A)))
P('   of which ZERO sponsor-role rows ............................... %d   (%.1f%%)'
  % (len(SPONSORLESS_A), 100.0 * len(SPONSORLESS_A) / len(GA)))
P('member rows in the archive ....................................... %d' % len(ARCH))
P('   member rows riding on a ZERO-sponsor bill ..................... %d   (%.1f%%)'
  % (sum(len(v) for v in SPONSORLESS_A.values()),
     100.0 * sum(len(v) for v in SPONSORLESS_A.values()) / len(ARCH)))

P('\nby Congress:')
P('   %-10s %8s %8s %10s %12s %12s' % ('Congress', 'bills', 'no-spons', 'pct', 'rows', 'rows-no-spons'))
for c in sorted({k[1] for k in GA}):
    b = [k for k in GA if k[1] == c]
    n = [k for k in SPONSORLESS_A if k[1] == c]
    P('   %-10s %8d %8d %9.1f%% %12d %12d'
      % (c, len(b), len(n), 100.0 * len(n) / len(b),
         sum(len(GA[k]) for k in b), sum(len(GA[k]) for k in n)))

P('\nby chamber:')
P('   %-10s %8s %8s %10s %12s %12s' % ('chamber', 'bills', 'no-spons', 'pct', 'rows', 'rows-no-spons'))
for ch in ('House', 'Senate', 'UNKNOWN'):
    b = [k for k in GA if L.chamber(k[0]) == ch]
    if not b:
        continue
    n = [k for k in SPONSORLESS_A if L.chamber(k[0]) == ch]
    P('   %-10s %8d %8d %9.1f%% %12d %12d'
      % (ch, len(b), len(n), 100.0 * len(n) / len(b),
         sum(len(GA[k]) for k in b), sum(len(GA[k]) for k in n)))

P('\nby chamber x Congress (no-sponsor bills / all bills):')
for ch in ('House', 'Senate', 'UNKNOWN'):
    cells = []
    for c in sorted({k[1] for k in GA}):
        b = [k for k in GA if k[1] == c and L.chamber(k[0]) == ch]
        n = [k for k in SPONSORLESS_A if k[1] == c and L.chamber(k[0]) == ch]
        if b:
            cells.append('%s: %d/%d' % (c, len(n), len(b)))
    if cells:
        P('   %-8s %s' % (ch, '   '.join(cells)))

P('\nrole mix on the ZERO-sponsor bills:')
mix = collections.Counter()
for v in SPONSORLESS_A.values():
    for rr, n in roles(v).items():
        mix[rr] += n
for rr, n in mix.most_common():
    P('   %-22s %d rows' % (rr, n))
P('\nrole mix on bills that DO have a sponsor row:')
mix2 = collections.Counter()
for k, v in GA.items():
    if k in SPONSORLESS_A:
        continue
    for rr, n in roles(v).items():
        mix2[rr] += n
for rr, n in mix2.most_common():
    P('   %-22s %d rows' % (rr, n))

# ------------------------------------------------------------------ grain B
GB = collections.defaultdict(list)          # (bill,congress,category) -> [i]
NO_CAT = 0
for i, r in enumerate(ARCH):
    cat = L.canonical_category(r['Section'])
    if cat is None:
        NO_CAT += 1
        continue
    GB[L.bill_ident(r['Name'], r['Congress']) + (cat,)].append(i)
SPONSORLESS_B = {k: v for k, v in GB.items() if roles(v)['sponsor'] == 0}

bar('S1-b  GRAIN B : (bill, Congress, canonical category) -- the grain archive_leg.json sums on')
P('rows whose Section maps to no canonical category (producer: unknown-section) ... %d' % NO_CAT)
P('(bill,Congress,category) cells ................................................ %d' % len(GB))
P('   with >=1 sponsor-role row .................................................. %d' % (len(GB) - len(SPONSORLESS_B)))
P('   with ZERO sponsor-role rows ................................................ %d   (%.1f%%)'
  % (len(SPONSORLESS_B), 100.0 * len(SPONSORLESS_B) / len(GB)))
P('   member rows riding on a ZERO-sponsor cell .................................. %d'
  % sum(len(v) for v in SPONSORLESS_B.values()))
P('\nbills that have a sponsor row SOMEWHERE but not in every category they appear in:')
partial = {k for k in SPONSORLESS_B if (k[0], k[1]) not in SPONSORLESS_A}
P('   cells ...................................................................... %d' % len(partial))
P('   distinct bills ............................................................. %d' % len({(k[0], k[1]) for k in partial}))
P('   member rows ................................................................ %d'
  % sum(len(GB[k]) for k in partial))
P('   (this is the S.762 pattern: sponsor row exists under other sections only)')
for k in sorted(partial)[:12]:
    other = sorted({L.canonical_category(ARCH[i]['Section']) for i in GA[(k[0], k[1])]
                    if L.canonical_role(ARCH[i]['Role']) == 'sponsor'})
    P('      %-16s C=%-4s missing in %-26s sponsor row present in %s'
      % (ARCH[GB[k][0]]['Name'], k[1], k[2], other))

# ------------------------------------------------- bill-level Sponsor column
bar("S1-c  the archive's bill-level 'Sponsor' column")
P("header of 'All Bills' = %s" % list(ARCH[0].keys()))
pop = sum(1 for r in ARCH if L.clean_sponsor_cell(r.get('Sponsor')))
P("rows with a non-empty Sponsor cell ............................................ %d / %d" % (pop, len(ARCH)))
spon_names = {}
multi = []
for k, idxs in GA.items():
    vals = sorted({L.clean_sponsor_cell(ARCH[i].get('Sponsor')) for i in idxs} - {''})
    spon_names[k] = vals
    if len(vals) > 1:
        multi.append((k, vals))
P("(bill,Congress) with exactly one Sponsor spelling ............................. %d"
  % sum(1 for v in spon_names.values() if len(v) == 1))
P("(bill,Congress) with NO Sponsor value at all .................................. %d"
  % sum(1 for v in spon_names.values() if len(v) == 0))
P("(bill,Congress) with >1 distinct Sponsor spelling ............................. %d" % len(multi))
for k, v in multi[:8]:
    P('      %-16s C=%-4s %s' % (ARCH[GA[k][0]]['Name'], k[1], v))

resolved = {}
for k, vals in spon_names.items():
    got = sorted({RES.resolve(v) for v in vals} - {None})
    resolved[k] = got[0] if len(got) == 1 else None
    if len(got) > 1:
        resolved[k] = 'AMBIGUOUS'
named = [k for k, v in spon_names.items() if v]
inroster = [k for k in named if isinstance(resolved[k], str) and resolved[k] != 'AMBIGUOUS']
P('\nSponsor cell -> 533-member roster (re-implemented fec/members/member_identity.Resolver):')
P('   (bill,Congress) with a Sponsor name .......................................... %d' % len(named))
P('   resolves to a current roster member .......................................... %d' % len(inroster))
P('   refuses (person not in the roster, or ambiguous) .............................. %d'
  % (len(named) - len(inroster)))

# does the named sponsor have a sponsor-role member row?
# NOTE: the producer records audit['member'] only AFTER its exclusion gates (LIVE producer
# lines 168-179: unknown-section / excluded-title run BEFORE matchmember, excluded-override
# after but without recording the name), so audit['member'] is absent on excluded rows and
# cannot be used here.  Resolve the Member cell directly; S2-0 proves the transcribed
# Resolver reproduces the producer's resolution wherever the producer recorded one.
def sponsor_role_members(idxs):
    return {RES.resolve(ARCH[i]['Member']) for i in idxs
            if L.canonical_role(ARCH[i]['Role']) == 'sponsor'} - {None}


gap_A, gap_B = [], []
for k in inroster:
    who = resolved[k]
    if who not in sponsor_role_members(GA[k]):
        gap_A.append(k)
for k, idxs in GB.items():
    base = (k[0], k[1])
    who = resolved.get(base)
    if isinstance(who, str) and who != 'AMBIGUOUS' and who not in sponsor_role_members(idxs):
        gap_B.append(k)
P('\nthe named sponsor IS a current roster member but has NO sponsor-role member row:')
P('   grain A  (bill,Congress) ..................................................... %d / %d  (%.1f%%)'
  % (len(gap_A), len(inroster), 100.0 * len(gap_A) / len(inroster)))
P('   grain B  (bill,Congress,category) ............................................ %d / %d'
  % (len(gap_B), sum(1 for k in GB if isinstance(resolved.get((k[0], k[1])), str)
                     and resolved.get((k[0], k[1])) != 'AMBIGUOUS')))
P('   member rows riding on those grain-A bills .................................... %d'
  % sum(len(GA[k]) for k in gap_A))

P('\nfirst 15 grain-A gaps (bill / Congress / Sponsor cell / resolved / roles actually present):')
for k in sorted(gap_A)[:15]:
    P('   %-16s C=%-4s %-34s -> %-22s %s'
      % (ARCH[GA[k][0]]['Name'], k[1], (spon_names[k] or [''])[0][:34], resolved[k],
         sorted(roles(GA[k]))))

# ------------------------------------------------------------------ frame note
bar('S1-d  FRAME NOTE : the producer scores archive + sentinel-verified + manual, not the archive alone')
SENT = L.sentinel_scoring_rows()
MAN = L.manual_rows()
P('sentinel verified scoring rows ................................................ %d' % len(SENT))
P('   of which Role canonicalizes to sponsor ..................................... %d'
  % sum(1 for r in SENT if L.canonical_role(r.get('Role')) == 'sponsor'))
P('manual_bill_evidence.csv rows ................................................. %d' % len(MAN))
P('   of which Role canonicalizes to sponsor ..................................... %d'
  % sum(1 for r in MAN if L.canonical_role(r.get('Role')) == 'sponsor'))
frame_sponsor = collections.defaultdict(set)     # (bill,congress) -> roles from the whole frame
for r in ARCH:
    frame_sponsor[L.bill_ident(r['Name'], r['Congress'])].add(L.canonical_role(r['Role']))
for r in SENT:
    frame_sponsor[L.bill_ident(r.get('Bill'), r.get('Congress'))].add(L.canonical_role(r.get('Role')))
for r in MAN:
    frame_sponsor[L.bill_ident(r.get('Bill'), r.get('Congress'))].add(L.canonical_role(r.get('Role')))
rescued = [k for k in SPONSORLESS_A if 'sponsor' in frame_sponsor.get(k, set())]
P('\n(bill,Congress) sponsorless in the ARCHIVE but given a sponsor row by sentinel/manual .. %d'
  % len(rescued))
for k in sorted(rescued)[:10]:
    P('      %-18s C=%s' % (k[0], k[1]))
P('=> archive-only sponsorless bills that stay sponsorless in the scored frame ........... %d'
  % (len(SPONSORLESS_A) - len(rescued)))

# ------------------------------------------------------------------ state out
state = {
    'selected_archive': L.SEL_ARCHIVE,
    'archive_rows': len(ARCH),
    'grainA_bills': len(GA),
    'grainA_sponsorless': sorted(['%s|%s' % k for k in SPONSORLESS_A]),
    'grainA_sponsorless_rows': sum(len(v) for v in SPONSORLESS_A.values()),
    'grainB_cells': len(GB),
    'grainB_sponsorless': sorted(['%s|%s|%s' % k for k in SPONSORLESS_B]),
    'sponsor_cell': {'%s|%s' % k: v for k, v in spon_names.items()},
    'sponsor_resolved': {'%s|%s' % k: v for k, v in resolved.items()},
    'gapA': sorted(['%s|%s' % k for k in gap_A]),
    'gapB': sorted(['%s|%s|%s' % k for k in gap_B]),
    'rescued_by_frame': sorted(['%s|%s' % k for k in rescued]),
}
with open(os.path.join(HERE, 's1_state.json'), 'w', encoding='utf-8') as fh:
    json.dump(state, fh, indent=1, sort_keys=True)
P('\nwrote s1_state.json')
