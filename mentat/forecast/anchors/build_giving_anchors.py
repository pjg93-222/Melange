"""Build the Giving Forecast anchor snapshot: Mentat's own levels that the forecast applies its relative changes to.

    python build_giving_anchors.py [--project-root <Mentat\\mentat>] [--industry id ...] [--output-dir <dir>] [--check]

Owner rulings of 2026-09-30 implemented here: the forecast applies to MENTAT data (levels always from Mentat; OpenSecrets only estimated the
relationships); PAC shown as (1) the roster companies' PACs' own giving to candidates (FEC pas2, D-049) and (2) Mentat general giving (the
workbook's included Analysis Amount, all channels); shares on the employee and PAC bases; Melange LDA levels, both series; coverage end by rule;
thin-base flags; Community Banks separate; auto has no Mentat data and no entry.

READ-ONLY toward everything but its own two output files. SQLite files are opened immutable; FEC files and the LDA / CPI inputs are only read;
no money-collection or receipt-counting code is imported or run. The snapshot is written atomically (temporary file + replace) only after it
validates against the shared schema and the anchor invariants (mentat/forecast/contracts); an invalid build leaves the previous snapshot
in place. Output: <project>/state/giving-anchors/giving-anchors-v1.json + giving-anchors-v1.receipt.json (runtime state, D-048: not in git).
"""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'contracts'))
import contract  # noqa: E402
import coverage as coverage_rule  # noqa: E402
import cpi as cpi_reader  # noqa: E402
import fec_pas2  # noqa: E402
import glassbox  # noqa: E402
import lda as lda_reader  # noqa: E402
import mentat_sources as ms  # noqa: E402

VERSION = '1'
SNAPSHOT_NAME = 'giving-anchors-v1.json'
RECEIPT_NAME = 'giving-anchors-v1.receipt.json'
LDA_UNAVAILABLE = 'No Melange-LDA sector for this industry (sector_spend ROSTERS: crypto, credit_union, bank, fintech)'


class Unavailable(Exception):
    """An industry that cannot be anchored; the message is the reason the console shows."""


def utc_now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def dollars(cents):
    return round(cents / 100, 2)


def code_sha256():
    parts = sorted([p for p in HERE.glob('*.py')] + [HERE / 'registry.json'])
    return hashlib.sha256('\n'.join(ms.sha256_file(p) for p in parts).encode()).hexdigest()


def read_json(path):
    with Path(path).open(encoding='utf-8-sig') as stream:
        return json.load(stream)


# ---------------------------------------------------------------------------------------------------------------------------------
# locations
# ---------------------------------------------------------------------------------------------------------------------------------
def report_directory(project_root):
    value = os.environ.get('MENTAT_REPORT_DIRECTORY', '').strip()
    if not value:
        setting = read_json(Path(project_root) / 'config' / 'report-directory.json')
        if setting.get('schema_version') != 1:
            raise ValueError('Unsupported report-directory configuration.')
        value = setting['directory']
    directory = Path(value)
    if not directory.is_absolute() or not directory.is_dir():
        raise ValueError('The configured report directory is unavailable.')
    return directory.resolve()


def fec_root(project_root, override=None):
    if override:
        return Path(override)
    return Path(read_json(Path(project_root) / 'inputs' / 'active_fec_sources.json')['path'])


def default_lda_csv():
    base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
    return Path(base) / 'Melange' / 'lda_rebuild' / 'derived' / 'sector_spend' / 'sector_spend.csv'


def default_controls(project_root):
    return Path(project_root).resolve().parent / 'sector_growth_study' / 'data' / '00_controls.xlsx'


def default_output_dir(project_root):
    return Path(project_root) / 'state' / 'giving-anchors'


