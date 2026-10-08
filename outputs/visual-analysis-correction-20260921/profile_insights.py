import cProfile
import pstats
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'mentat/app'))
import analysis_data as a
directory = 'C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files'
source = a.data._source(directory, {'dataset':'Banking'})
path, pending = a.data._ready(source)
assert not pending, pending
request = a.validate({'dataset':'Banking','as_of':'2026-09-21'})
def run():
    for result, options, scope, provenance in a._prepare(path, source, request):
        print('panels',list(result['panels']),'records',result['metadata']['input_records'],flush=True)
t=time.perf_counter()
profile=cProfile.Profile()
profile.runcall(run)
print('seconds',round(time.perf_counter()-t,3),flush=True)
pstats.Stats(profile).strip_dirs().sort_stats('cumtime').print_stats(25)
