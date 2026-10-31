"""Review/pin the packaged interpreter closure used by the signature probe.

Only an explicit runtime is read. --check verifies a candidate against the
committed ASAR authority; changing the authority requires an explicit --write.
Site packages are excluded because the fixed probe runs Python with -I -S -B.
"""
import argparse
import hashlib
import json
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / 'client/signature-probe-runtime.json'


def roster(root):
    root = Path(root)
    rows = []
    def walk(directory):
        for item in sorted(directory.iterdir()):
            if item.is_symlink() or getattr(item, 'is_junction', lambda: False)():
                raise ValueError('Interpreter reparse point refused')
            relative = item.relative_to(root).as_posix()
            if item.is_dir():
                if relative != 'Lib/site-packages':
                    walk(item)
            elif item.is_file():
                raw = item.read_bytes()
                rows.append({'path': relative, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
            else:
                raise ValueError('Unsupported interpreter input')
    if root.is_symlink() or getattr(root, 'is_junction', lambda: False)():
        raise ValueError('Interpreter reparse root refused')
    walk(root)
    if not {'python.exe', 'python312.dll', 'Lib/encodings/__init__.py', 'DLLs/_ctypes.pyd'}.issubset({r['path'] for r in rows}):
        raise ValueError('Expected reviewed Python 3.12 layout is absent')
    return sorted(rows, key=lambda row: row['path'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True, choices=('melange', 'mentat', 'terrier'))
    parser.add_argument('--python-root', required=True)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    value = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {'schemaVersion': 1, 'applications': {}}
    rows = roster(args.python_root)
    if args.write:
        value['applications'][args.app] = rows
        OUTPUT.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')
    elif value.get('schemaVersion') != 1 or value.get('applications', {}).get(args.app) != rows:
        raise SystemExit('Signature probe interpreter differs from the reviewed ASAR roster')
    print(json.dumps({'app': args.app, 'files': len(rows), 'bytes': sum(r['bytes'] for r in rows), 'written': args.write}))


if __name__ == '__main__':
    main()
