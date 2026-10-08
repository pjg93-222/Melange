#!/usr/bin/env python3
"""Run legacy and LEGFIX3 archive wiring in isolated roots and report every cell delta."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


WORKTREE = Path(__file__).resolve().parents[2]
BUILDER = WORKTREE / 'fec' / 'build_archive_legislative.py'
NEW_REGISTRY = WORKTREE / 'bill_directions.csv'
LEGACY_REGISTRY = (
    WORKTREE / 'backups' / 'bill_directions.PRE-LEGFIX3.csv')
NEW_OVERRIDES = WORKTREE / 'bill_overrides.csv'


def inside(path, parent):
    """Return whether path resolves inside parent (including parent itself)."""
    path = Path(path).resolve()
    parent = Path(parent).resolve()
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def require_file(path, label):
    path = Path(path)
    if not path.is_file():
        raise SystemExit('ABORT: missing %s: %s' % (label, path))
    return path


def copy_inputs(live_root, target, overrides):
    """Create one self-contained builder data root without modifying live."""
    target.mkdir(parents=True)
    archives = sorted(live_root.glob('congress_bills_archive_*.xlsx'))
    if not archives:
        raise SystemExit('ABORT: no archive workbook under %s' % live_root)
    shutil.copy2(archives[-1], target / archives[-1].name)
    shutil.copy2(
        require_file(live_root / 'congestion.json', 'live congestion.json'),
        target / 'congestion.json')
    manual = live_root / 'manual_bill_evidence.csv'
    if manual.is_file():
        shutil.copy2(manual, target / manual.name)
    shutil.copy2(NEW_REGISTRY, target / 'bill_directions.csv')
    backup_dir = target / 'backups'
    backup_dir.mkdir()
    shutil.copy2(
        LEGACY_REGISTRY,
        backup_dir / 'bill_directions.PRE-LEGFIX3.csv')
    shutil.copy2(overrides, target / 'bill_overrides.csv')
    return archives[-1].name


def run_builder(data_root, legacy):
    env = os.environ.copy()
    env['MONEYBALL_ROOT'] = str(data_root)
    if legacy:
        env['LEGDIR_V1'] = '1'
    else:
        env.pop('LEGDIR_V1', None)
    result = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=str(WORKTREE),
        env=env,
        text=True,
        encoding='utf-8',
        errors='replace',
        capture_output=True,
        check=False,
    )
    if result.returncode:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(
            'ABORT: %s builder exited %d'
            % ('legacy' if legacy else 'new', result.returncode))
    return {
        'returncode': result.returncode,
        'stdout': result.stdout.splitlines(),
        'stderr': result.stderr.splitlines(),
    }


def load_json(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def selected_events(audit):
    """Index selected or neutral contribution for each member/category/bill event."""
    events = {}
    for row in audit.get('rows', []):
        if row.get('disposition') not in {
                'selected', 'neutral-override', 'neutral-manual',
                'neutral-registry'}:
            continue
        key = (
            row.get('member'),
            row.get('effective_category'),
            str(row.get('bill') or '').strip(),
            str(row.get('congress') or '').strip(),
        )
        events[key] = {
            'contribution': row.get('contribution', 0),
            'mechanism': row.get('direction_mechanism'),
            'category_mechanism': row.get('category_mechanism'),
            'override_reason': row.get('override_reason'),
            'sign': row.get('sign'),
            'source_section': row.get('source_section'),
        }
    return events


def rows_by_source(audit):
    return {
        row.get('source_row'): row
        for row in audit.get('rows', [])
        if row.get('source_row') is not None
    }


def changed_cells(old_leg, new_leg, old_events, new_events):
    cells = []
    members = sorted(set(old_leg) | set(new_leg))
    for member in members:
        old_categories = old_leg.get(member, {})
        new_categories = new_leg.get(member, {})
        for category in sorted(set(old_categories) | set(new_categories)):
            old_value = old_categories.get(category, 0)
            new_value = new_categories.get(category, 0)
            if old_value == new_value:
                continue
            event_keys = {
                key for key in set(old_events) | set(new_events)
                if key[0] == member and key[1] == category
            }
            responsible = []
            for key in sorted(event_keys, key=lambda item: (item[2], item[3])):
                old_event = old_events.get(key, {})
                new_event = new_events.get(key, {})
                old_contribution = old_event.get('contribution', 0)
                new_contribution = new_event.get('contribution', 0)
                if old_contribution == new_contribution:
                    continue
                responsible.append({
                    'bill': key[2],
                    'congress': key[3],
                    'old_contribution': old_contribution,
                    'new_contribution': new_contribution,
                    'old_mechanism': old_event.get('mechanism'),
                    'new_mechanism': new_event.get('mechanism'),
                    'old_category_mechanism': old_event.get(
                        'category_mechanism'),
                    'new_category_mechanism': new_event.get(
                        'category_mechanism'),
                    'old_override_reason': old_event.get('override_reason'),
                    'new_override_reason': new_event.get('override_reason'),
                    'old_sign': old_event.get('sign'),
                    'new_sign': new_event.get('sign'),
                    'old_source_section': old_event.get('source_section'),
                    'new_source_section': new_event.get('source_section'),
                })
            cells.append({
                'member': member,
                'category': category,
                'old': old_value,
                'new': new_value,
                'delta': new_value - old_value,
                'responsible': responsible,
            })
    return cells


def change_summary(old_audit, new_audit):
    old_rows = rows_by_source(old_audit)
    new_rows = rows_by_source(new_audit)
    newly_covered = {}
    sign_flips = {}
    exclusions = {}
    for source_row in sorted(set(old_rows) | set(new_rows)):
        old = old_rows.get(source_row, {})
        new = new_rows.get(source_row, {})
        mechanism = str(new.get('direction_mechanism') or '')
        identity = (
            str(new.get('bill') or old.get('bill') or '').strip(),
            str(new.get('congress') or old.get('congress') or '').strip(),
        )
        if (mechanism in {'registry-exact', 'registry-blank'}
                and old.get('direction_mechanism') != 'legacy-registry'):
            newly_covered[identity] = {
                'bill': identity[0],
                'congress': identity[1],
                'new_mechanism': mechanism,
                'old_mechanism': old.get('direction_mechanism'),
                'direction': new.get('sign'),
            }
        old_sign = old.get('sign')
        new_sign = new.get('sign')
        if old_sign in (-1, 1) and new_sign in (-1, 1) and old_sign != new_sign:
            sign_flips[identity] = {
                'bill': identity[0],
                'congress': identity[1],
                'old_sign': old_sign,
                'new_sign': new_sign,
                'old_mechanism': old.get('direction_mechanism'),
                'new_mechanism': new.get('direction_mechanism'),
            }
        if (new.get('disposition') == 'neutral-registry'
                and old.get('disposition') != 'neutral-registry'):
            exclusions[identity] = {
                'bill': identity[0],
                'congress': identity[1],
                'old_disposition': old.get('disposition'),
                'new_disposition': new.get('disposition'),
                'new_mechanism': mechanism,
            }
    order = lambda item: (item['bill'], item['congress'])
    return {
        'bills_newly_direction_covered': sorted(
            newly_covered.values(), key=order),
        'sign_flips': sorted(sign_flips.values(), key=order),
        'new_registry_exclusions': sorted(
            exclusions.values(), key=order),
    }


def atomic_json(document, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with open(temporary, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write('\n')
    os.replace(temporary, path)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-root', required=True, type=Path)
    parser.add_argument('--scratch-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    live_root = args.live_root.resolve()
    scratch_root = args.scratch_root.resolve()
    output = args.output.resolve()
    require_file(BUILDER, 'builder')
    require_file(NEW_REGISTRY, 'new registry')
    require_file(LEGACY_REGISTRY, 'legacy registry')
    require_file(NEW_OVERRIDES, 'new overrides')
    baseline_overrides = require_file(
        live_root / 'bill_overrides.csv', 'live baseline overrides')
    if not inside(scratch_root, WORKTREE):
        raise SystemExit(
            'ABORT: scratch root must be inside worktree: %s' % scratch_root)
    if not inside(output, WORKTREE):
        raise SystemExit(
            'ABORT: output must be inside worktree: %s' % output)
    if scratch_root.exists():
        raise SystemExit(
            'ABORT: scratch root already exists; choose a fresh path: %s'
            % scratch_root)
    if output.exists():
        raise SystemExit(
            'ABORT: output already exists; preserve it and choose a fresh path: %s'
            % output)
    baseline_root = scratch_root / 'baseline'
    new_root = scratch_root / 'new'
    archive_name = copy_inputs(
        live_root, baseline_root, baseline_overrides)
    copied_new_archive = copy_inputs(
        live_root, new_root, NEW_OVERRIDES)
    if copied_new_archive != archive_name:
        raise SystemExit('ABORT: scratch builds selected different archives')
    print('baseline root:', baseline_root)
    print('new root:', new_root)
    baseline_run = run_builder(baseline_root, legacy=True)
    new_run = run_builder(new_root, legacy=False)
    old_leg = load_json(baseline_root / 'archive_leg.json')
    new_leg = load_json(new_root / 'archive_leg.json')
    old_audit = load_json(
        baseline_root / 'legislation_routing_audit.json')
    new_audit = load_json(new_root / 'legislation_routing_audit.json')
    old_events = selected_events(old_audit)
    new_events = selected_events(new_audit)
    cells = changed_cells(old_leg, new_leg, old_events, new_events)
    summary = change_summary(old_audit, new_audit)
    summary['changed_cells'] = len(cells)
    summary['bills_newly_direction_covered_count'] = len(
        summary['bills_newly_direction_covered'])
    summary['sign_flip_count'] = len(summary['sign_flips'])
    summary['new_registry_exclusion_count'] = len(
        summary['new_registry_exclusions'])
    document = {
        'schema': 'legfix3-archive-wiring-delta-v1',
        'archive': archive_name,
        'baseline': {
            'mode': 'LEGDIR_V1=1',
            'registry': str(LEGACY_REGISTRY),
            'overrides': str(baseline_overrides),
            'run': baseline_run,
        },
        'new': {
            'mode': 'Congress-aware typed registry',
            'registry': str(NEW_REGISTRY),
            'overrides': str(NEW_OVERRIDES),
            'run': new_run,
        },
        'summary': summary,
        'cells': cells,
    }
    atomic_json(document, output)
    print('changed cells:', summary['changed_cells'])
    print(
        'bills newly direction-covered:',
        summary['bills_newly_direction_covered_count'])
    print('sign flips:', summary['sign_flip_count'])
    print(
        'new registry exclusions:',
        summary['new_registry_exclusion_count'])
    print('report:', output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
