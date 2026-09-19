"""Interleaved, read-only before/after measurements on the same saved data."""
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'mentat'
sys.path[:0] = [str(PROJECT / 'app'), str(PROJECT / 'tools')]
import server
import collection_coverage
from runtime_inputs import source_ignore


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'outputs/mentat-latency-baseline' / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


old_coverage = module('old_coverage', 'collection_coverage.py')
old_keys = module('old_keys', 'fec_key_store.py')
old_server = module('old_server', 'server.py')
old_server.PROJECT = PROJECT
old_server.inspect_coverage = old_coverage.inspect
old_server.load_keys = old_keys.load_keys
old_server.key_status = old_keys.status
root = Path.home() / 'AppData/Local/Mentat/console'
variants = {'before': (old_server.Console(root, read_only=True), old_coverage),
            'after': (server.Console(root, read_only=True), collection_coverage)}
measurements = {name: {'summary_cold': [], 'summary_warm': [], 'graph_catalog': []} for name in variants}
reference = {}
for sample in range(5):
    for name in (('before', 'after') if sample % 2 == 0 else ('after', 'before')):
        app, coverage = variants[name]
        coverage._inspect.cache_clear()
        coverage._inspection_failures.clear()
        coverage.file_digest.cache_clear()
        for label, action in [('summary_cold', app.summary), ('summary_warm', app.summary),
                              ('graph_catalog', lambda: app.graph_catalog('published-reports'))]:
            start = time.perf_counter(); cpu = time.process_time()
            value = action()
            elapsed = {'wall_ms': round((time.perf_counter() - start) * 1000, 3),
                       'cpu_ms': round((time.process_time() - cpu) * 1000, 3)}
            measurements[name][label].append(elapsed)
            reference.setdefault(label, value)
            if value != reference[label]:
                raise AssertionError(f'{name} {label}: before/after output changed')
    print(f'Completed paired sample {sample + 1}; outputs identical.', flush=True)

source = Path(json.loads((PROJECT / 'inputs/active_fec_sources.json').read_text())['path'])
sizes = {}
for cycles in ([2022, 2024, 2026], [2026]):
    total = 0
    for folder in ('fec_beneficiary', 'fec_committee_master'):
        parent = source / folder
        ignore = source_ignore(parent, cycles)
        pending = [parent]
        while pending:
            directory = pending.pop()
            children = list(directory.iterdir())
            excluded = ignore(directory, [p.name for p in children])
            for path in children:
                if path.name in excluded:
                    continue
                if path.is_dir(): pending.append(path)
                else: total += path.stat().st_size
    sizes[','.join(map(str, cycles))] = total
result = {'samples': measurements, 'source_snapshot_bytes': sizes, 'outputs_identical': True,
          'medians': {name: {label: {clock: statistics.median(row[clock] for row in rows)
                                   for clock in ('wall_ms', 'cpu_ms')}
                            for label, rows in timings.items()} for name, timings in measurements.items()}}
(ROOT / 'outputs/mentat-latency-comparison.json').write_text(json.dumps(result, indent=2))
print(json.dumps({key: value for key, value in result.items() if key != 'samples'}, indent=2), flush=True)
