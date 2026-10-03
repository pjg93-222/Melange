"""Insights over verified published facts, with bounded background preparation.

This adapter never repairs/reclassifies source observations or fetches APIs.
Dataset IDs resolve through the same report/source proof as Chart Studio.
"""
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date
import copy
import json
import math
from pathlib import Path
import re
import threading

import analysis_history as history
import analysis_scan
import analysis_metrics as metrics
import analysis_integrations as integrations
import contribution_data as data
import contribution_query as query_engine
import contribution_query_store as store
import contribution_workbook_guard as guard

PANELS = [
    ('favorites', 'Industry favorites', 'Recipient amounts, positive-gross shares, company breadth and persistence.'),
    ('trends', 'Comparable trends', 'Compare cycles at the same election-stage cutoff.'),
    ('changes', 'What changed', 'Reconcile continuing, newly observed and no-longer-observed company activity.'),
    ('concentration', 'Concentration & breadth', 'Positive-gross concentration, largest sources and recipient shares.'),
    ('relationships', 'Relationship persistence', 'Compare observed company–recipient relationships across cycles.'),
    ('overlap', 'Company portfolio overlap', 'Compare company distributions across recipient committees.'),
    ('timing', 'Timing patterns', 'Monthly and quarterly giving, election phase and historical context.'),
    ('profiles', 'Recipient profiles', 'Exact dated FEC committee and candidate links.'),
    ('spending', 'Outgoing spending', 'Separate saved disbursements and candidate financial summaries.'),
    ('legislation', 'Legislative context', 'Dated legislative records linked through explicit identities.'),
    ('forecast', 'Forecasts', 'Historical baselines and rolling backtests only when coverage supports them.')]
PANEL_IDS = [p[0] for p in PANELS]
ROOT = data.PROJECT / 'state' / 'insights'
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='mentat-insights')
_lock = threading.RLock()
_jobs = OrderedDict()
_code = {str(p): data._stamp(p) for p in (Path(__file__), Path(metrics.__file__), Path(history.__file__), Path(integrations.__file__), Path(analysis_scan.__file__))}
_code_hash = history.digest({p: data._hash(p) for p in _code})


class _CapacityReached(Exception):
    """Abort the incomplete journal while retaining honest unavailable panels."""


def _loaded():
    query_engine._check_loaded()
    if any(data._stamp(p) != stamp for p, stamp in _code.items()):
        raise ValueError('Insights code changed. Restart Mentat to load the current analysis rules.')


