"""Draft the external Brain update and seal this research generation locally."""
import argparse
import importlib.metadata
import platform
import sys
import zipfile
from pathlib import Path

from universe_common import CODE, ROOT, OLD, PREVIOUS, OUT, digest, read_json, stamp, write_json


def installed_versions(packages):
    versions = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def draft():
    verification=read_json(OUT/'verification_receipt.json');assert verification['status']=='PASS'
    results=read_json(OUT/'universe_results.json');stats=read_json(OUT/'universe_statistics.json')
    chosen=results['chosen_on_2023'];r=results['models'][chosen]['year_2024'];base=results['models']['boosted_dynamic']['year_2024']
    pair=stats['paired'][chosen+' vs boosted_dynamic'];plan=read_json(OUT/'universe_plan.json')
    strong=[n for n,s in plan['models'].items() if s['role']=='challenger' and not s['placebo']
            and all(stats['paired'][n+' vs '+b]['adjusted_interval'][0]>0 for b in ['boosted_dynamic','boosted_public_coverage','boosted_network','boosted_context'])]
    text=f'''# Brain update draft — apply through the normal Brain workflow

This is a draft in the research output directory. The external Project Brain has not been changed.

## Suggested STATE line

COSPONSORSHIP AUDIT COMPLETE {stamp()}: inventoried 402,142 artifacts / 323 path families / 80 declared stores; user-selected 377 continuing-member cohort; 24 shared-cohort refits and 79 paired contrasts. 2023-selected {chosen}: 2024 development {r['hits_at_8']}/{r['slots_at_8']} top-eight hits ({r['precision_at_8']:.3%}); independent prospective confirmation remains pending. Research only; prior issued forecasts unchanged.

## Findings to retain

- The broad audit covered psychology/behavior, public text, influence/network, staff, money/lobbying, demographics/elections, legislation/amendments and operational/derived stores. Path inventory is not a claim every byte or every measurement was modeled. Full triage records uninspected and unavailable families.
- Historical public/text/media collection was centered on the later roster. Departed House members have 0/156 and 0/80 retained coverage in Congress 117/118. The user explicitly chose the fixed continuing cohort as the benchmark: 377 members appearing in both historical risk panels and the official September 5 roster. All controls and challengers were refit on that cohort. These conclusions are conditional; current fitted Big Five/receptivity scores are still not valid historical inputs.
- Added dated conduct/activity, corrected bill stages, historical elections, BICAM amendment history, raw observed language and shared-broadcast relationships. Corrected the research feature looking for nonexistent action type=Passage using earlier CRS passage/reporting codes. Old models/features/forecasts remain intact.
- Selected on 2023: {chosen}. Later development: {r['hits_at_8']}/{r['slots_at_8']} versus dynamic trees: {base['hits_at_8']}/{base['slots_at_8']}. Paired extra hits: {pair['extra_hits']:+d}; adjusted precision interval: {100*pair['adjusted_interval'][0]:+.3f} to {100*pair['adjusted_interval'][1]:+.3f} percentage points. New variants beating all four tree controls after adjustment: {', '.join(strong) if strong else 'none'}.
- Statistics use 100,000 whole-legislative-family resamples; 79 contrasts include one identical-control sanity check, with adjustment separately for precision and Brier. Both 2023/2024 were previously inspected during historical research. This is development evidence, not independent confirmation or causal lobbying/influence identification.
- Existing D-013 audio and failed latent-state/personality criteria remain in force. Staff technical v5 checks pass within an exploratory release; that does not establish missing employment/promotions or historical publication/identity coverage.
- Independent source/cohort/model/statistics review and post-fit verification passed. Earlier research/prospective bindings were checked; archived exact protocol bytes resolve earlier LF/CRLF differences. Generation code is retained in code_snapshot.zip to preserve exact bytes.

## Next evidence boundary

The existing September 5 prospective predictions remain immutable. Their outcome window ends October 5 and can be scored no earlier than October 6. They are previous issued models, not the new cohort refits. Any new cohort-model prospective comparison requires its own source/feature/model/forecast receipt and observation times. Do not back-edit existing forecasts or call this cohort test a new independent Congress 119 holdout.

## Receipts

- outputs/cosponsor_universe_20260905/REPORT.md
- outputs/cosponsor_universe_20260905/universe_family_triage.json
- outputs/cosponsor_universe_20260905/gold_cohort.receipt.json
- outputs/cosponsor_universe_20260905/universe_plan.json
- outputs/cosponsor_universe_20260905/universe_selection.json
- outputs/cosponsor_universe_20260905/universe_results.json
- outputs/cosponsor_universe_20260905/universe_statistics.json
- outputs/cosponsor_universe_20260905/verification_receipt.json
- outputs/cosponsor_universe_20260905/experiment_manifest.json
'''
    (OUT/'BRAIN_UPDATE_DRAFT.md').write_text(text,encoding='utf-8')


