# -*- coding: utf-8 -*-
"""CR edge-growth attribution: 0625 Edges (R, June inputs) -> the lane's new network, by congress and by cause.

Offline, read-only. Starts from the parity-gate reconstruction of R's 2,214 edges (R's own cosponsor checkpoint) and
walks to the lane network one cause at a time, recomputing Stage 3 weights per bill (backfill_ties) at each step:
  S0  R as built (June cosponsors, June LastAction, sponsor mapped by NAME, a bill counted once per DetailLink)
  S0b sponsor identity / roster: BILLSTATUS sponsor bioguide; bills whose sponsor is off the roster drop out
  S1  new cosponsorships: BILLSTATUS cosponsor lists (adds, drops, original flags, C for sqrt)
  S2  passed-chamber status: LastAction recomputed from BILLSTATUS (moves the x3 factor)
  S2b section de-dup: R counted a bill once per ?hl= link; the lane counts it once
  S3  bills R never used: glossary-bug natives, stale/never-scraped (adds edges)
S3 must equal the lane network exactly (asserted).
  python fec/network/cr_edge_growth.py CHECKPOINT.csv RUN_DIR [--legacy]
Default mode = the lane's R-faithful network (S2b and S3 are no-ops, final state = S2). --legacy = archive bill set, dedupe."""
import os as _o, sys as _s
_s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))
_s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
import collections, json, os, sys
import build_cu_placeholder_backfill as BF  # stale-ok: script-mode import after explicit own-dir sys.path insert
import build_cu_member_lane as L  # stale-ok: script-mode import after explicit own-dir sys.path insert
import cr_parity_gate as PG  # stale-ok: script-mode import after explicit own-dir sys.path insert

CAUSES = ['S0b identity/roster', 'S1 new cosponsorships', 'S2 passed-status (x3)', 'S2b section de-dup', 'S3 bills R never used']


def bill_w(k, sponsor, cos, la):
    r = {'Name': L.bill_name(k[1], k[2]), 'Congress': k[0], 'DecayWeight': L.decay(k[0]), 'LastAction': la, 'Member': 'x'}
    t, _ = BF.backfill_ties([r], {k: {'sponsor': sponsor, 'cos': cos}}, {'x': sponsor})
    return {(f, to, k[0]): v[0] for (f, to), v in t.items()}


def add(acc, d):
    for key, w in d.items():
        acc[key] += w


def k3(name, congress):
    k = BF.bill_key(name, congress)
    return (k[0], k[1], k[2])