def validate(request, records=False):
    if not isinstance(request, dict):
        raise ValueError('Insights requests must be objects.')
    allowed = {'dataset', 'basis', 'as_of', 'company', 'funding_source', 'baseline_cycle',
               'current_cycle', 'comparison_dataset', 'panels', 'top_n', 'retry'}
    if records:
        allowed |= {'filters', 'offset', 'limit', 'index_token'}
    if set(request) - allowed:
        raise ValueError('Unknown Insights request fields: ' + ', '.join(sorted(set(request) - allowed)))
    out = dict(request)
    for key in ('dataset', 'company', 'funding_source', 'comparison_dataset'):
        value = out.get(key, '')
        if not isinstance(value, str) or len(value) > 300:
            raise ValueError('Choose a valid ' + key.replace('_', ' ') + '.')
    if not out.get('dataset'):
        raise ValueError('Choose a published industry dataset.')
    out['basis'] = out.get('basis', 'receipt')
    if not isinstance(out['basis'], str) or out['basis'] not in data.BASES or out['basis'] == 'raw':
        raise ValueError('Choose a giving or PAC activity basis; raw observations are not giving.')
    if out.get('as_of') is not None and not isinstance(out.get('as_of'), str):
        raise ValueError('Choose a valid as-of calendar date.')
    try:
        out['as_of'] = date.fromisoformat(out.get('as_of') or date.today().isoformat()).isoformat()
    except (ValueError, TypeError):
        raise ValueError('Choose a valid as-of calendar date.') from None
    for key in ('baseline_cycle', 'current_cycle'):
        value = out.get(key)
        if value:
            year = metrics._cycle(value)
            if year is None:
                raise ValueError('Choose a valid two-year election cycle.')
            out[key] = metrics._label(year)
    if out.get('baseline_cycle') and out.get('current_cycle') and out['baseline_cycle'] >= out['current_cycle']:
        raise ValueError('The baseline cycle must be earlier than the current cycle.')
    panels = out.setdefault('panels', ['favorites', 'trends', 'changes'])
    if not isinstance(panels, list) or any(not isinstance(p, str) or p not in PANEL_IDS for p in panels):
        raise ValueError('Choose valid analysis panels.')
    out['panels'] = list(dict.fromkeys(panels))
    count = out.setdefault('top_n', 25)
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError('Choose 1 to 100 result rows per panel.')
    if out.get('comparison_dataset') == out['dataset']:
        raise ValueError('Choose a different tracked industry for comparison.')
    if records:
        filters = out.get('filters', [])
        if not isinstance(filters, list) or len(filters) > 32:
            raise ValueError('Choose valid source filters.')
        safe_fields = set(data.DIMENSIONS) | {'amount'}
        if any(not isinstance(f, dict) or not isinstance(f.get('field'), str) or f['field'] not in safe_fields for f in filters):
            raise ValueError('Source inspection accepts only observation dimensions and amount filters.')
        for item in filters:
            values = item.get('value') if item.get('op') == 'in' and isinstance(item.get('value'), list) else [item.get('value')]
            if any(isinstance(value, int) and not -2**63 <= value <= 2**63 - 1 or
                   isinstance(value, float) and not math.isfinite(value) for value in values):
                raise ValueError('Source filters require finite values within the supported integer range.')
        data._validate({**out, 'dimensions': [], 'measures': ['amount']})
        if out.get('limit', 50) > 5000:
            raise ValueError('Inspect at most 5,000 source records per page.')
        if out.get('offset', 0) > 2**63 - 1:
            raise ValueError('Choose a valid source record offset.')
        if 'index_token' in out and (not isinstance(out['index_token'], str) or len(out['index_token']) > 128):
            raise ValueError('Choose a valid source snapshot token.')
        data._row_filter(filters, data.BASES[out['basis']][1])
    return out


def catalog(directory, sources=None):
    result = data.catalog(directory, sources)
    checks = {item['dataset']: item for item in guard.verify_sources(directory, strict=False)}
    for dataset in result['datasets']:
        check = checks.get(dataset['id'])
        if check and (not check['matched'] or any(check.get(k) is not None and dataset.get('provenance', {}).get(k) != check[k]
                                                 for k in ('workbook_sha256', 'database_sha256'))):
            dataset.update(available=False, message=check.get('error') or 'The published source changed. Refresh sources.')
    result['panels'] = [dict(id=p, title=t, description=d, default=p in PANEL_IDS[:3]) for p, t, d in PANELS]
    result['bases'] = [b for b in result.get('bases', []) if b.get('id') != 'raw']
    result['default_panels'] = PANEL_IDS[:3]
    return result


def _scope_filters(request):
    return [{'field': key, 'op': 'eq', 'value': request[key]}
            for key in ('company', 'funding_source') if request.get(key)]


def _rows(path, request):
    column = data.BASES[request['basis']][1]
    where, params = data._row_filter(_scope_filters(request), column)
    fields = ('source_id,industry,company,committee_id,recipient,date,cycle,funding_source,party,'
              'contributor_key,raw_cents,receipt_cents,original_cents,supported_cents,pac_cents')
    with closing(data._ro(path)) as db:
        for row in db.execute('SELECT ' + fields + ',' + column + ' AS amount_cents FROM facts WHERE ' + where + ' AND ' + column + ' != 0', params):
            yield dict(row)


def _options(path, basis):
    with closing(data._ro(path)) as db:
        column = data.BASES[basis][1]
        return {out: [r[0] for r in db.execute('SELECT DISTINCT "' + field + '" FROM facts WHERE ' + ('1' if field == 'company' else column + ' != 0') + ' AND "' + field + '" != \'\' ORDER BY "' + field + '"')]
                for field, out in [('company', 'companies'), ('cycle', 'cycles'), ('funding_source', 'funding_sources')]}


