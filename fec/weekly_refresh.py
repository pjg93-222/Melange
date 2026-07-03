# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root
"""WEEKLY REFRESH (user 2026-07-02: "if the UI could be updated every week that would be great").
Unattended data-refresh + full pipeline + dashboard regeneration, designed for Windows Task
Scheduler (registered as 'MoneyballWeeklyRefresh', Sundays 06:00; remove with
`schtasks /Delete /TN MoneyballWeeklyRefresh /F`). Also fine to run by hand anytime.

Steps (each logged to weekly_refresh.log; collectors are tolerant — a failed fetch never blocks
the UI regeneration; only a pipeline failure is a hard error):
  1. CREC floor speeches, incremental (last 14 days; resumable, non-session days cached)
  2. CHRG finance hearings, incremental (last 60 days; publication lags)
  3. big5_traits          — traits on the grown speech corpus
  4. social_interaction_layer + build_multilayer_network — refresh the social edge layer
  5. build_media_blend    — re-blend press+social into the workbook raw layer (skipped gracefully
                            if Excel has the workbook open/locked)
  6. run_pipeline         — the whole chain: stance, rank authority, engines, ALL dashboards, audit
X/Truth/Bluesky collectors are NOT run unattended (keys/discovery are interactive); run
tweet_collector.py + process_quorum.py manually when new exports/keys exist, then this script."""
import sys,os,subprocess,datetime,json,time
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FE=os.path.dirname(os.path.abspath(__file__))
LOG=os.path.join(MB_ROOT,'weekly_refresh.log')
def log(msg):
    line='[%s] %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),msg)
    print(line)
    with open(LOG,'a',encoding='utf-8') as f: f.write(line+'\n')
def step(name,args,timeout=3600,hard=False):
    t=time.time()
    try:
        r=subprocess.run([sys.executable,os.path.join(FE,args[0])]+args[1:],capture_output=True,
                         text=True,encoding='utf-8',errors='replace',timeout=timeout,cwd=FE)
        tail=(r.stdout or '').strip().splitlines()[-1:] or ['']
        ok=r.returncode==0
        log('%-28s %s %5.0fs  %s'%(name,'OK' if ok else '!!',time.time()-t,tail[0][:110]))
        if not ok:
            log('   stderr: '+(r.stderr or '')[-300:].replace('\n',' | '))
            if hard: log('HARD FAILURE — aborting refresh'); sys.exit(1)
        return ok
    except subprocess.TimeoutExpired:
        log('%-28s TIMEOUT after %ds%s'%(name,timeout,' — aborting' if hard else ' — continuing'))
        if hard: sys.exit(1)
        return False
    except Exception as e:
        log('%-28s ERROR %s'%(name,str(e)[:120]))
        if hard: sys.exit(1)
        return False
log('===== WEEKLY REFRESH START =====')
today=datetime.date.today()
prev=None
try: prev=json.load(open(os.path.join(MB_ROOT,'ranks_python.json')))['rank']
except Exception: pass
step('CREC floor speeches',['fetch_congressional_record.py','crec','--since',str(today-datetime.timedelta(days=14))],timeout=3000)
step('CHRG finance hearings',['fetch_congressional_record.py','chrg','--since',str(today-datetime.timedelta(days=60))],timeout=3000)
step('Big Five traits',['big5_traits.py'],timeout=1800)
step('social interaction layer',['social_interaction_layer.py'],timeout=900)
step('multilayer network',['build_multilayer_network.py'],timeout=900)
step('media blend',['build_media_blend.py'],timeout=1200)   # tolerant: Excel lock -> stale press this week, still consistent
step('FULL PIPELINE + dashboards',['run_pipeline.py'],timeout=3000,hard=True)
try:
    new=json.load(open(os.path.join(MB_ROOT,'ranks_python.json')))['rank']
    if prev:
        moved=sum(1 for m in new if prev.get(m)!=new[m])
        log('rank movement this week: %d/%d members'%(moved,len(new)))
except Exception as e: log('rank compare skipped: %s'%e)
log('===== WEEKLY REFRESH COMPLETE — dashboards regenerated =====')
