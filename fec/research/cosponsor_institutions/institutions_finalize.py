"""Seal the separately reviewed institutional development generation."""
import argparse
import importlib.metadata
import platform
import sys
import zipfile
from pathlib import Path
from institutions_common import CODE, ROOT, OUT, digest, read_json, write_json, stamp


def draft():
    r=read_json(OUT/'institutions_results.json');s=read_json(OUT/'institutions_statistics.json')
    n=r['chosen_on_2023'];m=r['models'][n]['year_2024']
    text=f'''# Brain update draft

The external Project Brain has not been changed. Apply this through its normal workflow.

Suggested STATE line: INSTITUTIONAL COSPONSOR DEVELOPMENT COMPLETE {stamp()}: same 377 continuing members; 13 new models plus four frozen references, 70 fixed contrasts and 100,000 legislative-family resamples. 2023-selected {n}: 2024 {m['hits_at_8']}/{m['slots_at_8']} correct top-eight selections ({m['precision_at_8']:.3%}). Independent future confirmation pending.

Added 25 dated voting features, 21 primary historical committee features and 15 caucus features. The caucus membership subset is one dated Problem Solvers roster per Congress, separate from prior-Congress CMO leadership observations. A null/inconclusive result does not reject comprehensive caucus membership. Four event-dated hearing features are sensitivity-only and ineligible for selection. Archived roster coverage is incomplete early in each Congress. Record update times are not original publication times.

This is a retrospective conditional benchmark, with both historical years previously inspected. It does not validate current psychological scores, infer staff attendance, identify causal lobbying effects or generalize automatically to departed/new members. Source anomalies and quarantines remain documented. Review all gains and adjusted intervals in REPORT.md and institutions_statistics.json; do not substitute a 2024 winner for the model selected in 2023.

Earlier September 5 prospective forecasts are unchanged; their window ends October 5, earliest scoring October 6. Those forecasts belong to earlier model generations. No production promotion, outreach, scheduler, push or external Brain edit was performed.

Receipts: outputs/cosponsor_institutions_20260905/REPORT.md, institutions_plan.json, institutions_selection.json, institutions_results.json, institutions_statistics.json, verification_receipt.json, final_claims_review.json and experiment_manifest.json.
'''
    (OUT/'BRAIN_UPDATE_DRAFT.md').write_text(text,encoding='utf-8')


def seal():
    dest=OUT/'experiment_manifest.json'
    assert not dest.exists(),'Generation already sealed'
    verification=read_json(OUT/'verification_receipt.json');assert verification['status']=='PASS'
    claims=read_json(OUT/'final_claims_review.json');assert claims['status']=='PASS' and not claims['blocking_findings']
    assert claims['report_sha256']==digest(OUT/'REPORT.md')
    assert claims['summary_sha256']==digest(OUT/'report_summary.json')
    summary=read_json(OUT/'report_summary.json')
    for name,expected in summary['source_hashes'].items():assert digest(OUT/name)==expected,name
    for name,record in verification['models'].items():
        assert digest(OUT/f'predictions/{name}.npy')==record['prediction_sha256'],name
        assert digest(OUT/f'models/{name}.joblib')==record['model_sha256'],name
    plan=read_json(OUT/'institutions_plan.json')
    assert digest(CODE/'institutions_models.py')==plan['model_code_sha256']
    assert digest(CODE/'PROTOCOL.md')==plan['protocol_sha256']
    for name,expected in plan['supporting_code_sha256'].items():assert digest(CODE/name)==expected,name
    for group in ['dependency_code_sha256','input_sha256','prior_bindings','frozen_feature_inputs_sha256','receipt_declared_source_sha256']:
        for name,expected in plan[group].items():assert digest(name)==expected,name
    for f in ['BRAIN_UPDATE_DRAFT.md','source_review_caucus.json','source_review_committees.json','source_review_votes.json','coverage_review.json']:
        assert (OUT/f).exists(),f
        if f.endswith('.json'):
            review=read_json(OUT/f)
            assert review['status'].startswith('PASS') and not review.get('blocking_findings',[]),f
    sources=sorted(set([*CODE.glob('*.py'),CODE/'PROTOCOL.md',CODE/'README.md',
        *[p for folder in ['cosponsor_challengers','cosponsor_refinement','cosponsor_universe'] for p in (CODE.parent/folder).glob('*.py')]]))
    with zipfile.ZipFile(OUT/'code_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sources:archive.writestr(path.relative_to(ROOT).as_posix(),path.read_bytes())
    versions={}
    for name in ['numpy','pandas','scipy','scikit-learn','pyarrow','joblib','threadpoolctl','PyYAML','PyMuPDF']:
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
    artifacts={p.relative_to(OUT).as_posix():dict(sha256=digest(p),bytes=p.stat().st_size)
        for p in sorted(OUT.rglob('*')) if p.is_file() and p!=dest and '__pycache__' not in p.parts}
    write_json(dest,dict(completed_utc=stamp(),status='institutional_development_complete_independent_confirmation_pending',
        models=len(plan['models']),comparison_count=len(plan['pairs']),bootstrap_replicates=100000,cohort_members=377,
        code_sha256={p.name:digest(p) for p in sorted(CODE.glob('*.py'))},protocol_sha256=digest(CODE/'PROTOCOL.md'),
        python_version=platform.python_version(),python_executable=sys.executable,package_versions=versions,
        render_environment=read_json(OUT/'report_summary.json')['render_environment'],artifacts=artifacts,
        prior_bindings=plan['prior_bindings'],scope='Local observational research. Prior forecasts unchanged. No production promotion, outreach, scheduler or external Brain edit.'))
    print('Sealed',len(artifacts),'artifacts',dest)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--draft-only',action='store_true');args=parser.parse_args()
    if args.draft_only:draft()
    else:seal()