def _context_rows(rows, context, request):
    pairs, companies = set(), {request['company']} if request.get('company') else set()
    cutoff = date.fromisoformat(request['as_of'])
    for row in rows:
        try:
            observed = date.fromisoformat(row['date'])
            eligible = observed <= cutoff
        except (ValueError, TypeError):
            eligible = False
        cycle = metrics._cycle(row['cycle'])
        if eligible and cycle and observed.year in (cycle - 1, cycle):
            companies.add(row['company'])
            if re.fullmatch(r'C\d{8}', row['committee_id'] or ''):
                pairs.add((row['committee_id'], cycle))
        yield row
    context.update(recipient_cycles=[{'recipient_id': recipient, 'cycle': cycle} for recipient, cycle in sorted(pairs)],
                   recipient_ids=sorted({p[0] for p in pairs}), cycles=sorted(set(context.get('cycles', [])) | {p[1] for p in pairs}), companies=sorted(companies))


def _reference(path, request, source):
    comparison = {**request, 'company': ''}
    channels = defaultdict(lambda: {'total_positive_cents': 0, 'recipient_positive_cents': defaultdict(int)})
    for row in _rows(path, comparison):
        try:
            if date.fromisoformat(row['date']) > date.fromisoformat(request['as_of']):
                continue
        except (ValueError, TypeError):
            pass  # Favorites includes undated observations and discloses that scope.
        amount = max(0, row['amount_cents'])
        group = channels[row['funding_source'] or metrics.UNKNOWN]
        group['total_positive_cents'] += amount
        group['recipient_positive_cents'][row['committee_id'] or metrics.UNKNOWN] += amount
    return {'by_channel': dict(channels), 'label': source.get('industry', source['id']),
            'coverage_note': 'Explicit tracked-industry comparator, all covered companies at the selected basis and cutoff; not a market-wide baseline.'}


def _periods(cycles, as_of, current=None):
    """Cycles at or before the as-of cycle, and the automatic current/baseline pair."""
    phase = date.fromisoformat(as_of).year
    phase += phase % 2
    available = [c for c in cycles if metrics._cycle(c) and metrics._cycle(c) <= phase]
    current = current or (available[-1] if available else '')
    earlier = [c for c in available if c < current]
    return available, current, (earlier[-1] if earlier else '')


# Cycle options seen for a source snapshot and basis. They let an explicit period
# that equals the automatic one share the automatic request's key and job.
_cycle_options = {}


def _remember_cycles(stamp, basis, cycles):
    if len(_cycle_options) >= 64:
        _cycle_options.clear()
    _cycle_options[(stamp, basis)] = list(cycles)


def _canonical(request, stamp):
    cycles = _cycle_options.get((stamp, request['basis']))
    if cycles is None:
        return request
    out = dict(request)
    _, automatic_current, _ = _periods(cycles, request['as_of'])
    if out.get('current_cycle') == automatic_current:
        del out['current_cycle']
    _, _, automatic_baseline = _periods(cycles, request['as_of'], out.get('current_cycle'))
    if out.get('baseline_cycle') and out['baseline_cycle'] == automatic_baseline:
        del out['baseline_cycle']
    return out


