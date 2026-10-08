# -*- coding: utf-8 -*-
"""Lane F1 / addendum : the inverse gap -- sponsor rows the scored frame HAS that the workbook
sheet 'Sponsor Interactions' does not, i.e. how stale the sheet is relative to the chain."""
import collections, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f1_lib as L
P = print
WBS = L.xl(L.WORKBOOK, 'Sponsor Interactions')
ARCH = L.xl(L.SEL_ARCHIVE, 'All Bills')
SENT = L.sentinel_scoring_rows()
MAN = L.manual_rows()

def trip(member, bill, congress, section):
    return (str(member or '').strip(), L.bill_ident(bill, congress), L.canonical_category(section))

wb = {trip(r['Member'], r['Name'], r['Congress'], r['Section']) for r in WBS}
src = {}
for r in ARCH:
    if L.canonical_role(r['Role']) == 'sponsor':
        src.setdefault(trip(r['Member'], r['Name'], r['Congress'], r['Section']), set()).add('selected-archive')
for r in SENT:
    if L.canonical_role(r.get('Role')) == 'sponsor':
        src.setdefault(trip(r.get('Member'), r.get('Bill'), r.get('Congress'), r.get('Section')), set()).add('sentinel-verified')
for r in MAN:
    if L.canonical_role(r.get('Role')) == 'sponsor':
        src.setdefault(trip(r.get('Member'), r.get('Bill'), r.get('Congress'), r.get('Category')), set()).add('manual-evidence')
missing = {k: v for k, v in src.items() if k not in wb}
P('=' * 100)
P("ADDENDUM  sponsor rows in the SCORED FRAME that the workbook sheet does not carry")
P('=' * 100)
P('scored-frame sponsor keys .................... %d' % len(src))
P('present in the workbook ..................... %d' % sum(1 for k in src if k in wb))
P('ABSENT from the workbook .................... %d' % len(missing))
P('\nby source lane:')
for s, n in collections.Counter(frozenset(v) for v in missing.values()).most_common():
    P('   %-40s %d' % ('+'.join(sorted(s)), n))
P('\nby Congress:')
for c, n in sorted(collections.Counter(k[1][1] for k in missing).items()):
    P('   C=%-5s %d' % (c, n))
P('\nevery absent key:')
for k, v in sorted(missing.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    P('   %-26s %-22s C=%-5s %-26s %s' % (k[0], k[1][0], k[1][1], k[2], '+'.join(sorted(v))))
