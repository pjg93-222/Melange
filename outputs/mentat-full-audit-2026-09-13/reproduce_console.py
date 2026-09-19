"""Offline probes; process launches, credentials, and process kills are mocked."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('audit_console',ROOT/'mentat/app/server.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
result={}
with tempfile.TemporaryDirectory(dir=OUT) as name:
    root=Path(name)
    with patch.object(app,'report_directory',return_value=root),patch.object(app,'environment_keys',return_value=[]):
        first=app.Console(root,rscript=sys.executable)
        second=app.Console(root,rscript=sys.executable)
    runid='a'*32
    directory=root/runid
    directory.mkdir()
    app.atomic_json(directory/'upload.json',{'id':runid,'name':'Offline fixture','state':'completed','created_at':0,'pid':123456,'finished_at':1})
    with patch.object(app.subprocess,'run',return_value=SimpleNamespace(returncode=0,stderr=b'')) as kill:
        stop=first.stop({'id':runid,'force':True})
        result['terminal_run_stop']={'request_state':'completed','saved_pid':123456,'actual_process_executed':False,'attempted_command':kill.call_args.args[0],'response':stop}
    app.atomic_json(directory/'upload.json',{'id':runid,'name':'Offline fixture','state':'ready','created_at':0})
    barrier=threading.Barrier(2)
    original_runs=app.Console.runs
    def synchronized_runs(console):
        runs=original_runs(console)
        barrier.wait(timeout=8)
        return runs
    def synchronized_keys():
        barrier.wait(timeout=8)
        return ['offline-fixture-key']
    with patch.object(app.Console,'runs',synchronized_runs),patch.object(app,'load_keys',side_effect=synchronized_keys),patch.object(app.Console,'prepare_launch') as prepare:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(c.launch,{'id':runid,'cycles':[2024]}) for c in (first,second)]
            calls=[]
            for f in futures:
                try:calls.append(f.result())
                except Exception as error:calls.append({'error':str(error)})
        result['concurrent_console_launch']={'actual_process_executed':False,'responses':calls,'launch_preparations':prepare.call_count}

(OUT/'console-reproductions.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))

# A single pytest-style function has no fixtures; execute via unittest adapter.
import unittest
spec=importlib.util.spec_from_file_location('telecom_offline_test',ROOT/'mentat/tests/test_split_telecom_workbook.py')
test=importlib.util.module_from_spec(spec);spec.loader.exec_module(test)
with (OUT/'python/test_split_telecom_adapter.log').open('w') as log:
    tested=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.TestSuite([unittest.FunctionTestCase(test.test_make_tables_excel_safe_normalizes_strict_excel_rules)]))
print(json.dumps({'telecom_test_count':tested.testsRun,'passed':tested.wasSuccessful()}))
