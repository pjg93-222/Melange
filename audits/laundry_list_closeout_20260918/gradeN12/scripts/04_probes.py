# -*- coding: utf-8 -*-
"""Adversarial mechanical probes over the whole ledger + corpus-wide gap sizing.  READ-ONLY."""
import io, json, re, sqlite3, collections, sys

LEDGER = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
          r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\fixN12'
          r'\dry_run_ledger.jsonl')
DB = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems/social_media.db'

rows = []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if line:
            rows.append(json.loads(line))

out = io.open(sys.argv[1], 'w', encoding='utf-8', newline='\n')


def w(s=''):
    out.write(s + '\n')


# ---------------------------------------------------------------- P1: kept-text cut quality
# Classes A/D/E are sentence-anchored, so a correct cut leaves the kept text ending on a
# terminator.  Class C is UNANCHORED and can cut mid-sentence.
TERM = re.compile(r'(?:[.?!]["\u201d\']?|--|\u2014|>>|\))\s*$')
bad_cut = collections.Counter()
bad_cut_rows = collections.defaultdict(list)
for r in rows:
    if r['skip']:
        continue
    kept = r['kept']['raw']
    first = r['removed'][0]
    if not TERM.search(kept.rstrip()):
        bad_cut[first['class']] += 1
        bad_cut_rows[first['class']].append(r['rowid'])
w('=' * 100)
w('P1  KEPT TEXT DOES NOT END ON A SENTENCE TERMINATOR (mid-sentence cut candidates)')
w('    by the class of the FIRST removed segment:')
for k, v in sorted(bad_cut.items()):
    w('      %-28s %5d   e.g. %s' % (k, v, bad_cut_rows[k][:12]))
w('    total %d of %d non-skipped rows' % (sum(bad_cut.values()), len([r for r in rows
                                                                      if not r['skip']])))

# ---------------------------------------------------------------- P2: label debris in kept text
w()
w('=' * 100)
w('P2  KEPT TEXT ENDS WITH WHAT LOOKS LIKE THE START OF A LABEL (leading edge of a foreign tag)')
LOOSE_TAIL = re.compile(r'(?:^|[\s.?!])([A-Z][A-Z\'`.\-]{1,20}(?:\s+[A-Z][A-Z\'`.\-]{1,20}){0,3},?)\s*$')
n = 0
ex = []
for r in rows:
    if r['skip']:
        continue
    m = LOOSE_TAIL.search(r['kept']['raw'].rstrip())
    if m and len(m.group(1).strip(' ,')) > 2:
        n += 1
        if len(ex) < 25:
            ex.append((r['rowid'], m.group(1), r['removed'][0]['class'],
                       r['removed'][0]['tag'][:40]))
w('    rows whose kept text ends in an ALL-CAPS run: %d' % n)
for e in ex:
    w('      rowid=%-7s trailing=%-34r next_class=%-24s next_tag=%r' % e)

# ---------------------------------------------------------------- P3: debris at the START of a
# removed/inserted segment (label remainder the class could not consume)
w()
w('=' * 100)
w('P3  SEGMENT TEXT STARTS WITH LABEL DEBRIS (punctuation / party / role tail / paren)')
DEBRIS = re.compile(r'^\s*(?:[,;:.\)]|\((?:[Vv]oice|VOICE|[Oo]n\s?camera|[Rr]ecorded)|'
                    r'\(?[RDI][\)\-,]|CHAIR|,\s*[A-Z])')
deb = collections.Counter()
deb_ins = collections.Counter()
deb_rows = collections.defaultdict(list)
for r in rows:
    for seg in r['removed']:
        if DEBRIS.match(seg['text']):
            deb[seg['class']] += 1
            if seg['disposition'] in ('reattributed', 'own_later_turn'):
                deb_ins[seg['class']] += 1
                deb_rows[seg['class']].append((r['rowid'], seg['text'][:60]))
w('    ALL segments with leading debris, by class: %s (total %d)'
  % (dict(deb), sum(deb.values())))
w('    of those, segments that WOULD BE INSERTED : %s (total %d)'
  % (dict(deb_ins), sum(deb_ins.values())))
for cls, items in sorted(deb_rows.items()):
    for rid, t in items:
        w('      INSERT rowid=%-7s %-26s %r' % (rid, cls, t))

