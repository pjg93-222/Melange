# -*- coding: utf-8 -*-
"""FIX R1: proof that 12_predict_from_laneB_refs.py measures TODAY's inputs.

12_ consumes lane B's re-derived mention list (scratchpad/laneB/refs.jsonl, written 2026-09-18
23:40:48) instead of re-scanning the databases, because several other lanes were saturating the
box. That is only legitimate if none of the layer's inputs has moved since. This prints the
mtime of every input the extraction reads, against refs.jsonl's own mtime.

READ-ONLY: stats files, reads nothing."""
import datetime, io, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DRAFT = r'C:\Users\pgoff\OneDrive\Desktop\Draft Systems'
REFS = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
        r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
        r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB\refs.jsonl')

INPUTS = [
    (LIVE, r'social_media.db', 'speeches pass (CREC / INTERVIEW / CHRG) + the twitter handle map'),
    (LIVE, r'Quorum Processed.xlsx', 'X mention pass'),
    (DRAFT, r'cu_press_stance_tone.csv', 'PRESS pass, historical tone rows'),
    (LIVE, r'data\stance\press_refresh_tone.csv', 'PRESS pass, refresh tone rows'),
    (LIVE, r'data\press\official_mentions.jsonl', 'PRESS_OFFICIAL_MENTION pass'),
    (LIVE, r'data\engine\congestion.json', 'roster + chamber pools + the roster surname pool'),
    (LIVE, r'data\members\member_reference_cache_fable.jsonl', 'label cache (drives n_scored)'),
    (LIVE, r'data\members\member_reference_cache_baseline_v2.json', 'legacy label bindings'),
    (LIVE, r'member_references.json', 'the shipped artifact the parity check compares against'),
]


def stamp(t): return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')


cut = os.path.getmtime(REFS)
print('laneB/refs.jsonl (53,011 mentions) written : %s' % stamp(cut))
print('%-54s %-21s %s' % ('input', 'mtime', 'verdict'))
newer = missing = 0
for root, rel, why in INPUTS:
    p = os.path.join(root, rel)
    if not os.path.exists(p):
        print('%-54s %-21s MISSING' % (rel, '-')); missing += 1; continue
    m = os.path.getmtime(p)
    late = m > cut
    newer += late
    print('%-54s %-21s %s   [%s]' % (rel, stamp(m), 'NEWER -- refs.jsonl IS STALE' if late else 'older, unchanged', why))
print()
print('inputs newer than refs.jsonl : %d   missing: %d' % (newer, missing))
print('VERDICT: %s' % ('refs.jsonl is CURRENT for every input the extraction reads'
                       if not newer and not missing else 'STALE -- re-run 02c/10 before trusting 12'))
print('DONE 14')
