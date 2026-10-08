# -*- coding: utf-8 -*-
"""V5: the exact rows where the MEMBER'S OWN words leave the live corpus.  READ-ONLY, ledger only.

(a) full detail for every row carrying an explicit OWN-member tag after the cut;
(b) rowid 83061 -- the v1 grade's untagged-return case -- exact words and count;
(c) a LOOSER untagged-return sweep than the section-2 enrichment: the LAST removed segment is a
    voice-over / on-camera correspondent turn, its TAIL carries a first-person clause, and the
    row member's surname appears in the segment.  This is the stratum where an untagged return
    to the member hides; sampled and read.
"""
import io
import json
import random
import re
import sys
import unicodedata

LEDGER, OUTDIR = sys.argv[1], sys.argv[2]
_AP = "'`’‘ʼ"


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    for ch in _AP:
        s = s.replace(ch, "'")
    return re.sub(r"[^a-z ]", '', s.lower()).strip()


rows, truncated = {}, []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if line:
            r = json.loads(line)
            rows[r['rowid']] = r
            if not r['skip']:
                truncated.append(r)

out = io.open(OUTDIR + '/V5_member_word_loss.txt', 'w', encoding='utf-8', newline='\n')


def W(s=''):
    out.write(s + '\n')


W('=' * 100)
W('(a) EVERY TRUNCATED ROW WITH AN EXPLICIT OWN-MEMBER TAG AFTER THE CUT -- full text of the')
W('    member-tagged segments that would leave the live corpus.')
W('=' * 100)
for r in truncated:
    msur = (norm(r['member']).split() or [''])[-1]
    owned = [s for s in r['removed']['segments']
             if s['ownership'] == 'own' or (msur and msur in norm(s['tag']).split())]
    if not owned:
        continue
    W('rowid=%-7s member=%r %s show=%s pkg=%s' % (r['rowid'], r['member'], r['date'],
                                                  r['chamber'], r['package']))
    W('   cut_tag=%r  orig=%sw kept=%sw removed=%sw  own-tagged words removed=%d'
      % (r['cut_tag'], r['original']['nwords'], r['kept']['nwords'], r['removed']['nwords'],
         sum(s['nwords'] for s in owned)))
    W('   KEPT (200 chars): %s' % r['kept']['text'][:200])
    for s in owned:
        W('     OWN-TAG %r (%dw): %s' % (s['tag'], s['nwords'], (s['text'] or '')[:400]))
    W()

W('=' * 100)
W('(b) rowid 83061 -- the v1 grade\'s untagged member return, still present in v2')
W('=' * 100)
r = rows.get(83061)
if r:
    W('member=%r %s show=%s  skip=%s' % (r['member'], r['date'], r['chamber'], r['skip']))
    W('orig=%sw kept=%sw removed=%sw' % (r['original']['nwords'], r['kept']['nwords'],
                                         r['removed']['nwords']))
    W('KEPT: %s' % r['kept']['text'])
    for s in r['removed']['segments']:
        W('SEG %r (%dw): %s' % (s['tag'], s['nwords'], s['text']))
    tail = r['removed']['raw']
    m = re.search(r'The question is, are we being strategic\?', tail)
    if m:
        W()
        W('the member-voice tail begins at offset %d of the removed text; it runs %d words:'
          % (m.start(), len(tail[m.start():].split())))
        W('   %r' % tail[m.start():])

# (c) looser untagged-return sweep
W()
W('=' * 100)
W('(c) LOOSER UNTAGGED-RETURN SWEEP')
W('=' * 100)
BCAST = re.compile(r'\((?:voice[\s\-]?over|voiceover|on\s?camera|on-camera)\)', re.I)
FP_LOOSE = re.compile(r"\b(?:I|I'm|I've|I'd|my|we|we're|we've|our)\b", re.I)
cand = []
for r in truncated:
    segs = r['removed']['segments']
    if not segs:
        continue
    last = segs[-1]
    if not BCAST.search(last['tag'] or ''):
        continue
    body = last['text'] or ''
    if len(body.split()) < 25:
        continue
    tail = body[-320:]
    msur = (norm(r['member']).split() or [''])[-1]
    if msur and msur in norm(body).split() and FP_LOOSE.search(tail):
        cand.append(r)
W('stratum size: %d of %d truncated rows (%.2f%%)'
  % (len(cand), len(truncated), 100.0 * len(cand) / len(truncated)))
W('83061 in this stratum: %s' % (83061 in {c['rowid'] for c in cand}))
rnd = random.Random(20260920)
samp = sorted(rnd.sample(cand, min(25, len(cand))), key=lambda r: r['rowid'])
W('sampled rowids: %s' % [r['rowid'] for r in samp])
W()
for i, r in enumerate(samp, 1):
    last = r['removed']['segments'][-1]
    W('--- %02d rowid=%s member=%r cut_tag=%r  last seg %r (%dw)'
      % (i, r['rowid'], r['member'], r['cut_tag'], last['tag'], last['nwords']))
    W('    KEPT ...%s' % r['kept']['text'][-140:])
    W('    LASTSEG TAIL: ...%s' % (last['text'] or '')[-420:])
    W()
out.close()
print('done: own_rows=%d loose_stratum=%d' %
      (sum(1 for r in truncated
           if any(s['ownership'] == 'own'
                  or ((norm(r['member']).split() or [''])[-1] in norm(s['tag']).split())
                  for s in r['removed']['segments'])), len(cand)))
