# -*- coding: utf-8 -*-
"""LANE B final integrity check: no lock appeared, no input/artifact mtime moved during the run,
and the cache's only datable evidence (no per-row timestamps exist)."""
import datetime, io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
WT = LIVE + r'\.claude\worktrees\unfinished-work-handoff-a3bbad'
print('=== .pipeline_run.lock at LIVE root? ===')
lk = os.path.join(LIVE, '.pipeline_run.lock')
print('%s : %s' % (lk, 'PRESENT -> STOP' if os.path.exists(lk) else 'ABSENT'))
print()
print('=== mtime / ctime of every file this lane read or reported on ===')
paths = [
    LIVE + r'\member_references.json',
    LIVE + r'\data\members\member_reference_cache_fable.jsonl',
    LIVE + r'\data\members\member_reference_cache_baseline_v2.json',
    LIVE + r'\data\members\member_reference_classification_receipt.json',
    LIVE + r'\data\members\member_reference_verify.csv',
    LIVE + r'\social_media.db',
    LIVE + r'\Quorum Processed.xlsx',
    LIVE + r'\data\engine\congestion.json',
    LIVE + r'\data\engine\sentinel_admission_policy.json',
    LIVE + r'\data\press\official_mentions.jsonl',
    LIVE + r'\data\stance\press_refresh_tone.csv',
    LIVE + r'\data\stance\press_refresh_feed_receipt.json',
    os.path.abspath(os.path.join(LIVE, os.pardir, 'Draft Systems', 'cu_press_stance_tone.csv')),
    LIVE + r'\fec\members\member_reference_layer.py',
    LIVE + r'\fec\members\reference_cache.py',
    LIVE + r'\fec\press_stream.py',
    WT + r'\fec\members\member_reference_layer.py',
    WT + r'\fec\stance\resolve_attribution_domain.py',
    WT + r'\fec\surfaces\build_dashboard_bundle.py',
    WT + r'\fec\surfaces\make_member_desk.py',
]
print('%-58s %-19s %-19s %s' % ('file', 'mtime', 'ctime(created)', 'bytes'))
for p in paths:
    if not os.path.exists(p):
        print('%-58s MISSING' % os.path.basename(p)); continue
    st = os.stat(p)
    print('%-58s %-19s %-19s %d' % (os.path.basename(p)[:58],
                                    datetime.datetime.fromtimestamp(st.st_mtime).isoformat(sep=' ')[:19],
                                    datetime.datetime.fromtimestamp(st.st_ctime).isoformat(sep=' ')[:19],
                                    st.st_size))
print()
print('=== cache datability ===')
CACHE = LIVE + r'\data\members\member_reference_cache_fable.jsonl'
st = os.stat(CACHE)
print('cache file created : %s' % datetime.datetime.fromtimestamp(st.st_ctime).isoformat(sep=' ')[:19])
print('cache file modified: %s' % datetime.datetime.fromtimestamp(st.st_mtime).isoformat(sep=' ')[:19])
print('per-row timestamp fields: NONE (fields are k/out/model/transport/classifier; see 01 receipt)')
print('-> CACHE DATE RANGE PER ROW = UNKNOWN; only file ctime/mtime bound it.')
print()
print('=== worktree cleanliness (git status --porcelain, read-only command) ===')
print('(run separately in PowerShell; see 07_integrity.out.txt tail)')
print('DONE 07')
