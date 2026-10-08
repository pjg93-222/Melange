"""Prepare only this task's edits against HEAD, preserving other live work.

Short character edits are transplanted only when their old text plus context
has one exact match in HEAD. Ambiguity fails; inspect staged_delta.patch before
applying it to the Git index. This never changes the working source files.
"""
import difflib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
from capture import FILES


def transplant(head, before, after):
    changes = [op for op in difflib.SequenceMatcher(None, before, after, autojunk=True).get_opcodes() if op[0] != 'equal']
    for kind, a, b, c, d in reversed(changes):
        matches = []
        for left in (160, 100, 60, 30, 15, 5, 0):
            for right in (160, 100, 60, 30, 15, 5, 0):
                lo, hi = max(0, a-left), min(len(before), b+right)
                old = before[lo:hi]
                if old and head.count(old) == 1:
                    matches.append((len(old), old, before[lo:a] + after[c:d] + before[b:hi]))
        if not matches:
            raise ValueError(f'No unique unchanged context: {kind} {before[a:b]!r} => {after[c:d]!r}')
        _, old, new = max(matches, key=lambda item: item[0])
        head = head.replace(old, new, 1)
    return head


def diff(before, after, name):
    return ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/'+name, tofile='b/'+name))


def main():
    staged, live = [], []
    shadows = OUT / 'commit_shadow'
    for name in FILES:
        print('Preparing ' + name, flush=True)
        before = (OUT / 'before' / name).read_text(encoding='utf-8')
        after = (ROOT / name).read_text(encoding='utf-8')
        head = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT).decode('utf-8').replace('\r\n', '\n')
        original_head = head
        if name.endswith('staffer-route.js'):
            # The prior dashboard redesign changed this sentence. Both variants
            # receive the same evidence-limited wording in this commit.
            head = head.replace('Best route verified for your selected ranking and records.',
                                'Connection path verified against the shared records.')
        # Payroll's sole pre-existing edit was its explanatory missing-bundle
        # error branch, which this fix replaces in full (reviewed in the diff).
        target = after if name.endswith('staffer_payroll_identity.py') else transplant(head, before, after)
        if name.endswith('staffer-route.js'):
            target = target.replace('Balances strong connections with fewer introductions.', 'Balances shared-background scores with fewer steps.')
            target = target.replace('Favors stronger connections, even when the route takes more steps.', 'Favors larger shared-background scores, even when the route takes more steps.')
            target = target.replace('Uses the fewest introductions; stronger ties break a tie.', 'Uses the fewest steps; shared-background scores break a tie.')
        shadow = shadows / name
        shadow.parent.mkdir(parents=True, exist_ok=True)
        shadow.write_text(target, encoding='utf-8', newline='\n')
        staged.append(diff(original_head, target, name))
        live.append(diff(target, after, name))
    test = 'fec/surfaces/test_staffer_live_service.py'
    # This integration suite was already untracked in the shared checkout.
    # Retain only our wording assertion update as a separately applicable patch.
    (OUT / 'integration_test_delta.patch').write_text(diff((OUT / 'before' / test).read_text(encoding='utf-8'),
        (ROOT / test).read_text(encoding='utf-8'), test), encoding='utf-8', newline='\n')
    (OUT / 'staged_delta.patch').write_text(''.join(staged), encoding='utf-8', newline='\n')
    (OUT / 'live_dependencies.patch').write_text(''.join(live), encoding='utf-8', newline='\n')
    print(json.dumps({'files': FILES, 'prepared': 'staged_delta.patch', 'live_dependencies': 'live_dependencies.patch'}))


if __name__ == '__main__':
    main()
