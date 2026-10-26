"""Copy an isolated Windows CPython environment into a private application runtime.

The interpreter, standard library, native extensions and package license files
stay together. This is a development build step, not a redistribution approval.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

# LAUNCH F3: pip, setuptools and venv launcher stubs. They run only when pip installs a console script or venv builds
# an environment; the desktop does neither, so they would ship as dormant executables. Matched by their folder, never
# by name alone, so no other package's executable is dropped. venvlauncher names are unambiguous in any folder.
_DORMANT = (
    (('pip', '_vendor', 'distlib'), {'t32.exe', 't64.exe', 't64-arm.exe', 'w32.exe', 'w64.exe', 'w64-arm.exe'}),
    (('setuptools',), {'cli.exe', 'cli-32.exe', 'cli-64.exe', 'cli-arm64.exe', 'gui.exe', 'gui-32.exe', 'gui-64.exe', 'gui-arm64.exe'}),
    (('venv', 'scripts', 'nt'), {'python.exe', 'pythonw.exe'}),
    ((), {'venvlauncher.exe', 'venvwlauncher.exe'}),
)


def dormant_launchers(directory, names):
    """shutil.copytree ignore callable: the dormant launcher executables in this directory."""
    parts = tuple(part.lower() for part in Path(directory).parts)
    return {name for name in names for folder, files in _DORMANT
            if parts[len(parts) - len(folder):] == folder and name.lower() in files}


def _ignore(*patterns):
    base = shutil.ignore_patterns(*patterns)
    return lambda directory, names: set(base(directory, names)) | dormant_launchers(directory, names)


def bundle_python(destination):
    if os.name != 'nt' or sys.version_info[:2] != (3, 12):
        raise RuntimeError('This native builder requires Windows CPython 3.12')
    base, environment = Path(sys.base_prefix), Path(sys.prefix)
    configuration = environment / 'pyvenv.cfg'
    if base == environment or not configuration.is_file() or 'include-system-site-packages = false' not in configuration.read_text(encoding='utf-8').lower():
        raise RuntimeError('Use a dedicated virtual environment without global site packages')
    destination = Path(destination)
    destination.mkdir(parents=True)
    for name in ('python.exe', 'python3.dll', 'python312.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'LICENSE.txt'):
        source = base / name
        if not source.is_file():
            raise RuntimeError('Required CPython distribution file missing: ' + name)
        shutil.copy2(source, destination / name)
    ignore = _ignore('__pycache__', '*.pyc', 'test', 'tests', 'idlelib', 'ensurepip', 'site-packages')
    shutil.copytree(base / 'Lib', destination / 'Lib', ignore=ignore)
    shutil.copytree(base / 'DLLs', destination / 'DLLs', ignore=shutil.ignore_patterns('_test*', '*.pdb'))
    shutil.copytree(environment / 'Lib' / 'site-packages', destination / 'Lib' / 'site-packages',
                    ignore=_ignore('__pycache__', '*.pyc', 'tests', 'test'))
    # Launchers use -E -s, and child jobs inherit PYTHONNOUSERSITE=1. This flag is
    # defense in depth; sitecustomize alone does not remove an already-added path.
    # Do not use an embeddable ._pth file: the existing tools require ordinary
    # script-directory and -c semantics when they launch their own interpreter.
    custom = destination / 'Lib' / 'site-packages' / 'sitecustomize.py'
    custom.write_text('import site\nsite.ENABLE_USER_SITE = False\n', encoding='utf-8')
    # pyvenv.cfg is deliberately absent: paths resolve from this private Python.
    clean = {key: value for key, value in os.environ.items() if not key.upper().startswith('PYTHON')}
    clean['PYTHONNOUSERSITE'] = '1'
    result = subprocess.run([str(destination / 'python.exe'), '-s', '-c',
                             'import json,sys;print(json.dumps({"prefix":sys.prefix,"executable":sys.executable}))'],
                            env=clean, capture_output=True, text=True, timeout=30, check=True)
    import json
    facts = json.loads(result.stdout)
    if Path(facts['prefix']).resolve() != destination.resolve():
        raise RuntimeError('Bundled Python resolved outside its own installation')
    return facts
