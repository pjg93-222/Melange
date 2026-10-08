"""Write MANIFEST.txt: file list, pre-image sha256 (with where those bytes come from), expected post-image sha256, terminator profile before and after,
and the drift verdict of the post-image against the branch tip's file (live_patch.py drift)."""
import difflib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANDING = os.path.dirname(HERE)
LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
WT = r'C:/Users/pgoff/Melange-wt/route-search'
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402

NAME = 'ids_followup'
summary = json.load(open(os.path.join(LANDING, NAME + '.summary.json'), encoding='utf-8'))
patch = open(os.path.join(LANDING, NAME + '.patch'), 'rb').read()
tool = os.path.join(LIVE, 'fec', 'tools', 'live_patch.py')
env = dict(os.environ, PYTHONIOENCODING='utf-8', GIT_OPTIONAL_LOCKS='0')

lines = ['# ids_followup patch: manifest (landing_v3_ids)',
         '',
         'requires          landing_v2 applied to LIVE first (route_latency.patch, branch tip %s)' % summary['base'],
         'LIVE main         %s  (the base landing_v2 was cut against; unchanged at this cut)' % summary['live_head'],
         'branch tip        %s  (claude/staffer-search-ids-followup-20261003)' % summary['tip'],
         'patch             %s.patch  %d bytes  sha256 %s' % (NAME, len(patch), summary['patch_sha256']),
         'files             %d: %d edited in place, %d new' % (len(summary['files']),
                                                              sum(f['kind'] == 'edit' for f in summary['files']),
                                                              sum(f['kind'] == 'new' for f in summary['files'])),
         '',
         'The pre-image of an edited file is the LIVE working file as it is now, landing_v2 applied: byte for byte landing_v2\'s post-image for a file landing_v2 edits or creates,',
         'and LIVE\'s own file for a file landing_v2 does not touch. apply_landing.py refuses unless every pre-image hash below matches.',
         'Terminator profiles are live_patch.py `eol` lines (crlf = CRLF-terminated lines, lf = bare-LF lines).',
         'verdict = `live_patch.py drift <post-image> <branch tip file>`: IDENTICAL_BYTES, or EOL_ONLY where the pre-image keeps its own terminators.',
         '']
for item in summary['files']:
    rel = item['file']
    post = os.path.join(LANDING, 'post_images', *rel.split('/'))
    done = subprocess.run([sys.executable, tool, 'drift', post, os.path.join(WT, *rel.split('/'))], capture_output=True, env=env)
    verdict = done.stdout.decode('utf-8', 'replace').strip().splitlines()[-1].split()[-1]
    post_bytes = open(post, 'rb').read()
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
              '    pre-image       sha256 %s' % (item['pre_sha256'] or '(does not exist)'),
              '    pre-image from  %s' % (item['pre_source'] or '-'),
              '    post-image      sha256 %s' % item['post_sha256'],
              '    profile before  %s' % (item['pre_eol'] or '-'),
              '    profile after   %s' % item['post_eol'],
              '    change          %s   verdict vs branch tip: %s' % (changed, verdict),
              '']
open(os.path.join(LANDING, 'MANIFEST.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('\n'.join(lines[:14]))
print('... %d lines written' % len(lines))