# ---------------------------------------------------------------------------------------------------------------------------------
# the Mentat side of one industry
# ---------------------------------------------------------------------------------------------------------------------------------
def mentat_side(spec, ctx):
    workbook = ctx['report_dir'] / spec['workbook']
    if not workbook.is_file():
        raise Unavailable('The published workbook ' + spec['workbook'] + ' is not in the report directory.')
    workbook_sha = ms.sha256_file(workbook)
    found = ms.find_index(ctx['index_dir'], workbook_sha)
    if found is None:
        raise Unavailable('No contribution-analytics index matches the published workbook (sha256 ' + workbook_sha[:8] + '). Open the industry in the console so its index is built, then rebuild the anchors.')
    index_path, manifest = found
    prov = manifest['provenance']
    source = ms.find_source_db(ctx['project_root'], spec['source_db_candidates'], prov['database_sha256'], ctx['hashes'])
    if source is None:
        raise Unavailable('The pinned source database (sha256 ' + str(prov['database_sha256'])[:8] + ') was not found under the Mentat project folder.')
    collected = ms.collection_date(source, spec['mentat_dataset'])
    open_cycle = int(collected[:4]) + int(collected[:4]) % 2
    cov = coverage_rule.coverage(collected, spec.get('coverage_cut_back'))
    cuts = fec_pas2.month_ends(open_cycle - 1, cov['coverage_end'])
    agg = ms.index_aggregates(index_path, source, open_cycle, cuts)
    expected = {k.split('-')[-1]: v for k, v in manifest['receipt_cycles'].items()}
    if agg['cycles'] != expected:
        raise Unavailable('The index receipt totals differ from its own manifest; the index is not trustworthy.')
    progress = ms.work_progress(source, open_cycle)
    return dict(workbook=workbook, workbook_sha=workbook_sha, index_path=index_path, manifest=manifest, source=source,
                collected=collected, open_cycle=open_cycle, cov=cov, cuts=cuts, agg=agg, progress=progress)


def _chambers(blocks):
    return {ch: {k: dollars(blocks[ch][k]) for k in ('D', 'R', 'other')} for ch in ('House', 'Senate')}


def _thin(cycles, threshold):
    return {cy: {ch: (row[ch]['D'] + row[ch]['R']) < threshold for ch in ('House', 'Senate')} for cy, row in cycles.items()}


def general_and_candidates(side, threshold):
    agg = side['agg']
    general = {
        'status': 'ready', 'reason': None, 'basis': 'receipt',
        'label': 'Published included receipt view (workbook Analysis Amount), all funding sources and recipient categories, net of negative adjustments',
        'cycles': {cy: dollars(v) for cy, v in sorted(agg['cycles'].items())},
        'by_funding_source': {cy: {k: dollars(v) for k, v in sorted(src.items())} for cy, src in sorted(agg['by_source'].items())},
        'observed': [{'through': cut, 'amount': dollars(v)} for cut, v in agg['general_cuts']]}
    cycles = {cy: _chambers(blocks) for cy, blocks in sorted(agg['candidates'].items())}
    candidates = {
        'status': 'ready', 'reason': None,
        'basis': 'Employees\' included giving to House (committee type H) and Senate (S) candidate committees: the index joined to the pinned source '
                 'database on sub_id; party D / R from the index, anything else "other"; presidential (P) committees excluded',
        'cycles': cycles, 'observed': [dict(through=cut, **_chambers(blocks)) for cut, blocks in agg['candidate_cuts']],
        'thin_base': _thin(cycles, threshold)}
    return general, candidates


# ---------------------------------------------------------------------------------------------------------------------------------
# FEC pas2
# ---------------------------------------------------------------------------------------------------------------------------------
def _yy(cycle):
    return '%02d' % (cycle % 100)


def _http_date(value):
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return None


def fec_inputs(root, cycles):
    """[(role, relative file, path, receipt dict)] of the pas2 / cn / cm files of these cycles, each verified against its source receipt."""
    out = []
    for cycle in cycles:
        yy = _yy(cycle)
        for role, folder, sub, name in (('pas2', 'fec_beneficiary', 'pas2' + yy, 'itpas2.txt'), ('cn', 'fec_beneficiary', 'cn' + yy, 'cn.txt'),
                                        ('cm', 'fec_committee_master', 'cm' + yy, 'cm.txt')):
            path = Path(root) / folder / sub / name
            if not path.is_file():
                raise Unavailable('FEC input missing: ' + str(Path(folder) / sub / name))
            receipt_path = path.with_name('source-receipt.json')
            receipt = read_json(receipt_path) if receipt_path.is_file() else {}
            sha = ms.sha256_file(path)
            if receipt.get('sha256') and receipt['sha256'] != sha:
                raise Unavailable('FEC input ' + sub + '/' + name + ' differs from its source receipt; re-run the FEC refresh before anchoring.')
            out.append({'role': role + ':' + str(cycle), 'file': sub + '/' + name, 'path': path, 'sha256': sha,
                        'fec_last_modified': _http_date(receipt.get('last_modified')), 'yy': yy, 'family': role})
    return out


