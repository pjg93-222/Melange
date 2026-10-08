"""Cut the staffer route-latency patch set against the LIVE working-tree bytes (D-060).

Read-only on LIVE and on the branch worktree. Nothing here writes inside any repository; every output goes under
--out (a plain directory).

Method, per modified file (bytes end to end, lines split on LF only, via fec/tools/live_patch.py):
  * LIVE's lines, terminators kept, are the pre-image. The base blob (BASE) and the tip blob (TIP) are compared line
    by line on content (terminator stripped); LIVE must hold exactly the base content, or the cut stops.
  * Every changed region of base -> tip is spliced into LIVE's lines. Its anchor (a few unchanged lines on each side of
    the old lines, taken from the file as it is at that moment) must hit EXACTLY ONCE in LIVE's content, or the cut
    stops. New lines carry the file's MAJORITY terminator (live_patch rule); untouched lines are never rewritten.
  * After the last splice the content must equal the tip blob line for line.
New files become new-file patches carrying the exact tip bytes (the terminator convention they have on the branch).
"""
import argparse
import difflib
import hashlib
import json
import os
import subprocess
import sys

LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
WT = r'C:/Users/pgoff/Melange-wt/route-jobs'
BASE_SHA = '3248a6a02e42bd23665995e69dc649ac926aab95'
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402


def git(*args, cwd, ok=(0,)):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
        env.pop(name, None)
    done = subprocess.run(['git', *args], cwd=cwd, env=env, capture_output=True)
    if done.returncode not in ok:
        raise RuntimeError('git %s failed (%s): %s' % (' '.join(args), done.returncode, done.stderr.decode('utf-8', 'replace')))
    return done.stdout


