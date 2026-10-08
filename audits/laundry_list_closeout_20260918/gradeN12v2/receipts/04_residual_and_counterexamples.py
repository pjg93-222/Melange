# -*- coding: utf-8 -*-
"""Residual risk buckets + the v1 counter-examples (V4).  READ-ONLY, ledger only."""
import collections
import io
import json
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


rows = {}
truncated, skipped = [], []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        rows[r['rowid']] = r
        (skipped if r['skip'] else truncated).append(r)

out = io.open(OUTDIR + '/V2V4_residual_and_counterexamples.txt', 'w', encoding='utf-8',
              newline='\n')


def W(s=''):
    out.write(s + '\n')


def show(r, kepttail=260, remhead=300, label=''):
    W('  rowid=%-7s %-26s %-18s %s cut_class=%s' % (r['rowid'], r['member'][:26], r['date'],
                                                    label, r['cut_class']))
    W('     CUT_TAG=%r  kept=%sw  removed=%sw  orig=%sw'
      % (r['cut_tag'], r['kept']['nwords'], r['removed']['nwords'], r['original']['nwords']))
    W('     KEPT ...%s' % r['kept']['text'][-kepttail:])
    W('     GONE    %s' % r['removed']['raw'][:remhead])
    W()


# ---------------------------------------------- A. cut tags that NAME a Congress-style person
W('=' * 100)
W('A.  EVERY CUT TAG THAT NAMES A RANKED OFFICE-HOLDER (SEN./REP./GOV./DR.) -- is the tag the')
W("    ROW'S OWN MEMBER?  own_lenient() is supposed to make that impossible.")
W('=' * 100)
RANKED = re.compile(r'^\s*(?:\[\d[^\]]*\]\s*)?(?:\(\w+\)\s*)?'
                    r'(SEN\.|REP\.|SENATOR|REPRESENTATIVE|GOV\.|GOVERNOR|DR\.|FMR\.|DEL\.)', re.I)
selfhits = []
ranked_rows = [r for r in truncated if RANKED.match(r['cut_tag'] or '')]
W('rows whose cut tag starts with a rank: %d' % len(ranked_rows))
for r in ranked_rows:
    msur = (norm(r['member']).split() or [''])[-1]
    tagn = norm(r['cut_tag'])
    if msur and (msur in tagn.split() or msur in tagn.replace(' ', '')):
        selfhits.append(r['rowid'])
        show(r, label='*** SELF-TAG ***')
W('cut tags that contain the row member\'s own surname: %d  %s' % (len(selfhits), selfhits))
W()
W('distinct ranked cut tags with the row member beside them:')
seen = set()
for r in sorted(ranked_rows, key=lambda r: r['cut_tag']):
    k = (r['cut_tag'], r['member'])
    if k in seen:
        continue
    seen.add(k)
    W('   %-55s | member=%s' % (r['cut_tag'][:55], r['member']))
W()

# ------------------------------------------------------------- B. S4 residual buckets, read
TS = re.compile(r'\[\d{1,2}:\d{2}(?::\d{2})?\]\s*$')
PAREN_END = re.compile(r'\([^)]*\)\s*$')
DASH_END = re.compile(r'(?:--|—|-)\s*$')
TERMINAL, CLOSERS = '.?!…', '"”’\')]»'
buckets = collections.defaultdict(list)
for r in truncated:
    k = (r['kept']['text'] or '').rstrip()
    kk = k
    while kk and kk[-1] in CLOSERS:
        kk = kk[:-1].rstrip()
    if kk and kk[-1] in TERMINAL:
        continue
    if TS.search(k):
        core = TS.sub('', k).rstrip()
        while core and core[-1] in CLOSERS:
            core = core[:-1].rstrip()
        b = 'ts_after_terminal' if (core and core[-1] in TERMINAL) else 'ts_after_NONterminal'
    elif DASH_END.search(k):
        b = 'dash'
    elif PAREN_END.search(k):
        b = 'paren'
    elif k.endswith(','):
        b = 'comma'
    elif k.endswith(':') or k.endswith(';'):
        b = 'colon'
    else:
        b = 'bare_word'
    buckets[b].append(r)

W('=' * 100)
W('B.  S4 (kept text ends without terminal punctuation) -- EVERY row in the buckets that are')
W('    NOT the benign CNN-timestamp form, plus a 10-row read of each benign bucket.')
W('=' * 100)
for b in ('bare_word', 'comma', 'colon', 'ts_after_NONterminal', 'paren'):
    W('--- bucket %s: n=%d (ALL SHOWN)' % (b, len(buckets[b])))
    for r in buckets[b]:
        show(r, kepttail=220, remhead=220)
for b in ('dash', 'ts_after_terminal'):
    W('--- bucket %s: n=%d (first 8 shown)' % (b, len(buckets[b])))
    for r in buckets[b][:8]:
        show(r, kepttail=200, remhead=180)

# -------------------------------------------------------- C. X1 bare single-token cut tags
W('=' * 100)
W('C.  X1 cut tags that are ONE bare token (no honorific, no parenthetical): distinct list')
W('=' * 100)
HONre = re.compile(r'\b(?:SEN|REP|PRES|GOV|DR|FMR|AMB|DEL|MR|MS|MRS|SENATOR|REPRESENTATIVE|'
                   r'CONGRESSMAN|CONGRESSWOMAN|CHAIRMAN|CHAIRWOMAN|PRESIDENT|GOVERNOR|SPEAKER|'
                   r'SECRETARY|GENERAL|JUDGE|MAYOR)\b\.?', re.I)
