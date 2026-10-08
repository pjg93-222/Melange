"""Command line: discover | collect | extract | validate | build (= extract + validate, offline) | run (= collect + build) | status | receipt."""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

from . import config as C
from .fetch import Fetcher, iso_to_epoch
from .lock import LockHeld, OwnerLock
from .runner import ALL_TIERS, STAGES, Runner
from .util import atomic_write_json


def build_parser():
    p = argparse.ArgumentParser(prog='osc', description='Standardized OpenSecrets public-page collector (cache-first, resumable, bounded).')
    p.add_argument('command', choices=['discover', 'collect', 'extract', 'validate', 'build', 'run', 'status', 'receipt'])
    p.add_argument('--scopes', default=str(C.DEFAULT_SCOPES), help='scope registry JSON')
    p.add_argument('--data-dir', default=str(C.DEFAULT_DATA), help='raw-byte cache + request log + retry_state.json + owner lock')
    p.add_argument('--state-dir', default=str(C.DEFAULT_STATE), help='work queue, status/progress JSON')
    p.add_argument('--out-dir', default=str(C.DEFAULT_OUT), help='CSV output directory')
    p.add_argument('--roster-csv', default=str(C.DEFAULT_ROSTER), help='read-only Mentat roster CSV (normalized_company_name column) for exact-name org search; "" disables')
    p.add_argument('--offline-lobby-dir', default=str(C.DEFAULT_OFFLINE_LOBBY),
                   help='directory with the unchanged native annual-lobbying exports + RECOVERY_NOTES.txt (supplemental, used only where the HTTP annual chart is unavailable); "" disables')
    p.add_argument('--concurrency', type=int, default=4)
    p.add_argument('--min-interval', type=float, default=0.35, help='seconds between transport calls, global across workers and families')
    p.add_argument('--transport', choices=['auto', 'curl', 'requests'], default='auto')
    p.add_argument('--refresh', action='store_true', help='refetch everything (ignore cache)')
    p.add_argument('--retry-failed', action='store_true', help='refetch cached failures too (403/404 are otherwise final)')
    p.add_argument('--tiers', default='all', help=f'comma list of {sorted(ALL_TIERS)} or "all" (default all: seeds, PAC recipient pages, lobbying splits, org profiles)')
    p.add_argument('--max-requests', type=int, default=None, help='hard cap on transport calls for this run')
    p.add_argument('--split-cap', type=int, default=None, help='cap on client in-house/outside pages')
    p.add_argument('--org-cap', type=int, default=None, help='cap on organisations looked up')
    p.add_argument('--only', default='', help='comma list of stages to run (default: all selected tiers)')
    p.add_argument('--extract-only', default='', help='extract/validate only these builders (e.g. national); writes only their tables (use a separate --out-dir)')
    p.add_argument('--max-retry-after', type=float, default=300.0, help='longest explicit Retry-After sat out inline; longer defers (always honoured, also after restart)')
    p.add_argument('--family-429-limit', type=int, default=3, help='consecutive 429s without Retry-After before a URL family is deferred')
    p.add_argument('--family-cooldown', type=float, default=300.0, help='seconds a 429-limited family is deferred (other families keep running)')
    p.add_argument('--deadline-utc', default='', help='ISO-8601 UTC wall-clock deadline: no new request is issued after it; unfinished URLs stay deferred in the queue (resume = re-run)')
    p.add_argument('--max-passes', type=int, default=500, help='cap on resume passes when --max-defer-wait lets the process wait out deferrals')
    p.add_argument('--max-defer-wait', type=float, default=0.0,
                   help='if the earliest deferral resumes within this many seconds, wait and continue in-process; else stop and persist the queue (default 0 = never idle-wait)')
    return p


def _tiers(arg):
    if arg == 'all':
        return set(ALL_TIERS)
    t = {x.strip() for x in arg.split(',') if x.strip()}
    bad = t - ALL_TIERS
    if bad:
        raise SystemExit(f'unknown tier(s): {sorted(bad)}')
    return t


def make_fetcher(a, cache_only=False):
    return Fetcher(a.data_dir, refresh=a.refresh and not cache_only, retry_failed=a.retry_failed and not cache_only,
                   concurrency=a.concurrency, min_interval=a.min_interval, transport=a.transport,
                   cache_only=cache_only, budget=a.max_requests, max_retry_after=a.max_retry_after,
                   family_429_limit=a.family_429_limit, family_cooldown=a.family_cooldown,
                   stop_after_epoch=iso_to_epoch(a.deadline_utc) if a.deadline_utc else None)


def resume_command(a):
    return f'python -m osc collect --tiers {a.tiers} --data-dir "{a.data_dir}" --state-dir "{a.state_dir}" --out-dir "{a.out_dir}"'


