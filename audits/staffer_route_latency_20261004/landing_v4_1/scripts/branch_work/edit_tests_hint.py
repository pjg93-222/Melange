"""v4.1 fixes 4 and 5, the unreachable-hint tests (fec/tests/surfaces/test_staffer_unreachable_hint.py): the new office field, and explanation = message."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit_lib import edit

PATH = r'C:\Users\pgoff\Melange-wt\route-core\fec\tests\surfaces\test_staffer_unreachable_hint.py'

FIELDS_OLD = r'''# What an office result carries since D-086 (an office route searches to its covered staff): test_staffer_office_covered_staff.py.
OFFICE_COVERAGE_FIELDS = {'uncovered_staff_count', 'uncovered_staff_ids'}
'''
FIELDS_NEW = r'''# What an office result carries since D-086 (an office route searches to its covered staff) and the v4.1 basis of the count: test_staffer_office_covered_staff.py.
OFFICE_COVERAGE_FIELDS = {'uncovered_staff_count', 'uncovered_staff_ids', 'uncovered_basis'}
'''

ANCHOR = r'''def test_the_page_selector_and_the_server_agree_on_the_ecosystem_objective():
'''
EXPLANATION = r'''# --------------------------------------------------------------------------- the explanation is the message (the re-check's finding A4)
# An unreachable answer that carries a reason says it in `message`; its `explanation` (the text under "How this route was chosen", and what
# any other consumer of the payload reads) is that same text, not the generic sentence that was written before the reasons existed. An answer
# with no reason keeps the generic sentence, and so does every other status.
GENERIC = ('No supported path exists in the currently indexed evidence under these filters. This does not establish that no real-world '
           'introduction is possible.')
ALTERNATIVES = ' Alternatives are found by excluding contacts used in earlier choices'
REASONED = [name for name, case in CASES.items() if 'unreachable_reason' in case['payload']]


def asked(service, name, **override):
    origin, destination, extra = SCENARIOS[name]
    options = {**UI, **extra, **override}
    if isinstance(destination, str):
        return service.route(origin, destination, options)
    return service.office_route(origin, destination[0], options)


def explanation_failures(produce):
    """Every unreachable answer with a reason whose explanation is not its message (nor the contract's message)."""
    wrong = []
    for name in REASONED:
        for override in ({}, {'route_count': 1}, {'alternative_strategy': 'independent'}, {'alternative_strategy': 'ranked'}):
            answer = produce(name, **override)
            if not (answer['status'] == 'unreachable' and answer['explanation'] == answer['message'] == CASES[name]['payload']['message']):
                wrong.append((name, override, answer['status'], answer['explanation'][:70]))
    return wrong


def test_the_explanation_of_an_unreachable_answer_with_a_reason_is_its_message_for_every_reason_and_strategy():
    services = {name: make_service(router_for(name)) for name in REASONED}
    assert len(REASONED) == 9 and 'insufficient_work_coverage' not in REASONED
    assert explanation_failures(lambda name, **override: asked(services[name], name, **override)) == []


def test_the_explanation_of_an_unreachable_answer_with_a_reason_is_its_message_over_http(stack):
    served = {name: stack(router_for(name))[1] for name in REASONED}
    for name in REASONED:
        answer = via_http(served[name], name)
        assert answer['status'] == 'unreachable' and answer['unreachable_reason']
        assert answer['explanation'] == answer['message'] == CASES[name]['payload']['message'], name


def test_an_unreachable_answer_without_a_reason_and_every_other_status_keep_their_explanation():
    router = world()
    service = make_service(router)
    # Ecosystem has no reasons: its unreachable answer keeps the generic sentence, and the distinct portfolio's note after it
    ecosystem = {**UI, 'objective': closeness.SUGGESTED_OBJECTIVE}
    single = service.route('a1', 'b1', {**ecosystem, 'route_count': 1})
    assert single['status'] == 'unreachable' and 'unreachable_reason' not in single and single['explanation'] == GENERIC
    portfolio = service.route('a1', 'b1', ecosystem)
    assert portfolio['status'] == 'unreachable' and 'unreachable_reason' not in portfolio
    assert portfolio['explanation'].startswith(GENERIC + ALTERNATIVES) and portfolio['explanation'] != portfolio.get('message')
    # the Staffer answers that are not unreachable
    found = service.route('a1', 'a3', {**UI, 'route_count': 1})
    assert found['status'] == 'found' and found['explanation'].startswith('Ranks complete paths')
    unknown = service.route('a1', 'nobody-at-all', {**UI, 'route_count': 1})
    assert unknown['status'] == 'unknown_person' and unknown['explanation'].startswith('No search was run')
    restricted = make_service(router_for('insufficient_work_coverage'))
    coverage = asked(restricted, 'insufficient_work_coverage', route_count=1)
    assert coverage['status'] == 'insufficient_work_coverage' and coverage['explanation'] == coverage['message']
    distinct = asked(restricted, 'insufficient_work_coverage')
    assert distinct['explanation'].startswith(distinct['message'] + ALTERNATIVES), 'a coverage answer is worded as it always was'


def test_a_payload_with_a_status_of_unreachable_and_a_reason_but_no_message_keeps_the_generic_sentence(monkeypatch):
    """The page reads its sentence from `message` only when the reason and the message are both there, and so does the explanation."""
    service = make_service(router_for('no_path_in_work_records'))
    real = ClosenessRoutes.route

    def without_message(self, *args, **kwargs):
        result = real(self, *args, **kwargs)
        return {k: v for k, v in result.items() if k != 'message'} if result['status'] == 'unreachable' else result
    monkeypatch.setattr(ClosenessRoutes, 'route', without_message)
    answer = asked(service, 'no_path_in_work_records', route_count=1)
    assert answer['status'] == 'unreachable' and answer['unreachable_reason'] and 'message' not in answer and answer['explanation'] == GENERIC


def test_the_explanation_check_has_teeth(monkeypatch):
    """Negative control: the service as it was before the change (the generic sentence for every unreachable answer) fails it, for all nine."""
    real = LiveService._route_response

    def generic(self, router, result, started):
        answer = real(self, router, result, started)
        return {**answer, 'explanation': GENERIC} if result['status'] == 'unreachable' else answer
    monkeypatch.setattr(LiveService, '_route_response', generic)
    services = {name: make_service(router_for(name)) for name in REASONED}
    failures = explanation_failures(lambda name, **override: asked(services[name], name, **override))
    assert {name for name, *_ in failures} == set(REASONED) and len(failures) == 4 * len(REASONED)


''' + ANCHOR

edit(PATH, [(FIELDS_OLD, FIELDS_NEW), (ANCHOR, EXPLANATION)])
