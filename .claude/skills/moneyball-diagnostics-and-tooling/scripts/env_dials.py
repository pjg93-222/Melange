# -*- coding: utf-8 -*-
"""env_dials.py -- live scan of every environment dial the fec/ code reads
(read-only, stdlib-only; parses source text with regex, never imports fec modules).

Finds os.environ.get(...), os.environ[...], and os.getenv(...) calls in every
.py file under <root>/fec/, recursively (skipping __pycache__, hidden directories
and fec/attic), and prints each dial with:
  - its in-code default (as written at the call site; '(expr)' when not a literal)
  - the files that read it
  - whether it is CURRENTLY SET in this shell's environment (dials silently
    change engine behavior -- the ratified state is ALL DIALS UNSET)

The curated, annotated dial catalog lives in the moneyball-config-and-flags skill;
this script is the drift detector -- run it to find dials added since that catalog
was written, or to prove your shell is clean before a baseline run.

Usage:
  python env_dials.py "<root>"     # root containing fec/ (worktree or live tree)
"""
import os, re, sys, collections
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PATTERNS = [
    re.compile(r"""os\.environ\.get\(\s*['"](?P<name>[A-Z][A-Z0-9_]*)['"]\s*(?:,\s*(?P<dflt>[^)]*))?\)"""),
    re.compile(r"""os\.environ\[\s*['"](?P<name>[A-Z][A-Z0-9_]*)['"]\s*\]"""),
    re.compile(r"""os\.getenv\(\s*['"](?P<name>[A-Z][A-Z0-9_]*)['"]\s*(?:,\s*(?P<dflt>[^)]*))?\)"""),
]
# OS/platform variables some fec/ code reads (profile, temp and app-data paths). Windows always
# sets them and they are not Moneyball dials, so they never count against a clean shell.
PLATFORM = {'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP', 'USERPROFILE', 'HOME', 'PATH',
            'USERNAME', 'COMPUTERNAME', 'PROGRAMDATA', 'SYSTEMROOT', 'WINDIR'}

def clean_default(raw):
    if raw is None:
        return '(required/None)'
    raw = raw.strip()
    m = re.match(r"""^['"](.*)['"]$""", raw)
    if m:
        return repr(m.group(1))
    if re.match(r'^-?[0-9.]+$', raw):
        return raw
    return '(expr: %s)' % (raw[:40] + ('...' if len(raw) > 40 else ''))

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    root = sys.argv[1]
    fec = os.path.join(root, 'fec')
    dials = collections.defaultdict(lambda: {'defaults': set(), 'files': set()})
    nfiles = 0
    # Recursive (2026-09-30): the engines live in fec/<domain>/ subdirectories, so the old
    # top-level-only scan missed FRONTIER_OUT, OPT_OUT, SEED, MC, TOPIC and most other dials.
    for d, subdirs, fns in os.walk(fec):
        subdirs[:] = sorted(s for s in subdirs if s != '__pycache__' and not s.startswith('.')
                            and not (d == fec and s == 'attic'))
        for fn in sorted(fns):
            if not fn.endswith('.py'):
                continue
            path = os.path.join(d, fn)
            if not os.path.isfile(path):
                continue
            nfiles += 1
            try:
                src = open(path, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            for pat in PATTERNS:
                for m in pat.finditer(src):
                    name = m.group('name')
                    dflt = clean_default(m.groupdict().get('dflt'))
                    dials[name]['defaults'].add(dflt)
                    dials[name]['files'].add(fn)
    print('scanned %d files under %s' % (nfiles, os.path.join(root, 'fec')))
    print('%d distinct env dials found:\n' % len(dials))
    set_now = []
    for name in sorted(dials):
        d = dials[name]
        cur = os.environ.get(name)
        if cur is not None and name in PLATFORM:
            flag = '  (platform variable, set by the OS -- not a dial)'
        else:
            flag = '  <== SET NOW: %r' % cur if cur is not None else ''
            if cur is not None:
                set_now.append(name)
        defaults = ' | '.join(sorted(d['defaults']))
        files = ','.join(sorted(d['files'])[:4]) + ('...' if len(d['files']) > 4 else '')
        print('%-16s default %-28s %s%s' % (name, defaults, files, flag))
    if set_now:
        print('\nWARNING: %d dial(s) set in this shell: %s' % (len(set_now), ', '.join(set_now)))
        print('Defaults ARE the ratified state -- unset these before baselines/audits '
              '(MONEYBALL_ROOT excepted when deliberately re-rooting).')
    else:
        print('\nshell clean: no dial set -- defaults (the ratified state) apply.')

if __name__ == '__main__':
    main()
