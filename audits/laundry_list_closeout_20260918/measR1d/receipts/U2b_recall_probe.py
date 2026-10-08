# -*- coding: utf-8 -*-
"""measR1d U2b: RECALL probe for D-U2.

Grading the 40 unflagged rows turned up one real bleed the detector rejected:
rowid 235129 (Nancy Pelosi, ctw) ends "... It is quite sad. FOX (voice-over): Twenty holdouts
rally their support for ..." -- 'FOX' is in D-U2's STOP list, so the tag was discarded.

Rather than extrapolate a corpus figure from a single sample hit, this enumerates the residual
classes DIRECTLY, so the recall correction is a census and not an inference:

  R1  STOP-rejected tag that carries a PARENTHETICAL ((voice-over)/(on camera)/(through
      translator)/(voiceover)) -- the parenthetical is itself proof of a broadcast speaker tag,
      so a STOP name in front of one is a false rejection ('FOX (voice-over):').
  R2  single-token tag NOT in SPEAKER_LEX but carrying a parenthetical (unknown correspondent
      surname the lexicon never saw in full-name form).
  R3  qualifying tag + parenthetical whose ANCHOR failed -- it sits mid-sentence (after a comma,
      a quote, a bracketed timestamp, or simply after a word).
  R4  MIXED-CASE speaker tag ('Judy Woodruff:' / 'Rep. Tom Kean:') at a sentence start, in the
      legs that use MIXED_LABEL (PBS / CSIS / AEI / Aspen) -- D-U2 is ALL-CAPS-only and cannot
      see these at all.

Each class is counted, then a seeded (20260918) sample of up to 20 rows per class is written for
grading.  READ-ONLY.
"""
import collections, io, json, os, re, sqlite3, sys, unicodedata, random, csv

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
PK = HERE
DB = LIVE + r'\social_media.db'
SEED = 20260918

# reuse D-U2 exactly: execute the prelude of U2_row_census.py up to its pass-1 marker
src = io.open(os.path.join(HERE, 'U2_row_census.py'), encoding='utf-8').read()
cut = src.index('# ---------------------------------------------------------------- pass 1: lexicon')
H = {'__name__': '_u2'}
exec(compile(src[:cut], 'U2<prelude>', 'exec'), H)
TAG, STOP, tag_parts, is_upper_tag = H['TAG'], H['STOP'], H['tag_parts'], H['is_upper_tag']
allcaps_row, nrm, HONRE, ROSTER_SUR = H['allcaps_row'], H['nrm'], H['HONRE'], H['ROSTER_SUR']
NAMETOK, HON, PAREN = H['NAMETOK'], H['HON'], H['PAREN']

PARENTHETICAL = re.compile(r'\((?:voice[\s\-]?over|on\s?camera|through\s+(?:a\s+)?translator|'
                           r'voiceover|on\s?the\s?phone|via\s+\w+|audio|recorded|taped)\)', re.I)
# R3: same tag body, NO anchor requirement, but a parenthetical is MANDATORY (that is what keeps
# it from firing on "told CNN: ...").
TAG_NOANCHOR = re.compile(r'((?:' + HON + r'\s+)?' + NAMETOK + r'(?:\s+' + NAMETOK + r'){0,3}'
                          r"(?:\s*,\s*[A-Z][A-Za-z.'\- ]{1,60}?)?\s*\([^)]{1,30}\))\s*::?(?=\s|$)")
# R4: mixed-case label at a sentence start (the MIXED_LABEL shape, re-anchored for collapsed text)
MIXED = re.compile(r'(?:^|(?<=[.?!])|(?<=\-\-)|(?<=\u2014))[ ]{0,2}'
                   r"((?:Sen\.|Rep\.|Del\.|Gov\.|Dr\.|Speaker|Leader)?\s*"
                   r"[A-Z][a-z][A-Za-z.'\-]{1,20}(?:\s+[A-Z][a-z][A-Za-z.'\-]{1,20}){1,3}"
                   r"(?:\s*\([A-Za-z.\- ]{1,24}\))?):\s")
MIXED_LEGS = ('pbs-newshour', 'csis', 'aei', 'aspensf')

# recompute SPEAKER_LEX the same way U2 did (pass 1)
con = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
rows = con.execute("SELECT rowid, member, date, chamber, package, text FROM speeches "
                   "WHERE source='INTERVIEW'").fetchall()
con.close()
lex = collections.Counter()
for rid, mem, date, cham, pkg, txt in rows:
    if not txt or allcaps_row(txt):
        continue
    for m in TAG.finditer(txt):
        tag = m.group(1)
        if not is_upper_tag(tag):
            continue
        hon, up = tag_parts(tag)
        if len(up) >= 2 and not all(w in STOP for w in up):
            last = nrm(up[-1])
            if len(last) >= 3 and up[-1] not in STOP:
                lex[last] += 1
SPEAKER_LEX = set(ROSTER_SUR) | set(lex)


def qualifies(tag):
    hon, up = tag_parts(tag)
    if not up or all(w in STOP for w in up):
        return False
    nonstop = [w for w in up if w not in STOP]
    if hon or len(nonstop) >= 2:
        return True
    return len(up) == 1 and nrm(up[0]) in SPEAKER_LEX


fn_compat = H['fn_compat']