def committee_ids_in_master(files):
    found = set()
    for f in files:
        if f['family'] == 'cm':
            with open(f['path'], encoding='latin-1') as stream:
                for line in stream:
                    found.add(line.split('|', 1)[0])
    return found


def build_pac(group, root, open_cycle, sides, threshold):
    """{industry id: pac_to_candidates block} for the industries (with rosters) of one open cycle."""
    cycles = [open_cycle - 4, open_cycle - 2, open_cycle]
    inputs = fec_inputs(root, cycles)
    cn_files = [(f['yy'], f['path']) for f in sorted(inputs, key=lambda f: f['yy'], reverse=True) if f['family'] == 'cn']
    parties = fec_pas2.load_parties(cn_files)
    membership = {}
    for spec in group:
        for committee in spec['pac_roster']:
            membership.setdefault(committee['id'], []).append(spec['id'])
    in_master = committee_ids_in_master(inputs)
    out, notes = {}, {}
    cuts = {spec['id']: sides[spec['id']]['cuts'] for spec in group}
    results = {}
    for f in inputs:
        if f['family'] != 'pas2':
            continue
        cycle = int(f['role'].split(':')[1])
        results[cycle] = fec_pas2.aggregate_file(f['path'], f['yy'], parties, membership, cuts if cycle == open_cycle else None)
    for spec in group:
        ident = spec['id']
        by_cycle, through, observed = {}, {}, []
        for cycle in cycles:
            block = results[cycle].get(ident)
            by_cycle[str(cycle)] = fec_pas2.dollars(block['totals'] if block else fec_pas2.blank_block())
            if block and block['max_date']:
                through[str(cycle)] = block['max_date']
        block = results[open_cycle].get(ident)
        for cut in cuts[ident]:
            cut_block = block['cuts'][cut] if block else fec_pas2.blank_block()
            d = fec_pas2.dollars(cut_block)
            observed.append({'through': cut, 'House': d['House'], 'Senate': d['Senate'], 'to_house_senate': d['to_house_senate']})
        roster = spec['pac_roster']
        missing = sorted(c['id'] for c in roster if c['id'] not in in_master)
        out[ident] = {
            'status': 'ready', 'reason': None, 'source': 'FEC committee-to-candidate bulk files (pas2) with the candidate master (cn)',
            'rule': fec_pas2.RULE_TEXT, 'committee_count': len(roster), 'single_pac': len(roster) == 1,
            'committees': [dict(c) for c in roster],
            'inputs': [{'role': f['role'], 'file': f['file'], 'sha256': f['sha256'], 'fec_last_modified': f['fec_last_modified']} for f in inputs],
            'cycles': by_cycle, 'file_through': through, 'observed': observed,
            'thin_base': _thin({cy: row for cy, row in by_cycle.items()}, threshold)}
        found = []
        if missing:
            found.append('Roster committee(s) absent from the FEC committee masters: ' + ', '.join(missing))
        undated = sum((results[c].get(ident) or {}).get('undated_cents', 0) for c in cycles)
        if undated:
            found.append(f'${format(dollars(undated), ",.2f")} of counted FEC rows carry no usable date: they are in the cycle totals and in no observed cut.')
        if found:
            notes[ident] = ' '.join(found)
    return out, notes


def unavailable_pac(reason):
    return {'status': 'unavailable', 'reason': reason, 'source': '', 'rule': '', 'committee_count': 0, 'single_pac': False, 'committees': [],
            'inputs': [], 'cycles': {}, 'file_through': {}, 'observed': [], 'thin_base': {}}


