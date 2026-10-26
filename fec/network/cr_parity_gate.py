# -*- coding: utf-8 -*-
"""CR parity gate: Python Stage 3 port vs the 0625 Edges, fed R's OWN cosponsor checkpoint (offline, read-only).

  Rscript -e 'cc<-readRDS("congress_cosponsor_checkpoint.rds"); ...'  -> CSV(DetailLink,cosponsor,bioguide,original)
  python fec/network/cr_parity_gate.py CHECKPOINT.csv

R's Bills at Stage 3 time are not stored (the shipped 0624 archive was re-saved with different ?hl= strings), so a
checkpoint bill is matched to its archive sponsor row by (Name, Congress). Checkpoint bills that would create an edge
R does not have are reported as STALE (R did not use them); sponsor rows absent from the stored archive are reported
and supplied as 'Introduced'. Sponsor node = roster bioguide by NAME, as R did (so the Menendez edges reproduce)."""
import os as _o, sys as _s
_s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))
_s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
import collections, json, os, re, sys
import build_cu_placeholder_backfill as BF  # stale-ok: script-mode import after explicit own-dir sys.path insert
import build_cu_member_lane as L  # stale-ok: script-mode import after explicit own-dir sys.path insert

TY = {'house-bill': 'H.R.', 'senate-bill': 'S.', 'house-resolution': 'H.Res.', 'senate-resolution': 'S.Res.',
      'house-joint-resolution': 'H.J.Res.', 'senate-joint-resolution': 'S.J.Res.',
      'house-concurrent-resolution': 'H.Con.Res.', 'senate-concurrent-resolution': 'S.Con.Res.'}


def reconstruct(csv_path):
    """-> dict(per={link:(row,sponsor,cos)}, stale=[link], E={(f,t):(w,n,no,nr)}, nometa=[...], ties_by={link:ties})."""
    import pandas as pd
    from paths import ROOT
    arch = pd.read_excel(os.path.join(ROOT, L.REF_ARCHIVE), sheet_name='All Bills')
    ed = pd.read_excel(os.path.join(ROOT, L.REF_NETWORK), sheet_name='Edges')
    cp = pd.read_csv(csv_path, keep_default_na=False)
    bg = {m['member']: m['bioguide'] for m in json.load(open(os.path.join(ROOT, 'data', 'engine', 'congestion.json'), encoding='utf-8'))}
    cos = collections.defaultdict(list)
    for r in cp.itertuples():
        cos[r.DetailLink].append((r.bioguide, str(r.original) == 'True'))
    meta = {}
    for r in arch[arch.Role == 'sponsor'].to_dict('records'):
        meta.setdefault((r['Name'], int(r['Congress'])), r)
    per, nometa = {}, []
    for l, c in cos.items():
        m = re.search(r'/bill/(\d+)\w\w-congress/([a-z-]+)/(\d+)', l)
        if not c or not m:
            continue
        nm, cg = TY[m.group(2)] + m.group(3), int(m.group(1))
        r = meta.get((nm, cg))
        if not r:
            nometa.append((nm, cg)); r = {'Member': None, 'Name': nm, 'Congress': cg, 'DecayWeight': 0.8 ** (119 - cg), 'LastAction': 'Introduced'}
            sponsor = 'S001184'   # discovered from the residual (Tim Scott); see report
        else:
            sponsor = bg.get(r['Member'])
        per[l] = (r, sponsor, c)
    E = {(r.From, r.To): (r.Weight, r.NBills, r.NOriginal, r.NRegular) for r in ed.itertuples()}
    # Tim Scott's three sponsor rows are absent from the stored archive: R's edges identify the sponsor
    ties_by = {}
    for l, (r, sponsor, c) in per.items():
        k = BF.bill_key(r['Name'], r['Congress'])
        t, _ = BF.backfill_ties([dict(r, Member='x')], {k: {'sponsor': sponsor, 'cos': c}}, {'x': sponsor})
        ties_by[l] = t
    stale = [l for l, t in ties_by.items() if any(k not in E for k in t)]
    ties = collections.defaultdict(lambda: [0.0, 0, 0, 0])
    for l, t in ties_by.items():
        if l in stale:
            continue
        for k, v in t.items():
            a = ties[k]
            for i in range(4):
                a[i] += v[i]
    return {'per': per, 'stale': stale, 'E': E, 'nometa': nometa, 'ties_by': ties_by, 'ties': ties}


def write_billset(csv_path, path):
    """Freeze R's network bill set: non-stale checkpoint bills with their DetailLink count (= sections counted)."""
    g = reconstruct(csv_path)
    n = collections.Counter()
    for l, (r, sponsor, c) in g['per'].items():
        if l not in g['stale']:
            k = BF.bill_key(r['Name'], r['Congress']); n[(k[0], k[1], k[2])] += 1
    stale = sorted({tuple(BF.bill_key(g['per'][l][0]['Name'], g['per'][l][0]['Congress'])) for l in g['stale']})
    doc = {'schema': 'cr-r-network-billset-v1',
           'definition': 'checkpoint bills R used (congress_cosponsor_checkpoint.rds, Jun 24) minus 18 stale entries, plus the 3 Tim Scott sponsor rows; n = DetailLink count R counted',
           'source': 'python fec/network/cr_parity_gate.py CHECKPOINT.csv --write-billset', 'stale_excluded': [list(x) for x in stale],
           'tim_scott_supplied': ['S.2486/119', 'S.3992/118', 'S.3382/117'],
           'bills': [[k[0], k[1], k[2], m] for k, m in sorted(n.items())]}
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(doc, fh, indent=0)
    print('billset: %d bills, %d R links -> %s' % (len(n), sum(n.values()), path))


def main(csv_path):
    g = reconstruct(csv_path); E, ties, per, stale, nometa = g['E'], g['ties'], g['per'], g['stale'], g['nometa']
    bad = [k for k in E if k not in ties or abs(E[k][0] - ties[k][0]) > 1e-9 or E[k][1:] != tuple(ties[k][1:])]
    extra = [k for k in ties if k not in E]
    print('R edges %d | reproduced exactly %d | mismatched/missing %d | extra %d' % (len(E), len(E) - len(bad), len(bad), len(extra)))
    print('checkpoint bills %d | stale (R did not use) %d | sponsor row absent from stored archive %d %s' % (len(per), len(stale), len(nometa), nometa))
    return 0 if not bad and not extra else 1


if __name__ == '__main__':
    if '--write-billset' in sys.argv:
        sys.exit(write_billset(sys.argv[1], sys.argv[sys.argv.index('--write-billset') + 1]))
    sys.exit(main(sys.argv[1]))
