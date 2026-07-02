# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
"""CANONICAL PIPELINE RUNNER (deep-audit fix 2026-07-02: the stale-electoral-frontier failure class).
One command regenerates everything in the right order — no more hand-typed chains that forget a pass.
Steps marked [wb] read the workbook: if you have just WRITTEN to the workbook (media blend, tier sync),
run the Excel COM recalc first (see --recalc).
Usage:
  python run_pipeline.py            # full chain + audit
  python run_pipeline.py --recalc   # Excel COM recalc FIRST (needed after any workbook write), then chain
  python run_pipeline.py --from optimize   # resume mid-chain"""
import subprocess,sys,os,argparse,time
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FE=os.path.dirname(os.path.abspath(__file__))
CHAIN=[('receptivity_layer.py',[]),            # personality/incentive receptivity (big5_traits.py = manual, corpus-driven)
       ('per_category_stance.py',[]),          # [wb] stance matrix from the (media-blended) workbook
       ('sync_stance_g.py',[]),                # [wb-write] tier sync back into the workbook
       ('RECALC',None),                        # workbook recalc AFTER sync (tiers feed rank formulas)
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
WBP=MB_ROOT+r'\Moneyball Main Version - Blended.xlsx'
def _wb_ready():
    """Workbook readable AND a structurally valid xlsx with stable size (2026-07-02 incidents:
    a PermissionError lock race, then a TRUNCATED save — Excel/OneDrive contention left a 2.2MB
    partial file while the recalc still printed ok)."""
    import zipfile
    try:
        s1=os.path.getsize(WBP)
        if not zipfile.is_zipfile(WBP): return False
        time.sleep(2)
        return os.path.getsize(WBP)==s1 and zipfile.is_zipfile(WBP)
    except OSError: return False
def recalc():
    ps=('Get-Process EXCEL -ErrorAction SilentlyContinue | Stop-Process -Force -Confirm:$false; Start-Sleep -Seconds 2; '
        '$xl = New-Object -ComObject Excel.Application; $xl.Visible=$false; $xl.DisplayAlerts=$false; '
        '$wb = $xl.Workbooks.Open("'+WBP+'"); '
        '$xl.CalculateFullRebuild(); $wb.Save(); $wb.Close($true); $xl.Quit(); Write-Output "recalc ok"')
    for attempt in (1,2):
        r=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True)
        print('  [RECALC attempt %d]'%attempt,(r.stdout or r.stderr).strip()[:120])
        if 'recalc ok' in (r.stdout or ''):
            for _ in range(15):
                if _wb_ready(): return
                time.sleep(2)
        print('  !! workbook not valid/stable after recalc attempt %d'%attempt)
    print('  !! recalc failed twice — restore the newest backups\\*.BACKUP-*.xlsx and rerun'); sys.exit(2)
ap=argparse.ArgumentParser(); ap.add_argument('--recalc',action='store_true'); ap.add_argument('--from',dest='frm',default=None)
a=ap.parse_args()
if a.recalc: recalc()
started=a.frm is None
t0=time.time()
for script,args in CHAIN:
    if not started:
        if script.startswith(a.frm): started=True
        else: continue
    if script=='RECALC': recalc(); continue
    t=time.time()
    r=subprocess.run([sys.executable,os.path.join(FE,script)]+ (args or []),capture_output=True,text=True,encoding='utf-8',errors='replace')
    tail=(r.stdout or '').strip().splitlines()[-1:] or ['']
    print('  %-28s %s %5.1fs  %s'%(script+' '+' '.join(args or []),'OK' if r.returncode==0 else '!!',time.time()-t,tail[0][:90]))
    if r.returncode!=0:
        print((r.stdout or '')[-800:]); print((r.stderr or '')[-800:]); sys.exit(1)
print('PIPELINE COMPLETE in %.1f min'%((time.time()-t0)/60))
