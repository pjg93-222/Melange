"""Build a primary or independent twin against a receipt-pinned input generation."""
import argparse
import json
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORK))
from audits.staffer_network import build_staffer_social_network as builder


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit-persons', type=int, default=0)
    parser.add_argument('--hill-spine-root', type=Path)
    parser.add_argument('--spine-id-map', type=Path)
    parser.add_argument('--config-name')
    args = parser.parse_args()
    receipt = json.loads(args.baseline.read_text())
    inputs = {entry['role']: entry['path'] for entry in receipt['inputs']}
    argv = ['--repository-root', str(args.root), '--output', str(args.output),
            '--generated-at', '2026-09-08T00:00:00Z', '--no-glassbox',
            '--hill-spine-root', str(args.hill_spine_root or Path(inputs['hill_person_spine']).parent),
            '--house-ledger-root', str(Path(inputs['house_personnel_observations']).parent),
            '--senate-committee-root', str(Path(inputs['senate_committee_payroll_candidates']).parent)]
    for key in ('politico_direct_policy_memberships', 'politico_direct_link_receipt',
                'exploratory_revolving_edges', 'spine_id_map', 'design_doc', 'metrics_doc',
                'politico_current_committee_assertions', 'politico_profile_employment_assertions',
                'politico_profile_education_assertions', 'politico_profile_policy_deltas',
                'politico_explicit_committee_side_assertions'):
        if key in inputs:
            value = str(args.spine_id_map) if key == 'spine_id_map' and args.spine_id_map else inputs[key]
            argv += ['--' + key.replace('_', '-'), value]
    if args.spine_id_map and 'spine_id_map' not in inputs:
        argv += ['--spine-id-map', str(args.spine_id_map)]
    if args.config_name:
        argv += ['--config-name', args.config_name]
    if args.limit_persons:
        argv += ['--limit-persons', str(args.limit_persons)]
    print('Building', args.output, 'from', args.baseline, flush=True)
    result = builder.run(builder.parse_args(argv))
    print(json.dumps({'output': result['output'], 'ranking_math': result['receipt']['ranking_math'],
                      'edge_counts': result['receipt']['edge_counts']}), flush=True)


if __name__ == '__main__':
    main()
