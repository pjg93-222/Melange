# -*- coding: utf-8 -*-
"""G1/SRC-1 sourcing census (read-only) - holistic-network v1 evaluation.
Counts bills per congress x type in (a) the local govinfo BILLSTATUS bulk archive
(zip entry listings, nothing extracted) and (b) the BICAM snapshot bills.csv (streamed).
Self-denominator: bill numbers are sequential per type+congress, so max(number)
approximates introduced count; gap = max - files. Official congress.gov cross-check
is a separate step. stdlib only; no fec imports; writes census_g1_results.json."""
import os, re, csv, json, zipfile, collections, datetime

RAW = os.path.join(os.environ['LOCALAPPDATA'], r'Melange\lda_rebuild\raw')
BICAM_BILLS = r'C:\melange-data\bicam_snapshot\extracted\bicam_bills\bills.csv'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'census_g1_results.json')
CONGS = (117, 118, 119)

res = {'billstatus': {}, 'bicam': {}, 'notes': []}
pat = re.compile(r'BILLSTATUS-(\d+)([a-z]+)(\d+)\.xml$', re.I)
for cg in CONGS:
    d = os.path.join(RAW, 'billstatus%d' % cg)
    for zp in sorted(os.listdir(d)):
        if not zp.lower().endswith('.zip'):
            continue
        zpath = os.path.join(d, zp)
        mt = datetime.datetime.utcfromtimestamp(os.path.getmtime(zpath)).strftime('%Y-%m-%d')
        with zipfile.ZipFile(zpath) as z:
            names = z.namelist()
        nums = []; bad = 0
        for n in names:
            m = pat.search(n)
            if m: nums.append(int(m.group(3)))
            else: bad += 1
        bt = zp.replace('BILLSTATUS-%d-' % cg, '').replace('.zip', '').lower()
        res['billstatus']['%d/%s' % (cg, bt)] = {
            'files': len(nums), 'max_number': max(nums) if nums else 0,
            'gap': (max(nums) - len(nums)) if nums else 0,
            'nonmatching_entries': bad, 'first_entry': names[0] if names else None,
            'zip_vintage_utc': mt}

bic = collections.defaultdict(lambda: {'rows': 0, 'max_number': 0})
tot = collections.Counter()
with open(BICAM_BILLS, encoding='utf-8', errors='replace', newline='') as fh:
    for row in csv.DictReader(fh):
        try: cg = int(float(row['congress']))
        except (ValueError, TypeError, KeyError): continue
        tot[cg] += 1
        if cg in CONGS:
            bt = (row['bill_type'] or '').lower()
            try: bn = int(float(row['bill_number']))
            except (ValueError, TypeError): bn = 0
            k = '%d/%s' % (cg, bt); bic[k]['rows'] += 1
            if bn > bic[k]['max_number']: bic[k]['max_number'] = bn
res['bicam'] = {k: dict(v) for k, v in sorted(bic.items())}
res['bicam_all_congress_rowcounts'] = {str(k): tot[k] for k in sorted(tot)}

print('%-14s %9s %8s %5s | %10s %8s | %s' % ('stratum','BS_files','BS_max','gap','BICAM_rows','BI_max','BS_vintage'))
for k in sorted(set(res['billstatus']) | set(res['bicam'])):
    b = res['billstatus'].get(k, {}); c = res['bicam'].get(k, {})
    print('%-14s %9s %8s %5s | %10s %8s | %s' % (k, b.get('files','-'), b.get('max_number','-'),
          b.get('gap','-'), c.get('rows','-'), c.get('max_number','-'), b.get('zip_vintage_utc','-')))
print('TOTALS 117-119: BILLSTATUS files=%d | BICAM rows=%d' % (
    sum(v['files'] for v in res['billstatus'].values()), sum(v['rows'] for v in res['bicam'].values())))
print('BICAM congress row-counts (all): %s' % {k: tot[k] for k in sorted(tot)})
json.dump(res, open(OUT, 'w', encoding='utf-8'), indent=1)
print('wrote', OUT)