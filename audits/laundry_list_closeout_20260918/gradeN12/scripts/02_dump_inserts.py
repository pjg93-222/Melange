# -*- coding: utf-8 -*-
"""Dump every planned INSERT with enough surrounding text to grade the speaker.  READ-ONLY."""
import io, json, sys

LEDGER = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
          r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\fixN12'
          r'\dry_run_ledger.jsonl')
BEFORE = 700     # chars of the ORIGINAL text immediately before the tag
AFTER = 500      # chars of the ORIGINAL text immediately after the segment ends

out = io.open(sys.argv[1], 'w', encoding='utf-8', newline='\n')
n = 0
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        for i, seg in enumerate(r['removed']):
            if seg['disposition'] not in ('reattributed', 'own_later_turn'):
                continue
            n += 1
            txt = r['original']['text']
            s, e = seg['start'], seg['end']
            pre = txt[max(0, s - BEFORE):s]
            post = txt[e:e + AFTER]
            out.write('=' * 110 + '\n')
            out.write('INSERT %02d | rowid=%s | seg_index=%d/%d | class=%s | disp=%s\n'
                      % (n, r['rowid'], i + 1, len(r['removed']), seg['class'],
                         seg['disposition']))
            out.write('  stored member (row) : %s\n' % r['member'])
            out.write('  INSERT attributed to: %s\n' % seg['speaker'])
            out.write('  date=%s show=%s package=%s\n' % (r['date'], r['chamber'], r['package']))
            out.write('  tag                 : %r\n' % seg['tag'])
            out.write('  seg nwords          : %d\n' % seg['nwords'])
            out.write('  ALL tags in this row: %s\n'
                      % json.dumps([(x['tag'], x['class'], x['own'], x['speaker'],
                                     x['disposition']) for x in r['removed']],
                                   ensure_ascii=False))
            out.write('  --- %d chars of ORIGINAL text BEFORE the tag ---\n' % len(pre))
            out.write('  ...%s\n' % pre)
            out.write('  --- RAW removed span (tag + words), first 2500 chars ---\n')
            out.write('  %s\n' % seg['raw'][:2500])
            out.write('  --- INSERT text (what would be stored), first 2500 chars ---\n')
            out.write('  %s\n' % seg['text'][:2500])
            out.write('  --- %d chars AFTER the segment ---\n' % len(post))
            out.write('  %s...\n' % post)
            out.write('\n')
out.close()
print('inserts dumped: %d' % n)
