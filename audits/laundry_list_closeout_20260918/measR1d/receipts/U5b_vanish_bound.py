# -*- coding: utf-8 -*-
"""measR1d U5b: adversarial bound on the VANISH count, plus D-U2 negative controls.

U5 assumed every mention at/after a row's FIRST foreign tag lands in a non-member segment.  That
over-counts when the row later returns to the member ("MEMBER: ... HOST: ... MEMBER: ..."), because
a SELF tag after the foreign tag restores the member as speaker.  This measures that exact
over-count instead of waving at it, and prints the structured-ingest negative controls.  READ-ONLY.
"""
import collections, io, json, os, re, sqlite3, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
REFS = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
        r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
        r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB\refs.jsonl')

s = io.open(os.path.join(HERE, 'U2_row_census.py'), encoding='utf-8').read()
cut = s.index('# ---------------------------------------------------------------- pass 1: lexicon')
H = {'__name__': '_u2'}
exec(compile(s[:cut], 'U2<prelude>', 'exec'), H)
TAG, STOP, tag_parts, is_upper_tag = H['TAG'], H['STOP'], H['tag_parts'], H['is_upper_tag']
nrm, allcaps_row, ROSTER_SUR = H['nrm'], H['allcaps_row'], H['ROSTER_SUR']

con = sqlite3.connect('file:%s?mode=ro' % (LIVE + r'\social_media.db').replace('\\', '/'), uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
rows = con.execute("SELECT rowid, member, source, chamber, text FROM speeches").fetchall()
con.close()

lex = collections.Counter()
for rid, mem, srcv, cham, txt in rows:
    if srcv != 'INTERVIEW' or not txt or allcaps_row(txt):
        continue
    for m in TAG.finditer(txt):
        tg = m.group(1)
        if not is_upper_tag(tg):
            continue
        hon, up = tag_parts(tg)
        if len(up) >= 2 and not all(w in STOP for w in up):
            last = nrm(up[-1])
            if len(last) >= 3 and up[-1] not in STOP:
                lex[last] += 1
LEX = set(ROSTER_SUR) | set(lex)


def qual(tg):
    hon, up = tag_parts(tg)
    if not up or all(w in STOP for w in up):
        return False
    ns = [w for w in up if w not in STOP]
    if hon or len(ns) >= 2:
        return True
    return len(up) == 1 and nrm(up[0]) in LEX


FL = {r['rowid']: r for r in json.load(io.open(os.path.join(HERE, 'U2_flagged_rows.json'), encoding='utf-8'))}
# for every flagged row, find the first SELF tag strictly after the first foreign tag
restore = {}
multi = 0
for rid, mem, srcv, cham, txt in rows:
    if rid not in FL or not txt:
        continue
    b0 = FL[rid]['first_at']
    msur = (nrm(mem).split() or [''])[-1]
    tags = []
    for m in TAG.finditer(txt):
        tg = m.group(1)
        if not is_upper_tag(tg) or not qual(tg):
            continue
        hon, up = tag_parts(tg)
        tags.append((m.start(1), m.end(0), tg, msur in [nrm(w) for w in up]))
    if len(tags) > 1:
        multi += 1
    for st, en, tg, slf in tags:
        if st > b0 and slf:
            restore[rid] = en
            break
print('flagged rows                                  : %d' % len(FL))
print('flagged rows with >1 qualifying tag            : %d' % multi)
print('flagged rows where a SELF tag follows the first foreign tag (speaker restored): %d'
      % len(restore))

vanish_total = 0
vanish_restored = 0
for line in io.open(REFS, encoding='utf-8'):
    r = json.loads(line)
    if r.get('src') != 'INTERVIEW':
        continue
    sid = r.get('_sid')
    if sid not in FL:
        continue
    pos = (r.get('_pos') or 1) - 1
    if pos < FL[sid]['first_at']:
        continue
    vanish_total += 1
    if sid in restore and pos >= restore[sid]:
        vanish_restored += 1
print()
print('mentions at/after the first foreign tag        : %d' % vanish_total)
print('   of those inside a RESTORED (self-tag) segment -> would NOT vanish: %d' % vanish_restored)
print('   net mentions genuinely mis-attributed today : %d' % (vanish_total - vanish_restored))

print()
print('=== NEGATIVE CONTROLS: D-U2 on corpora where no broadcast bleed should exist ===')
agg = collections.Counter()
tot = collections.Counter()
for rid, mem, srcv, cham, txt in rows:
    t = txt or ''
    if not t or allcaps_row(t):
        continue
    if srcv == 'INTERVIEW':
        key = 'INTERVIEW/' + ('c-span' if cham == 'washington-journal' or cham == 'cspan-wj' else
                              'pbs' if cham == 'pbs-newshour' else
                              'npr' if cham.startswith('npr-') else
                              'hewitt' if cham == 'hugh-hewitt' else 'other')
    else:
        key = srcv
    tot[key] += 1
    msur = (nrm(mem).split() or [''])[-1]
    for m in TAG.finditer(t):
        tg = m.group(1)
        if not is_upper_tag(tg) or not qual(tg):
            continue
        hon, up = tag_parts(tg)
        if msur in [nrm(w) for w in up]:
            continue
        agg[key] += 1
        break
for k in sorted(tot):
    print('  %-22s %8d rows  %7d flagged  %7.3f%%' % (k, tot[k], agg[k], 100.0 * agg[k] / tot[k]))
print('DONE U5b')
