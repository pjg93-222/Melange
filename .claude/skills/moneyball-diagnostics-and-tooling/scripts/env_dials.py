# -*- coding: utf-8 -*-
"""env_dials.py -- live scan of every environment dial the fec/ code reads
(read-only, stdlib-only; parses source text with regex, never imports fec modules).

Finds os.environ.get(...), os.environ[...], and os.getenv(...) calls in
<root>/fec/*.py and <root>/fec/tests/*.py, and prints each dial with:
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
    scan_dirs = [os.path.join(root, 'fec'), os.path.join(root, 'fec', 'tests')]
    dials = collections.defaultdict(lambda: {'defaults': set(), 'files': set()})
    nfiles = 0
    for d in scan_dirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
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
