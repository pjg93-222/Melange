"""Cut the Staffer route v4 patch (landing_v4) against the bytes LIVE holds NOW, landing_v2 and landing_v3_ids already applied there (D-060, DE-040, DE-041).

Read-only on LIVE, on the two earlier landings and on the branch worktree. Nothing here writes inside any repository; every output goes under --out (a plain directory).

What v4 is: the branch claude/staffer-route-v4-20261003 is f23a40aee (the content LIVE holds: landing_v2 plus landing_v3_ids) plus the unreachable-hint branch, the cold-path branch
and the committee-name branch merged, plus three fix commits. The patch carries every file that differs between f23a40aee and the tip.

The pre-image of every file v4 edits is the LIVE working file as it is now, read here in binary and read-only. For a file landing_v3_ids edits or creates, those bytes must also equal
landing_v3_ids's post-image (its summary's post_sha256, and byte for byte the copy in landing_v3_ids\\post_images); for a file only landing_v2 edits or creates, landing_v2's post-image;
that is what "both are applied" means, and if the bytes differ LIVE has moved since and the cut stops. A file neither landing touches is LIVE's own.

Method, per modified file (bytes end to end, lines split on LF only, via fec/tools/live_patch.py; the same cutter as landing_v2's and landing_v3_ids's cut_landing.py):
  * the pre-image's lines, terminators kept, are what gets edited. BASE (the blob at f23a40aee) and TIP (the blob at the branch tip) are compared line by line on content (terminator
    stripped); the pre-image must hold exactly the BASE content, or the cut stops.
  * every changed region of BASE -> TIP is spliced into the pre-image's own lines. Its anchor (a few unchanged lines on each side of the old lines, taken from the file as it is at
    that moment) must hit EXACTLY ONCE, or the cut stops. New lines carry the file's MAJORITY terminator (live_patch rule); untouched lines are never rewritten (a MIXED file stays MIXED).
  * after the last splice the content must equal the TIP blob line for line.
New files become new-file patches carrying the exact TIP bytes (the blob: pure LF).
"""
import argparse
import difflib
import hashlib
import json
import os
import subprocess
import sys

LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
WT = r'C:/Users/pgoff/Melange-wt/route-core'
SP = r'C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad'
V2 = SP + '/landing_v2'
V3 = SP + '/landing_v3_ids'
BASE_REV = 'f23a40aee4c749bae9db132599a853a52c81d9bf'           # the tip landing_v2 plus landing_v3_ids were cut from: exactly the content LIVE holds
LIVE_HEAD = '3248a6a02e42bd23665995e69dc649ac926aab95'          # LIVE main, which both earlier landings were cut against
V2_SUMMARY, V3_SUMMARY = 'route_latency.summary.json', 'ids_followup.summary.json'
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


def cut_file(label, pre_bytes, base_bytes, tip_bytes):
    base_lines, tip_lines = split_content(base_bytes), split_content(tip_bytes)
    if lp.eol_stats(base_bytes)['ends_with_eol'] != lp.eol_stats(tip_bytes)['ends_with_eol']:
        raise RuntimeError('%s: base and tip differ in their final terminator' % label)
    live = Cut(label, pre_bytes)
    live_lines = [lp.content(line) for line in live.lines]
    if live_lines != base_lines:
        raise RuntimeError('%s: the pre-image does not hold the base content' % label)
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


def landing_files(folder, summary_name):
    summary = json.load(open(os.path.join(folder, summary_name), encoding='utf-8'))
    return {item['file']: item for item in summary['files']}


