"""Offline regression runner; only temporary fixture workbooks are generated."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
tests=ROOT/'mentat/tests'
python_suites=['test_downstream_review.py','test_downstream_network.py','test_downstream_capture.py',
    'test_downstream_enrichment.py','test_transfer_graph.py','test_pac_evidence.py','test_graph_data.py',
    'test_tidy_workbook.py','test_workbook_payload.py','test_evidence_geo.py','test_pac_cash_model.py']
r_suites=['test_downstream_review.R','test_downstream_system.R','test_transfer_evidence.R',
    'test_tidy_stage.R','test_fec_beneficiary_helpers.R']
js_suites=['test_downstream_review.cjs','test_downstream_measurement_browser.cjs']
jobs=[(name,[sys.executable,str(tests/name)]) for name in python_suites]
jobs += [(name,[r'C:\Program Files\R\R-4.6.0\bin\Rscript.exe',str(tests/name)]) for name in r_suites]
jobs += [(name,['node','--test',str(tests/name)]) for name in js_suites]
def run(job):
    name,command=job;start=time.monotonic()
    try:
        result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=360)
        (HERE/(name+'.log')).write_bytes(result.stdout+b'\n'+result.stderr)
        return dict(suite=name,exit_code=result.returncode,seconds=round(time.monotonic()-start,2))
    except Exception as error:
        return dict(suite=name,exit_code=-1,error=str(error))
results=[]
with ThreadPoolExecutor(max_workers=3) as pool:
    for future in as_completed([pool.submit(run,job) for job in jobs]):
        row=future.result();results.append(row);print(json.dumps(row),flush=True)
(HERE/'test_results.json').write_text(json.dumps(results,indent=2))
sys.exit(int(any(row['exit_code'] for row in results)))
