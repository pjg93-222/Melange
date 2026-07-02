# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
"""CANONICAL PIPELINE RUNNER.
One command regenerates everything in the right order — no more hand-typed chains that forget a pass.

PHASE-2 (system-of-record inversion, user sign-off 2026-07-02): Python owns ALL derived math.
compute_pillars --write produces ranks_python.json (THE rank authority the engines read); the
workbook is a self-refreshing VIEW — its formulas recalculate whenever the user opens it
(fullCalcOnLoad is set by every writer). There is NO Excel COM step anywhere: the recalc/kill-Excel/
OneDrive-truncation failure class is retired. Historical incidents that shaped this: a PermissionError
lock race and a 2.2MB truncated save, both from COM+OneDrive contention (2026-07-02).
Usage:
  python run_pipeline.py                    # full chain + audit
  python run_pipeline.py --from optimize    # resume mid-chain
  (--recalc is accepted but retired: prints a note and continues)"""
import subprocess,sys,os,argparse,time
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FE=os.path.dirname(os.path.abspath(__file__))
CHAIN=[('receptivity_layer.py',[]),            # personality/incentive receptivity (big5_traits.py = manual, corpus-driven)
       ('per_category_stance.py',[]),          # stance matrix (press normalization computed in Python from raw)
       ('compute_pillars.py',['--write']),     # THE RANK AUTHORITY (before sync: reads O/E/F while the view cache is alive; falls back to its snapshot otherwise)
       ('sync_stance_g.py',[]),                # col-G tier sync (openpyxl values write; kills formula caches — view self-heals on open)
       ('per_topic_flip.py',[]),
       ('per_topic_coalition.py',[]),
       ('budget_frontier.py',[]),
       ('budget_frontier.py',['--electoral']), # the pass that got forgotten once — never again
       ('optimize.py',[]),
       ('build_im_allocation.py',[]),
       ('salience_shock.py',['--advise']),    # advisory must be fresh BEFORE the bundle exports engine.adv
       ('build_dashboard_bundle.py',[]),
       ('make_dashboard_html.py',[]),
       ('make_member_desk.py',[]),
       ('make_combined.py',[]),
       ('audit_full.py',[])]
ap=argparse.ArgumentParser(); ap.add_argument('--recalc',action='store_true'); ap.add_argument('--from',dest='frm',default=None)
a=ap.parse_args()
if a.recalc: print('note: --recalc is RETIRED (phase 2) — Python owns the math (compute_pillars --write); the workbook view self-heals on open via fullCalcOnLoad.')
started=a.frm is None
t0=time.time()
for script,args in CHAIN:
    if not started:
        if script.startswith(a.frm): started=True
        else: continue
    t=time.time()
    r=subprocess.run([sys.executable,os.path.join(FE,script)]+ (args or []),capture_output=True,text=True,encoding='utf-8',errors='replace')
    tail=(r.stdout or '').strip().splitlines()[-1:] or ['']
    print('  %-28s %s %5.1fs  %s'%(script+' '+' '.join(args or []),'OK' if r.returncode==0 else '!!',time.time()-t,tail[0][:90]))
    if r.returncode!=0:
        print((r.stdout or '')[-800:]); print((r.stderr or '')[-800:]); sys.exit(1)
print('PIPELINE COMPLETE in %.1f min'%((time.time()-t0)/60))