def pre_image(path, v2, v3):
    """(bytes, source label) of the file as LIVE holds it now, or (None, None) if LIVE has no such file.

    Both earlier landings are applied in LIVE, so for a file landing_v3_ids edits or creates the bytes must be landing_v3_ids's post-image, and for a file only landing_v2 edits or creates
    they must be landing_v2's post-image: the sha256 of its summary, and byte for byte the copy in post_images. Anything else means LIVE moved after the landings, and the cut stops.
    """
    live_path = os.path.join(LIVE, *path.split('/'))
    if not os.path.isfile(live_path):
        return None, None
    data = open(live_path, 'rb').read()
    for name, folder, table in (('landing_v3_ids', V3, v3), ('landing_v2', V2, v2)):
        if path not in table:
            continue
        saved = open(os.path.join(folder, 'post_images', *path.split('/')), 'rb').read()
        if sha(saved) != table[path]['post_sha256']:
            raise SystemExit('%s: %s post-image does not hash to its own summary value' % (path, name))
        if data != saved:
            raise SystemExit("%s: LIVE holds %s, not %s's post-image %s: LIVE moved after it was applied" % (path, sha(data)[:12], name, sha(saved)[:12]))
        return data, 'LIVE working file now = %s post-image' % name
    return data, 'LIVE working file now (neither landing_v2 nor landing_v3_ids touches it)'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tip', default='HEAD')
    parser.add_argument('--out', required=True)
    parser.add_argument('--name', default='staffer_route_v4')
    args = parser.parse_args()
    tip = git('rev-parse', args.tip, cwd=WT).decode().strip()
    live_head = git('rev-parse', 'HEAD', cwd=LIVE).decode().strip()
    if live_head != LIVE_HEAD:
        raise SystemExit('LIVE has moved: HEAD is %s, not %s' % (live_head, LIVE_HEAD))
    if git('merge-base', BASE_REV, tip, cwd=WT).decode().strip() != BASE_REV:
        raise SystemExit('tip does not descend from %s' % BASE_REV)
    rows = git('diff', '--name-status', '-z', BASE_REV, tip, cwd=WT).split(b'\0')
    entries = [(rows[i].decode(), rows[i + 1].decode()) for i in range(0, len(rows) - 1, 2)]
    unexpected = [e for e in entries if e[0] not in ('A', 'M')]
    if unexpected:
        raise SystemExit('only added and modified files are expected: %r' % unexpected)
    v2, v3 = landing_files(V2, V2_SUMMARY), landing_files(V3, V3_SUMMARY)
    os.makedirs(args.out, exist_ok=True)
    patchset, files, rows_out = lp.PatchSet(), {}, []
    for status, path in entries:
        tip_bytes = blob(tip, path)
        pre, source = pre_image(path, v2, v3)
        if status == 'M':
            if pre is None:
                raise SystemExit('%s: modified by v4 but absent from LIVE' % path)
            live, blocks = cut_file(path, pre, blob(BASE_REV, path), tip_bytes)
            patchset.add(live)
            files[path] = (pre, live.after)
            rows_out.append({'file': path, 'kind': 'edit', 'blocks': blocks, 'before': pre, 'after': live.after, 'source': source})
        else:
            if pre is not None:
                raise SystemExit('%s: v4 adds a file that LIVE already holds' % path)
            on_branch = open(os.path.join(WT, *path.split('/')), 'rb').read()
            if on_branch.replace(b'\r\n', b'\n') != tip_bytes.replace(b'\r\n', b'\n'):
                raise SystemExit('%s: the worktree content differs from the tip blob' % path)
            patchset.add_new_file(path, tip_bytes)
            files[path] = (None, tip_bytes)
            rows_out.append({'file': path, 'kind': 'new', 'blocks': 1, 'before': None, 'after': tip_bytes, 'source': None})
    patch_path = os.path.join(args.out, args.name + '.patch')
    patchset.write(patch_path)
    proof = lp.prove(patchset.to_bytes(), files)
    print('tip %s  base %s  files %d' % (tip, BASE_REV[:9], len(rows_out)))
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
    summary = {'base': BASE_REV, 'live_head': LIVE_HEAD, 'tip': tip, 'patch': os.path.basename(patch_path), 'patch_sha256': sha(patchset.to_bytes()),
               'requires': 'landing_v2 (route_latency.patch) and landing_v3_ids (ids_followup.patch) applied to LIVE', 'files': []}
    for row in rows_out:
        before, after = row['before'], row['after']
        summary['files'].append({
            'file': row['file'], 'kind': row['kind'], 'blocks': row['blocks'],
            'pre_sha256': None if before is None else sha(before),
            'pre_source': row['source'],
            'post_sha256': sha(after),
            'pre_eol': None if before is None else lp.format_stats(lp.eol_stats(before)),
            'post_eol': lp.format_stats(lp.eol_stats(after))})
    with open(os.path.join(args.out, args.name + '.summary.json'), 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(summary, handle, indent=1)
        handle.write('\n')
    for item in summary['files']:
        print('%-4s %-66s %s -> %s' % (item['kind'], item['file'], item['pre_eol'] or '-', item['post_eol']))


if __name__ == '__main__':
    main()
