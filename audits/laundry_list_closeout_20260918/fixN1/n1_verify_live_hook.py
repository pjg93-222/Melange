# -*- coding: utf-8 -*-
"""Prove the LIVE hook lands the SAME change as the worktree edit.

Re-derives the patched LIVE content with the cutter's own OPS, then diffs it against the
worktree file.  Every remaining difference must be a hunk this branch already committed
(A5 / N2 / N4 / reference filters) -- never one of N1a's own lines.
"""
import difflib, importlib.util, io, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('cut', os.path.join(HERE, 'cut_patch.py'))
cut = importlib.util.module_from_spec(spec)
sys.argv = ['cut_patch.py', '--probe']
try:
    spec.loader.exec_module(cut)
except SystemExit:
    pass
WT = cut.WT
N1A_MARKERS = ('N1a', 'DESK_PRESS_SOURCE', 'desk_press_source', '_press_rows',
               '_press_source_ledger', 'press_stream:BASE_TONE_PATH',
               'press_refresh_tone.csv', 'test_desk_press_source')
for rel in (cut.DESK, cut.INTEG, cut.RUNNER, cut.SPEC, cut.SKILL):
    patched = [ln.rstrip('\r\n') for ln in cut.edited[rel]]
    worktree = [ln.rstrip('\r\n') for ln in cut.split(cut.read(os.path.join(WT, rel)))]
    diff = [d for d in difflib.unified_diff(patched, worktree, 'patched-LIVE', 'WORKTREE',
                                            lineterm='', n=0)
            if d[:1] in '+-' and d[:3] not in ('+++', '---')]
    leaked = [d for d in diff if any(m in d for m in N1A_MARKERS)]
    print('%-46s residual diff lines %3d   N1a lines in the residual: %d %s'
          % (os.path.basename(rel), len(diff), len(leaked),
             'OK' if not leaked else 'MISMATCH'))
    for d in leaked[:8]:
        print('     LEAK %s' % d[:150])
for rel in cut.NEW_FILES:
    print('%-46s new file, patch body read straight from the worktree' % os.path.basename(rel))