def _prepare(path, source, request, comparator=None):
    import analysis_integrations as integrations
    stamp = data._stamp(path)
    path = analysis_scan.view(path)
    options = _options(path, request['basis'])
    _remember_cycles(stamp, request['basis'], options['cycles'])
    available, current, baseline = _periods(options['cycles'], request['as_of'], request.get('current_cycle'))
    for field in ('current_cycle', 'baseline_cycle'):
        if request.get(field) and request[field] not in available:
            raise ValueError('Choose a cycle present in this dataset at or before the as-of cycle.')
    baseline = request.get('baseline_cycle') or baseline
    if baseline and current and baseline >= current:
        raise ValueError('The baseline cycle must be earlier than the current cycle.')
    scoped = {**request, 'baseline_cycle': baseline, 'current_cycle': current}
    with closing(data._ro(path)) as db:
        metadata = json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
    provenance = {**metadata.get('provenance', {}), 'index_token': data._token(source), 'analysis_code_sha256': _code_hash}
    context = {'source_scope': {'dataset': source['id'], 'industry': source.get('industry', source['id']),
                                'basis': request['basis'], 'as_of': request['as_of']}, 'provenance': provenance,
               'cycles': sorted({metrics._cycle(c) for c in available})}
    if comparator:
        context['industry_reference'] = _reference(comparator[0], scoped, comparator[1])
        provenance['comparison'] = data._provenance(comparator[1])
    # Complete collection history is deliberately not inferred from observed rows.
    # No trusted completeness manifest is presently part of the contribution index.
    try:
        with history.inspection(source['id'], provenance['index_token'], provenance) as journal:
            facts = _context_rows(journal.observe(_rows(path, scoped)), context, scoped)
            result = metrics.analyze(facts, {**scoped, 'panels': [p for p in request['panels'] if p in metrics.PANEL_ORDER]}, context)
            if result.get('metadata', {}).get('complete_input_scan') is False:
                raise _CapacityReached()
            extra = integrations.enrich(scoped, context) if set(request['panels']) & {'profiles', 'spending', 'legislation'} else {}
            for panel in extra.values():
                total = max(panel.get('total_rows', 0), len(panel.get('rows', [])))
                panel['total_rows'] = total
                if len(panel.get('rows', [])) > request['top_n']:
                    panel['rows'] = panel['rows'][:request['top_n']]
                    panel['truncated'] = True
                    panel.setdefault('notices', []).append(f"Showing {request['top_n']} of {total} source rows; source coverage and totals remain separate from this display limit.")
            result['panels'].update(extra)
            result['history'] = journal.summary()
            yield result, options, scoped, provenance
    except _CapacityReached:
        notice = 'This scope exceeds the exact analysis capacity. Select a company or funding source; no partial totals or inspection snapshot were published.'
        for key, title, description in PANELS:
            result['panels'][key] = {'title': title, 'status': 'unavailable', 'summary': notice,
                                     'columns': [], 'rows': [], 'notices': [notice]}
        result['history'] = None
        yield result, options, scoped, provenance


def _stable(path, source, stamp, token):
    return store.source_stable(path, stamp) and data._token(source) == token


def query(directory, request):
    _loaded()
    request = validate(request)
    source = data._source(directory, request)
    path, pending = data._ready(source, retry=request.get('retry') is True)
    if pending:
        return pending
    token, stamp = data._token(source), data._stamp(path)
    comparator = None
    if request.get('comparison_dataset'):
        guard.verify_sources(directory, request['comparison_dataset'])
        other = data._source(directory, {'dataset': request['comparison_dataset']})
        other_path, pending = data._ready(other, retry=request.get('retry') is True)
        if pending:
            return {**pending, 'provenance': data._provenance(source), 'message': 'Preparing the selected comparison industry.'}
        comparator = (other_path, other, data._stamp(other_path), data._token(other))
    import analysis_integrations as integrations
    integration_context = {'source_scope': {'dataset': source['id'], 'industry': source.get('industry', source['id']),
                                            'basis': request['basis'], 'as_of': request['as_of']}}
    needs_integrations = bool(set(request['panels']) & {'profiles', 'spending', 'legislation'})
    fingerprint = integrations.sources_fingerprint(integration_context) if needs_integrations else None
    # One job per resolved scope: every engine panel is computed once (the scan
    # dominates their cost) and the reply is filtered to the requested panels, so
    # switching an engine analysis on or off reuses the job. Saved integrations
    # open only when asked for. An explicit period equal to the automatic one is
    # keyed as automatic, so Swap or re-picking the shown cycle reuses it too.
    canonical = {**_canonical(request, stamp),
                 'panels': [p for p in PANEL_IDS if p in metrics.PANEL_ORDER or p in request['panels']]}
    canonical.pop('retry', None)
    key = history.digest({'source': token, 'stamp': stamp, 'code': _code_hash, 'integrations': fingerprint,
                          'comparator': comparator[2:] if comparator else None, 'request': canonical})

    def stable():
        _loaded()
        return (_stable(path, source, stamp, token) and (not comparator or _stable(*comparator))
                and (not needs_integrations or integrations.sources_fingerprint(integration_context) == fingerprint))

    if not stable():
        raise ValueError('An Insights source has changed or has active writes. Retry after collection is stable.')

    def build():
        if not stable():
            raise ValueError('The analysis source changed before preparation.')
        prepared = _prepare(path, source, canonical, comparator)
        try:
            result, options, scoped, provenance = next(prepared)
            if not stable():
                raise ValueError('An Insights source changed during analysis. Refresh against the current snapshot.')
            # Resume the generator to commit the observation journal only after
            # verifying every input still identifies the same snapshot.
            try:
                next(prepared)
            except StopIteration:
                pass
        finally:
            prepared.close()
        return {'status': 'ready', 'dataset': source['id'], 'scope': {**scoped, 'basis_label': data.BASES[canonical['basis']][0]},
                'provenance': provenance, 'options': options, **result,
                'source_history': history.snapshots(source['id']),
                'notices': [history.NOTICE, 'Event-date cutoffs do not recreate what was publicly known on that date.',
                            'Amounts describe observed giving; they do not establish influence or a causal connection to legislative activity.']}

    with _lock:
        future = _jobs.get(key)
        if future and future.done() and future.exception() and request.get('retry'):
            del _jobs[key]
            future = None
        if future is None:
            if sum(not job.done() for job in _jobs.values()) >= 6:
                return {'status': 'preparing', 'message': 'Other Insights requests are finishing. This request will retry shortly.',
                        'retry_after_ms': 2000, 'provenance': data._provenance(source)}
            future = _pool.submit(store.cached, 'insights', {'request_key': key}, build, stable)
            _jobs[key] = future
        _jobs.move_to_end(key)
        while len(_jobs) > 12:
            old = next((k for k, f in _jobs.items() if f.done() and k != key), None)
            if old is None:
                break
            del _jobs[old]
    if not future.done():
        return {'status': 'preparing', 'message': 'Analyzing the complete verified scope and saved source integrations…',
                'retry_after_ms': 1500, 'provenance': data._provenance(source)}
    result = copy.deepcopy(future.result())
    if not stable():
        raise ValueError('The source changed before the analysis could be displayed. Refresh sources.')
    if (result.get('options') or {}).get('cycles') is not None:
        _remember_cycles(stamp, request['basis'], result['options']['cycles'])
    result['panels'] = {key: value for key, value in result['panels'].items() if key in request['panels']}
    result['scope']['panels'] = request['panels']
    return result


