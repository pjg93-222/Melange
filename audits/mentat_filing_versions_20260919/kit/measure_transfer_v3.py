"""Measure what the VERSION 3 unresolved-version rule costs on a real itoth.txt.

Read-only toward the Mentat checkout: the committed tools/ module is imported
from its own directory (never copied, never modified).  Everything transfer_index
writes -- its cache JSON, its .sqlite ledger and the .pending file -- lands beside
the itoth.txt path it is GIVEN, so this script must always be pointed at a
HARD LINK inside a scratch directory, never at the real source tree.

Usage:
  python measure_transfer_v3.py --cycle 2024 \
      --itoth <scratch>\\oth24\\itoth.txt \
      [--header-dir C:\\Users\\pgoff\\Mentat\\mentat\\state\\cross-reference\\filing-headers] \
      --out <scratch>\\out\\v3-2024-headers.json
"""
import argparse
import ctypes
import ctypes.wintypes as wintypes
import json
import os
import sqlite3
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path

TOOLS = Path(r'C:\Users\pgoff\Mentat\mentat\tools')


def peak_working_set_bytes():
    """Windows PeakWorkingSetSize for this process; None elsewhere/on failure."""
    try:
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                        ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        # psapi.dll forwards on some builds; kernel32's K32 export always works.
        for library, name in ((ctypes.windll.kernel32, 'K32GetProcessMemoryInfo'),
                              (ctypes.windll.psapi, 'GetProcessMemoryInfo')):
            function = getattr(library, name, None)
            if function and function(handle, ctypes.byref(counters), counters.cb):
                return int(counters.PeakWorkingSetSize)
        return None
    except Exception:
        return None


class DiskWatcher(threading.Thread):
    """Sample the bytes transfer_index has on disk beside the hard link."""

    def __init__(self, directory, interval=2.0):
        super().__init__(daemon=True)
        self.directory = Path(directory)
        self.interval = interval
        self.peak = 0
        self.peak_detail = {}
        self._stop = threading.Event()

    def sample(self):
        total = 0
        detail = {}
        for path in self.directory.iterdir():
            if path.name.endswith('itoth.txt') or not path.is_file():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            total += size
            detail[path.name] = size
        if total > self.peak:
            self.peak = total
            self.peak_detail = detail
        return total

    def run(self):
        while not self._stop.wait(self.interval):
            self.sample()

    def stop(self):
        self._stop.set()
        self.sample()


def load_headers(header_dir):
    """Exactly what fec_transfer_graph.main() loads: *.json minus *.review.json."""
    if not header_dir:
        return []
    return [json.loads(p.read_text(encoding='utf-8'))
            for p in sorted(Path(header_dir).glob('*.json'))
            if not p.name.endswith('.review.json')]


def open_ledger_readonly(path):
    uri = Path(path).resolve().as_uri() + '?mode=ro'
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def money(cents):
    return round((cents or 0) / 100.0, 2)