def is_self(tag, member):            # byte-identical logic to U2_row_census.is_self
    hon, up = tag_parts(tag)
    if not up:
        return False
    mp = nrm(member).split()
    if not mp:
        return False
    msur, mfirst = mp[-1], mp[0]
    tn = [nrm(w) for w in up if nrm(w)]
    if msur not in tn:
        return False
    if len(tn) >= 2:
        cand = [t for t in tn if t != msur]
        return any(fn_compat(t, mfirst) for t in cand) or len(cand) == 0
    return True

flagged = {r['rowid'] for r in json.load(io.open(os.path.join(PK, 'U2_flagged_rows.json'),
                                                 encoding='utf-8'))}
cls = collections.defaultdict(list)
for rid, mem, date, cham, pkg, txt in rows:
    t = txt or ''
    if not t or allcaps_row(t) or rid in flagged:
        continue
    hitR1 = hitR2 = hitR3 = hitR4 = None
    for m in TAG.finditer(t):
        tag = m.group(1)
        if not is_upper_tag(tag) or is_self(tag, mem):
            continue
        if qualifies(tag):
            continue                      # would already have flagged the row
        if not PARENTHETICAL.search(tag):
            continue
        hon, up = tag_parts(tag)
        if up and all(w in STOP for w in up):
            hitR1 = hitR1 or (m.start(1), tag)
        elif len(up) == 1:
            hitR2 = hitR2 or (m.start(1), tag)
    if hitR1 is None and hitR2 is None:
        for m in TAG_NOANCHOR.finditer(t):
            tag = m.group(1)
            if not is_upper_tag(tag) or is_self(tag, mem):
                continue
            hon, up = tag_parts(tag)
            if not up or all(w in STOP for w in up):
                continue
            if TAG.match(t, max(0, m.start(1) - 2)):
                continue
            hitR3 = (m.start(1), tag)
            break
    if cham in MIXED_LEGS:
        for m in MIXED.finditer(t):
            lab = m.group(1)
            p = nrm(lab).split()
            if not p or len(p) < 2:
                continue
            mp = nrm(mem).split()
            if mp and mp[-1] in p:
                continue
            if any(w.upper() in STOP for w in p):
                continue
            hitR4 = (m.start(1), lab)
            break
    for name, hit in (('R1', hitR1), ('R2', hitR2), ('R3', hitR3), ('R4', hitR4)):
        if hit:
            cls[name].append(dict(rowid=rid, member=mem, date=date, show=cham,
                                  tag=' '.join(hit[1].split()), at=hit[0], nchars=len(t), text=t))

NON_ALLCAPS = sum(1 for r in rows if r[5] and not allcaps_row(r[5]))
UNFLAGGED = NON_ALLCAPS - len(flagged)
print('INTERVIEW rows %d | non-all-caps %d | D-U2 flagged %d | unflagged %d'
      % (len(rows), NON_ALLCAPS, len(flagged), UNFLAGGED))
print()
DESC = {'R1': 'STOP-name tag WITH a broadcast parenthetical (e.g. "FOX (voice-over):")',
        'R2': 'single-token tag not in SPEAKER_LEX, WITH a parenthetical',
        'R3': 'qualifying tag + parenthetical whose SENTENCE ANCHOR failed (mid-sentence)',
        'R4': 'MIXED-CASE label at a sentence start, in PBS/CSIS/AEI/Aspen rows'}
seen_any = set()
for k in ('R1', 'R2', 'R3', 'R4'):
    ids = {r['rowid'] for r in cls[k]}
    seen_any |= ids
    print('%s  rows=%5d  (%.3f%% of unflagged)   %s' % (k, len(ids), 100.0 * len(ids) / UNFLAGGED, DESC[k]))
    for tg, n in collections.Counter(r['tag'] for r in cls[k]).most_common(8):
        print('        %5d  %s' % (n, tg[:64]))
print()
print('UNION of R1-R4 (distinct rows): %d  (%.3f%% of unflagged)'
      % (len(seen_any), 100.0 * len(seen_any) / UNFLAGGED))
print('D-U2 flagged + R1-R4 union     : %d  (%.3f%% of %d INTERVIEW rows)'
      % (len(flagged) + len(seen_any), 100.0 * (len(flagged) + len(seen_any)) / len(rows), len(rows)))

rnd = random.Random(SEED)
for k in ('R1', 'R2', 'R3', 'R4'):
    uniq = {}
    for r in sorted(cls[k], key=lambda x: x['rowid']):
        uniq.setdefault(r['rowid'], r)
    pool = list(uniq.values())
    s = rnd.sample(pool, 20) if len(pool) > 20 else pool
    p = os.path.join(PK, 'U2b_%s_sample_UNGRADED.csv' % k)
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['n', 'rowid', 'member', 'date', 'show', 'tag', 'at', 'nchars', 'GRADE', 'note', 'text'])
        for i, r in enumerate(s, 1):
            w.writerow([i, r['rowid'], r['member'], r['date'], r['show'], r['tag'], r['at'],
                        r['nchars'], '', '', ' '.join(r['text'].split())])
    print('wrote U2b_%s_sample_UNGRADED.csv (%d of %d)' % (k, len(s), len(pool)))
with io.open(os.path.join(PK, 'U2b_residual_rows.json'), 'w', encoding='utf-8') as f:
    json.dump({k: [{kk: vv for kk, vv in r.items() if kk != 'text'} for r in v]
               for k, v in cls.items()}, f, ensure_ascii=False, indent=1)
print('DONE U2b')