# ---------------------------------------------------------------- P4: an UNCAUGHT speaker label
# inside a segment that would be inserted (foreign words travelling into the new row)
w()
w('=' * 100)
w('P4  AN APPARENT SPEAKER LABEL SURVIVES *INSIDE* A SEGMENT THAT WOULD BE INSERTED')
INNER = re.compile(r'(?<=[.?!\u2014>\)\-])\s{0,2}((?:[A-Z][A-Z\'`.\-]{1,20})'
                   r'(?:[ ,]+[A-Z][A-Za-z\'`.\-\u201c\u201d"/&]{0,24}){0,6})\s*:')
for r in rows:
    for i, seg in enumerate(r['removed'], 1):
        if seg['disposition'] not in ('reattributed', 'own_later_turn'):
            continue
        hits = [m.group(1) for m in INNER.finditer(seg['text'])]
        hits = [h for h in hits if h.strip()]
        if hits:
            w('    rowid=%-7s seg%-2d -> %-24s class=%-24s inner labels=%s'
              % (r['rowid'], i, seg['speaker'], seg['class'], hits[:6]))

# ---------------------------------------------------------------- P5: corpus-wide gap sizing
w()
w('=' * 100)
w('P5  GAPS THE GRAMMAR CANNOT SEE AT ALL (corpus-wide, INTERVIEW rows)')
con = sqlite3.connect('file:%s?mode=ro' % DB, uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
flagged = {r['rowid'] for r in rows}
NOSPACE = re.compile(r'(?<=[.?!\u2014])\s{0,2}([A-Z][A-Z\'`.\-]{2,20}(?:\s+[A-Z][A-Z\'`.\-]{1,20}){0,3}):(?=[A-Za-z])')
QCOLON = re.compile(r'(?<=[.?!\u201d\)])\s{1,2}Q:\s')
UNID = re.compile(r'\bUNIDENTIFIED\s+(?:MALE|FEMALE|VOICE|SPEAKER)\b')
c_nospace = c_q = c_unid = 0
ex_nospace, ex_q, ex_unid = [], [], []
tot = 0
for rid, txt in con.execute("SELECT rowid,text FROM speeches WHERE source='INTERVIEW'"):
    tot += 1
    if not txt:
        continue
    if NOSPACE.search(txt):
        c_nospace += 1
        if rid not in flagged and len(ex_nospace) < 8:
            ex_nospace.append((rid, NOSPACE.search(txt).group(1)))
    if QCOLON.search(txt):
        c_q += 1
        if rid not in flagged and len(ex_q) < 8:
            ex_q.append((rid, txt[:90]))
    if UNID.search(txt):
        c_unid += 1
        if rid not in flagged and len(ex_unid) < 8:
            ex_unid.append((rid, UNID.search(txt).group(0)))
w('    INTERVIEW rows scanned: %d   (flagged by the migration: %d)' % (tot, len(flagged)))
w('    "NAME:" with NO space after the colon (NBC/MTP shape, invisible to TAG): %d rows' % c_nospace)
w('        unflagged examples: %s' % ex_nospace)
w('    a bare "Q: " questioner turn (CFR/PBS shape, never qualifies)          : %d rows' % c_q)
w('        unflagged examples: %s' % [e[0] for e in ex_q])
w('    an "UNIDENTIFIED MALE/FEMALE" label present                            : %d rows' % c_unid)
w('        unflagged examples: %s' % ex_unid)

# ---------------------------------------------------------------- P6: tags that swallow filler
w()
w('=' * 100)
w('P6  TAGS WHOSE FIRST TOKEN IS FILLER, NOT A NAME (the tag ate the member\'s own words)')
FILLER = frozenset(('OK.', 'OK', 'YES.', 'YES', 'NO.', 'NO', 'SO', 'AND', 'BUT', 'WELL',
                    'RIGHT.', 'RIGHT', 'THANK', 'THANKS', 'Q', 'A', 'I', 'YEAH', 'YEAH.',
                    'ALL', 'NOW', 'THAT'))
hits = []
for r in rows:
    for i, seg in enumerate(r['removed'], 1):
        first_tok = (seg['tag'] or '').split()
        if first_tok and first_tok[0].upper().strip(",") in FILLER:
            hits.append((r['rowid'], seg['class'], seg['tag'][:50], seg['disposition'],
                         r['kept']['nwords'], r['skip']))
w('    segments whose tag starts with a filler token: %d' % len(hits))
for h in hits[:60]:
    w('      rowid=%-7s %-24s tag=%-52r %-26s kept_nw=%-4s skip=%r' % h)
con.close()
out.close()
print('done')
