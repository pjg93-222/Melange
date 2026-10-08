# -*- coding: utf-8 -*-
"""Corrected untagged-return sweep: ANY removed voice-over/on-camera segment (not only the last)
whose body NAMES the row member and whose second half carries a first-person clause -- the exact
shape of rowid 83061, which both earlier strata missed.  READ-ONLY, ledger only.
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


truncated = []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if line:
            r = json.loads(line)
            if not r['skip']:
                truncated.append(r)

BCAST = re.compile(r'\((?:voice[\s\-]?over|voiceover|on\s?camera|on-camera)\)', re.I)
FP = re.compile(r"\b(?:I|I'm|I've|I'd|my|we|we're|we've|our)\b", re.I)
cand = []
for r in truncated:
    msur = (norm(r['member']).split() or [''])[-1]
    if not msur or len(msur) < 4:
        continue
    for s in r['removed']['segments']:
        body = s['text'] or ''
        if not BCAST.search(s['tag'] or '') or len(body.split()) < 25:
            continue
        if msur not in norm(body).split():
            continue
        if FP.search(body[len(body) // 2:]):
            cand.append((r, s))
            break

out = io.open(OUTDIR + '/V3_untagged_return_sweep.txt', 'w', encoding='utf-8', newline='\n')
out.write('corrected untagged-return stratum: %d of %d truncated rows (%.2f%%)\n'
          % (len(cand), len(truncated), 100.0 * len(cand) / len(truncated)))
out.write('83061 captured: %s\n\n' % (83061 in {r['rowid'] for r, _ in cand}))
rnd = random.Random(20260920)
samp = sorted(rnd.sample(cand, min(30, len(cand))), key=lambda x: x[0]['rowid'])
out.write('sampled rowids: %s\n\n' % [r['rowid'] for r, _ in samp])
for i, (r, s) in enumerate(samp, 1):
    out.write('--- %02d rowid=%s member=%r show=%s  seg %r (%dw)\n'
              % (i, r['rowid'], r['member'], r['chamber'], s['tag'], s['nwords']))
    out.write('    KEPT ...%s\n' % r['kept']['text'][-130:])
    out.write('    SEG: %s\n\n' % (s['text'] or '')[:900])
out.close()
print('stratum=%d captured83061=%s' % (len(cand), 83061 in {r['rowid'] for r, _ in cand}))
