"""Re-hash the reviewed program path list after changing packaged source code.

This does not discover files or expand authority from downloaded metadata. New
imports must be explicitly added to ADDITIONS and reviewed before packaging.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ADDITIONS = {'melange': ('fec/surfaces/melange_public_pages.py', 'fec/surfaces/demand_data.py')}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def outputs(applications=('melange', 'mentat')):
    existing = runpy.run_path(str(HERE / 'module_application_inventory.py'))['APPLICATION_SPECS']
    specs = {}
    for app, original in existing.items():
        spec = {key: list(value) if isinstance(value, tuple) else value for key, value in original.items()}
        if app not in applications:
            spec['programFiles'] = [dict(item) for item in spec['programFiles']]
            specs[app] = spec
            continue
        paths = {(item['root'], item['path']) for item in original['programFiles']}
        paths.update(('source', name) for name in ADDITIONS.get(app, ()))
        files = []
        for area, name in sorted(paths):
            file = (HERE if area == 'bootstrap' else ROOT) / name
            if file.is_symlink() or not file.is_file():
                raise ValueError(f'Reviewed program input is unavailable: {file}')
            raw = file.read_bytes()
            files.append({'root': area, 'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        spec['programFiles'] = files
        spec['programFingerprint'] = hashlib.sha256(encoded(files)).hexdigest()
        specs[app] = spec
    lines = ['"""Literal installed-program declarations. No data, factories or downloaded selectors."""',
             'from types import MappingProxyType', '', 'APPLICATION_SPECS = MappingProxyType({']
    for app, spec in specs.items():
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
        'module.exports=Object.freeze({APPLICATION_SPECS});\n')
    return {HERE / 'module_application_inventory.py': '\n'.join(lines),
            HERE.parent / 'client/module-application-inventory.cjs': javascript}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Update both literal inventories after review')
    parser.add_argument('--app', choices=('melange', 'mentat'), action='append',
                        help='Hash only this app; retain the other app declaration in split repositories')
    options = parser.parse_args()
    changed = []
    for file, value in outputs(options.app or ('melange', 'mentat')).items():
        if file.read_bytes() != value.encode('utf-8'):
            changed.append(str(file))
            if options.write: file.write_text(value, encoding='utf-8', newline='\n')
    if changed and not options.write:
        raise SystemExit('Program inventory drift: ' + ', '.join(changed))
    print(json.dumps({'updated' if options.write else 'verified': changed}))


if __name__ == '__main__': main()