def cmd_collect(a, only_seeds=False):
    cfg = C.load_scopes(a.scopes)
    f = make_fetcher(a)
    r = Runner(f, cfg, a.state_dir, tiers=_tiers(a.tiers), split_cap=a.split_cap, org_cap=a.org_cap, roster_csv=a.roster_csv)
    atomic_write_json(Path(a.state_dir) / 'pid.json', {'pid': os.getpid(), 'run_id': f.run_id, 'started_utc': r.started, 'argv': sys.argv, 'cwd': os.getcwd()})
    only = {s.strip() for s in a.only.split(',') if s.strip()} or ({s for s in STAGES if s.startswith('seeds')} if only_seeds else None)
    print(f'[osc] pid={os.getpid()} run_id={f.run_id} transport={f.transport_name()} concurrency={f.concurrency} min_interval={f.min_interval}s '
          f'tiers={sorted(r.tiers)} budget={a.max_requests}', flush=True)
    t = time.monotonic()
    try:
        r.run(only=only, max_defer_wait=a.max_defer_wait, max_passes=a.max_passes)
    finally:
        if r.phase not in ('collect_finished', 'collect_deferred'):
            r.phase = 'interrupted'
        r.save()
    s = f.stats
    print(f"[osc] collect {r.phase} in {time.monotonic() - t:.0f}s transport_calls={s['transport_calls']} redirect_hops={s['redirect_hops']} "
          f"url_fetches={s['url_fetches']} cache_hits={s['cache_hits']} dup_avoided={s['duplicate_requests_avoided']} retries={s['retries']} "
          f"429s={s['http_429']} deferred_urls={s['deferred_urls']} status={s['status_counts']} bytes={s['bytes_downloaded']}", flush=True)
    ds = r.deferred_summary()
    if ds['urls']:
        print(f"[osc] {ds['urls']} URL(s) DEFERRED by server rate limits (not observed, not failed): earliest resume {ds['earliest_resume_utc']}; "
              f"by stage {ds['by_stage']}\n[osc] resume with: {resume_command(a)}", flush=True)
    return r


def cmd_discover(a):
    r = cmd_collect(a, only_seeds=True)
    print('[osc] discovery: derived-stage plan sizes (transport calls still needed = planned - already cached)')
    f = make_fetcher(a, cache_only=True)
    r.f = f
    for stage in ['pac_recipients', 'lobby_splits', 'org_search', 'org_totals']:
        urls = r.plan(stage)
        cached = sum(1 for u in urls if f.load_cached(u) is not None)
        print(f'  {stage}: planned={len(urls)} cached={cached} to_fetch={len(urls) - cached}')


def process_info(pid):
    """Read-only liveness + identity query. NEVER os.kill(pid, 0): on Windows CPython that is TerminateProcess for non-CTRL signals."""
    if not pid:
        return {'alive': False, 'is_osc': False, 'command_line': ''}
    pid = int(pid)
    if sys.platform == 'win32':
        try:
            cmd = f"Get-CimInstance Win32_Process -Filter 'ProcessId={pid}' | Select-Object -ExpandProperty CommandLine"
            p = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', cmd], capture_output=True, text=True, timeout=30)
            line = (p.stdout or '').strip()
            if p.returncode == 0:
                return {'alive': bool(line), 'is_osc': ' osc' in f' {line}' or 'osc.cli' in line, 'command_line': line[:300]}
        except (OSError, subprocess.SubprocessError):
            pass
        out = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'], capture_output=True, text=True).stdout
        return {'alive': f'"{pid}"' in out, 'is_osc': None, 'command_line': ''}
    try:  # POSIX: signal 0 is a pure existence probe
        os.kill(pid, 0)
    except OSError:
        return {'alive': False, 'is_osc': False, 'command_line': ''}
    try:
        line = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
    except OSError:
        line = ''
    return {'alive': True, 'is_osc': ('osc' in line) if line else None, 'command_line': line[:300]}


def cmd_status(a):
    sp = Path(a.state_dir) / 'status.json'
    if not sp.exists():
        print('no status.json yet')
        return
    st = json.loads(sp.read_text(encoding='utf-8'))
    pid = st.get('pid')
    info = process_info(pid)
    print(json.dumps({k: st[k] for k in ('run_id', 'phase', 'stage', 'elapsed_s', 'queue_states', 'deferred', 'updated_utc') if k in st}, indent=1))
    print(f"pid={pid} alive={info['alive']} command_is_osc={info['is_osc']} (read-only query; persisted status is as of {st.get('updated_utc')})")
    owner = OwnerLock(a.data_dir).owner()
    if owner:
        print(f"owner lock file: pid={owner.get('pid')} acquired={owner.get('acquired_utc')} released={owner.get('released_utc', '-')}")
    rs = Path(a.data_dir) / 'retry_state.json'
    if rs.exists():
        print(f'retry_state: {rs.read_text(encoding="utf-8")[:600]}')
    for name, stage in st.get('stages', {}).items():
        print(f'  {name}: {stage}')


def main(argv=None):
    a = build_parser().parse_args(argv)
    lock = None
    if a.command in ('discover', 'collect', 'run'):
        try:  # one collector per cache directory: discover and collect can never overlap
            lock = OwnerLock(a.data_dir).acquire(command=a.command, state_dir=str(a.state_dir))
        except LockHeld as exc:
            print(f'[osc] refusing to start: {exc}', file=sys.stderr)
            raise SystemExit(2)
    try:
        _dispatch(a)
    finally:
        if lock:
            lock.release()


def _dispatch(a):
    if a.command == 'discover':
        cmd_discover(a)
    elif a.command == 'collect':
        cmd_collect(a)
    elif a.command == 'status':
        cmd_status(a)
    elif a.command == 'receipt':
        from .receipt import write_receipt
        t = subprocess.run([sys.executable, '-m', 'pytest', str(C.ROOT / 'tests'), '-q'], capture_output=True, text=True, cwd=str(C.ROOT))
        rep = write_receipt(a, t.stdout + t.stderr)
        print(f"[receipt] RECEIPT.md written; transport_calls={rep['transport_calls']} checks={rep['crosscheck_summary']} pytest={rep['pytest']}")
    else:
        from . import extract as E  # imported lazily: extraction is offline and independent of collection
        if a.command == 'run':
            cmd_collect(a)
        E.run_extract_and_validate(a, make_fetcher(a, cache_only=True), do_extract=a.command in ('extract', 'build', 'run'),
                                   do_validate=a.command in ('validate', 'build', 'run'))


if __name__ == '__main__':
    main()
