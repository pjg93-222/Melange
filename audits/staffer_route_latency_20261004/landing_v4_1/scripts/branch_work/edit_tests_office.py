"""v4.1 fix 4, the office tests (fec/tests/surfaces/test_staffer_office_covered_staff.py): uncovered_basis, and the directory-only scenario of the re-check (D1)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit_lib import edit

PATH = r'C:\Users\pgoff\Melange-wt\route-core\fec\tests\surfaces\test_staffer_office_covered_staff.py'

DOC_OLD = r'''office route drops the uncovered staff, searches to the covered ones and says who was left out: every office result (found,
unreachable or coverage) carries uncovered_staff_count and uncovered_staff_ids (sorted). The request fails as
insufficient_work_coverage only when its origin is uncovered or none of the office's staff is covered, with the message and
'''
DOC_NEW = r'''office route drops the uncovered staff, searches to the covered ones and says who was left out: every office result (found,
unreachable or coverage) carries uncovered_staff_count and uncovered_staff_ids (sorted) and uncovered_basis, the coverage they lack
(payroll_or_roster, or roster alone where the comparison reads directory episodes only, so no payroll evidence can cover anyone). The
request fails as insufficient_work_coverage only when its origin is uncovered or none of the office's staff is covered, with the message and
'''

FIELDS_OLD = r'''NEW_FIELDS = {'uncovered_staff_count', 'uncovered_staff_ids'}
'''
FIELDS_NEW = r'''NEW_FIELDS = {'uncovered_staff_count', 'uncovered_staff_ids', 'uncovered_basis'}   # every field an office answer gained
COUNT_FIELDS = {'uncovered_staff_count', 'uncovered_staff_ids'}                    # who was left out
'''

LEFT_OLD = r'''def left_out(result):
    return {key: result[key] for key in sorted(NEW_FIELDS)}
'''
LEFT_NEW = r'''def left_out(result):
    return {key: result[key] for key in sorted(COUNT_FIELDS)}
'''

TAIL_OLD = r'''            assert over_http['unreachable_reason'] == 'office_without_work_records' and over_http['message'] == sentence
        finally:
            server.close()
            service.route_executor.shutdown(wait=True, cancel_futures=True)
'''
TAIL_NEW = TAIL_OLD + r'''

# --------------------------------------------------------------------------- what the left-out staff lack (uncovered_basis)
# The line the page shows says which coverage the left-out staff lack. Payroll evidence can cover a person only where it is read: a
# comparison of directory episodes only (work_sources=directory) has none, so there "uncovered" means "not on the staffer roster", and the
# page must not say "payroll or" (the re-check's finding D1: a person with payroll rows and no roster entry is left out of that comparison).
# The basis names what the mode can use, not whether the world happens to hold payroll rows.
def work_row(person_id, office, start, end, how):
    provenance = {'work_route_source': 'politico_profile_history'} if how == 'directory' else {'method': 'payroll-identity-rows-v1'}
    return {'person_id': person_id, 'employer_id': office, 'start': start, 'end_exclusive': end, 'employment_verified': True, 'provenance': provenance}


DIRECTORY_OFFICE = 'office:t'
DIRECTORY_STAFF = ('d1', 'p1')
MODES = (('payroll_and_directory', 'payroll_or_roster'), ('directory', 'roster'))


def directory_world(operational=('o', 'd1')):
    """o and d1 are on the staffer roster (a directory episode each at the office); p1 has payroll rows and a directory row there and is not."""
    nodes = {'o': person('Origin Person'), 'p1': person('Payroll Person'), 'd1': person('Directory Person'), DIRECTORY_OFFICE: office_node(DIRECTORY_OFFICE)}
    episodes = [work_row('o', DIRECTORY_OFFICE, '2019-01-01', '2021-01-01', 'directory'),
                work_row('p1', DIRECTORY_OFFICE, '2020-01-01', '2022-01-01', 'payroll'),
                work_row('p1', DIRECTORY_OFFICE, '2020-01-01', '2022-01-01', 'directory'),
                work_row('d1', DIRECTORY_OFFICE, '2020-06-01', '2022-01-01', 'directory')]
    router = AdvocacyRouter(nodes, episodes, 'directory-mode', AS_OF)
    router.operational_staffer_ids = set(operational)
    return router


def basis_failures():
    """Every way an office answer differs from the rule: payroll_or_roster where payroll evidence is read, roster alone where it is not."""
    failures = []

    def check(what, answer, basis, status=None, left=None):
        for item in (answer, *answer.get('routes', [])):
            if item.get('uncovered_basis') != basis:
                failures.append('%s: uncovered_basis %r, not %r' % (what, item.get('uncovered_basis'), basis))
            if left is not None and item.get('uncovered_staff_ids') != left:
                failures.append('%s: left out %r, not %r' % (what, item.get('uncovered_staff_ids'), left))
        if status is not None and answer['status'] != status:
            failures.append('%s: status %r, not %r' % (what, answer['status'], status))
    # The re-check's scenario: p1 has payroll rows and no roster entry. Payroll evidence read, p1 is covered; directory episodes only, it is not.
    for mode, basis in MODES:
        left = ['p1'] if mode == 'directory' else []
        for count, strategy in ((1, 'ranked'), (3, 'ranked'), (3, 'distinct'), (3, 'independent')):
            answer = ask(directory_world(), 'o', DIRECTORY_STAFF, DIRECTORY_OFFICE, work_sources=mode, route_count=count, alternative_strategy=strategy)
            check('%s, %d %s' % (mode, count, strategy), answer, basis, 'found', left)
        # nobody the model can use but the origin: payroll covers p1 where it is read, so only d1 is left out there, and both are left out here
        answer = ask(directory_world(operational=('o',)), 'o', DIRECTORY_STAFF, DIRECTORY_OFFICE, work_sources=mode)
        if mode == 'directory':
            check(mode + ', nobody covered', answer, basis, 'insufficient_work_coverage', ['d1', 'p1'])
        else:
            check(mode + ', one covered by payroll', answer, basis, 'found', ['d1'])
        # the origin is the one without coverage
        check(mode + ', uncovered origin', ask(directory_world(operational=('d1',)), 'o', DIRECTORY_STAFF, DIRECTORY_OFFICE, work_sources=mode),
              basis, 'insufficient_work_coverage')
        # an unreachable answer: the office the covered staff do not work at
        answer = ask(reasons_world(), 'o', PROFILE, 'office:profile', work_sources=mode)
        check(mode + ', unreachable', answer, basis, 'unreachable', ['u5'])
    return failures


def test_every_office_answer_says_which_coverage_its_left_out_staff_lack():
    assert basis_failures() == []


def test_the_basis_check_has_teeth(monkeypatch):
    """Negative control: a producer that says payroll_or_roster in every mode fails the directory-only answers, and every one of them."""
    real = ClosenessRoutes.route

    def always_payroll_or_roster(self, *args, **kwargs):
        result = real(self, *args, **kwargs)
        return {**result, 'uncovered_basis': 'payroll_or_roster'} if 'uncovered_basis' in result else result
    monkeypatch.setattr(ClosenessRoutes, 'route', always_payroll_or_roster)
    failures = basis_failures()
    assert failures and all('directory' in f for f in failures), failures
    assert any('nobody covered' in f for f in failures) and any('unreachable' in f for f in failures) and any('uncovered origin' in f for f in failures)


def test_a_person_with_payroll_rows_and_no_roster_entry_is_left_out_of_a_directory_only_comparison_and_the_basis_says_why():
    router = directory_world()
    both = ask(router, 'o', DIRECTORY_STAFF, DIRECTORY_OFFICE, work_sources='payroll_and_directory')
    assert both['status'] == 'found' and left_out(both) == {'uncovered_staff_count': 0, 'uncovered_staff_ids': []}
    directory_only = ask(directory_world(), 'o', DIRECTORY_STAFF, DIRECTORY_OFFICE, work_sources='directory')
    assert left_out(directory_only) == {'uncovered_staff_count': 1, 'uncovered_staff_ids': ['p1']} and directory_only['target'] == 'd1'
    assert directory_only['uncovered_basis'] == 'roster' and both['uncovered_basis'] == 'payroll_or_roster'
    index = router.closeness().index(router._options({'objective': 'work_time', 'work_sources': 'directory'}))
    assert 'p1' not in closeness._payroll_people(index), 'a directory-only index holds no payroll evidence, so payroll covers nobody in it'
    assert 'p1' in closeness._payroll_people(router.closeness().index(router._options({'objective': 'work_time'})))


def test_a_world_without_payroll_rows_still_names_payroll_or_roster_where_payroll_evidence_is_read():
    result = ask(reasons_world(), 'o', PROFILE, 'office:profile')
    assert result['uncovered_basis'] == 'payroll_or_roster' and result['uncovered_staff_ids'] == ['u5']
    assert ask(reasons_world(), 'o', PROFILE, 'office:profile', work_sources='directory')['uncovered_basis'] == 'roster'


def test_the_service_and_the_handler_serve_the_basis_on_the_answer_and_on_every_route():
    page = {'objective': 'work_time', 'route_count': 3, 'alternative_strategy': 'distinct', 'include_historical': 1, 'include_review': 1,
            'include_policy': 0, 'include_unresolved': 0, 'include_user_asserted': 1}
    for mode, basis in MODES:
        left = ['p1'] if mode == 'directory' else []
        service = service_for(directory_world(), DIRECTORY_STAFF, DIRECTORY_OFFICE)
        server = Served(service)
        try:
            answer = service.office_route('o', DIRECTORY_OFFICE, {**UI, 'route_count': 3, 'work_sources': mode})
            over_http = via_http(server, '/api/staffer-office-route', origin='o', office=DIRECTORY_OFFICE, work_sources=mode, **page)
            for name, served in (('service', answer), ('handler', over_http)):
                assert served['status'] == 'found' and served['routes'], (mode, name)
                for item in (served, *served['routes']):
                    assert (item['uncovered_basis'], item['uncovered_staff_ids']) == (basis, left), (mode, name, item['uncovered_basis'])
        finally:
            server.close()
            service.route_executor.shutdown(wait=True, cancel_futures=True)
    person_page = {**page, 'target': 'p1', 'origin': 'o'}
    service = service_for(directory_world(), DIRECTORY_STAFF, DIRECTORY_OFFICE)
    server = Served(service)
    try:
        assert NEW_FIELDS.isdisjoint(via_http(server, '/api/staffer-route', work_sources='directory', **person_page)), 'a person route carries none of it'
    finally:
        server.close()
        service.route_executor.shutdown(wait=True, cancel_futures=True)
'''

edit(PATH, [(DOC_OLD, DOC_NEW), (FIELDS_OLD, FIELDS_NEW), (LEFT_OLD, LEFT_NEW), (TAIL_OLD, TAIL_NEW)])
