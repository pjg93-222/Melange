"""Rebuild, run all relationship tests, and verify reproducible output hashes."""
import subprocess,sys
from .data import ROOT,read_json,write_json,digest
from .run_anchored import OUT


def run(args):
    result=subprocess.run([sys.executable]+args,cwd=ROOT,text=True,encoding='utf-8',errors='replace',capture_output=True)
    if result.returncode:
        print(result.stdout);print(result.stderr)
        raise RuntimeError(f'Command failed: {args}')
    return result.stdout+result.stderr


def main():
    log=run(['-m','fec.research.member_personal_relationships.run_anchored'])
    before=read_json(OUT/'manifest.json')['output_hashes']
    tests=run(['-m','unittest','discover','-s','fec/research/member_personal_relationships/tests','-v'])
    (OUT/'TEST_RESULTS.txt').write_text(tests,encoding='utf-8')
    log+='\nDeterministic rebuild\n'+run(['-m','fec.research.member_personal_relationships.run_anchored'])
    after=read_json(OUT/'manifest.json')['output_hashes']
    if before!=after: raise AssertionError('Rebuild changed deterministic output')
    (OUT/'run_log.txt').write_text(log,encoding='utf-8')
    report=run(['-m','fec.research.member_personal_relationships.report_anchored'])
    m=read_json(OUT/'manifest.json')
    write_json(OUT/'verification_receipt.json',dict(status='passed',deterministic_artifacts=len(before),
        output_hashes=after,inputs_unchanged=m['inputs_unchanged'],
        test_result_tail=tests.splitlines()[-5:],tests_sha256=digest(OUT/'TEST_RESULTS.txt'),
        scope='Full v1 and v2 relationship test suite; source hashes; deterministic rebuild; no production write',
        test_first='The first 11 v2 contracts were run before implementation and failed with ModuleNotFoundError; the remaining checks cover discovered risks and integration.'))
    print(tests[-1800:]);print(report);print('Verified identical hashes for',len(before),'fitted artifacts')


if __name__=='__main__': main()
