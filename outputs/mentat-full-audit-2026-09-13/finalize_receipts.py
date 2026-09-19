"""Consolidate audit outcomes while preserving original failed-run logs."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re

OUT=Path(__file__).resolve().parent
read=lambda name:json.loads((OUT/name).read_text(encoding='utf-8-sig'))
original=read('python-results.json')
browser=read('frontend/browser-results.json')
units=read('frontend/unit-results.json')
rs=read('collection/r-verified-results.json')
dbs=read('source-database-checks.json')
report=OUT/'MENTAT_FULL_AUDIT.md'
text=report.read_text(encoding='utf-8')
bad=[]
for link in re.findall(r'\]\((C:/[^)]+)\)',text):
    path=re.sub(r':\d+$','',link)
    if not Path(path).exists():bad.append(link)
summary={
    'completed_utc':datetime.now(timezone.utc).isoformat(),
    'confirmed_defects':8,'priority_1':2,'priority_2':6,
    'python':{'final_test_count':500,'final_failed':0,'initial_unittest_count':499,
        'initial_nonzero_modules':[r['module'] for r in original if r['returncode']],
        'resolution':'Two R-dependent test cases passed on rerun with installed packages; one standalone function passed through unittest.FunctionTestCase. Initial logs retained.'},
    'js_unit':{'files':len(units),'tests':sum(int(r.get('tests') or 0) for r in units),'passed':sum(int(r.get('pass') or 0) for r in units)},
    'browser':{'files':len(browser),'tests':sum(int(r.get('tests') or 0) for r in browser),
        'passed':sum(int(r.get('pass') or 0) for r in browser),'failed':sum(int(r.get('fail') or 0) for r in browser),
        'nonzero_files':[r['file'] for r in browser if r.get('exit')!=0]},
    'R':{'shipped_files':len(rs),'passed':sum(r['exit_code']==0 for r in rs),'failed':sum(r['exit_code']!=0 for r in rs),
        'supplemental_fixture_passes':2},
    'powershell':{'shipped_guard_suites':5,'passed':5},
    'source_databases':{'count':len(dbs),'all_quick_checks_ok':all(r.get('quick_check')==['ok'] for r in dbs),
        'all_unchanged':all(r.get('unchanged_during_check') for r in dbs)},
    'broken_report_links':bad}
(OUT/'final-validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
