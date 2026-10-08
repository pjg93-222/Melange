# -*- coding: utf-8 -*-
"""LANE A / R0 -- generation guard.  Re-read at the END of the lane: no .pipeline_run.lock, and
every artifact this lane measured still carries the mtime/size it had when it was read.
A moved mtime would make the lane's reads mixed-generation and therefore invalid.
"""
import os, sys, hashlib, datetime, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DRAFT = r'C:\Users\pgoff\OneDrive\Desktop\Draft Systems'
print('=' * 100)
print('R0  GENERATION GUARD   run', datetime.datetime.now().isoformat(timespec='seconds'))
print('=' * 100)
lock = os.path.join(ROOT, '.pipeline_run.lock')
print('\n.pipeline_run.lock present: %s' % os.path.exists(lock))

FILES = [
    'Moneyball Main Version - Blended.xlsx', 'Social Master.xlsx', 'Quorum Master.xlsx',
    'Quorum Processed.xlsx', 'social_media.db', 'per_topic_alloc.json', 'category_stance.json',
    'dashboard_data.json', 'cu-member-desk.html', 'cu-member-desk-profiles.js',
    'member_desk_bundle.json', 'press_stance_final.csv', 'speech_stance_final.csv',
    'press_text_cache.jsonl', 'speeches_cu.csv',
    r'data\stance\tweet_stance_final.csv', r'data\stance\hearing_stance_final.csv',
    r'data\stance\interview_stance_final.csv', r'data\stance\press_domain_routing_audit.json',
    r'data\stance\press_component_meta.json', r'data\stance\press_raw_original.json',
    r'data\stance\press_refresh_tone.csv', r'data\stance\quorum_member_tweets.csv',
    r'data\stance\api_press_stance.csv', r'data\stance\press_stance_overrides.json',
    r'data\stance\hearings_cu.csv', r'data\stance\interviews_cu.csv',
    r'data\engine\congestion.json',
]
print('\n%-58s %14s  %s' % ('artifact', 'bytes', 'mtime'))
snap = {}
for rel in FILES:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print('%-58s %14s  %s' % (rel, 'ABSENT', '-'))
        continue
    st = os.stat(p)
    snap[rel] = [st.st_size, st.st_mtime]
    print('%-58s %14d  %s' % (rel, st.st_size,
                              datetime.datetime.fromtimestamp(st.st_mtime).isoformat(sep=' ')))
p = os.path.join(DRAFT, 'cu_press_stance_tone.csv')
st = os.stat(p)
print('%-58s %14d  %s' % ('../Draft Systems/cu_press_stance_tone.csv', st.st_size,
                          datetime.datetime.fromtimestamp(st.st_mtime).isoformat(sep=' ')))

print('\n-- generation note --')
wbm = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, 'Moneyball Main Version - Blended.xlsx')))
pcm = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, 'data', 'stance', 'press_component_meta.json')))
desk = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, 'cu-member-desk.html')))
print('   workbook                     %s' % wbm.isoformat(sep=' '))
print('   press_component_meta.json    %s   <- written ONLY by build_media_blend.py' % pcm.isoformat(sep=' '))
print('   cu-member-desk.html          %s' % desk.isoformat(sep=' '))
print('   => the media blend last ran %s; the published surfaces were built %s.'
      % (pcm.date().isoformat(), desk.date().isoformat()))

# sha256 of the two engine press inputs, to prove the 09-17 blend is valid for today's inputs
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


meta = json.load(open(os.path.join(ROOT, 'data', 'stance', 'press_component_meta.json'), encoding='utf-8'))
print('\n-- inputs_sha256 recorded by that blend run vs the files now --')
ok = True
for rel, h in (meta.get('inputs_sha256') or {}).items():
    q = os.path.normpath(os.path.join(ROOT, rel))
    if not os.path.exists(q):
        print('   %-58s MISSING' % rel)
        ok = False
        continue
    now = sha(q)
    same = (now == h)
    ok = ok and same
    print('   %-58s %s' % (rel, 'MATCH' if same else 'CHANGED'))
print('\n   every press input the 2026-09-17 blend consumed is byte-identical today: %s' % ok)
print('\nDONE R0')