def main(csv_path, run_dir, raw_root=None, legacy=False):
    from paths import ROOT
    g = PG.reconstruct(csv_path)
    roster, _ = L.load_roster(ROOT)
    raw_root = raw_root or os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Melange', 'lda_rebuild', 'raw')
    seed, order = L.section_seed([os.path.join(ROOT, p) for p in L.SEED_ARCHIVES])
    need = set(seed)
    rkeys = {}
    for l, (r, sponsor, c) in g['per'].items():
        if l in g['stale']:
            continue
        k = k3(r['Name'], r['Congress'])
        rkeys.setdefault(k, []).append((r, sponsor, c)); need.add(k)
    bills, refused = L.read_bills(raw_root, list(need))
    rows = L.archive_rows(seed, bills, roster, order)
    new_la = {k3(r['Name'], r['Congress']): r['LastAction'] for r in rows}
    W = [collections.defaultdict(float) for _ in range(6)]
    notes = collections.Counter()
    for k, lst in rkeys.items():
        b = bills.get(k)
        for r, sponsor, c in lst:
            la_old = r['LastAction']
            add(W[0], bill_w(k, sponsor, c, la_old))
            if not b:
                notes['R link-bills not in BILLSTATUS/seed (dropped at S0b)'] += 1; continue
            sp = (b['sponsor'] or {}).get('bioguide')
            if sp not in roster:
                notes['R link-bills with sponsor off roster (dropped at S0b)'] += 1; continue
            add(W[1], bill_w(k, sp, c, la_old))
            cos_new = [(x['bioguide'], x['original']) for x in b['cos']]
            add(W[2], bill_w(k, sp, cos_new, la_old))
            add(W[3], bill_w(k, sp, cos_new, new_la.get(k, la_old)))
            notes['R link-bills'] += 1
            if set(c) != set(cos_new):
                notes['R link-bills with changed cosponsor list'] += 1
            if bool(BF.PASSED_RE.search(la_old)) != bool(BF.PASSED_RE.search(new_la.get(k, la_old))):
                notes['R link-bills with passed-status flip'] += 1
        if legacy and b and (b['sponsor'] or {}).get('bioguide') in roster:   # one copy per bill (section de-dup)
            add(W[4], bill_w(k, b['sponsor']['bioguide'], [(x['bioguide'], x['original']) for x in b['cos']], new_la.get(k, lst[0][0]['LastAction'])))
    if legacy:
        edges, _, labels = L.network_edges('archive', 'dedupe', rows, bills, roster, seed)
    else:
        edges, _, labels = L.network_edges('r', 'per-section', rows, bills, roster, seed)
        W[4] = W[3]
    for key, w in W[4].items():
        W[5][key] += w
    seenb = set()
    for r in (rows if legacy else []):
        k = k3(r['Name'], r['Congress'])
        if r['Role'] == 'sponsor' and k not in seenb:
            seenb.add(k)
            if k not in rkeys:
                b = bills[k]
                add(W[5], bill_w(k, b['sponsor']['bioguide'], [(x['bioguide'], x['original']) for x in b['cos']], r['LastAction']))
                notes['bills new to R (S3)'] += 1
    final = collections.defaultdict(float)
    for (f, t, c), w in W[5].items():
        final[(f, t)] += w
    actual = {(e['From'], e['To']): e['Weight'] for e in edges}
    assert set(final) == set(actual) and all(abs(final[k] - actual[k]) < 1e-9 for k in actual), 'S3 != lane network'
    s0 = collections.defaultdict(float)
    for (f, t, c), w in W[0].items():
        s0[(f, t)] += w
    out = {'notes': dict(notes), 'by_congress': {}}
    for c in L.CONGRESSES:
        cells = lambda S: {k: w for k, w in S.items() if k[2] == c and w > 0}
        a, z = cells(W[0]), cells(W[5])
        out['by_congress'][c] = {'cells_R': len(a), 'cells_new': len(z), 'added': len(set(z) - set(a)),
                                 'removed': len(set(a) - set(z)),
                                 'changed_1e-9': sum(1 for k in set(a) & set(z) if abs(a[k] - z[k]) > 1e-9),
                                 'weight_R': round(sum(a.values()), 2), 'weight_new': round(sum(z.values()), 2)}
    cause_w = {c: collections.defaultdict(float) for c in CAUSES}
    cause_node = {c: collections.defaultdict(float) for c in CAUSES}
    for i, cname in enumerate(CAUSES):
        for key in set(W[i]) | set(W[i + 1]):
            d = W[i + 1].get(key, 0.0) - W[i].get(key, 0.0)
            if abs(d) > 1e-12:
                cause_w[cname][key[2]] += d
                cause_node[cname][key[0]] += d; cause_node[cname][key[1]] += d
    out['weight_delta_by_cause_and_congress'] = {c: {str(k): round(v, 2) for k, v in sorted(d.items())} for c, d in cause_w.items()}

    def dom(key):
        best, bw = None, 0.0
        for i, cname in enumerate(CAUSES):
            d = sum(W[i + 1].get((key[0], key[1], c), 0.0) - W[i].get((key[0], key[1], c), 0.0) for c in L.CONGRESSES)
            if abs(d) > abs(bw):
                best, bw = cname, d
        return best
    cls = {'added': collections.Counter(), 'removed': collections.Counter(), 'changed': collections.Counter()}
    for key in set(s0) | set(actual):
        a, z = s0.get(key, 0.0), actual.get(key, 0.0)
        if a == 0 and z > 0:
            cls['added'][dom(key)] += 1
        elif a > 0 and z == 0:
            cls['removed'][dom(key)] += 1
        elif abs(a - z) > 1e-9:
            cls['changed'][dom(key)] += 1
    out['edge_pairs_by_dominant_cause'] = {k: dict(v, total=sum(v.values())) for k, v in cls.items()}
    wo0, wi0, wo1, wi1 = (collections.defaultdict(float) for _ in range(4))
    for (f, t), w in s0.items():
        wo0[f] += w; wi0[t] += w
    for (f, t), w in actual.items():
        wo1[f] += w; wi1[t] += w
    mem = []
    for n in set(wo0) | set(wi0) | set(wo1) | set(wi1):
        dout, din = wo1[n] - wo0[n], wi1[n] - wi0[n]
        causes = {c: cause_node[c].get(n, 0.0) for c in CAUSES}
        mem.append({'node': n, 'label': labels.get(n, n), 'dWeightedOut': round(dout, 2), 'dWeightedIn': round(din, 2),
                    'dTotal': round(dout + din, 2), 'WeightedOut_R': round(wo0[n], 2), 'WeightedOut_new': round(wo1[n], 2),
                    'WeightedIn_R': round(wi0[n], 2), 'WeightedIn_new': round(wi1[n], 2),
                    'main_cause': max(causes, key=lambda c: abs(causes[c]))})
    mem.sort(key=lambda m: -abs(m['dTotal']))
    out['top10_weighted_degree_change'] = mem[:10]
    with open(os.path.join(run_dir, 'cr_edge_growth.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1], sys.argv[2], legacy='--legacy' in sys.argv))
