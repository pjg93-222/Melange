# -*- coding: utf-8 -*-
"""G3/G5: what the migration DELETES from the corpus, and where the member's own untagged words
sit inside a segment that would be deleted.  READ-ONLY."""
import io, json, re, sys, collections, random

LEDGER = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
          r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\fixN12'
          r'\dry_run_ledger.jsonl')
KEEP = ('reattributed', 'own_later_turn')

rows = []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if line:
            rows.append(json.loads(line))

out = io.open(sys.argv[1], 'w', encoding='utf-8', newline='\n')


def w(s=''):
    out.write(s + '\n')


# ------------------------------------------------ word accounting
orig_words = kept_words = ins_words = del_words = 0
del_by_disp = collections.Counter()
for r in rows:
    if r['skip']:
        continue
    orig_words += r['original']['nwords']
    kept_words += r['kept']['nwords']
    for seg in r['removed']:
        if seg['disposition'] in KEEP:
            ins_words += seg['nwords']
        else:
            del_words += seg['nwords']
            del_by_disp[seg['disposition']] += seg['nwords']
w('=' * 100)
w('W1  WORD ACCOUNTING over the 5,859 rows that would be UPDATEd')
w('    words in the rows today          : %d' % orig_words)
w('    words the member would keep      : %d' % kept_words)
w('    words moved into the 64 new rows : %d' % ins_words)
w('    words DELETED from the corpus    : %d   %s' % (del_words, dict(del_by_disp)))
w('    (deleted words survive only in the ledger; --restore is the only way back)')

# ------------------------------------------------ member's own surname inside a DELETED segment
w()
w('=' * 100)
w('W2  DELETED SEGMENTS THAT NAME THE ROW\'S OWN MEMBER (risk zone: the narration is ABOUT the')
w('    member, so the member\'s own untagged words may sit inside the segment that is deleted)')
FIRSTPERSON = re.compile(r'(?:^|[.?!]["\u201d\']?\s|\s--\s)\s*(?:I|We|My|Our)\b')
cands = []
for r in rows:
    if r['skip']:
        continue
    sur = r['member'].split()[-1].lower()
    for i, seg in enumerate(r['removed'], 1):
        if seg['disposition'] in KEEP:
            continue
        low = seg['text'].lower()
        if sur in low and seg['nwords'] >= 12:
            fp = bool(FIRSTPERSON.search(seg['text']))
            cands.append((r['rowid'], r['member'], i, seg['class'], seg['nwords'], fp,
                          seg['tag'][:34], seg['text']))
w('    deleted segments >=12 words that contain the member\'s surname: %d' % len(cands))
w('    of those, ALSO carrying a sentence-initial first-person pronoun: %d'
  % len([c for c in cands if c[5]]))
w()
rnd = random.Random(20260919)
fp_cands = [c for c in cands if c[5]]
show = rnd.sample(fp_cands, min(30, len(fp_cands)))
w('    ---- seeded sample of 30 of the first-person ones, full text, for reading ----')
for c in sorted(show, key=lambda x: x[0]):
    w('    rowid=%-7s member=%-24s seg%-2d %-26s nw=%-4d tag=%r'
      % (c[0], c[1], c[2], c[3], c[4], c[6]))
    w('        %s' % c[7][:1600])
    w()

# ------------------------------------------------ tiny kept text (the row is nearly all foreign)
w('=' * 100)
w('W3  ROWS WHOSE KEPT TEXT WOULD FALL BELOW THE COLLECTOR\'S OWN 8-WORD FLOOR')
tiny = [(r['rowid'], r['member'], r['kept']['nwords'], r['original']['nwords'],
         r['kept']['text'][:90]) for r in rows if not r['skip'] and r['kept']['nwords'] < 8]
w('    rows: %d  (the collector would never have written a turn this short:'
  ' turn_tags.MIN_TURN_WORDS=8)' % len(tiny))
for t in sorted(tiny)[:40]:
    w('      rowid=%-7s %-24s kept=%-3d of %-5d %r' % t)
out.close()
print('done')