def measure(index, ledger_path):
    connection = open_ledger_readonly(ledger_path)
    out = {}
    try:
        out['status_rows'] = {r['status']: r['n'] for r in connection.execute(
            'SELECT status, COUNT(*) AS n FROM records GROUP BY status ORDER BY status')}
        # Cash rows as allocate() sees them: 24G/24K, non-memo.
        out['cash_rows_by_status'] = {
            r['status']: {'rows': r['n'], 'dollars': money(r['cents'])}
            for r in connection.execute(
                "SELECT status, COUNT(*) AS n, SUM(cents) AS cents FROM records "
                "WHERE type IN ('24G','24K') AND memo<>'X' GROUP BY status ORDER BY status")}
        out['unresolved_record_rows'] = out['status_rows'].get('unresolved_record', 0)
        out['unresolved_version_rows'] = out['status_rows'].get('unresolved_version', 0)
        out['superseded_or_duplicate_rows'] = (out['status_rows'].get('superseded', 0)
                                               + out['status_rows'].get('duplicate', 0))
        out['current_rows'] = out['status_rows'].get('current', 0)
        # Why each unresolved source is unresolved.
        reasons = defaultdict(dict)
        for status in ('unresolved_version', 'unresolved_record'):
            for row in connection.execute(
                    'SELECT source, COUNT(*) AS n FROM records WHERE status=? GROUP BY source', (status,)):
                reasons[row['source']][status] = row['n']
        # Every competing version's dollars, i.e. the gross contents of the
        # withheld groups (NOT what any single design would have counted).
        withheld = connection.execute(
            "SELECT COUNT(*) AS n, SUM(cents) AS cents FROM records "
            "WHERE status LIKE 'unresolved_%' AND type IN ('24G','24K') AND memo<>'X' AND cents>0").fetchone()
        out['withheld_ambiguous_cash_rows'] = withheld['n']
        out['withheld_ambiguous_cash_dollars_gross'] = money(withheld['cents'])
        # A version group that lives inside ONE filing can never be settled by a
        # filing header: the header describes the filing, not which of two rows
        # in it is current. Split the cost on exactly that line.
        out['unresolved_version_groups_by_span'] = {
            r['span']: {'groups': r['groups'], 'rows': r['rows'], 'cash_dollars': money(r['cents'])}
            for r in connection.execute(
                "SELECT span, COUNT(*) AS groups, SUM(n) AS rows, SUM(cents) AS cents FROM ("
                "  SELECT version_key,"
                "    CASE WHEN COUNT(DISTINCT file_num)>1 THEN 'multi_file' ELSE 'single_file' END AS span,"
                "    COUNT(*) AS n,"
                "    SUM(CASE WHEN type IN ('24G','24K') AND memo<>'X' AND cents>0 THEN cents ELSE 0 END) AS cents"
                "  FROM records WHERE status='unresolved_version' GROUP BY version_key"
                ") GROUP BY span")}
        # What the previous rule ("highest file number wins") would have counted
        # out of each withheld group: one winning row per version_key.
        winner = connection.execute(
            "SELECT COUNT(*) AS n, SUM(cents) AS cents FROM ("
            "  SELECT cents, ROW_NUMBER() OVER ("
            "    PARTITION BY version_key"
            "    ORDER BY file_num DESC,"
            "      CASE amendment WHEN 'T' THEN 2 WHEN 'A' THEN 1 ELSE 0 END DESC,"
            "      sub_id DESC) AS rank"
            "  FROM records WHERE status='unresolved_version'"
            ") WHERE rank=1 AND cents>0").fetchone()
        out['v2_style_winner_rows'] = winner['n']
        out['v2_style_winner_cash_dollars'] = money(winner['cents'])
        unresolved_record_cash = connection.execute(
            "SELECT COUNT(*) AS n, SUM(cents) AS cents FROM records WHERE status='unresolved_record' "
            "AND type IN ('24G','24K') AND memo<>'X' AND cents>0").fetchone()
        out['unresolved_record_cash_dollars'] = money(unresolved_record_cash['cents'])
        out['distinct_file_nums'] = connection.execute(
            'SELECT COUNT(DISTINCT file_num) FROM records').fetchone()[0]
        out['file_nums_needed_for_multi_file_groups'] = connection.execute(
            "SELECT COUNT(DISTINCT file_num) FROM records WHERE status='unresolved_version' "
            "AND version_key IN (SELECT version_key FROM records WHERE status='unresolved_version' "
            "GROUP BY version_key HAVING COUNT(DISTINCT file_num)>1)").fetchone()[0]
        out['ledger_tables'] = {r['name']: connection.execute(
            f"SELECT COUNT(*) FROM {r['name']}").fetchone()[0]
            for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        connection.close()

    unresolved = set(index.get('unresolved_sources') or [])
    edges = index['edges']
    positive = [e for e in edges if e['amount'] > 0]           # allocate() skips amount<=0
    total_positive = sum(e['amount'] for e in positive)
    blocked = [e for e in positive if e['source'] in unresolved]
    blocked_dollars = sum(e['amount'] for e in blocked)
    by_source = defaultdict(lambda: {'dollars': 0.0, 'edges': 0, 'records': 0})
    for edge in blocked:
        bucket = by_source[edge['source']]
        bucket['dollars'] += edge['amount']
        bucket['edges'] += 1
        bucket['records'] += edge['record_count']
    top = sorted(by_source.items(), key=lambda kv: -kv[1]['dollars'])[:25]

    out['edges'] = len(edges)
    out['edges_positive'] = len(positive)
    out['current_cash_edge_dollars'] = round(total_positive, 2)
    out['unresolved_source_committees'] = len(unresolved)
    out['unresolved_all_sources'] = bool(index.get('unresolved_all_sources'))
    out['edge_source_committees'] = len({e['source'] for e in positive})
    out['edge_source_committees_unresolved'] = len({e['source'] for e in positive} & unresolved)
    out['blocked_edge_dollars'] = round(blocked_dollars, 2)
    # Share of the cash edge dollars allocate() will refuse to allocate because
    # their SOURCE committee is wholly uncertain.
    out['blocked_edge_share'] = (round(blocked_dollars / total_positive, 6) if total_positive else None)
    # Common baseline: what a "highest file number wins" build would have had in
    # its edge table -- today's current edges plus one winner per withheld group.
    baseline = (total_positive + out['v2_style_winner_cash_dollars']
                + out['unresolved_record_cash_dollars'])
    out['v2_equivalent_edge_dollars'] = round(baseline, 2)
    committed_loss = (blocked_dollars + out['v2_style_winner_cash_dollars']
                      + out['unresolved_record_cash_dollars'])
    alternative_loss = out['v2_style_winner_cash_dollars'] + out['unresolved_record_cash_dollars']
    out['committed_rule_loss_dollars'] = round(committed_loss, 2)
    out['committed_rule_loss_share'] = round(committed_loss / baseline, 6) if baseline else None
    out['alternative_rule_loss_dollars'] = round(alternative_loss, 2)
    out['alternative_rule_loss_share'] = round(alternative_loss / baseline, 6) if baseline else None
    out['top_blocked_sources'] = [
        {'committee_id': source, 'outgoing_current_dollars': round(v['dollars'], 2),
         'edges': v['edges'], 'records': v['records'],
         'reason': reasons.get(source) or {'malformed_or_not_in_ledger': True}}
        for source, v in top]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cycle', type=int, required=True, choices=(2022, 2024, 2026))
    parser.add_argument('--itoth', type=Path, required=True,
                        help='HARD LINK inside the scratch root. Never the real source path.')
    parser.add_argument('--header-dir', type=Path, default=None)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--publish', action='store_true',
                        help='Also write transfer-edges.csv / -info / -current beside the hard link.')
    parser.add_argument('--allow-real-tree', action='store_true',
                        help='Override the refusal to write inside C:\\Users\\pgoff\\Mentat.')
    args = parser.parse_args()

    itoth = args.itoth.resolve()
    guarded = Path(r'C:\Users\pgoff\Mentat')
    if not args.allow_real_tree and guarded in itoth.parents:
        parser.error(f'{itoth} is inside {guarded}; transfer_index writes beside it. Use a hard link in scratch.')

    sys.path.insert(0, str(TOOLS))
    import fec_transfer_graph as graph          # the COMMITTED module, imported in place
    if graph.VERSION != 3:
        parser.error(f'Expected committed VERSION 3, found {graph.VERSION}')

    headers = load_headers(args.header_dir)
    source_stat = itoth.stat()
    watcher = DiskWatcher(itoth.parent)
    before = {p.name: p.stat().st_size for p in itoth.parent.iterdir() if p.is_file()}
    cached_already = bool(list(itoth.parent.glob('transfer-index-v3-*.sqlite')))
    watcher.start()
    started = time.monotonic()
    try:
        index = graph.transfer_index(itoth, args.cycle, headers)
    finally:
        watcher.stop()
    wall_seconds = round(time.monotonic() - started, 3)
    if args.publish:
        graph.publish_index(itoth.parent, index)

    ledger = Path(index['ledger_path'])
    result = {
        'measured_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'module': {'path': str((TOOLS / 'fec_transfer_graph.py').resolve()),
                   'version': graph.VERSION,
                   'mtime': time.strftime('%Y-%m-%dT%H:%M:%S',
                                          time.localtime((TOOLS / 'fec_transfer_graph.py').stat().st_mtime))},
        'cycle': args.cycle,
        'itoth': str(itoth),
        'itoth_bytes': source_stat.st_size,
        'itoth_mtime': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(source_stat.st_mtime)),
        'source_sha256': index['source_sha256'],
        'header_dir': str(args.header_dir) if args.header_dir else None,
        'headers_loaded': len(headers),
        'header_file_nums': sorted({h['header']['file_num'] for h in headers}) if headers else [],
        'filing_headers_sha256': index['filing_headers_sha256'],
        'counts': index['counts'],
        'built_seconds': index['built_seconds'],
        'wall_seconds': wall_seconds,
        'cache_hit': cached_already and wall_seconds < index['built_seconds'],
        'ledger_path': str(ledger),
        'ledger_bytes': ledger.stat().st_size,
        'cache_json_bytes': ledger.with_suffix('.json').stat().st_size,
        'peak_scratch_bytes_beside_link': watcher.peak,
        'peak_scratch_detail': watcher.peak_detail,
        'peak_working_set_bytes': peak_working_set_bytes(),
        'files_before': before,
    }
    result.update(measure(index, ledger))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')

    after = itoth.stat()
    if (after.st_size, after.st_mtime_ns) != (source_stat.st_size, source_stat.st_mtime_ns):
        raise SystemExit('SOURCE FILE CHANGED during measurement -- investigate before trusting anything')
    summary = {k: result[k] for k in (
        'cycle', 'headers_loaded', 'built_seconds', 'wall_seconds', 'ledger_bytes',
        'peak_scratch_bytes_beside_link', 'current_rows', 'unresolved_version_rows',
        'unresolved_record_rows', 'superseded_or_duplicate_rows',
        'unresolved_source_committees', 'unresolved_all_sources', 'edges_positive',
        'current_cash_edge_dollars', 'blocked_edge_dollars', 'blocked_edge_share',
        'unresolved_version_groups_by_span', 'withheld_ambiguous_cash_dollars_gross',
        'v2_style_winner_cash_dollars', 'v2_equivalent_edge_dollars',
        'committed_rule_loss_dollars', 'committed_rule_loss_share',
        'alternative_rule_loss_dollars', 'alternative_rule_loss_share',
        'distinct_file_nums', 'file_nums_needed_for_multi_file_groups')}
    print(json.dumps(summary, indent=2), flush=True)
    print(f'full result -> {args.out}', flush=True)


if __name__ == '__main__':
    main()
