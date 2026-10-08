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
    t=time.time(); proc=None
    try:
        flags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0
        proc=subprocess.Popen([sys.executable,os.path.join(FE,args[0])]+args[1:],stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',cwd=FE,
                              creationflags=flags,start_new_session=os.name!='nt')
        stdout,stderr=proc.communicate(timeout=timeout)
        tail=(stdout or '').strip().splitlines()[-1:] or ['']
        ok=proc.returncode==0
        log('%-28s %s %5.0fs  %s'%(name,'OK' if ok else '!!',time.time()-t,tail[0][:110]))
        if not ok:
            log('   stderr: '+(stderr or '')[-300:].replace('\n',' | '))
            if hard: log('HARD FAILURE — aborting refresh'); sys.exit(1)
        return ok
    except subprocess.TimeoutExpired:
        if proc is not None:
            if os.name=='nt':
                subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else:
                try: os.killpg(proc.pid,9)
                except ProcessLookupError: pass
            proc.wait()
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
# interview accrual (N-gate audit 2026-07-10): the refresh re-DERIVED interaction features every
# week but nothing GREW the interview corpus — reactivity coverage (round-4 gate: MEM_N>=250,
# now 203) was frozen forever. Incremental resumes, all cheap (per-URL 'ok' cache); fox excluded
# (transcripts ended ~2022, archive fully walked); soft-fail keeps the refresh alive.
step('interviews: CNN (14d)',['fetch_interviews.py','cnn','--since',str(today-datetime.timedelta(days=14))],timeout=1800)
step('interviews: MTP',['fetch_interviews.py','mtp'],timeout=1200)
step('interviews: CBS',['fetch_interviews.py','cbs'],timeout=1200)
step('interviews: ABC',['fetch_interviews.py','abc'],timeout=1200)
step('interviews: PBS (21d)',['fetch_interviews.py','pbs','--since',str(today-datetime.timedelta(days=21))],timeout=1800)
step('interviews: NPR (14d)',['fetch_interviews.py','npr','--since',str(today-datetime.timedelta(days=14))],timeout=1800)
step('interviews: MS NOW',['fetch_interviews.py','msnow'],timeout=1800)   # WP REST resume; per-post keys make re-runs cheap (archive may be dead post-2024 -> no-op)
step('Big Five traits',['big5_traits.py'],timeout=1800)
step('interaction features',['interaction_features.py'],timeout=900)      # conversational dynamics (feeds dominance disposition)
step('behavior panel',['behavior_panel.py'],timeout=900)                  # nomological fix 2026-07-04: dispositions measured from behavior
step('behavioral dispositions',['behavioral_dispositions.py'],timeout=900)  # must precede receptivity (run_pipeline chain)
step('Big5 v2 (behavior-calibrated)',['big5_lexcal_v2.py'],timeout=900)     # text instrument, honest held-out; desk radar source
step('Big5 v3 (hybrid)',['big5_hybrid.py'],timeout=900)                     # lexical+interaction+persona; wins expected post-nickfix corpus
step('social interaction layer',['social_interaction_layer.py'],timeout=900)
# C-2 (audit 2026-07-08): refresh the press-derived engagement + HCoI edge layers BEFORE build_multilayer
# folds them into the weekly AUG network. Previously neither producer was in the weekly chain, so a frozen
# (days-stale) press_engagement.json / press_hcoi.json got re-baked into every otherwise-fresh AUG, silently
# mixing provenance. Both read the external R tone CSV (Draft Systems\cu_press_stance_tone.csv), so they are
# order-independent of the other Python steps; step() is tolerant, so a missing/locked CSV just leaves the
# prior layer in place (same graceful degradation as before, now refreshed when the CSV is present).
step('press engagement layer',['press_engagement_layer.py'],timeout=600)
step('press HCoI layer',['press_hcoi.py'],timeout=600)
step('multilayer network',['build_multilayer_network.py'],timeout=900)
step('co-appearance layer',['co_appearance_layer.py'],timeout=600)                 # joint interview-episode pairings (user 2026-07-05)
step('reference layer (rebuild)',['member_reference_layer.py','--rebuild'],timeout=900)  # FREE cache-only re-aggregation; paid --score passes stay manual
step('press stance stack',['press_stance_stack.py'],timeout=1800)   # re-score the (grown) corpus so the sidecar never goes stale (frozen-archive lesson); new articles missing Fable cache fields degrade gracefully to reader+DEBATE features
step('FULL PIPELINE + dashboards',['run_pipeline.py'],timeout=3000,hard=True)
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
step('say-do gap (diag)',['say_do_gap.py'],timeout=900)   # 2026-07-07: feeds delivery_mult (engine talker discount); runs AFTER desks so it reads the fresh bundle
# Audio/narrative safety deployment (2026-07-13): run_pipeline now rebuilds the guarded audio
# descriptor and construct-honest profile basis before the desk. The old unattended fetch ->
# single-model verification -> voiceprint -> paid narrative chain is retired. Audio remains absent
# until two distinct target-speaker reviews satisfy b5_audio_reviews_v2.json. Narrative regeneration
# is manual through b5_narratives_local.py after explicit user approval; it costs $0.
log('===== WEEKLY REFRESH COMPLETE — dashboards regenerated =====')