# ---------------------------------------------------------------------------------------------------------------------------------
# LDA
# ---------------------------------------------------------------------------------------------------------------------------------
def build_lda(spec, rows, lda_path, lda_sha):
    if spec.get('lda_sector') and rows is None:
        return {'status': 'unavailable', 'reason': 'The Melange LDA output ' + lda_path.name + ' was not found.', 'sector': spec['lda_sector'], 'label': None,
                'source_file': None, 'source_sha256': None, 'through': None, 'series': {}, 'note': lda_reader.NOTE}
    if not spec.get('lda_sector'):
        return {'status': 'unavailable', 'reason': LDA_UNAVAILABLE, 'sector': None, 'label': None, 'source_file': None, 'source_sha256': None,
                'through': None, 'series': {}, 'note': lda_reader.NOTE}
    levels = lda_reader.sector_levels(rows, spec['lda_sector'])
    if levels is None:
        return {'status': 'unavailable', 'reason': 'The Melange LDA output has no rows for sector ' + spec['lda_sector'], 'sector': spec['lda_sector'],
                'label': None, 'source_file': lda_path.name, 'source_sha256': lda_sha, 'through': None, 'series': {}, 'note': lda_reader.NOTE}
    label = {'bank': 'Melange LDA bank sector (total, not a bank tier)', 'credit_union': 'Melange LDA credit-union sector'}.get(spec['lda_sector'],
                                                                                                                              'Melange LDA sector ' + spec['lda_sector'])
    return {'status': 'ready', 'reason': None, 'sector': spec['lda_sector'], 'label': label, 'source_file': lda_path.name, 'source_sha256': lda_sha,
            'through': levels['through'], 'series': levels['series'], 'note': lda_reader.NOTE}


# ---------------------------------------------------------------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------------------------------------------------------------
def industry_flags(spec, side, pac_note, cpi_multipliers):
    coverage_flags, flags = [], []
    progress = side['progress']
    if progress and progress['stored_complete'] < progress['units']:
        coverage_flags.append(f"{progress['stored_complete']} of {progress['units']} {side['open_cycle']} collection work units are stored_complete "
                              f"({progress['fetched_complete']} fetched) in the collection database's own progress table; the observed total is probably low.")
    if side['agg']['after_cut']:
        coverage_flags.append('Included receipts dated after the coverage end ($' + format(dollars(side['agg']['after_cut']), ',.2f') +
                              ') are not observed; they stay in the remainder window.')
    if side['cov']['reason']:
        coverage_flags.append('Coverage cut back from ' + side['cov']['rule_coverage_end'] + ' to ' + side['cov']['coverage_end'] + ': ' + side['cov']['reason'] + '.')
    if str(side['open_cycle']) not in cpi_multipliers:
        coverage_flags.append(f"No {side['open_cycle']} CPI exists yet: {side['open_cycle'] - 1}-{side['open_cycle']} observed amounts are compared at face value.")
    non_giving = {cy: v for cy, src in side['agg']['by_source'].items() for k, v in src.items() if k == 'non_giving' and v}
    if non_giving:
        flags.append('Included receipts the accounting engine buckets as non_giving stay inside the Analysis Amount (reported, not changed): ' +
                     '; '.join(f'{cy} ${format(dollars(v), ",.2f")}' for cy, v in sorted(non_giving.items())) + '.')
    if side['agg']['type_conflicts']:
        flags.append(f"{side['agg']['type_conflicts']} sub_ids carry conflicting recipient committee types in the pinned source database.")
    if side['agg']['unmatched'][0]:
        flags.append(f"{side['agg']['unmatched'][0]} included facts (${format(dollars(side['agg']['unmatched'][1]), ',.2f')}) have no source row and are outside the chamber split.")
    if pac_note:
        flags.append(pac_note)
    if len(spec.get('pac_roster') or []) == 1:
        flags.append('PAC channel = one committee (' + spec['pac_roster'][0]['company'] + '); it is not the industry\'s PAC giving (thin base).')
    return coverage_flags, flags


