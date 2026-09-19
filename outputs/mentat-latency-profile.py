"""Read-only local latency measurements; no collection or report writes."""
import argparse
import cProfile
import io
import json
from pathlib import Path
import pstats
import statistics
import sys
import time
from urllib.request import urlopen

PROJECT=Path(__file__).resolve().parents[1]/'mentat'
sys.path[:0]=[str(PROJECT/'app'),str(PROJECT/'tools')]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8805)
    parser.add_argument('--profile',action='store_true')
    args=parser.parse_args()
    timings=[]
    endpoints=['/api/health','/api/session','/api/runs','/api/report-sources',
               '/api/graph-catalog?id=published-reports','/api/cross-reference']
    for endpoint in endpoints:
        elapsed=[];size=0
        for sample in range(3):
            start=time.perf_counter()
            with urlopen(f'http://127.0.0.1:{args.port}{endpoint}',timeout=60) as response:
                body=response.read();status=response.status
            elapsed.append(round((time.perf_counter()-start)*1000,3));size=len(body)
        row=dict(endpoint=endpoint,milliseconds=elapsed,median_ms=statistics.median(elapsed),bytes=size,status=status)
        timings.append(row);print(json.dumps(row),flush=True)
    result={'http':timings}
    if args.profile:
        import server
        app=server.Console(Path.home()/'AppData/Local/Mentat/console',read_only=True)
        profiler=cProfile.Profile();profiler.enable()
        summary=app.summary()
        profiler.disable()
        stream=io.StringIO();pstats.Stats(profiler,stream=stream).sort_stats('cumulative').print_stats(28)
        result['summary_profile']=stream.getvalue()
        result['runs']=len(summary['runs']);result['coverage_rows']=len(summary['coverage'])
        print(stream.getvalue(),flush=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')

if __name__=='__main__':main()
