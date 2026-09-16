"""Measure evidence_csv.parse() cost. Imports the module unmodified; never writes to the repo.

Usage: measure.py <csv-path> <mode> <instrument>
  mode:       asis | bytes | bytes+rows
              'bytes'      monkeypatches evidence_csv.MAX_BYTES at RUNTIME in this
                           process only (module attribute assignment, no file edit)
              'bytes+rows' also raises MAX_ROWS
  instrument: tracemalloc | psutil

One case per process so nothing carries over. tracemalloc and psutil are run in
SEPARATE processes because tracemalloc's own bookkeeping inflates RSS and wall time.
"""
import sys, time, gc, json
from pathlib import Path

APP = Path(r"C:\Users\pgoff\Mentat\mentat\app")
TOOLS = Path(r"C:\Users\pgoff\Mentat\mentat\tools")
sys.path.insert(0, str(APP))
sys.path.insert(0, str(TOOLS))

import evidence_csv  # noqa: E402  -- imported, never modified on disk

csv_path, mode, instrument = Path(sys.argv[1]), sys.argv[2], sys.argv[3]

ORIGINAL = (evidence_csv.MAX_BYTES, evidence_csv.MAX_ROWS)
if mode in ('bytes', 'bytes+rows'):
    evidence_csv.MAX_BYTES = 10 ** 9           # runtime-only, this process only
if mode == 'bytes+rows':
    evidence_csv.MAX_ROWS = 10 ** 9            # runtime-only, this process only

text = csv_path.read_text(encoding='utf-8')    # the server already holds this string
name = csv_path.name
gc.collect()

result = {'file': name, 'bytes': len(text.encode('utf-8')), 'mode': mode,
          'instrument': instrument, 'limits_in_effect': [evidence_csv.MAX_BYTES, evidence_csv.MAX_ROWS],
          'limits_on_disk': list(ORIGINAL)}

proc = None
if instrument == 'psutil':
    import psutil
    proc = psutil.Process()
    result['rss_before'] = proc.memory_info().rss
else:
    import tracemalloc
    tracemalloc.start()

start = time.perf_counter()
try:
    document = evidence_csv.parse(name, text)
    elapsed = time.perf_counter() - start
    result['outcome'] = 'parsed OK'
    result['rows'] = len(document['rows'])
    result['columns'] = len(document['columns'])
    result['supported'] = sum(r['status'] == 'supported' for r in document['rows'])
except Exception as error:                      # noqa: BLE001 - we want the exact type
    elapsed = time.perf_counter() - start
    document = None
    result['outcome'] = f'raised {type(error).__name__}'
    result['message'] = str(error)

result['seconds'] = round(elapsed, 4)

if instrument == 'psutil':
    result['rss_after_holding_document'] = proc.memory_info().rss
    result['rss_delta_holding_document'] = result['rss_after_holding_document'] - result['rss_before']
    # Does releasing the parsed document give the memory back? The server does NOT
    # release it: import_evidence_csv keeps the document in self.csv_imports.
    document = None
    gc.collect()
    result['rss_after_release'] = proc.memory_info().rss
else:
    import tracemalloc
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result['tracemalloc_current'] = current
    result['tracemalloc_peak'] = peak

print(json.dumps(result))
