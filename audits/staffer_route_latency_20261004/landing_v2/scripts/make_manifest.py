"""Write MANIFEST.txt: file list, LIVE pre-image sha256, expected post-image sha256, terminator profile before and after,
and the drift verdict of the post-image against the branch tip's file (live_patch.py drift)."""
import difflib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANDING = os.path.dirname(HERE)
LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
WT = r'C:/Users/pgoff/Melange-wt/route-jobs'
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402

summary = json.load(open(os.path.join(LANDING, 'route_latency.summary.json'), encoding='utf-8'))
patch = open(os.path.join(LANDING, 'route_latency.patch'), 'rb').read()
tool = os.path.join(LIVE, 'fec', 'tools', 'live_patch.py')
env = dict(os.environ, PYTHONIOENCODING='utf-8', GIT_OPTIONAL_LOCKS='0')


def git(*args):
    return subprocess.run(['git', *args], cwd=WT, env=env, capture_output=True).stdout


lines = ['# route_latency patch set: manifest',
         '',
         'base (LIVE main)  %s' % summary['base'],
         'branch tip        %s  (claude/staffer-route-latency-20261002)' % summary['tip'],
         'patch             route_latency.patch  %d bytes  sha256 %s' % (len(patch), summary['patch_sha256']),
         'files             %d: %d edited in place, %d new' % (len(summary['files']),
                                                              sum(f['kind'] == 'edit' for f in summary['files']),
                                                              sum(f['kind'] == 'new' for f in summary['files'])),
         '',
         'Terminator profiles are live_patch.py `eol` lines (crlf = CRLF-terminated lines, lf = bare-LF lines).',
         'verdict = `live_patch.py drift <post-image> <branch tip file>`: IDENTICAL_BYTES, or EOL_ONLY where LIVE keeps its own terminators.',
         '']
for item in summary['files']:
    rel = item['file']
    post = os.path.join(LANDING, 'post_images', *rel.split('/'))
    done = subprocess.run([sys.executable, tool, 'drift', post, os.path.join(WT, *rel.split('/'))], capture_output=True, env=env)
    verdict = done.stdout.decode('utf-8', 'replace').strip().splitlines()[-1].split()[-1]
    post_bytes = open(post, 'rb').read()
    changed = ''
    if item['kind'] == 'edit':
        pre_bytes = open(os.path.join(LANDING, 'pre_images', *rel.split('/')), 'rb').read()
        before, after = lp.split_lines(pre_bytes), lp.split_lines(post_bytes)
        sm = difflib.SequenceMatcher(None, before, after, autojunk=False)
        removed = sum(i2 - i1 for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag in ('replace', 'delete'))
        added = sum(j2 - j1 for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag in ('replace', 'insert'))
        changed = '+%d / -%d lines' % (added, removed)
    else:
        changed = '+%d lines (new file)' % len(lp.split_lines(post_bytes))
    lines += ['%s  %s' % ('EDIT' if item['kind'] == 'edit' else 'NEW ', rel),
              '    LIVE pre-image  sha256 %s' % (item['live_pre_sha256'] or '(does not exist)'),
              '    post-image      sha256 %s' % item['post_sha256'],
              '    profile before  %s' % (item['live_pre_eol'] or '-'),
              '    profile after   %s' % item['post_eol'],
              '    change          %s   verdict vs branch tip: %s' % (changed, verdict),
              '']
open(os.path.join(LANDING, 'MANIFEST.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('\n'.join(lines[:12]))
print('... %d lines written' % len(lines))
