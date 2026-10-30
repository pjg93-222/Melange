"""Re-hash the reviewed program path list after changing packaged source code.

This does not discover files or expand authority from downloaded metadata. New
imports must be explicitly added to ADDITIONS or BOOTSTRAP_ADDITIONS and reviewed
before packaging. Bootstrap-only refreshes retain the previously reviewed source
descriptors without inspecting a different source checkout in a split repository.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ADDITIONS = {'melange': ('fec/surfaces/melange_public_pages.py', 'fec/surfaces/demand_data.py',
                         'fec/surfaces/staffer_live_generation.py')}
WORKSPACE_BOOTSTRAP = ('desktop_workspace.py', 'workspace_data_contract.py', 'module_workspace_handoff.py',
    'workspace_archive.py', 'workspace_sqlite.py', 'workspace_graph.py', 'workspace_cache.py',
    'module_workspace_inputs.py', 'workspace_melange.py', 'workspace_mentat.py', 'module_workspace_installers.py',
    'module_workspace_render.py', 'module_workspace_ui_templates.py',
    'module_workspace_combined_ui.py', 'module_workspace_industry_ui.py')
BOOTSTRAP_ADDITIONS = {'melange': ('terrier_standalone.py', 'desktop_credentials.py', 'terrier_github_snapshot.py', 'module_catalogue_cache.py', *WORKSPACE_BOOTSTRAP),
                       'mentat': ('terrier_standalone.py', 'desktop_credentials.py', 'terrier_github_snapshot.py', *WORKSPACE_BOOTSTRAP)}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def district_specs(existing):
    """Retain reviewed Geo source rows; refresh the explicit build helper list."""
    if not existing:
        return {}
    if set(existing) != {'terrier'}:
        raise ValueError('Unsupported district program declaration')
    tree = ast.parse((HERE / 'build_runtime.py').read_text(encoding='utf-8'))
    declarations = [node.value for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'BOOTSTRAP_FILES'
                            for target in node.targets)]
    if len(declarations) != 1:
        raise ValueError('Explicit bootstrap roster is unavailable')
    helpers = ast.literal_eval(declarations[0])
    if (not isinstance(helpers, (tuple, list)) or not helpers
            or len(set(helpers)) != len(helpers)
            or any(type(name) is not str or Path(name).name != name for name in helpers)):
        raise ValueError('Invalid explicit bootstrap roster')
    original = existing['terrier']
    if set(original) != {'schemaVersion', 'appId', 'programFiles', 'programFingerprint'} or original['schemaVersion'] != 1 or original['appId'] != 'terrier':
        raise ValueError('Invalid district program declaration')
    # This literal is the existing sole recursive trust-anchor exclusion.
    files = [dict(row) for row in original['programFiles'] if row['root'] == 'source']
    if not files:
        raise ValueError('Reviewed district source descriptors are unavailable')
    for name in helpers:
        if name == 'module_application_inventory.py':
            continue
        file = HERE / name
        if file.is_symlink() or not file.is_file():
            raise ValueError('Reviewed district helper is unavailable')
        raw = file.read_bytes()
        files.append({'root': 'bootstrap', 'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    files.sort(key=lambda row: (row['root'], row['path']))
    return {'terrier': {'schemaVersion': 1, 'appId': 'terrier', 'programFiles': files,
                        'programFingerprint': hashlib.sha256(encoded(files)).hexdigest()}}


def outputs(applications=('melange', 'mentat'), *, bootstrap_only=False):
    inventory = runpy.run_path(str(HERE / 'module_application_inventory.py'))
    existing = inventory['APPLICATION_SPECS']
    districts = district_specs(inventory.get('DISTRICT_PROGRAM_SPECS', {}))
    specs = {}
    for app, original in existing.items():
        spec = {key: list(value) if isinstance(value, tuple) else value for key, value in original.items()}
        if app not in applications:
            spec['programFiles'] = [dict(item) for item in spec['programFiles']]
            specs[app] = spec
            continue
        previous = {(item['root'], item['path']): item for item in original['programFiles']}
        paths = set(previous)
        paths.update(('bootstrap', name) for name in BOOTSTRAP_ADDITIONS.get(app, ()))
        if not bootstrap_only:
            paths.update(('source', name) for name in ADDITIONS.get(app, ()))
        files = []
        for area, name in sorted(paths):
            if bootstrap_only and area == 'source':
                files.append(dict(previous[(area, name)]))
                continue
            file = (HERE if area == 'bootstrap' else ROOT) / name
            if file.is_symlink() or not file.is_file():
                raise ValueError(f'Reviewed program input is unavailable: {file}')
            raw = file.read_bytes()
            files.append({'root': area, 'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        spec['programFiles'] = files
        spec['programFingerprint'] = hashlib.sha256(encoded(files)).hexdigest()
        specs[app] = spec
    from workspace_data_contract import WORKSPACE_KINDS, WORKSPACE_READERS, WORKSPACE_PRIVATE_BOUNDARIES
    # Both paired contracts pin the same reviewed union. An extra workspace
    # source/helper must be added to that union, never omitted to fake equality.
    workspaces = {app: {**spec, 'contractId': app + '.workspace.v1',
        'requiredKinds': WORKSPACE_KINDS[app], 'publicReaders': WORKSPACE_READERS[app],
        'privateBoundaries': WORKSPACE_PRIVATE_BOUNDARIES[app]} for app, spec in specs.items()}
    lines = ['"""Literal installed-program declarations. No data, factories or downloaded selectors."""',
             'from types import MappingProxyType', '']
    for name, table in (('APPLICATION_SPECS', specs), ('WORKSPACE_APPLICATION_SPECS', workspaces), ('DISTRICT_PROGRAM_SPECS', districts)):
        lines.append(name + ' = MappingProxyType({')
        for app, spec in table.items():
            lines.append(f'    {app!r}: MappingProxyType({{')
            for key, value in spec.items():
                if key == 'programFiles':
                    lines.append("        'programFiles': (")
                    lines.extend(f'            MappingProxyType({row!r}),' for row in value)
                    lines.append('        ),')
                else:
                    if isinstance(value, list): value = tuple(value)
                    lines.append(f'        {key!r}: {value!r},')
            lines.append('    }),')
        lines.extend(['})', ''])
    javascript = ("'use strict';\n// Compiled, reviewed program identities; never loaded from data or settings.\n"
        "// This literal declaration is the sole recursive native table exclusion.\n"
        "function freeze(value){if(value&&typeof value==='object'){for(const child of Object.values(value))freeze(child);Object.freeze(value);}return value;}\n"
        'const APPLICATION_SPECS=freeze(' + json.dumps(specs, indent=2, ensure_ascii=False) + ');\n'
        'const WORKSPACE_APPLICATION_SPECS=freeze(' + json.dumps(workspaces, indent=2, ensure_ascii=False) + ');\n'
        'const DISTRICT_PROGRAM_SPECS=freeze(' + json.dumps(districts, indent=2, ensure_ascii=False) + ');\n'
        'module.exports=Object.freeze({APPLICATION_SPECS,WORKSPACE_APPLICATION_SPECS,DISTRICT_PROGRAM_SPECS});\n')
    return {HERE / 'module_application_inventory.py': '\n'.join(lines),
            HERE.parent / 'client/module-application-inventory.cjs': javascript}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Update both literal inventories after review')
    parser.add_argument('--bootstrap-only', action='store_true',
                        help='Rehash reviewed bootstrap files; retain source descriptors without reading source files')
    parser.add_argument('--app', choices=('melange', 'mentat'), action='append',
                        help='Hash only this app; retain the other app declaration in split repositories')
    options = parser.parse_args()
    changed = []
    for file, value in outputs(options.app or ('melange', 'mentat'), bootstrap_only=options.bootstrap_only).items():
        if file.read_bytes() != value.encode('utf-8'):
            changed.append(str(file))
            if options.write: file.write_text(value, encoding='utf-8', newline='\n')
    if changed and not options.write:
        raise SystemExit('Program inventory drift: ' + ', '.join(changed))
    print(json.dumps({'updated' if options.write else 'verified': changed}))


if __name__ == '__main__': main()
