# -*- coding: utf-8 -*-
import os as _o,sys as _s
_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)))
from paths import ROOT as MB_ROOT

"""Canonical fail-closed Moneyball pipeline runner.

Python owns all derived math. ``compute_pillars.py --write`` produces ``ranks_python.json`` as the
rank authority; the workbook is a recalculating audit/view artifact.  A single exclusive lock covers
the entire writer chain so two runs cannot publish a mixed-vintage artifact set.
"""
import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
import subprocess
import sys
import time
import uuid

sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FE=os.path.dirname(os.path.abspath(__file__))

CHAIN=[
    # FIRST, deliberately: halt before ANY artifact is written if this run would change a published
    # calibration (2026-07-19 incident — a run from a branch missing a ratified ladder silently
    # reverted Ally 3.00 -> 2.50 with no error and no audit failure). Intended changes pass with
    # CALIB_ACK=1; the guard prints the exact command. It is a chain STEP rather than an audit_full
    # ck() because a ck() failure exits 1 and aborts the whole chain — a warning must not do that.
    ('calibration_guard.py',[]),
    ('coop_v2_candidate.py',[]),
    ('build_electoral.py',[]),
    ('build_district_industry.py',[]),
    ('receptivity_layer.py',[]),
    ('build_archive_legislative.py',[]),
    ('extract_cu_speeches.py',[]),
    ('speech_stance_stack.py',[]),
    ('hearing_stance_stack.py',[]),
    ('interview_stance_stack.py',[]),
    ('bluesky_stance_stack.py',[]),
    ('tweet_stance_stack.py',['--score']),
    ('build_media_blend.py',[]),
    ('per_category_stance.py',[]),
    ('compute_pillars.py',['--write']),
    ('sync_stance_g.py',[]),
    ('build_electoral_plays.py',[]),
    ('per_topic_flip.py',[]),
    ('per_topic_coalition.py',[]),
    ('lt_priming.py',[]),
    ('budget_frontier.py',[]),
    ('budget_frontier.py',['--electoral']),
    ('optimize.py',[]),
    ('build_im_allocation.py',[]),
    ('salience_shock.py',['--advise']),
    ('build_dashboard_bundle.py',[]),
    ('make_dashboard_html.py',[]),
    ('personal_texture_layer.py',['--refresh-local']),
    ('communication_style.py',[]),
    ('validate_communication_style.py',[]),
    ('b5_external_gold_validate.py',[]),
    ('b5_gold_multitrait_validate.py',[]),
    ('b5_profile_basis.py',[]),
    ('validate_guarded_profile_artifacts.py',[]),
    ('make_member_desk.py',[]),
    ('make_combined.py',[]),
    ('audit_full.py',[]),
]

# Steps whose input artifact may be absent in a fresh / data-isolated worktree.  When the input is
# missing we SKIP the step cleanly (no-op) instead of aborting the whole chain.  Both entries feed the
# CU floor-speech channel (Paul-approved 2026-07-15), which is gated OFF downstream (CU_SPEECH_CHANNEL),
# so skipping them can never move ranks.
_DEMO_DATA_ROOT=os.environ.get('DEMO_DATA_ROOT')
if not _DEMO_DATA_ROOT:
    _DEMO_DATA_ROOT=os.path.join(
        os.environ.get('LOCALAPPDATA') or os.path.expanduser(r'~\AppData\Local'),
        'Melange','demographics')
OPTIONAL_INPUTS={
    'extract_cu_speeches.py':'social_media.db',   # sqlite source of the CREC floor speeches
    'speech_stance_stack.py':'speeches_cu.csv',   # produced by extract_cu_speeches.py
    'build_district_industry.py':(
        'district_geography.json',
        os.path.join(_DEMO_DATA_ROOT,'lodes','lodes_cd_panel.csv.gz'),
    ),
}

CANONICAL_DEPENDENCIES={
    'networkx':'networkx',
    'numpy':'numpy',
    'openpyxl':'openpyxl',
    'pandas':'pandas',
    'scikit-learn':'sklearn',
    'scipy':'scipy',
}


