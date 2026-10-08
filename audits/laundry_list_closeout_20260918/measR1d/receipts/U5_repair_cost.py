# -*- coding: utf-8 -*-
"""measR1d U5: what a splitter repair would COST downstream, measured not guessed.

The reference layer's window is  w = text[pos-170 : pos+200]  (member_reference_layer.py:130) and
its cache key is  sha256(['reference-window-v2', a, b, w[:400]])  (fec/members/reference_cache.py:9-11).
So a window whose TEXT changes is a NEW key -- a cache MISS.  --rebuild is free but a missed window
contributes to n_raw only and carries no valence (member_reference_layer.py:22, :247-267); restoring
signed support needs the paid --score pass at ~$0.006/context under DYAD_CAP=4 (:205, :270).

This replays every INTERVIEW mention lane B re-derived (its refs.jsonl, an audit artifact -- no fec
module is imported or executed) against the U2 split points and classifies each mention:
   VANISH  - the mention sits at/after the first foreign tag, so after the split it belongs to a
             segment whose speaker is NOT a roster member -> extract() drops it (`if spk not in C`)
   REASSIGN- same, but the foreign tag NAMES a roster member -> the mention survives with a
             DIFFERENT speaker a (new dyad, new key)
   TRUNC   - the mention sits before the tag but its +200-char tail crosses the split -> window
             text shrinks -> new key -> cache miss
   SAME    - window text unchanged -> existing cached label still applies
READ-ONLY.
"""
import collections, io, json, os, re, sqlite3, sys, unicodedata

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
REFS = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
        r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
        r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB\refs.jsonl')

src = io.open(os.path.join(HERE, 'U2_row_census.py'), encoding='utf-8').read()
cut = src.index('# ---------------------------------------------------------------- pass 1: lexicon')
H = {'__name__': '_u2'}
exec(compile(src[:cut], 'U2<prelude>', 'exec'), H)
nrm = H['nrm']
ROSTER = {m['member'] for m in json.load(io.open(LIVE + r'\data\engine\congestion.json', encoding='utf-8'))}
SUR2MEM = collections.defaultdict(set)
for m in ROSTER:
    p = nrm(m).split()
    if p:
        SUR2MEM[p[-1]].add(m)

FL = {r['rowid']: r for r in json.load(io.open(os.path.join(HERE, 'U2_flagged_rows.json'), encoding='utf-8'))}
AFF = set(json.load(io.open(os.path.join(HERE, 'U2c_all_affected_ids.json'), encoding='utf-8')))
print('U2 flagged rows with a measured split offset : %d' % len(FL))
print('all U2-affected rows (incl. R1-R5 residual)   : %d' % len(AFF))

con = sqlite3.connect('file:%s?mode=ro' % (LIVE + r'\social_media.db').replace('\\', '/'), uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
TXT = {rid: (t or '') for rid, t in con.execute(
    "SELECT rowid, text FROM speeches WHERE source='INTERVIEW'")}
con.close()

cls = collections.Counter()
scored = collections.Counter()
dyads = collections.defaultdict(set)
examples = []
n_iv = 0
for line in io.open(REFS, encoding='utf-8'):
    r = json.loads(line)
    if r.get('src') != 'INTERVIEW':
        continue
    n_iv += 1
    sid = r.get('_sid')
    f = FL.get(sid)
    if f is None:
        cls['SAME (row not flagged)'] += 1
        continue
    t = TXT.get(sid, '')
    b0 = f['first_at']
    pos = (r.get('_pos') or 1) - 1
    lit = r.get('_lit') or ''
    wstart, wend = max(0, pos - 170), pos + 200
    if pos >= b0:
        tagtoks = [nrm(w) for w in re.split(r'[^A-Za-z]+', f['first_tag']) if w]
        named = {m for tk in tagtoks for m in SUR2MEM.get(tk, set())}
        k = 'REASSIGN (tag names a roster member: %s)' % (sorted(named)[0] if named else '')
        k = k if named else 'VANISH (segment speaker off-roster)'
        cls[k.split(' (')[0]] += 1
        if r.get('_counted_scored'):
            scored[k.split(' (')[0]] += 1
        dyads[k.split(' (')[0]].add((r['a'], r['b']))
        if len(examples) < 8:
            examples.append((k, sid, r['a'], r['b'], f['first_tag'], ' '.join(r['w'].split())[:150]))
    elif wend > b0:
        cls['TRUNC'] += 1
        if r.get('_counted_scored'):
            scored['TRUNC'] += 1
        dyads['TRUNC'].add((r['a'], r['b']))
    else:
        cls['SAME (flagged row, window before split)'] += 1
        if r.get('_counted_scored'):
            scored['SAME (flagged row, window before split)'] += 1

print()
print('INTERVIEW mentions in lane B refs.jsonl: %d' % n_iv)
print()
print('%-42s %8s %8s %8s' % ('outcome after the repair', 'windows', 'of which', 'dyads'))
print('%-42s %8s %8s %8s' % ('', '', 'SCORED', ''))
for k in sorted(cls, key=lambda x: -cls[x]):
    print('%-42s %8d %8d %8d' % (k, cls[k], scored.get(k, 0), len(dyads.get(k, ()))))
CHANGED = cls.get('VANISH', 0) + cls.get('REASSIGN', 0) + cls.get('TRUNC', 0)
CHANGED_SCORED = scored.get('VANISH', 0) + scored.get('REASSIGN', 0) + scored.get('TRUNC', 0)
print()
print('windows whose TEXT/SPEAKER changes -> cache MISS : %d' % CHANGED)
print('   of those currently inside n_scored (paid label now wasted): %d' % CHANGED_SCORED)
print('new windows needing a paid label to keep signed support       : %d (REASSIGN+TRUNC only; '
      'VANISH windows disappear and need nothing)' % (cls.get('REASSIGN', 0) + cls.get('TRUNC', 0)))
print('est --score cost at $0.006/context (member_reference_layer.py:205,:270): $%.2f'
      % (0.006 * (cls.get('REASSIGN', 0) + cls.get('TRUNC', 0))))
print()
print('examples:')
for k, sid, a, b, tg, w in examples:
    print('  %-52s sid=%-7s %s -> %s' % (k[:52], sid, a, b))
    print('      %s' % w)
print('DONE U5')
