"""Final receipt: parser coverage, request counts, elapsed, schemas, cross-checks, gaps, limitations, tests, benchmarks.
Everything numeric is computed from the run artifacts (request_log.jsonl, cache manifest, CSV outputs, status JSON); nothing is estimated by hand."""
from __future__ import annotations
import csv, json, re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from .extract import SCHEMAS
from .util import atomic_write_bytes, atomic_write_json, utc_now


CALL_EVENTS = ('transport_call', 'physical_request')   # 'physical_request' = pre-rename events of earlier runs (one transport invocation each)
# Archived pre-run_id log segments: per PROGRESS M3b the first two overlapping launches (discover + collect sharing one cache, 21:23-21:37Z) were
# duplicate/aborted and were killed at 21:37:44Z; everything later without a run_id is the 21:44Z single-process run that was stopped at 21:54Z.
ABORTED_DUPLICATE_BEFORE_UTC = '2026-10-01T21:40:00+00:00'


def run_segments(calls):
    """Benchmarks per run: events carry run_id; archived events without one are split into the documented aborted/duplicate launches and
    the later single-process run. Transport calls and redirect hops are counted separately; wall time is first-to-last call of the segment."""
    seg = defaultdict(list)
    for x in calls:
        rid = x.get('run_id') or ('archived_aborted_duplicate_runs_pre_run_id' if x['utc'] < ABORTED_DUPLICATE_BEFORE_UTC else 'archived_run_35396_pre_run_id')
        seg[rid].append(x)
    out = {}
    for rid, xs in seg.items():
        t = [datetime.fromisoformat(x['utc']) for x in xs]
        out[rid] = {'transport_calls': len(xs), 'redirect_hops': sum(x.get('redirect_hops') or 0 for x in xs), 'ok_200': sum(1 for x in xs if x.get('http_status') == 200),
                    'http_429': sum(1 for x in xs if x.get('http_status') == 429), 'bytes': sum(x.get('bytes') or 0 for x in xs),
                    'first_utc': xs[0]['utc'], 'last_utc': xs[-1]['utc'], 'wall_seconds': round((max(t) - min(t)).total_seconds(), 1),
                    'aborted_or_duplicate': rid.startswith('archived_aborted')}
    return out


def _csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def _page_type(url):
    rules = [(r'/elections-overview\?cycle=', 'national overview'), (r'cost-of-election', 'cost of election'), (r'industry-breakdown', 'PAC industry breakdown'),
             (r'industry-detail', 'PAC industry detail (roster)'), (r'candidate-recipients', 'PAC candidate recipients'), (r'/industries/totals', 'legacy industry totals'),
             (r'/industries/contrib', 'legacy top contributors'), (r'/industries/summary', 'legacy combined candidate list'),
             (r'/industries/lobbying', 'legacy lobbying'), (r'chunk=annual_trends', 'lobbying annual chart'), (r'industries/[^/]+/summary/content.*chunk=main', 'lobbying client table'),
             (r'federal-lobbying/industries/[^/?]+\?', 'lobbying category page'), (r'top-industries', 'lobbying about-data note'), (r'/clients/.*cycle_snapshot', 'lobbying client in-house/outside'),
             (r'/search\?', 'org search'), (r'/orgs/.*/totals', 'org totals history'), (r'/industries/slist', 'taxonomy list')]
    for pat, name in rules:
        if re.search(pat, url):
            return name
    return 'other'


