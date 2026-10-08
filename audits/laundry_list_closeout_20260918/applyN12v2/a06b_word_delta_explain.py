# -*- coding: utf-8 -*-
"""STEP 6, the one check that did not balance: --apply reported words_removed=346500 while the
measured (stored nwords BEFORE) - (stored nwords AFTER) delta is 346496.  Four words.  READ-ONLY.

TWO CANDIDATE MECHANISMS, and this script decides between them per row:
  M1  the cut lands INSIDE a whitespace-delimited token: the foreign tag is glued to the preceding
      character, so '....decision.CHUCK TODD:' counts 'decision.CHUCK' as ONE token in the
      original and as TWO once the string is split at the tag.  len(kept)+len(removed) is then
      len(original)+1 and the tool's removed_nwords overstates the true delta by exactly 1.
      Nothing is mis-cut and nothing is lost: the kept text is still a strict prefix.
  M2  the stored nwords of the ORIGINAL row disagreed with len(text.split()) before the apply --
      that would be a pre-existing corpus-invariant break, and a real finding.

It prints every row that does not balance, with the bytes on either side of the cut.
"""
import hashlib
import io
import json
import os
import sqlite3
import sys

LIVE_ROOT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = os.path.join(LIVE_ROOT, 'social_media.db')
BAK = os.path.join(LIVE_ROOT, 'backups', 'social_media.PRE-TURNSPLIT-20260919.db')
LEDGER = 'speeches_turn_split_ledger'


def uri(path):
    return 'file:%s?mode=ro' % path.replace('\\', '/')


def main():
    con = sqlite3.connect(uri(DB), uri=True, timeout=300)
    con.execute('ATTACH DATABASE ? AS bak', (uri(BAK),))
    con.execute('PRAGMA query_only=ON')

    rows = con.execute(
        'SELECT l.speech_rowid,l.kept_raw,l.removed_raw,l.kept_nwords,b.text,b.nwords,b.member,'
        'a.nwords,a.text FROM main.%s l '
        'JOIN bak.speeches b ON b.rowid=l.speech_rowid '
        'JOIN main.speeches a ON a.rowid=l.speech_rowid' % LEDGER).fetchall()
    print('ledger rows joined to both databases: %d' % len(rows))

    m1, m2, other = [], [], []
    sum_true_delta = sum_tool_removed = 0
    invariant_before_bad = 0
    for rid, kraw, rraw, knw, old, old_nw, member, live_nw, live_text in rows:
        old = old or ''
        kraw = kraw or ''
        rraw = rraw or ''
        removed_nw = len(rraw.split())
        true_delta = (old_nw or 0) - (live_nw or 0)
        sum_true_delta += true_delta
        sum_tool_removed += removed_nw
        if (old_nw or 0) != len(old.split()):
            invariant_before_bad += 1
        if true_delta == removed_nw:
            continue
        glued = bool(kraw) and not kraw[-1:].isspace()
        entry = {'rowid': rid, 'member': member, 'gap': removed_nw - true_delta,
                 'kept_tail': kraw[-60:], 'removed_head': rraw[:60],
                 'stored_nwords_before': old_nw, 'len_split_before': len(old.split()),
                 'kept_nwords': knw, 'live_nwords': live_nw, 'removed_nwords': removed_nw,
                 'cut_is_mid_token': glued}
        if (old_nw or 0) != len(old.split()):
            m2.append(entry)
        elif glued and removed_nw - true_delta == 1:
            m1.append(entry)
        else:
            other.append(entry)

    print('\nrows where (stored nwords before) - (stored nwords after) != removed_nwords: %d'
          % (len(m1) + len(m2) + len(other)))
    print('  M1 cut lands mid-token (benign, gap exactly 1): %d' % len(m1))
    print('  M2 the ORIGINAL row already broke nwords == len(text.split()): %d' % len(m2))
    print('  unexplained: %d' % len(other))
    print('pre-apply corpus invariant nwords == len(text.split()) on these %d originals: %s'
          % (len(rows), 'HELD' if invariant_before_bad == 0
             else 'BROKEN on %d rows' % invariant_before_bad))

    for label, group in (('M1', m1), ('M2', m2), ('UNEXPLAINED', other)):
        for e in group:
            print('\n%s rowid=%d member=%r gap=%+d  stored_nwords_before=%s len(split)=%s '
                  'kept=%s live=%s removed_nwords=%s cut_is_mid_token=%s'
                  % (label, e['rowid'], e['member'], e['gap'], e['stored_nwords_before'],
                     e['len_split_before'], e['kept_nwords'], e['live_nwords'],
                     e['removed_nwords'], e['cut_is_mid_token']))
            print('   kept  ...%r' % e['kept_tail'])
            print('   CUT -> %r...' % e['removed_head'])
            print('   the token straddling the cut: %r + %r'
                  % (e['kept_tail'].split()[-1] if e['kept_tail'].split() else '',
                     e['removed_head'].split()[0] if e['removed_head'].split() else ''))

    print('\nsum over all %d ledger rows:' % len(rows))
    print('  true word delta   (stored before - stored after) = %d' % sum_true_delta)
    print('  tool words_removed (sum len(removed_raw.split())) = %d' % sum_tool_removed)
    print('  gap = %d, and the per-row gaps account for it exactly: %s'
          % (sum_tool_removed - sum_true_delta,
             sum(e['gap'] for e in m1 + m2 + other) == sum_tool_removed - sum_true_delta))

    # the identity that IS exact, stated and checked
    exact = all(len((k or '').split()) + len((r or '').split())
                - (1 if (k or '') and not (k or '')[-1:].isspace() and (r or '') else 0)
                == len(((k or '') + (r or '')).split())
                for _rid, k, r, _knw, _o, _onw, _m, _lnw, _lt in rows)
    print('\nEXACT IDENTITY  len(kept.split()) + len(removed.split()) - [cut is mid-token] '
          '== len(original.split())  holds on all %d rows: %s' % (len(rows), exact))
    print('nothing is lost either way: the ledger reconstruction check (C11) already proved '
          'kept_raw + removed_raw == the original text byte for byte on all %d rows.' % len(rows))
    con.close()
    ok = not m2 and not other and exact
    print('\nVERDICT: %s' % ('the 4-word gap is entirely M1 (mid-token cuts); no data defect'
                             if ok else 'NOT fully explained -- see M2/UNEXPLAINED above'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