x1 = collections.Counter()
x1ex = {}
for r in truncated:
    tag = r['cut_tag'] or ''
    toks = [w for w in re.split(r"[^A-Za-zÀ-ɏ'’`\-]+", tag) if w]
    core = [w for w in toks if not HONre.fullmatch(w)]
    if len(core) == 1 and not HONre.search(tag) and '(' not in tag:
        x1[tag] += 1
        x1ex.setdefault(tag, r['rowid'])
for t, n in x1.most_common():
    W('   %4d  %-28r example rowid=%s' % (n, t, x1ex[t]))
W()

# ------------------------------------------------------- D. X3 biggest blast radius (<=10%)
W('=' * 100)
W('D.  X3 rows where <=10%% of the words survive -- distinct cut tags')
W('=' * 100)
x3 = collections.Counter()
for r in truncated:
    b = int(r['original']['nwords'] or 0)
    if b and r['kept']['nwords'] / float(b) <= 0.10:
        x3[r['cut_tag']] += 1
for t, n in x3.most_common():
    W('   %4d  %r' % (n, t))
W()

# ---------------------------------------------------------- E. X5 class E long removals
W('=' * 100)
W('E.  X5 class-E (colon-less) rows removing >=25 words -- ALL %d shown'
  % sum(1 for r in truncated if r['cut_class'] == 'E_colonless_honorific'
        and r['removed']['nwords'] >= 25))
W('=' * 100)
for r in truncated:
    if r['cut_class'] == 'E_colonless_honorific' and r['removed']['nwords'] >= 25:
        show(r, kepttail=200, remhead=330)

# ------------------------------------------------------------------ F. V4 counter-examples
W('=' * 100)
W('F.  V4 -- the v1 counter-examples')
W('=' * 100)
for rid in (80238, 192027, 226287, 245558, 66969, 69544, 244993, 278454, 278528, 83061,
            68730, 102837, 104285, 108647, 111034, 242833, 70149, 83941, 192133, 193439,
            225128, 225771, 242500, 82055, 71147, 70812, 205497, 258713, 257343, 258736,
            258820, 258130, 225986, 174172, 274133, 69517):
    r = rows.get(rid)
    if r is None:
        W('  rowid=%-7s NOT FLAGGED AT ALL by v2 (no plan, no ledger record)' % rid)
        continue
    W('  rowid=%-7s %-24s %s  %s' % (rid, r['member'][:24], r['date'],
                                     'SKIPPED:' + str(r['skip']) if r['skip'] else 'TRUNCATED'))
    W('     cut_class=%s cut_tag=%r cut_at=%s' % (r['cut_class'], r['cut_tag'], r['cut_at']))
    W('     ALL_TAGS=%s' % json.dumps(r['all_tags'], ensure_ascii=False))
    W('     kept(%sw): %s' % (r['kept']['nwords'], r['kept']['text'][:300]))
    if r['kept']['text'][300:]:
        W('        ...tail: %s' % r['kept']['text'][-200:])
    W('     gone(%sw): %s' % (r['removed']['nwords'], r['removed']['raw'][:420]))
    W()

# curly apostrophe / no-space colon / FORMER U.S. censuses over the flagged set
W('--- v1 gap censuses, measured over the v2 ledger ---')
curly = [r for r in rows.values() if '’' in (r['cut_tag'] or '')]
W('rows whose CUT TAG carries a curly apostrophe U+2019: %d (truncated %d) e.g. %s'
  % (len(curly), sum(1 for r in curly if not r['skip']),
     sorted(r['rowid'] for r in curly)[:12]))
anytag_curly = [r for r in rows.values()
                if any('’' in t['tag'] for t in r['all_tags'])]
W('rows with ANY tag carrying U+2019: %d' % len(anytag_curly))
nospace = [r for r in rows.values()
           if any(re.search(re.escape(t['tag']) + r':\S', r['original']['text'])
                  for t in r['all_tags'])]
W('flagged rows carrying a NO-SPACE colon after one of their tags: %d (truncated %d)'
  % (len(nospace), sum(1 for r in nospace if not r['skip'])))
former = [r for r in rows.values() if 'FORMER U.S.' in (r['cut_tag'] or '').upper()]
W('rows whose cut tag contains "FORMER U.S.": %d -> %s'
  % (len(former), [(r['rowid'], r['cut_tag']) for r in former]))
frag = [r for r in truncated if (r['cut_tag'] or '').strip().upper() in
        ('PRESIDENT AND', 'PRESIDENT', 'VICE PRESIDENT', 'PRESIDENT OF THE UNITED')]
W('rows cut on the v1 fragment tag "PRESIDENT AND" or similar: %d -> %s'
  % (len(frag), [(r['rowid'], r['cut_tag']) for r in frag]))
pbs = [r for r in rows.values() if r['cut_class'] == 'D_mixed_case_label']
W('class D rows flagged: %d (truncated %d); distinct D cut tags: %d'
  % (len(pbs), sum(1 for r in pbs if not r['skip']),
     len({r['cut_tag'] for r in pbs})))
out.close()
print('written')
