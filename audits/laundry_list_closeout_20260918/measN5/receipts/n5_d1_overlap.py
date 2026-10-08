# -*- coding: utf-8 -*-
"""N5 / D1 (READ-ONLY): the OTHER desk surface that already renders bills from the
routing audit -- the honors per-field ACTION LEDGER (make_member_desk_00.tpl:575-594,
actionLedger()) -- measured against the role-sheet Bills ledger, from the SHIPPED bundle.
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n5_lib as N
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
W = print

BUNDLE = N.P('member_desk_bundle.json')
D = json.load(open(BUNDLE, encoding='utf-8'))
W('=' * 102)
W('N5 / D1  OVERLAP: honors per-field ACTION LEDGER vs the role-sheet BILLS ledger')
W('=' * 102)
W('bundle top-level keys (%d): %s' % (len(D), sorted(D.keys())))
for k in sorted(D):
    if 'audit' in k.lower() or 'integrity' in k.lower():
        v = D[k]
        W('\n--- %s ---' % k)
        if isinstance(v, dict):
            for kk in sorted(v):
                if str(kk).startswith('bill') or 'excl' in str(kk):
                    W('   %-50s %s' % (kk, json.dumps(v[kk])[:220]))
W('\nrank_honors keys: %s' % sorted((D.get('rank_honors') or {}).keys()))
RH = D.get('rank_honors') or {}
W('measure_titles present: %s (n=%s)' % ('measure_titles' in RH, len(RH.get('measure_titles') or {})))

ms = D['members']
W('\nmembers with an effectiveness_shadow_html field at all: %d / %d (renders at tpl:1771)'
  % (sum(1 for m in ms if m.get('effectiveness_shadow_html')), len(ms)))

acts = collections.Counter()
kinds = collections.Counter()
led_keys = collections.defaultdict(set)      # member -> {(measure, role)}
led_bills = collections.defaultdict(set)     # member -> {measure}  for kind == legislative
per_member_rows = collections.Counter()
have_honors = 0
for m in ms:
    h = m.get('honors') or {}
    fields = h.get('fields') or {}
    if fields:
        have_honors += 1
    for cat, cell in fields.items():
        for a in (cell or {}).get('field_actions') or []:
            acts[cat] += 1
            kinds[a.get('k')] += 1
            per_member_rows[m['name']] += 1
            led_keys[m['name']].add((a.get('m'), a.get('k'), a.get('r')))
            if a.get('k') == 'legislative':
                # the ledger's measure id IS the repository key '<congress>:<type>:<number>'
                led_bills[m['name']].add(str(a.get('m') or '').strip().lower())
W('members carrying honors.fields                        : %d' % have_honors)
W('total field_action rows across the page               : %d' % sum(acts.values()))
W('field_action rows by KIND                             : %s' % dict(kinds.most_common()))
W('members with >=1 field_action row                     : %d' % len(per_member_rows))
W('distinct (measure, kind, role) ledger entries         : %d'
  % sum(len(v) for v in led_keys.values()))
W('distinct legislative measures per member (sum)        : %d'
  % sum(len(v) for v in led_bills.values()))

DESK = N.shipped_desk_ledger()


def wide_key(bill, congress):
    """'<congress>:<type>:<number>' for EVERY measure type the two surfaces carry,
    amendments included (the honors ledger uses e.g. '119:samdt:6241', while the desk's
    own Bills-repository identity at tpl:1951 deliberately drops amendments)."""
    import re
    raw = re.sub(r'[^A-Za-z0-9]', '', str(bill or '')).upper()
    m = re.match(r'^([A-Z]+)(\d+)$', raw)
    if not m:
        return None
    c = N.cong(congress)
    return '%s:%s:%d' % (c, m.group(1).lower(), int(m.group(2))) if c else None


bills_by_member = {}
unkeyable = collections.Counter()
amdt_rows = 0
for nm, rows in DESK.items():
    s = set()
    for b in rows:
        if 'AMDT' in N.norm_bill(b['bill']):
            amdt_rows += 1
        rk = wide_key(b['bill'], b['congress'])
        if rk:
            s.add(rk)
        else:
            unkeyable[nm] += 1
    bills_by_member[nm] = s
W('\ndesk bill rows that are AMENDMENTS (H.Amdt./S.Amdt.): %d' % amdt_rows)
W('desk bill rows the desk\'s OWN Bills-repository identity (tpl:1951) cannot key,')
W('   so they appear in the per-member Bills panel but NOT in the global Bills view: %d'
  % sum(1 for nm, rows in DESK.items() for b in rows if not N.repo_key(b['bill'], b['congress'])))
W('desk bill rows with no key at all under the wide identity: %d' % sum(unkeyable.values()))
W('\nBILLS section (legHTML/legBody) rows                  : %d across %d members'
  % (sum(len(v) for v in DESK.values()), sum(1 for v in DESK.values() if v)))
both = inter = only_bills = only_ledger = 0
examples_only_ledger = []
for nm in set(bills_by_member) | set(led_bills):
    b = bills_by_member.get(nm, set())
    l = led_bills.get(nm, set())
    inter += len(b & l)
    only_bills += len(b - l)
    only_ledger += len(l - b)
    for x in sorted(l - b)[:2]:
        if len(examples_only_ledger) < 15:
            examples_only_ledger.append((nm, x))
W('\nOVERLAP on (member, bill-number) between the two surfaces:')
W('   in BOTH the Bills section and the honors action ledger : %d' % inter)
W('   only in the Bills section (role sheets + sidecars)     : %d' % only_bills)
W('   only in the honors action ledger (routing audit)       : %d' % only_ledger)
W('   examples only in the action ledger: %s' % examples_only_ledger[:10])
W('\n   NOTE: the action ledger is per-FIELD (one table per legislative area inside the')
W('   honors block) and shows Measure / Title / Kind / Role / Direction / Contribution;')
W('   the Bills section is per-MEMBER and shows role badge / bill / Congress / title /')
W('   areas / sponsor / cosponsor count / summary / Congress.gov link.')
W('\nDONE')
