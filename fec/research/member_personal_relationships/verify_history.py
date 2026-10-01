"""Tests, deterministic decision rebuild and source-integrity receipt."""
import json
import subprocess
import sys
from .data import ROOT,digest,write_json,read_json
from .prepare_history import OUT


def main():
    before={p:digest(ROOT/p) for p in read_json(OUT/'work_manifest.json')['source_sha256']}
    command=[sys.executable,'-m','unittest','discover','-s','fec/research/member_personal_relationships/tests','-v']
    run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (OUT/'TEST_RESULTS.txt').write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:print(run.stdout+run.stderr);raise SystemExit(run.returncode)
    artifacts=['relationships.ndjson','reviewed_events.ndjson','personality_expression.json','benchmark.json','results.json']
    old={p:digest(OUT/p) for p in artifacts}
    rebuild=subprocess.run([sys.executable,'-m','fec.research.member_personal_relationships.run_history'],cwd=ROOT,capture_output=True,text=True)
    if rebuild.returncode:raise RuntimeError(rebuild.stderr)
    new={p:digest(OUT/p) for p in artifacts}
    after={p:digest(ROOT/p) for p in before}
    if old!=new:raise AssertionError('Decision rebuild not deterministic')
    if before!=after:raise AssertionError('Input changed during verification')
    # Store code and output hashes so this run can be audited after later edits.
    codefiles=['history_work.py','history_speech.py','prepare_history.py','run_history.py','report_history.py','history_reviews.json','verify_history.py']
    code={p:digest(ROOT/'fec/research/member_personal_relationships'/p) for p in codefiles}
    write_json(OUT/'verification_receipt.json',dict(passed=True,
        tests=run.stderr.strip().splitlines()[-4:],deterministic_decision_rebuild=True,
        input_sources_unchanged=True,input_sha256=before,output_sha256=new,code_sha256=code,
        independent_bill_recounts=read_json(OUT/'dossier_receipt.json'),
        execution='Production inputs read only; writes scoped to this research module and its output directory.'))
    print(run.stderr.strip().splitlines()[-4:]);print('Verified deterministic outputs and unchanged source inputs',flush=True)


if __name__=='__main__':main()
