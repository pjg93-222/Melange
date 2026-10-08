# -*- coding: utf-8 -*-
import os as _o,sys as _s
_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)))
from paths import DRAFT as MB_DRAFT
from paths import ROOT as MB_ROOT

"""Canonical fail-closed Moneyball pipeline runner.

Python owns all derived math. ``compute_pillars.py --write`` produces ``ranks_python.json`` as the
official reporting-rank authority; primacy tiers anchor allocation priority
with a leave-one-topic-out CU-orientation adjustment, and the workbook is a
recalculating audit/view artifact. A single exclusive lock covers
the entire writer chain so two runs cannot publish a mixed-vintage artifact set.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
import uuid
from pipeline_lock import pipeline_run_lock

sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FE=os.path.dirname(os.path.abspath(__file__))

# Glass Box: every process emits to the shared stream or it is not acceptable.
# This chain used to write only to stdout, so a twenty-minute production run
# that rewrote the rank authority was invisible to the dashboard. Emission is
# best-effort by design -- glassbox_emit swallows its own failures so an
# unwritable event can never take down a pipeline run.
try:
    from surfaces.glassbox_emit import emit as _gb, new_run_id as _gb_run, new_correlation_id as _gb_corr
except Exception:
    def _gb(*a, **k): return None
    def _gb_run(prefix='moneyball'): return ''
    def _gb_corr(): return ''
_GB_RUN=_gb_run('moneyball-pipeline')
_GB_CORR=_gb_corr()

CHAIN=[
    # FIRST, deliberately: halt before ANY artifact is written if this run would change a published
    # calibration (2026-07-19 incident — a run from a branch missing a ratified ladder silently
    # reverted Ally 3.00 -> 2.50 with no error and no audit failure). Intended changes pass with
    # CALIB_ACK=1; the guard prints the exact command. It is a chain STEP rather than an audit_full
    # ck() because a ck() failure exits 1 and aborts the whole chain — a warning must not do that.
    ('calibration_guard.py',[]),
    # Collection intake is a hard, hash-bound pre-publication gate.  Audio is queued only as a
    # candidate awaiting two independent reviews; press mentions remain relationship-only.
    ('audit_collection.py',['--output','data/engine/collection_intake_receipt.json']),
    ('build_press_engine_feed.py',[]),
    ('b5_audio_manifest_adapter.py',[]),
    ('b5_audio_descriptors_candidate.py',[
        '--review','data/members/b5_audio_reviews_v2.json.candidate',
        '--out','data/members/b5_audio_descriptors_v2.json.candidate']),
    # D-013 descriptive audio lane: prepares the complete accepted manifest,
    # measures missing clips, and emits a no-engine artifact for the surfaces.
    # Repointed 2026-09-02 at the cumulative source-media lane.  The bare defaults
    # still name the 28-clip v2 set sealed 08-30 02:06, which two sibling producers
    # invalidated within the day (calibration rewritten 02:18, inventory 17:44) and
    # which predates the final-receipt vocabulary change -- so the chain form of this
    # step had been failing "verified final receipt is stale or incomplete" since
    # 08-30, unnoticed because the collection gate aborted four steps earlier.  These
    # are the paths the last successful build used (08-31 01:29, 1847 verified
    # finals); the manifest and receipt hashes match that build byte for byte.
    ('build_descriptive_speech.py',[
        '--verified-manifest','data/speech/source_media_verified_cumulative_exact_windows_v6.jsonl',
        '--verified-receipt','data/speech/source_media_verified_cumulative_exact_windows_v6.receipt.json',
        '--identity-manifest','data/speech/source_media_identity_cumulative_all_verified_v5.jsonl',
        '--identity-receipt','data/speech/source_media_identity_cumulative_all_verified_v5.receipt.json',
        '--candidate-manifest','data/speech/source_media_candidates_cumulative_all_verified_v5.jsonl',
        '--candidate-receipt','data/speech/source_media_candidates_cumulative_all_verified_v5.receipt.json',
        '--source-media-inventory','data/speech/source_media_inventory_cumulative_expanded_v3_snapshot.jsonl',
        '--speaker-calibration','data/speech/speaker_anchor_calibration_all_verified_v3.json',
    ]),
    ('coop_v2_candidate.py',[]),
    ('build_electoral.py',[]),
    ('build_district_industry.py',[]),
    ('receptivity_layer.py',[]),
    # Same-cycle bill transaction: verify the official repository, persist
    # canonical bill IDs + review state into Excel, then let archive scoring
    # and labels consume that worksheet.  This must precede every legislative
    # downstream producer.
    # Verified collector -> ledger gate (2026-08-29 Paul). Consumes the previous-cycle
    # member_desk_bundle exactly like champions_v2/industry_tiers, plus the weekly
    # Congress.gov/GovInfo bill repository and its refresh receipt, and publishes the
    # additive cosponsor-join sidecar make_member_desk merges as its fourth membership
    # source. Local files only -- the chain's network-free law holds. It runs BEFORE
    # compute_pillars/build_primacy_surfaces so the same-cycle desk rebuild inside
    # build_primacy_surfaces --engine-inputs-only already sees the fresh sidecar.
    # Its refusal set is a strict SUBSET of the validate_live_repository gate that
    # make_member_desk already trips at import, so this step can only ever halt a chain
    # that was going to halt anyway -- and it halts it before compute_pillars --write.
    ('verify_collector_roster_updates.py',[]),
    # Runtime-absent is a CLEAN SKIP, not a failure: the sync keeps the last-good ledger
    # and records status SKIPPED_RUNTIME_ABSENT in its receipt. That skip cannot go
    # unnoticed -- audit_full's sentinel_ledger_freshness check ages it out at 21 days.
    ('sync_sentinel_bill_ledger.py',[]),
    ('build_archive_legislative.py',[]),
    ('extract_cu_speeches.py',[]),
    ('speech_stance_stack.py',[]),
    ('hearing_stance_stack.py',[]),
    ('extract_cu_interviews.py',[]),
    ('interview_stance_stack.py',[]),
    ('bluesky_stance_stack.py',[]),
    ('tweet_stance_stack.py',['--score']),
    ('press_stance_stack.py',[]),
    ('press_engagement_layer.py',[]),
    ('press_hcoi.py',[]),
    # Rebuild the live augmented cascade only after both fresh press-derived layers exist.
    ('build_multilayer_network.py',[]),
    ('member_reference_layer.py',['--rebuild']),
    ('build_media_blend.py',[]),
    ('per_category_stance.py',[]),
    ('compute_pillars.py',['--write']),
    # Primacy is an allocation-engine input. Build its beneficiary factor and
    # conduct-adjusted tier before any engine imports moneyball_core.
    ('build_primacy_surfaces.py',['--engine-inputs-only']),
    # Display-only CU ask take-up/capacity context.  It consumes the pre-chain
    # desk bundle plus the just-refreshed primacy factors, and must exist before
    # the final member desk and lobbying-board surfaces render it.
    ('responsiveness_layers.py',[]),
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
    # Coalition access price + majority-neutral capability for the builder's Underpriced basis.
    # Decision-layer only (like dashboard_legislative_workbench): reads congestion/say-do/LEP/
    # dispositions and the LDA attention window, writes coalition_pricing.json, and moves no rank.
    # Must precede make_member_desk.py, which folds it into the desk bundle.
    ('coalition_pricing.py',[]),
    # 2026-08-05 (Paul): the DESK renders LAST — it is the face, the display —
    # with the lobbying network generated before it. Order: network surfaces,
    # then the bill-lobbying sidecar, then the desk that folds everything in,
    # then the combine, then the audit.
    #
    # Industry/lobbying surface. Emits lobby-network.html, which make_combined.py
    # folds into the combined dashboard -- so it must precede make_combined.py or the
    # combine step merges a stale surface.
    # CU x fintech under-contested screen (Paul 2026-08-05): descriptive
    # residual lens from the round-3 look, rendered by the industry page.
    # Screen, not a score - no engine or rank reads it.
    ('contest_screen.py',[]),
    # 2026-08-06 Paul: direction-aware boards replace the residual-attention headline.
    ('champions_v2.py',[]),
    # Contest-adjusted investment and lobbying efficiency; decision layer only, moves no rank.
    # 2026-08-09 Paul: moved AFTER champions_v2 so the ADVERSARY exclusion consumes the
    # same-cycle boards (champion crown law) and the same-cycle coalition_pricing artifact;
    # both were one-cycle lagged at the old pre-dashboard slot. Safe since the desk-tab
    # move (d07eaea): the dashboard no longer reads efficiency output — its consumer is
    # make_member_desk, which renders later.
    ('efficiency_layers.py',[]),
    # 2026-08-10: consumes the previous-cycle member_desk_bundle exactly like champions_v2
    # (the documented bundle producer/consumer cycle), and hard-fails unless its credit-union
    # instance reproduces the desk bundle's tiers exactly. make_lobby_network_html.py hard-requires
    # data/lobbying/industry_tiers.json, so this must precede that step.
    ('industry_tiers.py',[]),
    ('org_mentions.py',[]),
    ('make_lobby_network_html.py',[]),
    # Interactions surface. Emits lobby-interactions.html, which make_combined.py deliberately
    # does NOT merge (it stays a real navigation target). It is chained so the surface stops
    # going stale silently. Its LEDGER producer (fec/lobbying/lobby_interactions.py) is
    # deliberately NOT chained (position classification, expensive); the ledger stays a manual
    # refresh and this step consumes whatever ledger is current.
    ('make_lobby_interactions_html.py',[]),
    # Bill-level lobbying sidecar. The desk folds it into the repository; the
    # basename resolver owns the producer path, like every other chain step.
    ('bill_lobbying_sidecar.py',[]),
    # The engine-input half already ran before allocation. Rebuild the final
    # evidence-bearing desk after the profile layers AND the lobbying surfaces finish.
    ('make_member_desk.py',[]),
    ('make_combined.py',[]),
    ('make_email_package.py',[]),
    ('audit_full.py',[]),
]

# 2026-08-05 Phase 3: this resolver is the single source of chain-path truth;
# CHAIN names are location-independent, and a missing or duplicated producer
# basename fails loudly at chain start.
_producer_paths={}
for _producer_dir,_producer_dirs,_producer_files in os.walk(FE):
    _producer_dirs[:]=sorted(
        _dir for _dir in _producer_dirs
        if _dir not in ('tests','attic','__pycache__')
        and not _dir.startswith('_quarantine')
    )
    for _producer_file in sorted(_producer_files):
        if not _producer_file.endswith('.py'):
            continue
        _producer_full_path=os.path.join(_producer_dir,_producer_file)
        if _producer_file in _producer_paths:
            raise RuntimeError('duplicate producer basename %s: %s and %s'%
                               (_producer_file,_producer_paths[_producer_file],
                                _producer_full_path))
        _producer_paths[_producer_file]=_producer_full_path

def _producer_path(_producer_name):
    _producer_basename=os.path.basename(_producer_name)
    if _producer_basename not in _producer_paths:
        raise RuntimeError('chain producer script not found: %s'%_producer_name)
    return _producer_paths[_producer_basename]

for _chain_script,_chain_args in CHAIN:
    _producer_path(_chain_script)

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
    # The collector->ledger gate needs the previous desk bundle AND a completed weekly bill
    # scrape. In a fresh or data-isolated worktree those are absent, and a clean skip is
    # correct: no sidecar is written, so the desk simply assembles the ledger as it did before.
    # A PRESENT-but-unverifiable receipt still fails the step loudly -- absence is not failure.
    'verify_collector_roster_updates.py':(
        'member_desk_bundle.json',
        'bill_repository_live.json',
        'data/engine/congress_bill_refresh_receipt.json',
    ),
    'sync_sentinel_bill_ledger.py':(
        'member_desk_bundle.json',
        'bill_repository_live.json',
        'data/engine/congress_bill_refresh_receipt.json',
        'data/members/collector_roster_updates.ndjson',
        'data/members/collector_roster_pending.ndjson',
    ),
    'extract_cu_speeches.py':'social_media.db',   # sqlite source of the CREC floor speeches
    'speech_stance_stack.py':'speeches_cu.csv',   # produced by extract_cu_speeches.py
    'build_district_industry.py':(
        'data/district/district_geography.json',
        os.path.join(_DEMO_DATA_ROOT,'lodes','lodes_cd_panel.csv.gz'),
    ),
    'org_mentions.py':(
        'press_text_cache.jsonl',
        'social_media.db',
        'data/stance/x_catalog.jsonl',
        'Quorum Processed.xlsx',
        os.path.join(MB_DRAFT,'cu_press_stance_tone.csv'),
        os.path.join(MB_DRAFT,'cu_press_debate_in.csv'),
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
    _gb('pipeline.run','running','chain started (%d steps)'%len(CHAIN[first:]),
        run_id=_GB_RUN,correlation_id=_GB_CORR)
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
                _gb('pipeline.step','running','%s'%(script+' '+' '.join(script_args)).strip(),
                    stage=script,run_id=_GB_RUN,correlation_id=_GB_CORR)
                run=subprocess.run(
                    [sys.executable,_producer_path(script)]+script_args,
                    capture_output=True,text=True,encoding='utf-8',errors='replace',
                )
                tail=(run.stdout or '').strip().splitlines()[-1:] or ['']
                print('  %-28s %s %5.1fs  %s'%(
                    script+' '+' '.join(script_args),'OK' if run.returncode==0 else '!!',
                    time.time()-started,tail[0][:90],
                ))
                _gb('pipeline.step','completed' if run.returncode==0 else 'failed',
                    tail[0][:200] or (script+' finished'),stage=script,
                    run_id=_GB_RUN,correlation_id=_GB_CORR,
                    duration_ms=int((time.time()-started)*1000),
                    detail='' if run.returncode==0 else ((run.stderr or '')[-1200:]))
                if run.returncode!=0:
                    print((run.stdout or '')[-800:])
                    print((run.stderr or '')[-800:])
                    _gb('pipeline.run','failed','chain halted at %s'%script,stage=script,
                        run_id=_GB_RUN,correlation_id=_GB_CORR,
                        duration_ms=int((time.time()-t0)*1000))
                    return 1
    except RuntimeError as exc:
        print('FATAL:',exc,file=sys.stderr)
        _gb('pipeline.run','failed','FATAL: %s'%exc,run_id=_GB_RUN,correlation_id=_GB_CORR,
            duration_ms=int((time.time()-t0)*1000))
        return 1
    print('PIPELINE COMPLETE in %.1f min'%((time.time()-t0)/60))
    _gb('pipeline.run','completed','PIPELINE COMPLETE in %.1f min'%((time.time()-t0)/60),
        run_id=_GB_RUN,correlation_id=_GB_CORR,duration_ms=int((time.time()-t0)*1000))
    return 0


if __name__=='__main__':
    sys.exit(main())
