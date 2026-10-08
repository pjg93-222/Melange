# -*- coding: utf-8 -*-
"""Final: systematic-hole sizing + graded CSVs + exact Clopper-Pearson intervals.  READ-ONLY."""
import io, json, math, re, sys, collections

PACK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
        r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\gradeN12'
        r'\receipts')
LEDGER = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
          r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\fixN12'
          r'\dry_run_ledger.jsonl')

rows = []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if line:
            rows.append(json.loads(line))
by_id = {r['rowid']: r for r in rows}


# ------------------------------------------------------------------ Clopper-Pearson
def _lbinom(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _cdf_le(k, n, p):
    """P(X <= k)."""
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0 if k < n else 1.0
    return sum(math.exp(_lbinom(n, i) + i * math.log(p) + (n - i) * math.log1p(-p))
               for i in range(0, k + 1))


def cp(k, n, conf=0.95):
    """Exact (Clopper-Pearson) two-sided interval for k successes of n."""
    a = (1.0 - conf) / 2.0
    lo, hi = 0.0, 1.0
    if k > 0:                       # P(X>=k|lo)=a  <=>  1-P(X<=k-1|lo)=a
        x0, x1 = 0.0, 1.0
        for _ in range(200):
            m = (x0 + x1) / 2
            if 1.0 - _cdf_le(k - 1, n, m) < a:
                x0 = m
            else:
                x1 = m
        lo = (x0 + x1) / 2
    if k < n:                       # P(X<=k|hi)=a
        x0, x1 = 0.0, 1.0
        for _ in range(200):
            m = (x0 + x1) / 2
            if _cdf_le(k, n, m) > a:
                x0 = m
            else:
                x1 = m
        hi = (x0 + x1) / 2
    return lo, hi


out = io.open(sys.argv[1], 'w', encoding='utf-8', newline='\n')


def w(s=''):
    out.write(s + '\n')


# ------------------------------------------------------------------ H1 systematic holes
w('=' * 100)
w('H1  THE PBS ANCHOR LABEL THAT CLASS D CANNOT SEE (non-ASCII letter / lower-case particle)')
ANCH = re.compile(r'(Laura Barr[o\u00f3]n-L[o\u00f3]pez|Fred de Sam Lazaro|Am?na Nawaz|'
                  r'Geoff Bennett|Nick Schifrin|William Brangham|Lisa Desjardins|'
                  r'John Yang|Stephanie Sy|Judy Woodruff)\s*:')
hits = collections.Counter()
rowhits = collections.defaultdict(list)
for r in rows:
    if r['skip']:
        continue
    for m in ANCH.finditer(r['kept']['text']):
        hits[m.group(1)] += 1
        rowhits[m.group(1)].append(r['rowid'])
w('    flagged rows whose KEPT text still contains a PBS anchor label:')
for k, v in hits.most_common():
    w('      %-26s %4d  e.g. %s' % (k, v, sorted(set(rowhits[k]))[:8]))
nrows = len({rid for ids in rowhits.values() for rid in ids})
w('    distinct rows affected: %d' % nrows)
w('    (all 40 class-D rows are pbs-newshour/csis/aei/aspensf; the shape is the anchor label,')
w('     and MIXED requires ASCII [A-Za-z] name tokens, so an accent or a "de" particle hides it)')

w()
w('=' * 100)
w('H2  THE "FORMER U.S. | PRESIDENT" CUT (an abbreviation period satisfies the sentence anchor)')
for r in rows:
    if r['skip']:
        continue
    k = r['kept']['text'].rstrip()
    if re.search(r'\b(?:U\.S\.|Jr\.|Sr\.|D\.C\.|Ph\.D\.)$', k):
        w('    rowid=%-7s member=%-22s kept ends %r  -> first tag %r'
          % (r['rowid'], r['member'], k[-60:], r['removed'][0]['tag'][:44]))

w()
w('=' * 100)
w('H3  CLASS C CUTS THAT LEAVE THE NEXT SPEAKER\'S NAME IN THE MEMBER\'S KEPT TEXT')
NAMEC = re.compile(r'(?:^|[.?!]\s)\s*([A-Z][A-Z\'`\-]{2,}(?:\s+[A-Z][A-Z\'`\-]{2,}){0,2}),\s*$')
n_c = 0
for r in rows:
    if r['skip']:
        continue
    m = NAMEC.search(r['kept']['text'].rstrip())
    if m:
        n_c += 1
        w('    rowid=%-7s member=%-22s kept ends %-28r -> tag %r'
          % (r['rowid'], r['member'], m.group(1), r['removed'][0]['tag'][:48]))
w('    rows: %d' % n_c)

# ------------------------------------------------------------------ G1 grades (hand, from text)
# label: C=correct speaker & clean | CD=correct speaker, label debris in the text |
#        PF=partial foreign (member's words + another speaker's words) | NS=not speech (pure label)
#        WS=wrong speaker (a different person entirely)
G1 = [
    (1, 66969, 'Patty Murray', 'C', 'oath response + presiding-officer instruction; Murray presided'),
    (2, 66973, 'Patty Murray', 'CD', "leading '. '"),
    (3, 68279, 'Carlos Gimenez', 'CD', "leading '; '"),
    (4, 68730, 'Maxine Waters', 'C', ''),
    (5, 68730, 'Adam Schiff', 'PF', "~75 of 100 words are the CNN anchor's copy ('Meanwhile, it appears Donald Trump is very close to picking his running mate...')"),
    (6, 68832, 'Bennie Thompson', 'C', ''),
    (7, 68832, 'Mike Quigley', 'C', ''),
    (8, 73089, 'Amy Klobuchar', 'C', 'teller reading the Virginia certificate'),
    (9, 75643, 'Alexandria Ocasio-Cortez', 'C', ''),
    (10, 79884, 'John Thune', 'CD', "leading '(voiceover): '"),
    (11, 80238, 'Bill Cassidy', 'NS', "the whole insert is the chyron: ', (R-KY) CHAIRMAN, SENATE COMMITTEE ON HEALTH, EDUCATION, LABOR &'"),
    (12, 82752, 'Richard Blumenthal', 'C', ''),
    (13, 84935, 'Eric Schmitt', 'CD', "leading '(R- '"),
    (14, 89101, 'Eric Burlison', 'CD', "leading '(R-Mop: '"),
    (15, 89353, 'Richard Blumenthal', 'C', ''),
    (16, 89961, 'Tim Scott', 'CD', "leading ', CHAIR, SENATE BANKING COMMITTEE::'"),
    (17, 91180, 'Susan Collins', 'C', ''),
    (18, 91491, 'Susan Collins', 'CD', "leading '; '"),
    (19, 102837, 'John Cornyn', 'CD', 'leading \', "THIS WEEK"/ABC, DEC. 17, 2017 :\''),
    (20, 102837, 'Chris Van Hollen', 'PF', "carries the next clip whole: 'UNIDENTIFIED MALE, MSNBC, AUG. 3, 2017: He enjoys very broad support...' + '(END VIDEO CLIPS)'"),
    (21, 104285, 'Tim Kaine', 'PF', "~66 of 81 words are Chuck Todd's ('CHUCK TODD:It's fair to say that no one has been more forceful...')"),
    (22, 104834, 'Pramila Jayapal', 'CD', "trailing '[END TAPE]'"),
    (23, 106351, 'Andy Kim', 'CD', "trailing '[END TAPE]'"),
    (24, 108647, 'Richard Durbin', 'PF', "leading ':' + ~85 of 170 words are Chuck Todd's next question"),
    (25, 108647, 'Richard Durbin', 'PF', "leading ':' + Chuck Todd's 'How do you enforce it?...'"),
    (26, 108647, 'Richard Durbin', 'PF', "leading ':' + Todd's sign-off 'Senator Dick Durbin, I have to leave it there...'"),
    (27, 108647, 'Richard Durbin', 'PF', "leading ':'; ~60 of 67 words are Todd's programming note ('By the way, NBC News will provide live coverage...')"),
    (28, 111034, 'Charles Schumer', 'PF', "leading ':' + ~78 of 122 words are Todd's question"),
    (29, 111034, 'Charles Schumer', 'PF', "leading ':' + ~54 of 269 words are Todd's question"),
    (30, 120706, 'Richard Durbin', 'CD', 'leading \', "STATE OF THE UNION"/CNN:\''),
    (31, 167914, 'Christopher Coons', 'CD', "leading ', D\u2014DELAWARE:'"),
    (32, 167914, 'Christopher Murphy', 'CD', "leading ', D\u2014CONNECTICUT:'"),
    (33, 187143, 'Christopher Murphy', 'CD', "leading ', D\u2014CONN.:'"),
    (34, 187143, 'Richard Blumenthal', 'CD', "leading ', D\u2014CONN.:'"),
    (35, 192027, 'Steve Scalise', 'NS', "the whole insert is the chyron: ', (R-LA), MINORITY WHIP, UNITED STATES HOUSE OF' (nwords=8, exactly at the floor)"),
    (36, 197182, 'Bernard Sanders', 'CD', "leading '; '"),
    (37, 198345, 'Tim Kaine', 'CD', 'leading \', "GMA"/ABC:\''),
    (38, 206687, 'Pramila Jayapal', 'C', ''),
    (39, 208795, 'Elizabeth Warren', 'CD', "leading ', PRESIDENTIAL CANDIDATE'"),
    (40, 215057, 'Josh Hawley', 'CD', "leading '(voice over): ' + trailing '[11:50:05]'"),
    (41, 215756, 'John Thune', 'CD', "leading '(Voice Over, Captioned): '"),
    (42, 218597, 'Alex Padilla', 'C', "own later turn, answers Lemon's question"),
    (43, 219462, 'Ralph Norman', 'CD', "leading '; '"),
    (44, 223251, 'Bennie Thompson', 'CD', "leading '(voice-over): ' + trailing '[03:55:02]'"),
    (45, 226287, 'Bennie Thompson', 'NS', "the whole insert is the chyron: ', CHAIR, U.S. HOUSE SELECT COMMITTEE ON JANUARY 6' (nwords=9)"),
    (46, 227229, 'Lindsey Graham', 'C', ''),
    (47, 230193, 'Thom Tillis', 'C', ''),
    (48, 241054, 'Tom Cotton', 'C', ''),
    (49, 242833, 'Richard Durbin', 'PF', "leading ', SENATE MAJORITY WHIP D-Ill.:' + ~215 of 262 words are Bret Baier's ('BRET BAIER, HOST OF \u201cSPECIAL REPORT\u201d: The omnibus spending bill...')"),
    (50, 243863, 'Don Bacon', 'C', ''),
    (51, 245558, 'Mike Johnson', 'WS', "a DIFFERENT Mike Johnson: 'My name is Mike Johnson. I'm the chief of conservation for Summit Metro Parks.' + trailing 'LISA KING,'"),
    (52, 245558, 'Mike Johnson', 'WS', 'same speaker: the Summit Metro Parks conservation chief, not the member'),
    (53, 245558, 'Mike Johnson', 'WS', 'same speaker: the Summit Metro Parks conservation chief, not the member'),
    (54, 245558, 'Mike Johnson', 'WS', 'same speaker: the Summit Metro Parks conservation chief, not the member'),
    (55, 245558, 'Mike Johnson', 'WS', 'same speaker: the Summit Metro Parks conservation chief, not the member'),
    (56, 249127, 'Pramila Jayapal', 'C', ''),
    (57, 253028, 'Pat Fallon', 'CD', "leading '(voice-over): '"),
    (58, 254901, 'John Kennedy', 'C', 'class D, clean'),
    (59, 260196, 'Nancy Pelosi', 'C', 'class D, clean'),
    (60, 260198, 'Nancy Pelosi', 'C', 'class D, clean'),
    (61, 265823, 'Bill Cassidy', 'CD', "leading ', (R) LOUISIANA;'"),
    (62, 273301, 'Elise Stefanik', 'CD', "leading '(voice over): '"),
    (63, 274112, 'Jeff Merkley', 'CD', "leading ':'"),
    (64, 274922, 'Pramila Jayapal', 'C', ''),
]

# ------------------------------------------------------------------ G2/G3 grades (hand)
# G2: CLEAN | KF=kept-foreign-words | CM=cut-member-words | UNC=unclear
# G3: NONE | SOME=some member words removed | UNC
G23 = [
    ('E', 102837, 'CLEAN', 'NONE', ''),
    ('E', 218527, 'CLEAN', 'NONE', 'removed text is a pure Fauci chyron'),
    ('E', 110238, 'CLEAN', 'NONE', ''),
    ('E', 217583, 'CLEAN', 'NONE', ''),
    ('E', 223251, 'CLEAN', 'NONE', ''),
    ('E', 307106, 'CLEAN', 'NONE', ''),
    ('E', 212286, 'CLEAN', 'NONE', ''),
    ('E', 80238, 'CLEAN', 'NONE', ''),
    ('E', 82055, 'KF', 'NONE', "kept still ends 'DONALD TRUMP (R), FORMER U.S.' - the cut fell INSIDE the next speaker's label"),
    ('E', 231698, 'CLEAN', 'NONE', ''),
    ('E', 91491, 'CLEAN', 'NONE', ''),
    ('E', 275908, 'CLEAN', 'NONE', ''),
    ('E', 69954, 'CLEAN', 'NONE', ''),
    ('E', 213957, 'CLEAN', 'NONE', ''),
    ('E', 70117, 'CLEAN', 'NONE', ''),
    ('E', 219771, 'CLEAN', 'NONE', ''),
    ('E', 66735, 'CLEAN', 'NONE', ''),
    ('E', 71147, 'KF', 'NONE', "kept still ends 'DONALD TRUMP (R), FORMER U.S.'"),
    ('E', 267967, 'CLEAN', 'NONE', ''),
    ('E', 198822, 'CLEAN', 'NONE', ''),
    ('D', 258736, 'KF', 'NONE', "~100 words of the PBS anchor stay: 'Laura Barron-Lopez: Again, those accusations are unsubstantiated...'"),
    ('D', 116271, 'CLEAN', 'NONE', ''),
    ('D', 254901, 'CLEAN', 'NONE', ''),
    ('D', 258820, 'KF', 'NONE', "~270 of 301 kept words are the anchor's ('Laura Barron-Lopez: Among the key things Zelenskyy asked for...')"),
    ('D', 305584, 'CLEAN', 'NONE', ''),
    ('D', 176057, 'CLEAN', 'NONE', ''),
    ('D', 175673, 'CLEAN', 'NONE', ''),
    ('D', 255829, 'CLEAN', 'NONE', ''),
    ('D', 258130, 'KF', 'NONE', "~180 of 281 kept words are the anchor's ('Laura Barron-Lopez: We asked every Republican senator...')"),
    ('D', 144501, 'CLEAN', 'NONE', ''),
    ('D', 256068, 'CLEAN', 'NONE', ''),
    ('D', 258150, 'CLEAN', 'NONE', ''),
    ('D', 137948, 'CLEAN', 'NONE', ''),
    ('D', 108613, 'CLEAN', 'NONE', ''),
    ('D', 257343, 'KF', 'NONE', "~95 of 114 kept words are the correspondent's ('Fred de Sam Lazaro: The plan would amend the Minneapolis charter...')"),
    ('D', 155292, 'CLEAN', 'NONE', ''),
    ('D', 258713, 'KF', 'NONE', "~80 of 92 kept words are the anchor's ('Laura Barron-Lopez: All the while, the war in Ukraine goes on...')"),
    ('D', 151413, 'CLEAN', 'NONE', ''),
    ('D', 257660, 'CLEAN', 'NONE', ''),
    ('D', 185172, 'CLEAN', 'NONE', ''),
    ('O', 225986, 'KF', 'NONE', 'WRONG PERSON already: the kept words are Daniel Webster of Johns Hopkins on Australian gun law, not Rep. Daniel Webster'),
    ('O', 216673, 'CLEAN', 'NONE', ''),
    ('O', 67279, 'CLEAN', 'NONE', ''),
    ('O', 238633, 'CLEAN', 'NONE', ''),
    ('O', 274164, 'CLEAN', 'NONE', ''),
    ('O', 239479, 'CLEAN', 'NONE', ''),
    ('O', 269045, 'CLEAN', 'NONE', ''),
    ('O', 262684, 'CLEAN', 'NONE', ''),
    ('O', 214224, 'CLEAN', 'NONE', ''),
    ('O', 89184, 'CLEAN', 'NONE', ''),
    ('O', 78939, 'CLEAN', 'NONE', ''),
    ('O', 273323, 'CLEAN', 'NONE', ''),
    ('O', 83061, 'CLEAN', 'SOME', "the removed PROKUPECZ voice-over ends with Dexter's OWN untagged words: 'The question is, are we being strategic? Are we being effective? And I would argue that being down there, taking a risk, that you become a player in this reality TV vision that Donald Trump has of Portland is a mistake.'"),
    ('O', 213722, 'CLEAN', 'NONE', ''),
    ('O', 205935, 'CLEAN', 'NONE', ''),
    ('O', 71608, 'CLEAN', 'NONE', ''),
    ('O', 242734, 'CLEAN', 'NONE', ''),
    ('O', 213548, 'CLEAN', 'NONE', ''),
    ('O', 206147, 'CLEAN', 'NONE', ''),
    ('O', 268184, 'CLEAN', 'NONE', ''),
]

# ------------------------------------------------------------------ write graded CSVs
with io.open(PACK + r'\G1_grades.csv', 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('insert_no,rowid,attributed_to,detector_class,disposition,grade,grade_long,note\n')
    ins = []
    for r in rows:
        for seg in r['removed']:
            if seg['disposition'] in ('reattributed', 'own_later_turn'):
                ins.append((r, seg))
    long = {'C': 'CORRECT-SPEAKER', 'CD': 'CORRECT-SPEAKER(label debris in text)',
            'PF': 'NOT-CORRECT:partial-foreign-words', 'NS': 'NOT-SPEECH',
            'WS': 'WRONG-SPEAKER'}
    for (no, rid, who, g, note), (r, seg) in zip(G1, ins):
        assert rid == r['rowid'] and (seg['speaker'] or '') == who, (no, rid, who, r['rowid'],
                                                                    seg['speaker'])
        fh.write('%d,%d,"%s",%s,%s,%s,"%s","%s"\n'
                 % (no, rid, who, seg['class'], seg['disposition'], g, long[g],
                    note.replace('"', "'")))
with io.open(PACK + r'\G2G3_grades.csv', 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('stratum,rowid,member,classes,g2_kept,g3_removed,note\n')
    for st, rid, g2, g3, note in G23:
        r = by_id[rid]
        fh.write('%s,%d,"%s","%s",%s,%s,"%s"\n'
                 % (st, rid, r['member'], '|'.join(r['classes']), g2, g3,
                    note.replace('"', "'")))

# ------------------------------------------------------------------ counts + intervals
w()
w('=' * 100)
w('G1  SPEAKER GRADE OF EVERY PLANNED INSERT (n=64)')
c1 = collections.Counter(g for _n, _r, _w, g, _x in G1)
for k in ('C', 'CD', 'PF', 'NS', 'WS'):
    w('    %-4s %-40s %d' % (k, long[k], c1[k]))
good = c1['C'] + c1['CD']
w('    speaker-correct (clean or debris-carrying)      : %d / 64' % good)
lo, hi = cp(good, 64)
w('    exact 95%% CI on the speaker-correct rate       : %.4f - %.4f' % (lo, hi))
bad = 64 - good
lo, hi = cp(bad, 64)
w('    NOT-CORRECT-SPEAKER (PF+NS+WS)                 : %d / 64  (%.1f%%), 95%% CI %.4f - %.4f'
  % (bad, 100.0 * bad / 64, lo, hi))
strict = c1['C']
lo, hi = cp(strict, 64)
w('    STRICTLY clean (no label debris at all)        : %d / 64, 95%% CI %.4f - %.4f'
  % (strict, lo, hi))
# class E split
eids = [(no, g) for (no, rid, who, g, note), (r, seg) in zip(G1, ins)
        if seg['class'] == 'E_colonless_honorific']
noneids = [(no, g) for (no, rid, who, g, note), (r, seg) in zip(G1, ins)
           if seg['class'] != 'E_colonless_honorific']
for name, grp in (('class E (colon-less)', eids), ('all other classes', noneids)):
    cc = collections.Counter(g for _n, g in grp)
    gd = cc['C'] + cc['CD']
    lo, hi = cp(gd, len(grp))
    w('    %-22s n=%-3d speaker-correct=%-3d (%s) 95%% CI %.4f - %.4f  | PF=%d NS=%d WS=%d'
      % (name, len(grp), gd, '%.1f%%' % (100.0 * gd / len(grp)), lo, hi,
         cc['PF'], cc['NS'], cc['WS']))

w()
w('=' * 100)
w('G2  KEPT TEXT (n=60, stratified 20 E / 20 D / 20 other)')
c2 = collections.Counter(g2 for _s, _r, g2, _g3, _n in G23)
w('    %s' % dict(c2))
clean = c2['CLEAN']
lo, hi = cp(clean, 60)
w('    CLEAN %d/60 = %.1f%%, exact 95%% CI %.4f - %.4f' % (clean, 100.0 * clean / 60, lo, hi))
lo, hi = cp(c2['KF'], 60)
w('    KEPT-FOREIGN-WORDS %d/60, exact 95%% CI %.4f - %.4f' % (c2['KF'], lo, hi))
w('    CUT-MEMBER-WORDS %d/60  (none found)' % c2['CM'])
for st in ('E', 'D', 'O'):
    sub = [g2 for s, _r, g2, _g3, _n in G23 if s == st]
    k = sub.count('CLEAN')
    lo, hi = cp(k, len(sub))
    w('      stratum %-2s CLEAN %2d/%d, exact 95%% CI %.4f - %.4f' % (st, k, len(sub), lo, hi))

w()
w('=' * 100)
w('G3  REMOVED TEXT (same 60 rows)')
c3 = collections.Counter(g3 for _s, _r, _g2, g3, _n in G23)
w('    %s' % dict(c3))
lo, hi = cp(c3['SOME'], 60)
w('    SOME-MEMBER-WORDS-REMOVED %d/60 = %.1f%%, exact 95%% CI %.4f - %.4f'
  % (c3['SOME'], 100.0 * c3['SOME'] / 60, lo, hi))
lo, hi = cp(c3['NONE'], 60)
w('    NONE %d/60, exact 95%% CI %.4f - %.4f' % (c3['NONE'], lo, hi))
w()
w('    second, independent read of the deletion risk: a seeded 30-row sample of the 174 deleted')
w('    segments that name the member AND carry a sentence-initial first person (receipt')
w('    G3G5_deletion_risk.txt) graded 1 SOME (rowid 244163, Warner\'s own written statement')
w('    quoted by the correspondent), 1 UNCLEAR (rowid 215035), 28 NONE.')
lo, hi = cp(1, 30)
w('    -> within that enriched risk stratum: 1/30, exact 95%% CI %.4f - %.4f' % (lo, hi))

w()
w('=' * 100)
w('G5  SCALING TO THE WHOLE MIGRATION')
for nm, k, n, scale in (('kept text not clean (G2)', c2['KF'] + c2['CM'], 60, 5859),
                        ('member words removed (G3)', c3['SOME'], 60, 5859)):
    lo, hi = cp(k, n)
    w('    %-28s %d/%d -> %.0f rows of %d  (95%% CI %.0f - %.0f rows)'
      % (nm, k, n, scale * k / float(n), scale, scale * lo, scale * hi))
w('    NOTE the G2/G3 sample is NOT a simple random sample of the 5,859: class D (40 rows) and')
w('    class E (289 rows) are over-sampled 30x and 2x. The stratum-weighted estimate of')
w('    "kept text not clean" is:')
wt = 0.0
for st, N in (('E', 289), ('D', 40), ('O', 5530)):
    sub = [g2 for s, _r, g2, _g3, _n in G23 if s == st]
    p = 1.0 - sub.count('CLEAN') / float(len(sub))
    wt += N * p
    w('      stratum %-2s N=%-5d bad rate %d/%d -> %.0f rows' % (st, N, len(sub) - sub.count('CLEAN'),
                                                                len(sub), N * p))
w('      weighted total: %.0f of 5,859 rows (%.1f%%)' % (wt, 100.0 * wt / 5859))
w('    INSERTS: %d of 64 are not CORRECT-SPEAKER -> the migration would create %d new rows'
  % (bad, bad))
w('      that carry words the attributed member did not say (3 pure chyron, 5 a different')
w('      Mike Johnson, 10 a member turn with another speaker\'s words glued on).')
out.close()
print(io.open(sys.argv[1], encoding='utf-8').read()[-6000:])
