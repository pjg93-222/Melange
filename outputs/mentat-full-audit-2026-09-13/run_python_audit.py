"""Run each shipped Mentat Python test module in a separate isolated process."""
import ast
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LOGS = OUT / 'python'
LOGS.mkdir(exist_ok=True)
env = os.environ.copy()
for key in list(env):
    if key.startswith('FEC_API_KEY') or key.startswith('MENTAT_'):
        env.pop(key)
env['PYTHONDONTWRITEBYTECODE'] = '1'
env['PYTHONIOENCODING'] = 'utf-8'
env['MENTAT_PYTHON'] = sys.executable
env['MENTAT_RSCRIPT'] = 'C:/Program Files/R/R-4.6.0/bin/Rscript.exe'
env['R_LIBS_USER'] = 'C:/Users/pgoff/AppData/Local/R/win-library/4.6'
env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env.get('PATH', '')
for setting, folder in [('MENTAT_DATA_ROOT','data'),('MENTAT_REPORT_DIRECTORY','reports'),('MENTAT_CROSS_REFERENCE_ROOT','cross-reference'),('MENTAT_ACCEPTED_SOURCE_ROOT','accepted')]:
    target = LOGS / folder
    target.mkdir(exist_ok=True)
    env[setting] = str(target)
env['MENTAT_API_BUDGET_DB'] = str(LOGS / 'budget.sqlite')
env['MENTAT_FEC_KEY_STORE'] = str(LOGS / 'keys.json')

inventory=[]
for folder in ('app','tools','R','tests','config','inputs'):
    for file in (ROOT/'mentat'/folder).rglob('*'):
        if file.is_file() and not any(x in file.parts for x in ('__pycache__','.cache','.pytest_cache')) and file.suffix.lower() in ('.py','.r','.js','.cjs','.mjs','.ps1','.psm1','.json','.html','.css','.cs','.md'):
            inventory.append({'path':str(file.relative_to(ROOT)), 'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
(OUT/'source-manifest.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
syntax=[]
for file in list((ROOT/'mentat/app').glob('*.py'))+list((ROOT/'mentat/tools').glob('*.py'))+list((ROOT/'mentat/tests').glob('*.py')):
    try: ast.parse(file.read_text(encoding='utf-8-sig'),filename=str(file))
    except SyntaxError as error: syntax.append({'path':str(file),'error':str(error)})
(OUT/'python-syntax.json').write_text(json.dumps(syntax,indent=2),encoding='utf-8')

def run(file):
    start=time.monotonic()
    try:
        result=subprocess.run([sys.executable,'-m','unittest','discover','-s','mentat/tests','-p',file.name,'-v'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
        content=result.stdout.decode('utf-8',errors='replace')
        code=result.returncode
    except subprocess.TimeoutExpired as error:
        content=(error.stdout or b'').decode('utf-8',errors='replace')+'\nAUDIT TIMEOUT after 240 seconds\n'
        code=124
    (LOGS/(file.stem+'.log')).write_text(content,encoding='utf-8')
    matches=re.findall(r'Ran (\d+) tests? in',content)
    value={'module':file.name,'returncode':code,'seconds':round(time.monotonic()-start,2),'tests':int(matches[-1]) if matches else None,'summary':content.strip().splitlines()[-1:]}
    print(json.dumps(value),flush=True)
    return value

files=sorted((ROOT/'mentat/tests').glob('test_*.py'))
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(run,files))
(OUT/'python-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps({'modules':len(results),'nonzero':sum(r['returncode']!=0 for r in results),'tests':sum(r['tests'] or 0 for r in results),'syntax_errors':syntax}),flush=True)