def write_receipt(a, pytest_text=''):
    out, state, data = Path(a.out_dir), Path(a.state_dir), Path(a.data_dir)
    log = []
    for line in (data / 'request_log.jsonl').read_text(encoding='utf-8').splitlines():   # tolerate a half-written last line while a collection appends
        try:
            log.append(json.loads(line))
        except ValueError:
            continue
    phys = [x for x in log if x.get('event') in CALL_EVENTS]
    manifest = _csv(out / 'request_manifest.csv')
    census = _csv(out / 'coverage_census.csv')
    gaps = _csv(out / 'gap_summary.csv')
    checks = _csv(out / 'crosschecks.csv')
    status = json.loads((state / 'status.json').read_text(encoding='utf-8')) if (state / 'status.json').exists() else {}
    ts = [datetime.fromisoformat(x['utc']) for x in phys]
    runs = run_segments(phys)
    rep = {'generated_utc': utc_now(), 'transport_calls': len(phys), 'redirect_hops': sum(x.get('redirect_hops') or 0 for x in phys),
           'by_status': dict(Counter(x['http_status'] for x in phys)),
           'by_transport': dict(Counter(x['transport'] for x in phys)), 'bytes_downloaded': sum(x.get('bytes') or 0 for x in phys),
           'first_request_utc': phys[0]['utc'] if phys else '', 'last_request_utc': phys[-1]['utc'] if phys else '',
           'wall_seconds_first_to_last_request': round((ts[-1] - ts[0]).total_seconds(), 1) if len(ts) > 1 else 0, 'urls_cached': len(manifest),
           'retries_logged': sum(1 for x in phys if x.get('attempt', 1) > 1), 'http_429_logged': sum(1 for x in phys if x.get('http_status') == 429),
           'skipped_events': dict(Counter(x['event'] for x in log if x.get('event') not in CALL_EVENTS)), 'runs': runs,
           'final_run_status': {k: status.get(k) for k in ('run_id', 'phase', 'elapsed_s', 'queue_states', 'deferred', 'min_interval_s', 'concurrency', 'transport')},
           'final_run_request_stats': status.get('request_stats', {})}
    # parser coverage by page type
    cov = defaultdict(lambda: Counter())
    for m in manifest:
        cov[_page_type(m['source_url'])][('ok' if m['http_status'] == '200' and m.get('challenge_content') not in ('True', True) else 'failed:' + str(m['http_status'] or m['error']))] += 1
    tables = {}
    for name in SCHEMAS:
        rows = _csv(out / f'{name}.csv')
        tables[name] = {'rows': len(rows), 'extraction_status': dict(Counter(r.get('extraction_status', '') for r in rows)),
                        'completeness_status': dict(Counter(r.get('completeness_status', '') for r in rows))}
    cands = {(r['requested_cycle'], r['recipient'], r['state_code']) for r in _csv(out / 'legacy_candidate_combined.csv')}
    split_rows = _csv(out / 'lobbying_client_splits.csv')
    rep.update(tables=tables, crosscheck_summary=dict(Counter(r['status'] for r in checks)), failed_checks=[r['check_id'] for r in checks if r['status'] == 'FAIL'],
               legacy_unique_candidate_cycles=len(cands), client_split_rows=len(split_rows), pytest=pytest_text.strip().splitlines()[-1] if pytest_text.strip() else '')
    atomic_write_json(out / 'receipt.json', rep)

    L = ['# OpenSecrets standardized collection - run receipt', f'Generated {rep["generated_utc"]} (UTC). Code: `standardized/osc`, README.md. No model publication/refit; Mentat production untouched.', '']
    L += ['## Requests / elapsed (computed from request_log.jsonl and the cache manifest)',
          f'- transport calls (one curl / requests invocation each; ALL runs incl. aborted duplicates): **{rep["transport_calls"]}** (by status {rep["by_status"]}; transport {rep["by_transport"]}); '
          f'redirect HTTP hops counted separately: {rep["redirect_hops"]}; URLs cached: **{rep["urls_cached"]}**; bytes downloaded {rep["bytes_downloaded"]:,}',
          f'- first/last transport call: {rep["first_request_utc"]} / {rep["last_request_utc"]}; ACTUAL wall time first-to-last call (includes rate-limit deferral waits and restarts, nothing removed): {rep["wall_seconds_first_to_last_request"]} s',
          f'- retries logged {rep["retries_logged"]}; HTTP 429 responses {rep["http_429_logged"]}; non-request events {rep["skipped_events"]}',
          f'- final run status: {rep["final_run_status"]}', f'- final run request stats: {rep["final_run_request_stats"]}', '',
          '### Benchmarks per run (aborted/duplicate launches are labelled and NOT counted as the successful-run benchmark)',
          '| run | aborted/duplicate | transport calls | redirect hops | HTTP 200 | HTTP 429 | bytes | first | last | wall s |', '|---|---|---|---|---|---|---|---|---|---|']
    for rid, v in runs.items():
        L.append(f'| {rid} | {v["aborted_or_duplicate"]} | {v["transport_calls"]} | {v["redirect_hops"]} | {v["ok_200"]} | {v["http_429"]} | {v["bytes"]:,} | {v["first_utc"]} | {v["last_utc"]} | {v["wall_seconds"]} |')
    L += ['']
    qpath = state / 'work_queue.json'
    queue = json.loads(qpath.read_text(encoding='utf-8')) if qpath.exists() else []
    by_stage = defaultdict(Counter)
    for q in queue:
        by_stage[q.get('stage', '?')][q.get('state', '?')] += 1
    ds = status.get('deferred') or {}
    finished = bool(queue) and not any(q.get('state') in ('deferred', 'failed', 'pending') for q in queue)
    rep['terminal_status'] = 'finished_complete' if finished else 'finished_with_gaps'
    rep['queue_by_stage'] = {k: dict(v) for k, v in by_stage.items()}
    atomic_write_json(out / 'receipt.json', rep)
    L += ['## Terminal status (from state/work_queue.json + status.json)',
          f'- **{rep["terminal_status"]}**: planned URLs by stage and state: {rep["queue_by_stage"]}',
          f'- deferred (server rate limit / managed challenge; not observed, not failed, never zero): {ds.get("urls", 0)}; earliest resume {ds.get("earliest_resume_utc", "")}; '
          f'active deferrals {ds.get("active_deferrals")}',
          f'- resume (same cache, same state; PowerShell, from the `standardized` folder): `python -m osc collect --tiers all --data-dir "{a.data_dir}" --state-dir "{a.state_dir}" --out-dir "{a.out_dir}"` then `python -m osc build`',
          '- Aggregates built on uncollected PAC/client/organisation pages are `partial`/`unavailable` with `partial_sum_usd` or blanks; nothing is completed from a partial census.', '']
    L += ['## Parser coverage by page type (cache manifest)', '| page type | cached ok | failed |', '|---|---|---|']
    for k, v in sorted(cov.items()):
        L.append(f'| {k} | {v["ok"]} | {sum(n for kk, n in v.items() if kk != "ok")} {({kk: n for kk, n in v.items() if kk != "ok"} or "")} |')
    L += ['', '## Tables (rows; extraction_status; completeness_status)', '| table | rows | extraction_status | completeness_status |', '|---|---|---|---|']
    for k, v in tables.items():
        L.append(f'| {k} | {v["rows"]} | {v["extraction_status"]} | {v["completeness_status"]} |')
    L += ['', '## Schemas', *[f'- `{k}`: ' + ', '.join(cols) for k, cols in SCHEMAS.items()], '']
    L += ['## Cross-checks', f'summary: {rep["crosscheck_summary"]}', '| status | check | expected | actual |', '|---|---|---|---|']
    for r in checks:
        L.append(f'| {r["status"]} | {r["check_id"]} | {r["expected"][:60]} | {r["actual"][:90]} |')
    L += ['', '## Gaps by reason (gap_summary.csv)', '| table | reason | rows |', '|---|---|---|']
    for g in sorted(gaps, key=lambda r: -int(r['rows']))[:60]:
        L.append(f'| {g["table"]} | {g["reason_code"]} | {g["rows"]} |')
    L += ['', '## Tests', '```', pytest_text.strip()[-1500:], '```', '']
    atomic_write_bytes(out.parent / 'RECEIPT.md', ('\n'.join(L) + '\n').encode('utf-8'))
    return rep
