"""D (the re-check's directory_mode.py, extended for v4.1): in the directory-only comparison, is a person with payroll records but no operational-roster entry left out, and what does the answer say
and the page show? cwd = an export of the tree to test. Prints one line per mode: status, who was left out, the answer's uncovered_basis (absent before v4.1) and the line the page builds from them
(staffer-route.js leftOutLine, evaluated by node on the export's own file)."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.getcwd())
from fec.surfaces.staffer_routing import AdvocacyRouter


def person(label):
    return {'kind': 'person', 'label': label, 'member_ids': [], 'committee_ids': [], 'policy_ids': []}


def ep(p, office, start, end, how):
    prov = {'work_route_source': 'politico_profile_history'} if how == 'directory' else {'method': 'payroll-identity-rows-v1'}
    return {'person_id': p, 'employer_id': office, 'start': start, 'end_exclusive': end, 'employment_verified': True, 'provenance': prov}


def page_line(answer):
    """The line the page shows for this answer: leftOutLine of the export's staffer-route.js, extracted and run by node (no DOM needed: it reads only the answer)."""
    source = open(os.path.join('fec', 'surfaces', 'staffer_live', 'staffer-route.js'), encoding='utf-8').read()
    start = source.index('  function leftOutLine(data){')
    end = source.index('  // After a Staffer search found no route', start)
    program = source[start:end] + '\nprocess.stdout.write(JSON.stringify(leftOutLine(%s)));' % json.dumps(answer)
    done = subprocess.run(['node', '-e', program], capture_output=True, text=True)
    return json.loads(done.stdout) if done.returncode == 0 else 'node failed: ' + done.stderr[:200]


nodes = {'o': person('Origin Person'), 'p1': person('Payroll Person'), 'd1': person('Directory Person'),
         'office:t': {'kind': 'container', 'container_kind': 'member_office', 'member_bioguide': 'M1', 'label': 'Office T'}}
episodes = [ep('o', 'office:t', '2019-01-01', '2021-01-01', 'directory'), ep('p1', 'office:t', '2020-01-01', '2022-01-01', 'payroll_row'),
            ep('p1', 'office:t', '2020-01-01', '2022-01-01', 'directory'),
            ep('d1', 'office:t', '2020-06-01', '2022-01-01', 'directory')]
for mode in ('payroll_and_directory', 'directory'):
    router = AdvocacyRouter(nodes, episodes, 'dirmode', '2026-09-11')
    router.operational_staffer_ids = {'o', 'd1'}
    r = router.route_many('o', ['p1', 'd1'], {'objective': 'work_time', '_target_office': 'office:t', 'work_sources': mode})
    print('%-22s status=%-10s uncovered=%s target=%s basis=%s | page line: %s' % (
        mode, r['status'], r.get('uncovered_staff_ids'), r.get('target'), r.get('uncovered_basis', '(absent)'), page_line(r) or '(no line)'))
print('p1 has payroll rows in the data:', any(e['provenance'].get('method') == 'payroll-identity-rows-v1' for e in router.by_person['p1']))