def seal():
    path=OUT/'experiment_manifest.json'
    if path.exists():raise RuntimeError('Final manifest already exists')
    for f in ['REPORT.md','verification_receipt.json','BRAIN_UPDATE_DRAFT.md','universe_statistics.json','final_claims_review.json','final_claims_review.md']:assert (OUT/f).exists(),f
    assert read_json(OUT/'verification_receipt.json')['status']=='PASS'
    claims = read_json(OUT/'final_claims_review.json')
    assert claims['status']=='PASS_FINAL_NUMERIC_AND_CLAIMS_REVIEW' and not claims['blocking_findings']
    assert digest(OUT/'REPORT.md')==claims['reviewed_report_sha256']
    assert digest(OUT/'report_summary.json')==claims['reviewed_summary_sha256']
    plan=read_json(OUT/'universe_plan.json')
    for file,expected in plan['supporting_code_sha256'].items():assert digest(CODE/file)==expected,file
    for file,expected in plan['dependency_code_sha256'].items():assert digest(file)==expected,file
    for file,expected in plan['previous_manifests'].items():assert digest(file)==expected,file
    sources=sorted([*CODE.glob('*.py'),CODE/'PROTOCOL.md',CODE/'README.md',
                    *(CODE.parent/'cosponsor_challengers').glob('*.py'),*(CODE.parent/'cosponsor_refinement').glob('*.py')])
    with zipfile.ZipFile(OUT/'code_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sources:archive.writestr(source.relative_to(ROOT).as_posix(),source.read_bytes())
    artifacts={p.relative_to(OUT).as_posix():dict(sha256=digest(p),bytes=p.stat().st_size)
               for p in sorted(OUT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p!=path}
    write_json(path,dict(completed_utc=stamp(),status='continuing_member_development_complete_independent_confirmation_pending',
      code_sha256={p.name:digest(p) for p in sorted(CODE.glob('*.py'))},protocol_sha256=digest(CODE/'PROTOCOL.md'),
      cohort_members=377,models=24,comparison_count=79,bootstrap_replicates=100000,
      python_version=platform.python_version(),python_executable=sys.executable,
      package_versions=installed_versions(
          ['numpy','pandas','scipy','scikit-learn','networkx','pyarrow','joblib','threadpoolctl','matplotlib','PyYAML']),
      render_environment=read_json(OUT/'report_summary.json')['render_environment'],
      environment_note='Model/statistics/verification and seal use the default project Python; the figure/report use the separately recorded isolated Matplotlib environment. Null package versions mean absent in the sealing environment.',
      artifacts=artifacts,previous_manifests=plan['previous_manifests'],
      scope='Research-only local generation; all24 models refit on the user-directed continuing cohort. No production promotion, outreach or scheduler.'))
    print('Sealed',len(artifacts),'artifacts:',path)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--draft-only',action='store_true');args=parser.parse_args()
    if args.draft_only:draft()
    else:seal()
