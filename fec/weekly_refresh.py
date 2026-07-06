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
try:   # user directive 2026-07-06: hold a system wake lock for the refresh's lifetime (the 01:10
    import ctypes   # machine sleep stalled collectors 5h; a mid-refresh sleep would do the same)
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    log('keep-awake: system wake lock held for this refresh')
except Exception as _e:
    log('keep-awake unavailable: %s' % str(_e)[:60])
log('===== WEEKLY REFRESH START =====')
today=datetime.date.today()
prev=None
try: prev=json.load(open(os.path.join(MB_ROOT,'ranks_python.json')))['rank']
except Exception: pass
step('CREC floor speeches',['fetch_congressional_record.py','crec','--since',str(today-datetime.timedelta(days=14))],timeout=3000)
step('CHRG finance hearings',['fetch_congressional_record.py','chrg','--since',str(today-datetime.timedelta(days=400))],timeout=3000)   # coverage audit 2026-07-06: hearing transcripts publish MONTHS late — a 60-day window structurally missed most of them forever ('ok' markers keep the wide window cheap)
step('Big Five traits',['big5_traits.py'],timeout=1800)
step('interaction features',['interaction_features.py'],timeout=900)      # conversational dynamics (feeds dominance disposition)
step('behavior panel',['behavior_panel.py'],timeout=900)                  # nomological fix 2026-07-04: dispositions measured from behavior
step('behavioral dispositions',['behavioral_dispositions.py'],timeout=900)  # must precede receptivity (run_pipeline chain)
step('Big5 v2 (behavior-calibrated)',['big5_lexcal_v2.py'],timeout=900)     # text instrument, honest held-out; desk radar source
step('Big5 v3 (hybrid)',['big5_hybrid.py'],timeout=900)                     # lexical+interaction+persona; wins expected post-nickfix corpus
step('social interaction layer',['social_interaction_layer.py'],timeout=900)
step('multilayer network',['build_multilayer_network.py'],timeout=900)
step('co-appearance layer',['co_appearance_layer.py'],timeout=600)                 # joint interview-episode pairings (user 2026-07-05)
step('reference layer (rebuild)',['member_reference_layer.py','--rebuild'],timeout=900)  # FREE cache-only re-aggregation; paid --score passes stay manual
step('press stance stack',['press_stance_stack.py'],timeout=1800)   # re-score the (grown) corpus so the sidecar never goes stale (frozen-archive lesson); new articles missing Fable cache fields degrade gracefully to reader+DEBATE features
step('media blend',['build_media_blend.py'],timeout=1200)   # tolerant: Excel lock -> stale press this week, still consistent
ok=step('FULL PIPELINE + dashboards',['run_pipeline.py'],timeout=3000)
if not ok:
    # S3-06 resolution (user-ratified 2026-07-03, "whatever is most optimal"): a locked workbook at the
    # col-G sync used to hard-abort ALL dashboard regeneration for the week. Fall back to rebuilding the
    # engines + dashboards from the last CONSISTENT artifact state — '--from per_topic_flip' skips the
    # workbook-writing steps entirely; the col-G view stays stale until the next unlocked run, which is
    # the standard view-self-heal contract. If even the fallback fails, THAT is a hard abort.
    log('pipeline failed — dashboard fallback from last consistent state (--from per_topic_flip)')
    step('DASHBOARD FALLBACK',['run_pipeline.py','--from','per_topic_flip'],timeout=3000,hard=True)
try:
    new=json.load(open(os.path.join(MB_ROOT,'ranks_python.json')))['rank']
    if prev:
        moved=sum(1 for m in new if prev.get(m)!=new[m])
        log('rank movement this week: %d/%d members'%(moved,len(new)))
except Exception as e: log('rank compare skipped: %s'%e)
# post-chain DIAGNOSTIC layers (run-4k/4l lit-audit augmentations): signed-coalition splinter,
# Battaglini-Patacchini KB benchmark, Volden-Wiseman LEP criterion. Tolerant — the chain consumes
# none of them and a diagnostic failure never blocks the refresh; they feed the desk External row.
step('signed coalitions (diag)',['signed_coalitions.py'],timeout=900)
step('KB benchmark (diag)',['kb_benchmark.py'],timeout=900)
step('LEP criterion (diag)',['lep_criterion.py'],timeout=900)
log('===== WEEKLY REFRESH COMPLETE — dashboards regenerated =====')
