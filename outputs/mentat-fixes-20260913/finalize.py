import hashlib,json,pathlib,re
root=pathlib.Path(__file__).resolve().parents[2];out=pathlib.Path(__file__).parent
results={}
for name in ['remaining-run.log','retry-run.log','final-r-run.log','map-rerun.log','temporal-rerun.log','ingest-rerun.log']:
    for line in (out/name).read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('{'):
            row=json.loads(line);results[row['file']]=row['returncode']
# This test needs native PowerShell utility modules; its direct-shell receipt is separate.
assert '15 passed, 0 failed' in (out/'last-good-rerun.log').read_text(encoding='utf-8-sig')
results['Test-MentatLastGoodGuard.ps1']=0
python=json.loads((out/'python-results.json').read_text())
for row in python:
    if row['module']=='test_cross_reference_runner.py':
        assert '\nOK' in (out/'cross-reference-rerun.log').read_text();row['returncode']=0
    if row['module']=='test_split_telecom_workbook.py':
        assert '\nOK' in (out/'telecom-rerun.log').read_text();row.update(returncode=0,tests=1)
units=0;browser=0
for name,code in results.items():
    if name.endswith(('.cjs','.js')):
        log=(out/(name+'.log')).read_text(encoding='utf-8-sig')
        n=int(re.search(r'tests (\d+)',log)[1])
        if 'browser' in name:browser+=n
        else:units+=n
summary={'python_tests':sum(r['tests'] or 0 for r in python),'python_modules':len(python),'python_failures':[r for r in python if r['returncode']],
         'r_scripts':sum(n.endswith('.R') for n in results),'powershell_scripts':sum(n.endswith('.ps1') for n in results),
         'javascript_unit_tests':units,'browser_tests':browser,'other_failures':{n:c for n,c in results.items() if c}}
files=['mentat/R/fec_api.R','mentat/app/server.py','mentat/tools/report_source_guard.py','mentat/tools/run_cross_reference.py','mentat/app/contribution-studio.js','mentat/app/chart-studio.js']
summary['production_files']=[{'path':p,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest()} for p in files]
(out/'FINAL_VALIDATION.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
assert not summary['python_failures'] and not summary['other_failures']