def preflight_dependencies():
    """Fail before any producer runs when the canonical environment is incomplete."""
    missing=[package for package,module in CANONICAL_DEPENDENCIES.items()
             if importlib.util.find_spec(module) is None]
    if missing:
        raise RuntimeError(
            'missing canonical Python dependencies: %s; run: "%s" -m pip install -r requirements.txt'
            % (', '.join(missing),sys.executable)
        )


def _pid_alive(pid):
    try:
        os.kill(int(pid),0)
        return True
    except (OSError,ValueError,TypeError):
        return False


@contextmanager
def pipeline_run_lock(path=os.path.join(MB_ROOT,'.pipeline_run.lock')):
    """Acquire an exclusive, stale-process-recoverable writer lock."""
    token=uuid.uuid4().hex
    for attempt in range(2):
        try:
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
            try:
                payload={'pid':os.getpid(),'token':token,'started_utc':time.time()}
                os.write(fd,json.dumps(payload,separators=(',',':')).encode('ascii'))
            finally:
                os.close(fd)
            break
        except FileExistsError:
            try:
                with open(path,encoding='utf-8') as handle:
                    prior=json.load(handle)
            except (OSError,ValueError,TypeError):
                prior={}
            if attempt==0 and not _pid_alive(prior.get('pid')):
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass
                continue
            raise RuntimeError('Moneyball pipeline is already running (pid %s)'%prior.get('pid','unknown'))
    try:
        yield
    finally:
        try:
            with open(path,encoding='utf-8') as handle:
                current=json.load(handle)
            if current.get('token')==token:
                os.remove(path)
        except (FileNotFoundError,OSError,ValueError,TypeError):
            pass


def start_index(resume):
    """Resolve one exact/case-sensitive chain prefix or reject it loudly."""
    if resume is None:
        return 0
    matches=[i for i,(script,_args) in enumerate(CHAIN)
             if resume in (script,os.path.splitext(script)[0]) or script.startswith(resume)]
    if len(matches)!=1:
        choices=', '.join(os.path.splitext(script)[0] for script,_args in CHAIN)
        raise ValueError('unknown --from target %r; choose exactly one of: %s'%(resume,choices))
    return matches[0]


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--recalc',action='store_true')
    parser.add_argument('--from',dest='frm',default=None)
    args=parser.parse_args(argv)
    try:
        first=start_index(args.frm)
    except ValueError as exc:
        parser.error(str(exc))
    if args.recalc:
        print('note: --recalc is retired; Python owns rank math and the workbook is a view.')
    t0=time.time()
    try:
        preflight_dependencies()
        with pipeline_run_lock():
            for script,script_args in CHAIN[first:]:
                started=time.time()
                req=OPTIONAL_INPUTS.get(script)
                reqs=(req,) if isinstance(req,str) else (req or ())
                missing=next((path for path in reqs
                              if not os.path.exists(
                                  path if os.path.isabs(path) else os.path.join(MB_ROOT,path))),None)
                if missing:
                    print('  %-28s %s %5.1fs  %s'%(
                        script+' '+' '.join(script_args),'--',time.time()-started,'skip: %s absent'%missing))
                    continue
                run=subprocess.run(
                    [sys.executable,os.path.join(FE,script)]+script_args,
                    capture_output=True,text=True,encoding='utf-8',errors='replace',
                )
                tail=(run.stdout or '').strip().splitlines()[-1:] or ['']
                print('  %-28s %s %5.1fs  %s'%(
                    script+' '+' '.join(script_args),'OK' if run.returncode==0 else '!!',
                    time.time()-started,tail[0][:90],
                ))
                if run.returncode!=0:
                    print((run.stdout or '')[-800:])
                    print((run.stderr or '')[-800:])
                    return 1
    except RuntimeError as exc:
        print('FATAL:',exc,file=sys.stderr)
        return 1
    print('PIPELINE COMPLETE in %.1f min'%((time.time()-t0)/60))
    return 0


if __name__=='__main__':
    sys.exit(main())
