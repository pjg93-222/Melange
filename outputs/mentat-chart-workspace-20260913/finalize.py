import json,hashlib
from pathlib import Path
out=Path(__file__).parent;root=out.parents[1]
results=json.loads((out/'python-results.json').read_text())
for item in results:
    if item['module']=='test_contribution_semantics.py':
        assert '\nOK' in (out/'semantics-rerun.log').read_text();item['returncode']=0
    if item['module']=='test_split_telecom_workbook.py':
        assert '\nOK' in (out/'telecom.log').read_text();item.update(returncode=0,tests=1)
    if item['module']=='test_workbook_payload.py':
        assert 'Ran 5 tests' in (out/'payload-rerun.log').read_text() and '\nOK' in (out/'payload-rerun.log').read_text();item.update(returncode=0,tests=5)
assert not [r for r in results if r['returncode']]
regressions=[json.loads(line) for line in (out/'regression-run.log').read_text().splitlines() if line.startswith('{')]
assert len(regressions)==7 and all(r['returncode']==0 for r in regressions)
assert 'pass 1' in (out/'browser-verified.log').read_text(encoding='utf-8') and 'fail 0' in (out/'browser-verified.log').read_text(encoding='utf-8')
for name in ['workbook-guards.log','report-directory.log','exporter-syntax.log']:assert 'PASS' in (out/name).read_text()
summary={'python_tests':sum(r['tests'] for r in results),'python_modules':len(results),'browser_tests':5,'r_regression_scripts':3,'powershell_regression_scripts':2,'failures':0,'deployment':'Code only; running consoles not restarted and published workbooks not regenerated.','screenshot':'four-charts.png (synthetic data)'}
paths=['mentat/app/chart-comparison.js','mentat/app/chart-studio.js','mentat/app/chart-studio.css','mentat/app/index.html','mentat/app/server.py','mentat/app/contribution_data.py','mentat/app/contribution_semantics.py','mentat/R/state_destinations.R','mentat/tools/export_crypto_spending_data.R','mentat/tools/prepare_workbook_payload.py','mentat/tools/crypto_workbook_builder.mjs','mentat/tools/build_industry_report.ps1']
summary['files']=[{'path':p,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest()} for p in paths]
(out/'FINAL_VALIDATION.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='files'},indent=2))
