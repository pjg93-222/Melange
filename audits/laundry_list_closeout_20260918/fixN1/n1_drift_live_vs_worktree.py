# -*- coding: utf-8 -*-
"""LIVE vs WORKTREE drift, line-ending/BOM normalised, byte-safe (no text-mode pipe)."""
import hashlib, io, os, sys, difflib
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
WT   = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\unfinished-work-handoff-a3bbad'
RELS = [r'fec\press_stream.py', r'fec\surfaces\make_member_desk.py', r'fec\stance\media_rules.py',
        r'fec\tests\run_tests.py', r'fec\audit\audit_full.py', r'fec\audit\dashboard_integrity.py',
        r'MATHEMATICAL_SPECIFICATION.md',
        r'.claude\skills\moneyball-config-and-flags\SKILL.md',
        r'fec\surfaces\desk_press_source.py',
        r'fec\tests\surfaces\test_desk_press_source.py']
def norm(b):
    if b.startswith(b'\xef\xbb\xbf'): b = b[3:]
    return b.replace(b'\r\n', b'\n')
for rel in RELS:
    a, b = os.path.join(LIVE, rel), os.path.join(WT, rel)
    ea, eb = os.path.isfile(a), os.path.isfile(b)
    if not ea or not eb:
        print('%-62s LIVE=%s WORKTREE=%s' % (rel, ea, eb)); continue
    ba, bb = open(a,'rb').read(), open(b,'rb').read()
    na, nb = norm(ba), norm(bb)
    same = na == nb
    print('%-62s %s  raw %d/%d bytes  crlf_live=%s crlf_wt=%s' % (
        rel, 'IDENTICAL(norm)' if same else 'DRIFTED', len(ba), len(bb),
        b'\r\n' in ba, b'\r\n' in bb))
    if not same:
        la = na.decode('utf-8','replace').splitlines()
        lb = nb.decode('utf-8','replace').splitlines()
        d = list(difflib.unified_diff(la, lb, 'LIVE', 'WT', lineterm='', n=0))
        changed = sum(1 for x in d if x[:1] in '+-' and x[:3] not in ('+++','---'))
        print('    normalised diff lines: %d   (hunks: %d)' % (changed, sum(1 for x in d if x.startswith('@@'))))
        for x in d[:40]: print('    ' + x[:170])
