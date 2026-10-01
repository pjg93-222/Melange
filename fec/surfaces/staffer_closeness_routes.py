"""Complete loopless work routes using absolute size-adjusted exposure."""
from collections import OrderedDict
from copy import deepcopy
import heapq
import itertools
import math
import time

from fec.staffer_network.closeness_math import ordinal, VERSION, HOP_FACTOR, MEMBER_BETA, HEADCOUNT_SEMANTICS
from fec.staffer_network.member_context import MemberContext
from fec.staffer_network.relationship_uncertainty import uncertainty, specification

SINK = '\0closeness-destination'


class ClosenessRoutes:
    def __init__(self, router):
        self.router = router
        self.indexes = OrderedDict()
        self.cache = OrderedDict()

    def index(self, options):
        key = (options['include_review'], options['include_unresolved'], options['include_historical'], options['work_sources'])
        if key not in self.indexes:
            from fec.surfaces.staffer_work_sources import build_index
            self.indexes[key] = build_index(self.router, options)
            while len(self.indexes) > 4:
                self.indexes.popitem(last=False)
        return self.indexes[key]

    def route(self, origin, targets, options, progress=None):
        started = time.monotonic()
        targets = tuple(sorted(set(targets)))
        router = self.router
        uncertainty_weight = options['uncertainty_weight']
        base = {**router._base(), 'origin': origin, 'target': None, 'target_count': len(targets),
                'algorithm': 'Dijkstra with terminal costs; Yen loopless alternatives',
                'objective': 'work_time', 'strength_model': VERSION,
                'cost': None, 'steps': None, 'node_ids': [], 'hops': [], 'edges': [],
                'graph': {'nodes': [], 'edges': []}, 'optimal': False, 'complete_search': True,
                'search_limited': False, 'cache_hit': False, 'timeout_ms': None,
                'personal_familiarity_established': False,
                'score_semantics': 'Best loopless path under explicit exposure and uncertainty assumptions; not a probability of access',
                'uncertainty_model': specification(router.as_of), 'uncertainty_weight': uncertainty_weight,
                'headcount_semantics': HEADCOUNT_SEMANTICS}
        if options['route_count'] > 1:
            base.update(routes=[], routes_requested=options['route_count'], routes_returned=0, alternatives_complete=True)
        index = self.index(options)
        base['work_source_coverage'] = index.source_coverage
        base['work_sources'] = options['work_sources']
        payroll_people = {p for p, rows in index.source_episodes.items() if any(r['work_source'].startswith('payroll') for r in rows)}
        operational = getattr(router, 'operational_staffer_ids', None)
        def allowed(p):
            return router._person_allowed(p, options) and (operational is None or p in operational or p in payroll_people)
        if not targets or any(not router._person_allowed(p, options) for p in (origin, *targets)):
            return {**base, 'status': 'unknown_person'}
        unavailable = [p for p in (origin, *targets) if not allowed(p)]
        if unavailable:
            return {**base, 'status': 'insufficient_work_coverage',
                    'unavailable_person_ids': unavailable,
                    'message': "These people are known, but their records do not meet this model's authenticated staffer coverage requirements. Try Ecosystem for documented associations."}
        key = (origin, targets, tuple(sorted(options.items())))
        if key in self.cache:
            return {**deepcopy(self.cache[key]), 'cache_hit': True}
        index = self.index(options)
        context = getattr(router, 'member_context', None) or MemberContext()
        excluded_contexts = set(options['_excluded_contexts'])
        office = options.get('_target_office')
        member = router.nodes.get(office, {}).get('member_bioguide') if office else None
        terminal = {}
        for p in targets:
            anchor = index.office_anchors(p).get(office, 0.) if office else 1.
            info = context.score(index.member_anchors(p), {member: 1.}) if member else {'value': 0., 'coverage': 0., 'status': 'no_member_target'}
            modifier = 1 + MEMBER_BETA * info['value']
            anchor_uncertainty = index.office_uncertainty(p, office, router.as_of) if office else {'cost': 0., 'factor': 1.}
            if anchor > 0:
                # Common normalization preserves ranking and keeps Dijkstra
                # terminal costs nonnegative, even with a prestige bonus.
                factor = anchor * modifier / (1 + MEMBER_BETA) if office else 1.
                terminal[p] = (-math.log(factor) + uncertainty_weight * anchor_uncertainty['cost'],
                               anchor, info, modifier, anchor_uncertainty)
        neighbor_cache, pair_cache = {}, {}
        expanded, checks = 0, 0
        serial = itertools.count()
        last_progress = started
        def neighbors(p):
            nonlocal checks
            if p not in neighbor_cache:
                out = []
                for other in sorted(index.neighbors(p)):
                    checks += 1
                    if not allowed(other):
                        continue
                    pair = tuple(sorted((p, other)))
                    if pair not in pair_cache:
                        raw = index.pair(*pair)
                        risk = uncertainty(raw['workplaces'], router.as_of)
                        pair_cache[pair] = {**raw, 'uncertainty': risk,
                            'adjusted_strength': raw['strength'] * math.exp(-uncertainty_weight * risk['cost'])}
                    evidence = pair_cache[pair]
                    if excluded_contexts:
                        from fec.surfaces.staffer_distinct_routes import evidence_contexts
                        if evidence_contexts(evidence) & excluded_contexts:
                            continue
                    if evidence['strength'] > 0:
                        cost = -math.log(HOP_FACTOR * evidence['strength']) + uncertainty_weight * evidence['uncertainty']['cost']
                        out.append((other, cost))
                neighbor_cache[p] = out
            return neighbor_cache[p]
        def search(start, blocked_nodes=frozenset(), blocked_edges=frozenset()):
            nonlocal expanded, last_progress
            queue = [(0., 0, next(serial), start)]
            distances, previous = {start: (0., 0)}, {}
            while queue:
                cost, steps, _, p = heapq.heappop(queue)
                if (cost, steps) != distances.get(p):
                    continue
                if p == SINK:
                    path = [p]
                    while path[-1] != start:
                        path.append(previous[path[-1]])
                    return list(reversed(path)), cost
                expanded += 1
                arcs = neighbors(p)
                if p in terminal:
                    arcs = [*arcs, (SINK, terminal[p][0])]
                for other, edge_cost in arcs:
                    if other in blocked_nodes or tuple(sorted((p, other))) in blocked_edges:
                        continue
                    candidate = (cost + edge_cost, steps + (other != SINK))
                    if candidate < distances.get(other, (math.inf, math.inf)):
                        distances[other], previous[other] = candidate, p
                        heapq.heappush(queue, (*candidate, next(serial), other))
                now = time.monotonic()
                if progress and now - last_progress > .2:
                    progress({'expanded': expanded, 'neighbor_checks': checks, 'elapsed_ms': round((now-started)*1000)})
                    last_progress = now
            return None
        def path_cost(path):
            total = 0.
            for a, b in zip(path, path[1:]):
                if b == SINK:
                    total += terminal[a][0]
                else:
                    evidence = pair_cache[tuple(sorted((a,b)))]
                    total += -math.log(HOP_FACTOR * evidence['strength']) + uncertainty_weight * evidence['uncertainty']['cost']
            return total
        # Yen with the terminal sink included: alternatives may end at different
        # staff, and even a zero-staff-edge office route can have alternatives.
        blocked_nodes = frozenset(options.get('_excluded_nodes', ()))
        blocked_edges = frozenset(options.get('_excluded_edges', ()))
        first = search(origin, blocked_nodes, blocked_edges)
        accepted, pending, seen = ([first] if first else []), [], set()
        if first:
            seen.add(tuple(first[0]))
        while accepted and len(accepted) < options['route_count']:
            previous = accepted[-1][0]
            for k in range(len(previous) - 1):
                root = previous[:k+1]
                excluded = {tuple(sorted((p[k], p[k+1]))) for p, _ in accepted if len(p) > k+1 and p[:k+1] == root}
                spur = search(root[-1], blocked_nodes | set(root[:-1]), blocked_edges | excluded)
                if not spur:
                    continue
                candidate = root[:-1] + spur[0]
                signature = tuple(candidate)
                if signature in seen:
                    continue
                seen.add(signature)
                cost = path_cost(candidate)
                heapq.heappush(pending, (cost, len(candidate), next(serial), candidate))
            if not pending:
                break
            cost, _, _, path = heapq.heappop(pending)
            accepted.append((path, cost))
        results = []
        for rank, (path, cost) in enumerate(accepted, 1):
            ids, hops = path[:-1], []
            for a, b in zip(ids, ids[1:]):
                evidence = pair_cache[tuple(sorted((a,b)))]
                hop_cost = -math.log(HOP_FACTOR * evidence['strength']) + uncertainty_weight * evidence['uncertainty']['cost']
                workplaces = [{**w, 'employer_label': router.nodes.get(w['employer_id'], {}).get('label', w['employer_id'])}
                              for w in evidence['workplaces']]
                selected_sources = {p: [{k:v for k,v in e.items() if not k.startswith('_')}
                    for e in index.source_episodes.get(p, [])
                    if any(e['employer_id'] == w['employer_id'] and
                           any(ordinal(e['start']) < end and ordinal(e['end_exclusive']) > start
                               for start,end in w['overlap_intervals']) for w in workplaces)] for p in (a,b)}
                modeled = any(e['modeled_payroll_interval'] for rows in selected_sources.values() for e in rows)
                hops.append({**evidence, 'workplaces': workplaces, 'source': a, 'target': b,
                    'work_sources': sorted({e['work_source'] for rows in selected_sources.values() for e in rows}),
                    'modeled_exposure': modeled,
                    'overlap_duration_days': None if modeled else evidence['overlap_duration_days'],
                    'model_interval_overlap_days': evidence['overlap_duration_days'] if modeled else None,
                    'date_semantics': 'Exposure may include modeled payroll report intervals; see source bounds and role scope' if modeled else 'Exposure from supplied employment intervals; payroll trajectory titles are stint summaries',
                    'relationship': 'work_time_overlap', 'relationship_label': 'Dated workplace overlap, adjusted for staff size',
                    'cost': hop_cost, 'work_proximity': evidence['effective_exposure_days']/evidence['overlap_duration_days'],
                    'employer_id': workplaces[0]['employer_id'] if len(workplaces) == 1 else None,
                    'employer_label': workplaces[0]['employer_label'] if len(workplaces) == 1 else 'Multiple documented workplaces',
                    'evidence_class': 'modeled_payroll_exposure' if modeled else 'dated_work_overlap', 'temporal_overlap_established': not modeled,
                    'modeled_overlap': modeled, 'personal_familiarity_established': False,
                    'provenance': {'model': VERSION, 'allocation_model_is_assumption': True,
                        'formula': 'route cost=sum(-log(0.8*W)+weight*u) plus uncertainty-adjusted terminal office anchor; u is not a probability',
                        'source_evidence': selected_sources}})
            end = ids[-1]
            score = math.exp(-cost) * ((1+MEMBER_BETA) if office else 1)
            uncertainty_cost = sum(h['uncertainty']['cost'] for h in hops) + terminal[end][4]['cost']
            unpenalized = math.prod(HOP_FACTOR * h['strength'] for h in hops)
            if office:
                unpenalized *= terminal[end][1] * terminal[end][3]
            results.append({**base, 'status': 'found', 'optimal': True, 'target': end,
                'node_ids': ids, 'steps': len(hops), 'cost': cost, 'ranking_cost': cost,
                'connection_score': score, 'route_strength': score/terminal[end][3] if office else score,
                'unpenalized_connection_score': unpenalized, 'uncertainty_cost': uncertainty_cost,
                'uncertainty_factor': math.exp(-uncertainty_weight * uncertainty_cost),
                'office_anchor_uncertainty': terminal[end][4] if office else None,
                'member_context': terminal[end][2], 'member_context_source': context.provenance,
                'member_context_max_bonus': MEMBER_BETA, 'office_anchor_strength': terminal[end][1] if office else None,
                'hops': hops, 'edges': hops, 'route_rank': rank,
                'graph': {'nodes': [router.nodes[p] for p in ids], 'edges': hops}})
        # Describe dependence among the returned alternatives without pretending
        # that k-best paths are independent trials or a calibrated success rate.
        if results:
            first_pairs = {tuple(sorted((a,b))) for a,b in zip(results[0]['node_ids'],results[0]['node_ids'][1:])}
            first_people = set(results[0]['node_ids'][1:-1])
            first_contexts = {w['context_group'] for h in results[0]['hops'] for w in h['workplaces']}
            for route in results:
                pairs = {tuple(sorted((a,b))) for a,b in zip(route['node_ids'],route['node_ids'][1:])}
                contexts = {w['context_group'] for h in route['hops'] for w in h['workplaces']}
                route['dependence_on_best_route'] = {
                    'shared_staff_edges': len(first_pairs & pairs),
                    'shared_intermediaries': len(first_people & set(route['node_ids'][1:-1])),
                    'shared_workplace_contexts': len(first_contexts & contexts),
                    'same_terminal_contact': route['target'] == results[0]['target'],
                    'scope': 'returned alternatives only; no independence or failure-probability claim'}
        result = results[0] if results else {**base, 'status': 'unreachable', 'optimal': True}
        result = {**result, 'expanded': expanded, 'neighbor_checks': checks,
                  'search_elapsed_ms': round((time.monotonic()-started)*1000, 2)}
        if options['route_count'] > 1:
            result.update(routes=results, routes_requested=options['route_count'], routes_returned=len(results), alternatives_complete=True)
        self.cache[key] = deepcopy(result)
        while len(self.cache) > 32:
            self.cache.popitem(last=False)
        return result