def records(directory, request):
    _loaded()
    request = validate(request, records=True)
    source = data._source(directory, request)
    if request.get('index_token') and data._token(source) != request['index_token']:
        raise ValueError('The source changed since this analysis. Refresh Insights before opening its records.')
    # The engine emits exact event/cycle constraints for each row. The global
    # cutoff also applies; undated facts remain eligible for nontemporal panels.
    column = data.BASES[request['basis']][1]
    filters = _scope_filters(request) + request.get('filters', [])
    path, pending = data._ready(source, retry=request.get('retry') is True)
    if pending:
        return pending
    token, stamp = data._token(source), data._stamp(path)
    cutoff = date.fromisoformat(request['as_of'])
    temporal = any(item.get('field') == 'date' for item in filters)
    def eligible(value):
        try:
            return int(date.fromisoformat(value) <= cutoff)
        except (TypeError, ValueError):
            return 0 if temporal else 1
    where, params = data._row_filter(filters, column)
    where += ' AND ' + column + ' != 0 AND insights_event_allowed(date)=1'
    limit, offset = request.get('limit', 50), request.get('offset', 0)
    with closing(data._ro(path)) as db:
        db.create_function('insights_event_allowed', 1, eligible, deterministic=True)
        count = db.execute('SELECT COUNT(*) FROM facts WHERE ' + where, params).fetchone()[0]
        rows = [dict(row) for row in db.execute('SELECT *,' + column + ' AS amount_cents FROM facts WHERE ' + where +
                ' ORDER BY date DESC,source_id LIMIT ? OFFSET ?', params + [limit, offset])]
    if not _stable(path, source, stamp, token):
        raise ValueError('The source changed during record inspection. Refresh Insights.')
    history.annotate(request['dataset'], rows)
    for row in rows:
        row.pop('contributor_key', None)
        for field in ('reasons', 'evidence_ids'):
            row[field] = json.loads(row[field])
    result = {'status': 'ready', 'dataset': source['id'], 'basis': request['basis'], 'rows': rows,
              'total_records': count, 'offset': offset, 'limit': limit, 'has_more': offset + len(rows) < count,
              'provenance': {**data._provenance(source), 'index_token': token}, 'amount_unit': 'cents',
              'notices': [history.NOTICE]}
    return result
