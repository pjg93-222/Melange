"""Prove the Staffer route v4 patch (landing_v4) against the bytes LIVE holds now, landing_v2 and landing_v3_ids applied (D-060). Read-only on LIVE, the two earlier landings, the worktree and
the object store.

  0. The pre-images are what LIVE holds: landing_v3_ids's post-image for a file it edits or creates, landing_v2's for a file only landing_v2 touches, LIVE's own file otherwise.
     The patch's file list is exactly what differs between the base content (f23a40aee) and the tip.
  1. Apply to a scratch tree that holds the pre-images, then run `live_patch.py drift` between every post-image and the branch tip's file in the worktree, and compare it with the tip's git blob.
     IDENTICAL_BYTES is expected; EOL_ONLY only where the pre-image's terminator profile differs from the worktree's checkout (each one is explained); CONTENT is a failure.
  2. No untouched line's terminator changed, and every inserted line carries the file's majority terminator.
  3. The dry run against LIVE itself (read-only) passes: pre-image check, then `git apply --check`, and the raw git command.
  4. LIVE has not moved from the landing_v3_ids post-images: HEAD is the base; every file either earlier landing touched holds the post-image of the last landing that touched it;
     the files only v4 edits hold this patch's pre-images; none of the new paths exists or is tracked.
  5. The two rollbacks (git apply -R, and the saved pre-images) restore the pre-images in the scratch tree.
  6. Every post-image JavaScript file passes `node --check` (and every Python file compiles).
"""
import argparse
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys

LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
WT = r'C:/Users/pgoff/Melange-wt/route-core'
SP = r'C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad'
V2 = SP + '/landing_v2'
V3 = SP + '/landing_v3_ids'
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402

FAILS = []


def check(ok, text):
    print(('PASS  ' if ok else 'FAIL  ') + text)
    if not ok:
        FAILS.append(text)
    return ok


def git(*args, cwd):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    done = subprocess.run(['git', *args], cwd=cwd, env=env, capture_output=True)
    if done.returncode:
        raise RuntimeError('git %s: %s' % (' '.join(args), done.stderr.decode('utf-8', 'replace')))
    return done.stdout


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    with open(path, 'rb') as handle:
        return handle.read()


