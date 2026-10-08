"""Read-only PAC candidate-spending audit; all new evidence stays here."""
import sys, json, hashlib, re
from pathlib import Path
from collections import defaultdict, Counter
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'mentat/app'))
from graph_data import activity_xml_rows

def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, default=str), encoding='utf-8')

def inventory():
    directory = Path(json.loads((ROOT/'mentat/config/report-directory.json').read_text())['directory'])
    allrows, summaries = [], []
    for path in directory.glob('*Industry Spending Overview.xlsx'):
        if path.name.startswith('~$'): continue
        before = (path.stat().st_size, path.stat().st_mtime_ns)
        metadata = {}
        raw = list(activity_xml_rows(path, metadata))
        groups = {}
        for row in raw:
            identity = (str(row['cycle'])[-4:], row['source_committee_id'], row['candidate_id'], row['support_oppose'])
            target = groups.setdefault(identity, {'report':path.name, 'cycle':identity[0], 'committee':identity[1], 'candidate_id':identity[2], 'direction':identity[3], 'candidate':row['candidate_officeholder'], 'amount':Decimal(0), 'rows':0, 'unverified':0, 'unresolved':0})
            target['amount'] += Decimal(str(row['net_included_amount']))
            target['rows'] += 1
            target['unverified'] += int(row.get('unverified_version_rows') or 0)
            target['unresolved'] += int(row.get('unresolved_version_rows') or 0)
        assert before == (path.stat().st_size, path.stat().st_mtime_ns)
        allrows.extend(groups.values())
        summary = {'report':path.name, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'raw_rows':len(raw), 'groups':len(groups), 'directions':dict(Counter(r['direction'] for r in groups.values())), 'ie_units':len({(r['cycle'],r['committee']) for r in groups.values() if r['direction'] in ('Support','Oppose')}), 'note':metadata.get('note')}
        summaries.append(summary)
        print(json.dumps(summary), flush=True)
    dump('report_inventory.json',summaries)
    dump('report_activity.json', allrows)
    unique = defaultdict(list)
    for r in allrows: unique[r['cycle'],r['committee'],r['candidate_id'],r['direction']].append(r)
    conflicts = [v for v in unique.values() if len({r['amount'] for r in v})>1]
    ies = [v[0] for v in unique.values() if v[0]['direction'] in ('Support','Oppose')]
    dump('cross_report_conflicts.json',conflicts)
    dump('independent_spending.json',ies)
    print('UNIQUE IE',len(ies),'UNITS',len({(r['committee'],r['cycle']) for r in ies}),'CONFLICTS',len(conflicts),flush=True)
    print('CULAC',json.dumps([r for r in allrows if r['committee']=='C00007880' and r['direction'] in ('Support','Oppose')],default=str),flush=True)

if __name__ == '__main__': inventory()
