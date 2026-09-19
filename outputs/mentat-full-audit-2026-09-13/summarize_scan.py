import hashlib
import json
from pathlib import Path
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8-sig'))
inventory=read('source-manifest.json')
changed=[]
for item in inventory:
    path=ROOT/item['path']
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:changed.append(item['path'])
books=read('workbook-scan.json')
roster=read('roster-readiness.json')
summary={'files_fingerprinted':len(inventory),'source_files_changed_since_start':changed,
    'workbooks':len(books),'worksheets':sum(len(b.get('sheets',[])) for b in books),
    'worksheet_rows':sum(s['rows'] for b in books for s in b.get('sheets',[])),
    'formula_cells':sum(s['formula_cells'] for b in books for s in b.get('sheets',[])),
    'stored_error_cells':sum(s['error_count'] for b in books for s in b.get('sheets',[])),
    'broken_reference_formulas':sum(len(s['broken_formula_refs']) for b in books for s in b.get('sheets',[])),
    'formulas_without_nonempty_cache':sum(s['formula_missing_cache'] for b in books for s in b.get('sheets',[])),
    'workbooks_unchanged':all(b.get('unchanged_during_scan') for b in books),
    'roster_industries':roster['industry_count'],'roster_companies':sum(r['company_count'] for r in roster['readiness']),
    'roster_variants':sum(r['variant_count'] for r in roster['readiness']),'roster_status':roster['status'],
    'accepted_snapshot_count':len(read('accepted-state-checks.json')),
    'accepted_facts':sum(s['facts'] for s in read('accepted-state-checks.json'))}
(OUT/'scan-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
status=subprocess.run(['git','status','--porcelain=v1','-uno'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(OUT/'git-status-final.txt').write_bytes(status.stdout)
print(json.dumps(summary,indent=2))