def table(folder, name):
    return {item['file']: item for item in json.load(open(os.path.join(folder, name), encoding='utf-8'))['files']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--landing', required=True)
    parser.add_argument('--work', required=True, help='scratch directory outside every repository')
    parser.add_argument('--name', default='staffer_route_v4')
    args = parser.parse_args()
    patch_path = os.path.join(args.landing, args.name + '.patch')
    summary = json.load(open(os.path.join(args.landing, args.name + '.summary.json'), encoding='utf-8'))
    v2, v3 = table(V2, 'route_latency.summary.json'), table(V3, 'ids_followup.summary.json')
    manifest = lp.load_manifest(patch_path)
    base, tip, live_head = summary['base'], summary['tip'], summary['live_head']
    files = summary['files']
    edits = [f for f in files if f['kind'] == 'edit']
    news = [f for f in files if f['kind'] == 'new']
    print('patch %s  tip %s  base content (f23a40aee) %s  files %d (%d edits, %d new)' % (os.path.basename(patch_path), tip[:9], base[:9], len(files), len(edits), len(news)))
    check(sha(read(patch_path)) == summary['patch_sha256'], 'the patch file hashes to the summary value')
    check(sorted(manifest) == sorted(f['file'] for f in files), 'the patch manifest names exactly the files of the patch set')
    check(all(manifest[f['file']]['before_sha256'] == f['pre_sha256'] and manifest[f['file']]['after_sha256'] == f['post_sha256'] for f in files),
          'the patch manifest and the summary agree on every pre- and post-image hash')
    rows = git('diff', '--name-status', '-z', base, tip, cwd=WT).split(b'\0')
    changed = {rows[i + 1].decode(): rows[i].decode() for i in range(0, len(rows) - 1, 2)}
    check(sorted(changed) == sorted(f['file'] for f in files) and all(v in ('A', 'M') for v in changed.values())
          and all((changed[f['file']] == 'A') == (f['kind'] == 'new') for f in files),
          'the patch carries exactly the files that differ between f23a40aee and the tip (%d: %d added, %d modified), no deletion and no rename' % (len(changed), len(news), len(edits)))

    # ---- 0. the pre-images are what LIVE holds
    print('\n== 0. every pre-image is LIVE\'s bytes now: the last earlier landing\'s post-image where one touches the file, LIVE\'s own file otherwise')
    for item in edits:
        rel = item['file']
        saved = read(os.path.join(args.landing, 'pre_images', *rel.split('/')))
        check(sha(saved) == item['pre_sha256'], 'saved pre-image hashes to the manifest value  %s' % rel)
        live_now = read(os.path.join(LIVE, *rel.split('/')))
        check(saved == live_now, '   and is LIVE\'s working file now, byte for byte  (%s)  from: %s' % (item['pre_sha256'][:12], item['pre_source']))
        for name, folder, tab in (('landing_v3_ids', V3, v3), ('landing_v2', V2, v2)):
            if rel in tab:
                check(item['pre_sha256'] == tab[rel]['post_sha256'] and saved == read(os.path.join(folder, 'post_images', *rel.split('/'))),
                      '   which is %s\'s post-image (%s), also byte for byte against its post_images' % (name, tab[rel]['post_sha256'][:12]))
                break

    # ---- 1. scratch apply of the pre-images, then drift against the branch tip
    print('\n== 1. apply to a scratch tree of the pre-images, drift against the branch tip (worktree file, and git blob)')
    scratch = os.path.join(args.work, 'scratch_tree')
    if os.path.exists(scratch):
        shutil.rmtree(scratch)
    os.makedirs(scratch)
    lp._assert_outside_repository(scratch)
    for item in edits:
        rel = item['file']
        target = os.path.join(scratch, *rel.split('/'))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as handle:
            handle.write(read(os.path.join(args.landing, 'pre_images', *rel.split('/'))))
    result = lp.apply_to(scratch, patch_path)
    check(result['ok'], 'apply_to() on the scratch tree: ok=%s reason=%r check_rc=%s apply_rc=%s' % (result['ok'], result['reason'], result['check_rc'], result['apply_rc']))
    if not result['ok']:
        print(result['stderr'])
        return 1
    drift_tool = os.path.join(LIVE, 'fec', 'tools', 'live_patch.py')
    verdicts = {}
    for item in files:
        rel = item['file']
        post = os.path.join(scratch, *rel.split('/'))
        check(sha(read(post)) == item['post_sha256'], 'post-image %s hashes to the manifest value' % rel)
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        done = subprocess.run([sys.executable, drift_tool, 'drift', post, os.path.join(WT, *rel.split('/'))], capture_output=True, env=env)
        text = done.stdout.decode('utf-8', 'replace')
        verdict = text.strip().splitlines()[-1].split()[-1]
        verdicts[rel] = (verdict, text, done.returncode)
        check(verdict in ('IDENTICAL_BYTES', 'EOL_ONLY') and done.returncode == {'IDENTICAL_BYTES': 0, 'EOL_ONLY': 1}.get(verdict),
              'drift post-image vs branch tip (worktree)  %-66s %s' % (rel, verdict))
    print('\n   EOL_ONLY explained (an edited file keeps its own terminators, a new file carries the git blob\'s LF, and the branch worktree holds git-checkout CRLF):')
    for rel, (verdict, text, _rc) in sorted(verdicts.items()):
        if verdict != 'EOL_ONLY':
            continue
        item = next(f for f in files if f['file'] == rel)
        lines_ = [line for line in text.splitlines() if line.startswith(('a ', 'b '))]
        print('   - %s' % rel)
        print('       pre-image      : %s' % (item['pre_eol'] or '(new file)'))
        print('       post-image     : %s   (%s)' % (item['post_eol'], 'the git blob\'s bytes' if item['kind'] == 'new' else 'inserted lines carry the majority terminator; untouched lines unchanged'))
        print('       branch tip file: %s' % (lines_[1].split('  ', 1)[1] if len(lines_) > 1 else ''))
        a = read(os.path.join(scratch, *rel.split('/')))
        b = read(os.path.join(WT, *rel.split('/')))
        check(lp.normalised_sha256(a) == lp.normalised_sha256(b), '       the EOL-normalised content is identical (so the difference is terminators only)')
        tip_blob = git('cat-file', 'blob', '%s:%s' % (tip, rel), cwd=WT)
        check([lp.content(l) for l in lp.split_lines(a)] == [lp.content(l) for l in lp.split_lines(tip_blob)], '       and the lines equal the tip blob line for line (terminators stripped)')
    counts = {}
    for verdict, _t, _r in verdicts.values():
        counts[verdict] = counts.get(verdict, 0) + 1
    print('   verdict counts (worktree):', counts)
    blob_counts = {}
    for item in files:
        rel = item['file']
        tip_blob = git('cat-file', 'blob', '%s:%s' % (tip, rel), cwd=WT)
        verdict = lp.drift_report(read(os.path.join(scratch, *rel.split('/'))), tip_blob)['verdict']
        blob_counts[verdict] = blob_counts.get(verdict, 0) + 1
        check(verdict in ('IDENTICAL_BYTES', 'EOL_ONLY') and (item['kind'] != 'new' or verdict == 'IDENTICAL_BYTES'),
              'drift post-image vs the tip\'s git blob  %-66s %s' % (rel, verdict))
    print('   verdict counts (blob):', blob_counts)

    # ---- 2. no untouched line changed its terminator
    print('\n== 2. terminator audit (pre-image -> post-image, aligned by the base -> tip line diff)')
    for item in edits:
        rel = item['file']
        pre = read(os.path.join(args.landing, 'pre_images', *rel.split('/')))
        post = read(os.path.join(scratch, *rel.split('/')))
        base_blob = git('cat-file', 'blob', '%s:%s' % (base, rel), cwd=WT)
        tip_blob = git('cat-file', 'blob', '%s:%s' % (tip, rel), cwd=WT)
        base_lines = [lp.content(l) for l in lp.split_lines(base_blob)]
        tip_lines = [lp.content(l) for l in lp.split_lines(tip_blob)]
        pre_lines, post_lines = lp.split_lines(pre), lp.split_lines(post)
        majority = lp.LF if lp.eol_stats(pre)['n_bare_lf'] > lp.eol_stats(pre)['n_crlf'] else lp.CRLF
        ok, untouched, changed_new, changed_old, bad = True, 0, 0, 0, []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base_lines, tip_lines, autojunk=False).get_opcodes():
            if tag == 'equal':
                for k in range(i2 - i1):
                    if pre_lines[i1 + k] != post_lines[j1 + k]:  # bytes including the terminator
                        ok = False
                        bad.append((i1 + k, pre_lines[i1 + k][-6:], post_lines[j1 + k][-6:]))
                untouched += i2 - i1
            else:
                changed_old += i2 - i1
                for k in range(j2 - j1):
                    line = post_lines[j1 + k]
                    if lp.terminator(line) != majority or lp.content(line) != tip_lines[j1 + k]:
                        ok = False
                        bad.append(('new', j1 + k, line[-6:]))
                changed_new += j2 - j1
        ok = ok and len(post_lines) == untouched + changed_new and len(pre_lines) == untouched + changed_old
        pre_stats, post_stats = lp.eol_stats(pre), lp.eol_stats(post)
        check(ok, '%-66s untouched %5d identical (bytes incl. terminator); changed %4d -> %4d lines at %s' % (
            rel, untouched, changed_old, changed_new, 'CRLF' if majority == lp.CRLF else 'LF'))
        check(post_stats['n_bare_lf'] <= pre_stats['n_bare_lf'] + (changed_new if majority == lp.LF else 0)
              and post_stats['n_lone_cr'] == pre_stats['n_lone_cr'] == 0,
              '   bare-LF lines %d -> %d, lone CR %d -> %d' % (pre_stats['n_bare_lf'], post_stats['n_bare_lf'], pre_stats['n_lone_cr'], post_stats['n_lone_cr']))
        for entry in bad[:3]:
            print('      mismatch', entry)

    # ---- 3. the dry run against LIVE
    print('\n== 3. the dry run against LIVE itself (read-only): pre-image check, then git apply --check')
    # Only the dry run (no --apply) is ever pointed at LIVE: it checks hashes and runs `git apply --check`, and writes nothing. --apply is proved on scratch trees only.
    apply_script = os.path.join(args.landing, 'scripts', 'apply_landing.py')
    env = dict(os.environ, PYTHONIOENCODING='utf-8', GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1')
    done = subprocess.run([sys.executable, apply_script], capture_output=True, env=env)
    out = done.stdout.decode('utf-8', 'replace')
    check(done.returncode == 0 and 'rc=0' in out and 'MISMATCH' not in out, 'apply_landing.py (dry run) against LIVE: pre-image check passes for all %d files, git apply --check rc=0 (rc=%s)' % (len(files), done.returncode))
    outcome = lp.check_against(LIVE, patch_path)
    check(outcome['rc'] == 0 and not outcome['timed_out'], 'raw `git -c core.autocrlf=false -c core.safecrlf=false apply --check` against LIVE itself passes: rc=%s %s' % (outcome['rc'], outcome['stderr'].strip()[:160]))
    print('\n'.join('      ' + line for line in out.strip().splitlines()))

    # ---- 4. LIVE has not moved
    print('\n== 4. LIVE has not moved from the landing_v3_ids post-images (read-only)')
    head = git('rev-parse', 'HEAD', cwd=LIVE).decode().strip()
    check(head == live_head, 'LIVE HEAD is %s' % head)
    expected = {}
    for tab in (v2, v3):                      # landing_v3_ids overrides landing_v2 for the files both touch
        for rel, item in tab.items():
            expected[rel] = item['post_sha256']
    wrong = []
    for rel, want in sorted(expected.items()):
        path = os.path.join(LIVE, *rel.split('/'))
        if not os.path.isfile(path) or sha(read(path)) != want:
            wrong.append(rel)
    check(not wrong, 'all %d files either earlier landing touched (landing_v2: %d, landing_v3_ids: %d, %d in both) hold the post-image of the last landing that touched them%s' % (
        len(expected), len(v2), len(v3), len(set(v2) & set(v3)), (' (WRONG: %s)' % wrong) if wrong else ''))
    for item in edits:
        rel = item['file']
        if rel in expected:
            continue
        now = sha(read(os.path.join(LIVE, *rel.split('/'))))
        check(now == item['pre_sha256'], 'LIVE holds this patch\'s pre-image (neither earlier landing touches it)  %s' % rel)
    check(all(not os.path.exists(os.path.join(LIVE, *f['file'].split('/'))) for f in news), 'none of the %d new files exists in LIVE' % len(news))
    tracked = git('ls-files', '--', *[f['file'] for f in news], cwd=LIVE).decode().split()
    check(tracked == [], 'none of the new paths is tracked in LIVE: %r' % tracked)

    # ---- 5. rollbacks
    print('\n== 5. rollback paths, on the scratch tree')
    reverse = subprocess.run(['git', '-C', scratch, '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false', 'apply', '-R', patch_path], capture_output=True)
    check(reverse.returncode == 0, 'git apply -R of the patch on the post-image tree: rc=%s %s' % (reverse.returncode, reverse.stderr.decode()[:120]))
    for item in edits:
        back = read(os.path.join(scratch, *item['file'].split('/')))
        check(back == read(os.path.join(args.landing, 'pre_images', *item['file'].split('/'))), '   restored byte-exact  %s' % item['file'])
    check(all(not os.path.exists(os.path.join(scratch, *f['file'].split('/'))) for f in news), '   the new files are gone again')

    # ---- 6. syntax of every post-image (reads the saved post-images, so it does not depend on the scratch tree)
    print('\n== 6. every post-image JavaScript file passes node --check, every Python file compiles (the saved post-images)')
    n_py = n_js = 0
    for item in files:
        rel = item['file']
        post = read(os.path.join(args.landing, 'post_images', *rel.split('/')))
        check(sha(post) == item['post_sha256'], 'saved post-image %s hashes to the manifest value' % rel)
        if rel.endswith('.py'):
            n_py += 1
            try:
                compile(post, rel, 'exec', dont_inherit=True)
                ok, detail = True, ''
            except SyntaxError as error:
                ok, detail = False, repr(error)
            check(ok, 'compiles (Python)            %s %s' % (rel, detail))
        elif rel.endswith(('.js', '.cjs', '.mjs')):
            n_js += 1
            tmp = os.path.join(args.work, 'syntax_check', *rel.split('/'))
            os.makedirs(os.path.dirname(tmp), exist_ok=True)
            with open(tmp, 'wb') as handle:
                handle.write(post)
            done = subprocess.run(['node', '--check', tmp], capture_output=True)
            check(done.returncode == 0, 'node --check (JavaScript)  %s %s' % (rel, done.stderr.decode('utf-8', 'replace')[:200]))
    print('   %d Python files compiled, %d JavaScript files checked' % (n_py, n_js))

    print('\nresult: %s (%d failed checks)' % ('ALL PASS' if not FAILS else 'FAILURES', len(FAILS)))
    for text in FAILS:
        print('  FAILED:', text)
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