def build_snapshot(project_root, registry, options):
    """-> (snapshot dict, receipt inputs list, problems). `options`: report_dir, fec_root, lda_csv, controls, only (ids or None), run (glassbox.Run)."""
    run = options.get('run')
    stage = (lambda name, summary=None: run and run.stage_start(name, summary))
    done = (lambda name, summary=None, **kw: run and run.stage_finish(name, summary, **kw))
    project_root = Path(project_root)
    threshold = float(registry['thin_base_threshold_usd'])
    specs = [s for s in registry['industries'] if not options.get('only') or s['id'] in options['only']]
    inputs = []

    stage('inputs', 'Reading the CPI and LDA inputs')
    cpi = cpi_reader.read_cpi(options['controls'])
    controls_sha = ms.sha256_file(options['controls'])
    inputs.append({'role': 'cpi', 'path': str(options['controls']), 'sha256': controls_sha})
    lda_path = Path(options['lda_csv'])
    lda_rows = lda_reader.read_sector_rows(lda_path) if lda_path.is_file() else None
    lda_sha = ms.sha256_file(lda_path) if lda_path.is_file() else None
    if lda_sha:
        inputs.append({'role': 'lda', 'path': str(lda_path), 'sha256': lda_sha})
    done('inputs')

    ctx = dict(project_root=project_root, report_dir=options['report_dir'], index_dir=project_root / ms.STATE_INDEX_DIR, hashes={})
    sides, unavailable = {}, {}
    for spec in specs:
        stage('mentat:' + spec['id'], 'Reading the index of ' + spec['mentat_dataset'])
        try:
            sides[spec['id']] = mentat_side(spec, ctx)
            done('mentat:' + spec['id'], status='succeeded')
        except (Unavailable, ValueError, OSError) as error:
            unavailable[spec['id']] = str(error)
            done('mentat:' + spec['id'], str(error), status='failed')
    for ident, side in sides.items():
        inputs.append({'role': 'workbook:' + ident, 'path': str(side['workbook']), 'sha256': side['workbook_sha']})
        inputs.append({'role': 'index:' + ident, 'path': str(side['index_path']), 'sha256': side['manifest']['token']})
        inputs.append({'role': 'source_db:' + ident, 'path': str(side['source']), 'sha256': side['manifest']['provenance']['database_sha256']})

    pac, pac_notes, pac_reason = {}, {}, {}
    by_cycle = {}
    for spec in specs:
        if spec['id'] in sides and spec.get('pac_roster'):
            by_cycle.setdefault(sides[spec['id']]['open_cycle'], []).append(spec)
    for open_cycle, group in by_cycle.items():
        stage('fec:' + str(open_cycle), 'Aggregating the roster PACs\' own giving to candidates')
        try:
            built, notes = build_pac(group, options['fec_root'], open_cycle, sides, threshold)
            pac.update(built)
            pac_notes.update(notes)
            for f in built[group[0]['id']]['inputs']:
                inputs.append({'role': 'fec:' + f['role'], 'path': f['file'], 'sha256': f['sha256']})
            done('fec:' + str(open_cycle))
        except (Unavailable, OSError, ValueError) as error:
            for spec in group:
                pac_reason[spec['id']] = str(error)
            done('fec:' + str(open_cycle), str(error), status='failed')

    stage('assemble', 'Assembling the snapshot')
    all_cycles = sorted({int(cy) for side in sides.values() for cy in side['agg']['cycles']} | {c for side in sides.values() for c in (side['open_cycle'] - 2,)})
    multipliers = cpi_reader.multipliers(cpi, all_cycles)
    industries = {}
    for spec in specs:
        ident = spec['id']
        if ident not in sides:
            continue
        side = sides[ident]
        general, candidates = general_and_candidates(side, threshold)
        if ident in pac:
            pac_block = pac[ident]
        else:
            pac_block = unavailable_pac(pac_reason.get(ident) or 'No roster PAC committees are resolved for this industry')
        lda = build_lda(spec, lda_rows, lda_path, lda_sha)
        cov_flags, flags = industry_flags(spec, side, pac_notes.get(ident), multipliers)
        prov = side['manifest']['provenance']
        industries[ident] = {
            'id': ident, 'label': spec['label'], 'forecast_industry': spec['forecast_industry'],
            'mentat': {'dataset': spec['mentat_dataset'], 'workbook': spec['workbook'], 'workbook_sha256': side['workbook_sha'],
                       'index_token': side['manifest']['token'], 'database_sha256': prov['database_sha256'], 'payload_sha256': prov.get('payload_sha256')},
            'coverage': {'rule': coverage_rule.RULE_TEXT, 'collection_date': side['cov']['collection_date'], 'current_cycle': side['open_cycle'],
                         'rule_coverage_end': side['cov']['rule_coverage_end'], 'coverage_end': side['cov']['coverage_end'],
                         'reason': side['cov']['reason'], 'flags': cov_flags},
            'status': {'general_giving': general['status'], 'candidate_receipts': candidates['status'],
                       'pac_to_candidates': pac_block['status'], 'lda': lda['status']},
            'general_giving': general, 'candidate_receipts': candidates, 'pac_to_candidates': pac_block, 'lda': lda, 'flags': flags}
    snapshot = {
        'schema_version': 1, 'kind': 'giving-anchors', 'built_at_utc': utc_now(),
        'builder': {'name': 'build_giving_anchors', 'version': VERSION, 'code_sha256': code_sha256(), 'python': platform.python_version()},
        'cpi': {'series': cpi_reader.SERIES, 'source_file': Path(options['controls']).name, 'source_sha256': controls_sha,
                'base_year': cpi_reader.BASE_YEAR, 'multipliers': multipliers},
        'thin_base_threshold_usd': threshold, 'industries': industries, 'unavailable': unavailable}
    done('assemble')
    return snapshot, inputs