def blob(rev, path):
    return git('cat-file', 'blob', '%s:%s' % (rev, path), cwd=WT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Cut(lp.LiveFile):
    """A LiveFile that can replace a counted run of lines, each splice anchored by unchanged context that hits once."""

    def splice(self, pos, old, new, max_context=60):
        """Replace the len(old) lines at `pos` (whose content must equal `old`) with `new` (content bytes, no terminator)."""
        have = [lp.content(line) for line in self._lines[pos:pos + len(old)]]
        if have != old:
            raise lp.AnchorError(self.label, old[:1] or [b'(insertion)'], [])
        for context in range(1 if not old else 0, max_context + 1):
            before = [lp.content(line) for line in self._lines[max(0, pos - context):pos]]
            after = [lp.content(line) for line in self._lines[pos + len(old):pos + len(old) + context]]
            anchor = before + old + after
            if not anchor:
                continue
            hits = self.find(anchor)
            if hits == [pos - len(before)]:
                break
            if len(hits) > 1 or (hits and hits != [pos - len(before)]):
                continue
        else:
            raise lp.AnchorError(self.label, anchor, hits)
        end = self.majority_eol()
        payload = lp._payload_lines(new, end) if new else []
        self._lines[pos:pos + len(old)] = payload
        self._restore_tail(end)
        return len(payload)


def split_content(data):
    return [lp.content(line) for line in lp.split_lines(data)]


def cut_file(label, live_bytes, base_bytes, tip_bytes):
    base_lines, tip_lines = split_content(base_bytes), split_content(tip_bytes)
    if lp.eol_stats(base_bytes)['ends_with_eol'] != lp.eol_stats(tip_bytes)['ends_with_eol']:
        raise RuntimeError('%s: base and tip differ in their final terminator' % label)
    live = Cut(label, live_bytes)
    live_lines = [lp.content(line) for line in live.lines]
    if live_lines != base_lines:
        raise RuntimeError('%s: LIVE does not hold the base content' % label)
    matcher = difflib.SequenceMatcher(None, base_lines, tip_lines, autojunk=False)
    delta, blocks = 0, 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        added = live.splice(i1 + delta, base_lines[i1:i2], tip_lines[j1:j2])
        delta += added - (i2 - i1)
        blocks += 1
    after = live.after
    if split_content(after) != tip_lines:
        raise RuntimeError('%s: the cut result does not equal the tip content' % label)
    return live, blocks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tip', default='HEAD')
    parser.add_argument('--out', required=True)
    parser.add_argument('--name', default='route_latency')
    args = parser.parse_args()
    tip = git('rev-parse', args.tip, cwd=WT).decode().strip()
    live_head = git('rev-parse', 'HEAD', cwd=LIVE).decode().strip()
    if live_head != BASE_SHA:
        raise SystemExit('LIVE has moved: HEAD is %s, not %s' % (live_head, BASE_SHA))
    if git('merge-base', BASE_SHA, tip, cwd=WT).decode().strip() != BASE_SHA:
        raise SystemExit('tip does not descend from the base')
    rows = git('diff', '--name-status', '-z', BASE_SHA, tip, cwd=WT).split(b'\0')
    entries = [(rows[i].decode(), rows[i + 1].decode()) for i in range(0, len(rows) - 1, 2)]
    unexpected = [e for e in entries if e[0] not in ('A', 'M')]
    if unexpected:
        raise SystemExit('only added and modified files are expected: %r' % unexpected)
    os.makedirs(args.out, exist_ok=True)
    patchset, files, rows_out = lp.PatchSet(), {}, []
    for status, path in entries:
        live_path = os.path.join(LIVE, *path.split('/'))
        tip_bytes = blob(tip, path)
        if status == 'M':
            live_bytes = open(live_path, 'rb').read()
            live, blocks = cut_file(path, live_bytes, blob(BASE_SHA, path), tip_bytes)
            patchset.add(live)
            files[path] = (live_bytes, live.after)
            rows_out.append({'file': path, 'kind': 'edit', 'blocks': blocks, 'before': live_bytes, 'after': live.after})
        else:
            if os.path.exists(live_path):
                raise SystemExit('LIVE already has %s' % path)
            on_branch = open(os.path.join(WT, *path.split('/')), 'rb').read()
            if on_branch != tip_bytes:
                raise SystemExit('%s: the worktree bytes differ from the tip blob' % path)
            patchset.add_new_file(path, tip_bytes)
            files[path] = (None, tip_bytes)
            rows_out.append({'file': path, 'kind': 'new', 'blocks': 1, 'before': None, 'after': tip_bytes})
    patch_path = os.path.join(args.out, args.name + '.patch')
    patchset.write(patch_path)
    proof = lp.prove(patchset.to_bytes(), files)
    print('tip %s  base %s  files %d' % (tip, BASE_SHA[:9], len(rows_out)))
    print('prove():', {k: proof[k] for k in ('ok', 'check_rc', 'apply_rc', 'mismatches')})
    if not proof['ok']:
        print(proof['stderr'])
        raise SystemExit(1)
    for kind in ('pre_images', 'post_images'):
        for row in rows_out:
            data = row['before'] if kind == 'pre_images' else row['after']
            if data is None:
                continue
            target = os.path.join(args.out, kind, *row['file'].split('/'))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as handle:
                handle.write(data)
    summary = {'base': BASE_SHA, 'tip': tip, 'patch': os.path.basename(patch_path), 'patch_sha256': sha(patchset.to_bytes()),
               'files': []}
    for row in rows_out:
        before, after = row['before'], row['after']
        summary['files'].append({
            'file': row['file'], 'kind': row['kind'], 'blocks': row['blocks'],
            'live_pre_sha256': None if before is None else sha(before),
            'post_sha256': sha(after),
            'live_pre_eol': None if before is None else lp.format_stats(lp.eol_stats(before)),
            'post_eol': lp.format_stats(lp.eol_stats(after))})
    with open(os.path.join(args.out, args.name + '.summary.json'), 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(summary, handle, indent=1)
        handle.write('\n')
    for item in summary['files']:
        print('%-4s %-62s %s -> %s' % (item['kind'], item['file'], item['live_pre_eol'] or '-', item['post_eol']))


if __name__ == '__main__':
    main()