def merge_with_published(snapshot, published_path, only):
    """A partial build (--industry) replaces only the industries it built: the others keep the anchors of the published snapshot, so one flag
    cannot wipe them. No valid published snapshot means the partial build stands alone."""
    try:
        old = read_json(published_path)
    except (OSError, ValueError):
        return snapshot
    if old.get('schema_version') != 1 or old.get('kind') != 'giving-anchors':
        return snapshot
    industries = {k: v for k, v in old['industries'].items() if k not in only}
    industries.update(snapshot['industries'])
    unavailable = {k: v for k, v in old.get('unavailable', {}).items() if k not in only and k not in industries}
    unavailable.update({k: v for k, v in snapshot['unavailable'].items() if k not in industries})
    return {**snapshot, 'industries': industries, 'unavailable': unavailable}


def validate_snapshot(snapshot):
    problems = contract.validate_kind(snapshot, 'anchors')
    if not problems:
        problems = contract.check_anchor_invariants(snapshot)
    return problems


def replace_atomic(temp, final, attempts=40):
    for attempt in range(attempts):
        try:
            os.replace(temp, final)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.05 + 0.2 * ((attempt * 37) % 10) / 10)


def write_outputs(snapshot, inputs, output_dir, elapsed):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(snapshot, indent=1, ensure_ascii=False, allow_nan=False) + '\n'
    final = output_dir / SNAPSHOT_NAME
    temp = output_dir / (SNAPSHOT_NAME + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_bytes(text.encode('utf-8'))
    replace_atomic(temp, final)
    receipt = {'schema_version': 1, 'snapshot': SNAPSHOT_NAME, 'snapshot_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
               'built_at_utc': snapshot['built_at_utc'], 'elapsed_seconds': round(elapsed, 2), 'builder': snapshot['builder'],
               'industries': {k: {'status': v['status'], 'workbook_sha256': v['mentat']['workbook_sha256'], 'index_token': v['mentat']['index_token'],
                                  'coverage_end': v['coverage']['coverage_end']} for k, v in snapshot['industries'].items()},
               'unavailable': snapshot['unavailable'], 'inputs': inputs}
    rtext = json.dumps(receipt, indent=1, ensure_ascii=False, allow_nan=False) + '\n'
    rtemp = output_dir / (RECEIPT_NAME + '.' + uuid.uuid4().hex + '.tmp')
    rtemp.write_bytes(rtext.encode('utf-8'))
    replace_atomic(rtemp, output_dir / RECEIPT_NAME)
    return final, receipt


def check_fresh(snapshot_path, project_root, report_dir):
    """{industry id: 'fresh' | 'stale' | 'missing'}: the snapshot's workbook sha against the workbook published now."""
    snapshot = read_json(snapshot_path)
    out = {}
    for ident, ind in snapshot['industries'].items():
        workbook = Path(report_dir) / ind['mentat']['workbook']
        out[ident] = 'missing' if not workbook.is_file() else 'fresh' if ms.sha256_file(workbook) == ind['mentat']['workbook_sha256'] else 'stale'
    return out


def run_build(project_root, output_dir=None, only=None, registry_path=None, fec=None, lda_csv=None, controls=None, report_dir=None, run_id=None):
    started = time.time()
    project_root = Path(project_root)
    registry = read_json(registry_path or HERE / 'registry.json')
    output_dir = Path(output_dir) if output_dir else default_output_dir(project_root)
    run = glassbox.Run(run_id or 'giving-anchors-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    run.start('Building the Giving Forecast anchor snapshot', 'project ' + str(project_root))
    try:
        options = dict(report_dir=Path(report_dir) if report_dir else report_directory(project_root), fec_root=fec_root(project_root, fec),
                       lda_csv=lda_csv or default_lda_csv(), controls=Path(controls) if controls else default_controls(project_root), only=only, run=run)
        snapshot, inputs = build_snapshot(project_root, registry, options)
        if only:
            snapshot = merge_with_published(snapshot, output_dir / SNAPSHOT_NAME, only)
        run.stage_start('validate', 'Validating against the shared schema and invariants')
        problems = validate_snapshot(snapshot) if snapshot['industries'] else ['no industry could be anchored: ' + json.dumps(snapshot['unavailable'])]
        if problems:
            run.stage_finish('validate', '; '.join(problems[:3]), status='failed')
            raise ValueError('The anchor snapshot is not valid; the previous snapshot is left in place: ' + '; '.join(problems[:5]))
        run.stage_finish('validate')
        run.stage_start('write', 'Writing the snapshot and its receipt')
        final, receipt = write_outputs(snapshot, inputs, output_dir, time.time() - started)
        run.stage_finish('write', str(final))
        run.finish('Anchor snapshot written: ' + ', '.join(sorted(snapshot['industries'])), json.dumps(snapshot['unavailable']))
        return final, receipt, snapshot
    except Exception as error:
        run.fail('Anchor build failed: ' + type(error).__name__, str(error))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--project-root', type=Path, default=HERE.parents[1], help='the Mentat project folder (<checkout>\\mentat); default: this checkout')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--industry', action='append', help='build only this registry id (repeatable)')
    parser.add_argument('--registry', type=Path)
    parser.add_argument('--fec-root', type=Path, help='default: inputs/active_fec_sources.json')
    parser.add_argument('--lda-csv', type=Path)
    parser.add_argument('--controls', type=Path, help='00_controls.xlsx (CPI)')
    parser.add_argument('--report-directory', type=Path)
    parser.add_argument('--check', action='store_true', help='only report whether the existing snapshot still matches the published workbooks')
    args = parser.parse_args(argv)
    if args.check:
        output_dir = args.output_dir or default_output_dir(args.project_root)
        result = check_fresh(output_dir / SNAPSHOT_NAME, args.project_root, args.report_directory or report_directory(args.project_root))
        print(json.dumps(result, indent=1))
        return 0 if all(v == 'fresh' for v in result.values()) else 2
    try:
        final, receipt, snapshot = run_build(args.project_root, args.output_dir, args.industry, args.registry, args.fec_root, args.lda_csv, args.controls,
                                             args.report_directory)
    except Exception as error:  # the message is the diagnosis; the previous snapshot is untouched
        print('FAILED: ' + str(error), file=sys.stderr)
        return 1
    print('wrote', final, 'sha256', receipt['snapshot_sha256'])
    for ident, ind in snapshot['industries'].items():
        print(' ', ident, 'coverage end', ind['coverage']['coverage_end'], 'status', json.dumps(ind['status']))
    for ident, reason in snapshot['unavailable'].items():
        print('  UNAVAILABLE', ident, '-', reason)
    return 0


if __name__ == '__main__':
    sys.exit(main())
