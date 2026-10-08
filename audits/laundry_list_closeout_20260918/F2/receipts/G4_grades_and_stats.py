# -*- coding: utf-8 -*-
"""F2 G4: my hand grades for all four samples, exact Clopper-Pearson intervals, the scaled
wrong-edge estimates, and the EXACT count of drawn edges that would lose all scored support.

Grading rules applied (from the lane brief):
  P2-A hits  : TRUE-BLEED = the mention sits in a different person's turn, so the DB-attributed
               speaker did not say it / GENUINE = the attributed speaker really refers to the
               target / UNCLEAR.
  P3b hits   : ARTEFACT = the name sits inside a vote roster, signature block or co-signer list,
               not a reference by the speaker / GENUINE / UNCLEAR.
  Recall probes are graded on the same scale over UNFLAGGED windows: a TRUE-BLEED / ARTEFACT
  there is a detector MISS.
Two extra, independently recorded tags on the P2-A hits, because they change the reading:
  marker_valid = the matched marker really is an undivided turn boundary (vs a spurious
                 honorific/heading match); bleed_class = INTERVIEW_TURN vs DOC_STRUCTURE
                 (a CHRG/CREC row that is a whole printed document, not a broadcast turn).
clopper_pearson() is lane B's own function, exec'd from 05b_p3_graded.py -- not reimplemented.
READ-ONLY; writes only into F2/receipts."""
import collections, csv, io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
LB = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\laneB\receipts')
PK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\F2\receipts')
SCRATCH_LB = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
              r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
              r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB')

s5 = io.open(os.path.join(LB, '05b_p3_graded.py'), encoding='utf-8').read()
G = {'__name__': '_cp'}
exec(compile(s5[s5.index('def clopper_pearson('):s5.index('samp = json.load(')], '05b<cp>', 'exec'), G)
cp = G['clopper_pearson']

# ----------------------------------------------------------------------------------------------
# G2  P2-A hits, n=40.  Every row graded TRUE-BLEED.  (mv = marker_valid, cls = bleed_class)
# ----------------------------------------------------------------------------------------------
TB, GEN, UNC = 'TRUE-BLEED', 'GENUINE', 'UNCLEAR'
AR = 'ARTEFACT'
IT, DS = 'INTERVIEW_TURN', 'DOC_STRUCTURE'
G2 = {
 1: (TB, False, DS, 'CHRG full hearing print: mention is the QFR header "Questions Submitted by Senator John Boozman"; not Collins. Marker "FMR. HUD" is Fair Market Rent + HUD, not a turn tag.'),
 2: (TB, True, IT, 'After "COLLINS (on camera):" -- CNN reporter Kaitlan Collins narrating, signs off "Kaitlan Collins, CNN"; not Kennedy.'),
 3: (TB, True, DS, 'Mention sits inside "PREPARED STATEMENT OF SENATOR SHERROD BROWN"; the McConnell jab is Brown\'s, not Crapo\'s.'),
 4: (TB, True, IT, 'Mention IS the speaker tag "SEN. SUSAN COLLINS (R-ME)" opening Collins\'s own quoted turn.'),
 5: (TB, True, IT, 'After "LEE (on camera):" -- CNN reporter narration about Cornyn; not Crenshaw.'),
 6: (TB, True, IT, 'After "SULLIVAN (voice-over):" -- reporter package ending "I\'m Jenn Sullivan reporting"; not Warren.'),
 7: (TB, True, IT, 'After "JESSICA SCHNEIDER, CNN JUSTICE CORRESPONDENT (voice-over):" -- reporter narration; not Cruz.'),
 8: (TB, True, DS, 'Mention is the header "PREPARED STATEMENT OF SENATOR CYNTHIA LUMMIS", i.e. Lummis\'s own statement; not Smith.'),
 9: (TB, True, IT, 'After "SCHNEIDER (voice-over):" -- reporter narration about Cornyn\'s tweet; not McConnell.'),
 10: (TB, True, IT, 'Canonical July case: mention is the tag "SEN. RICHARD BLUMENTHAL, D-CONN." fused to Blumenthal\'s own sentence; not Raskin.'),
 11: (TB, True, IT, 'Mention is the tag "SENATOR JEFF MERKLEY (D-OR):" starting Merkley\'s turn; preceding text is the host\'s; not Schumer.'),
 12: (TB, True, IT, 'Mention is the tag "SEN. BILL CASSIDY, (R) LOUISIANA;" starting Cassidy\'s turn; not Graham.'),
 13: (TB, True, IT, 'Mention is Graham\'s tag; Murphy\'s "truly reckless" sentence precedes it, so tone=negative is scored off a tag.'),
 14: (TB, True, IT, 'After "SCHNEIDER (voice over):" -- reporter narration about Graham; tone=negative credited to Schiff.'),
 15: (TB, True, IT, 'Mention is the tag "SEN. THOM TILLIS (R-NC)" starting Tillis\'s turn; not Thune.'),
 16: (TB, True, IT, 'Mention is the tag "SEN. SUSAN COLLINS (R-ME);" starting Collins\'s turn; not Tillis.'),
 17: (TB, True, IT, 'Mention is the tag "SEN. BERNIE SANDERS (I-VT);" starting Sanders\'s turn; not Warren.'),
 18: (TB, True, IT, 'Mention is the tag "REP. PRAMILA JAYAPAL (D-WA4):" starting Jayapal\'s turn; not Schiff.'),
 19: (TB, True, IT, 'Mention is the tag "SEN. DICK DURBIN, SENATE MAJORITY WHIP D-Ill.:"; not McConnell.'),
 20: (TB, True, IT, 'Mention is the tag "REP. RAJA KRISHNAMOORTHI, (D-IL) RANKING MEMBER"; not Hinson.'),
 21: (TB, True, IT, 'After "DEAN (voice-over):" -- reporter quoting Markwayne Mullin\'s spokesperson (also resolved to the wrong Mullin); not Moulton.'),
 22: (TB, True, IT, 'After "COLLINS (voice-over):" -- reporter narration about McConnell; not Schumer.'),
 23: (TB, True, IT, 'After "DEAN (voice-over):" -- reporter narration about Hickenlooper; not Sanders.'),
 24: (TB, True, IT, 'Mention is Schumer\'s tag "SEN. CHUCK SCHUMER (D-NY)," at the row end; not Johnson.'),
 25: (TB, True, IT, 'Mention is the tag "SEN. JOHN THUNE (R-SD) (voiceover):"; not Barrasso.'),
 26: (TB, True, IT, 'Mention sits inside the tag "SEN. MITCH McCONNELL:"; not Schumer.'),
 27: (TB, True, IT, 'Mention is the tag "REP. PRAMILA JAYAPAL" before [END TAPE]; not Castro.'),
 28: (TB, True, DS, 'Mention is the QFR header "RESPONSES TO WRITTEN QUESTIONS OF SENATOR WARREN FROM ALICIA PUENTE CACKLEY"; not Crapo.'),
 29: (TB, True, IT, 'Mention sits inside the tag "REP. CARLOS GIMENEZ (R-FL)"; not Roy.'),
 30: (TB, True, IT, 'Mention sits inside the tag "SEN. ELIZABETH WARREN (D-MA), 2020"; not Klobuchar.'),
 31: (TB, True, DS, 'Mention is the salutation "Chairman Crapo, Ranking Member Brown" of witness Douglas Holtz-Eakin\'s prepared statement (also the wrong Brown); not Crapo.'),
 32: (TB, True, IT, 'Mention is the tag "SEN. JOHN CORNYN, R-TEXAS, \'THIS WEEK\'/ABC" in a clip montage; not Tillis.'),
 33: (TB, True, IT, 'Mention is the tag "REP. ADAM SCHIFF (D-CA), JANUARY 6"; not Schumer.'),
 34: (TB, True, IT, 'After "COLLINS (on camera):" -- reporter narration addressed to "Jake"; not McCaul.'),
 35: (TB, True, IT, 'Mention is the tag "SEN. CHRIS MURPHY, D-CONN.:" in a rally montage; not Schumer.'),
 36: (TB, True, IT, 'Mention sits in host Chuck Todd\'s turn after "CHUCK TODD:"; not Graham.'),
 37: (TB, False, DS, 'CREC 102k-char row: mention is "amendment no. 263 offered by mr. austin scott of georgia" in a printed amendment list, not Rogers\'s speech. Marker is the section heading "DEPARTMENT OF DEFENSE MILITARY RETIREMENT FUND:", not a turn tag.'),
 38: (TB, False, DS, 'Same row: mention is "amendment no. 257 offered by mr. austin scott of georgia"; same spurious heading marker.'),
 39: (TB, True, IT, 'Mention is Jayapal\'s tag; Torres\'s censure defence precedes it, so tone=negative is scored off a tag.'),
 40: (TB, True, IT, 'Mention is the tag "REP. NANCY PELOSI (D-CA)," at the row end; not McConnell.'),
}
# ----------------------------------------------------------------------------------------------
# G3  P3b hits, n=40.  Every row graded ARTEFACT.  second field = list type
# ----------------------------------------------------------------------------------------------
RC, SB, PL = 'HOUSE_ROLLCALL', 'SENATE_SIGNATURE_BLOCK', 'PRESS_COSIGNER_LIST'
G3 = {
 1: (AR, RC, 'House roll-call roster; span straddles "Scott, Austin Scott, David".'),
 2: (AR, SB, 'Senate cloture/cosponsor signature block.'),
 3: (AR, PL, 'Press release: target appears only in the letter co-signer list.'),
 4: (AR, RC, 'House roll-call roster; straddles "Scott, Austin Scott, David".'),
 5: (AR, PL, 'Press release: target appears only in the 125-lawmaker co-signer list.'),
 6: (AR, RC, 'House roll-call roster.'),
 7: (AR, RC, 'House roll-call roster; straddles "Gonzalez, Vicente Gonzalez-Colon".'),
 8: (AR, PL, 'Press release: co-signer list only.'),
 9: (AR, RC, 'House roll-call roster; straddles "Gonzalez, Vicente Gonzalez-Colon".'),
 10: (AR, PL, 'Press release: "The letter was signed by: Reps. ..." co-signer list.'),
 11: (AR, SB, 'Senate signature block ending "Rick Scott."'),
 12: (AR, RC, 'House roll-call roster; straddles "Gonzalez, Vicente Gonzalez-Colon".'),
 13: (AR, SB, 'Senate signature block ending "United States Senators."'),
 14: (AR, SB, 'Cloture motion signature list on Executive Calendar nominations.'),
 15: (AR, PL, 'Press release: "Joining Biggs and Titus on the letter were U.S. Representatives ..." list.'),
 16: (AR, RC, 'House roll-call roster.'),
 17: (AR, SB, 'Senate cloture signature list.'),
 18: (AR, SB, 'Senate cosponsor signature block.'),
 19: (AR, SB, 'Senate signature block.'),
 20: (AR, SB, 'Senate signature block.'),
 21: (AR, RC, 'House roll-call roster.'),
 22: (AR, RC, 'House roll-call roster.'),
 23: (AR, SB, 'Senate signature block.'),
 24: (AR, PL, 'Press release co-signer list; tone scored neutral-substantive off a list entry.'),
 25: (AR, PL, 'Press release co-signer list.'),
 26: (AR, SB, 'Senate cloture signature list.'),
 27: (AR, SB, 'Senate signature block.'),
 28: (AR, PL, 'Press release co-signer list.'),
 29: (AR, RC, 'House roll-call roster.'),
 30: (AR, PL, 'Press release co-signer list.'),
 31: (AR, SB, 'Senate cloture signature list.'),
 32: (AR, PL, 'Press release: Senators/Representatives co-signer list.'),
 33: (AR, SB, 'Senate signature block.'),
 34: (AR, PL, 'Press release co-signer list.'),
 35: (AR, SB, 'Cloture motion signature list on Executive Calendar nominations.'),
 36: (AR, RC, 'House roll-call roster.'),
 37: (AR, RC, 'House roll-call roster.'),
 38: (AR, RC, 'House roll-call roster.'),
 39: (AR, SB, 'Senate signature block.'),
 40: (AR, SB, 'Senate cloture signature list.'),
}
# ----------------------------------------------------------------------------------------------
# G5a  UNFLAGGED INTERVIEW, n=40 : 6 missed bleeds
# ----------------------------------------------------------------------------------------------
G5A = {
 1: (GEN, 'Durbin\'s own criticism of McConnell; no turn boundary anywhere in the row.'),
 2: (GEN, 'Murkowski praising "my friend Joni Ernst".'),
 3: (GEN, 'Row opens "So, you\'re right. Good to see to you, Dan." -- one continuous Van Hollen answer (verified by reading the row from offset 0).'),
 4: (GEN, 'Durbin crediting Graham for the one investigative subcommittee.'),
 5: (GEN, 'Raskin recounting what Speaker Pelosi said.'),
 6: (GEN, 'Johnson on Pelosi knowing "the heart of Representative Omar".'),
 7: (GEN, 'Klobuchar naming Pelosi and Schumer as deal-makers.'),
 8: (GEN, 'Tim Scott\'s own anecdote about sitting with Graham.'),
 9: (GEN, 'Jeffries citing what the speaker and Hoyer indicated.'),
 10: (GEN, 'Horsford: "I WANT TO COMMEND CHAIRMAN BENNIE THOMPSON" (all-caps C-SPAN caption).'),
 11: (GEN, 'Durbin citing Raskin\'s argument approvingly.'),
 12: (GEN, 'AOC: "This is not about Representative Gosar".'),
 13: (GEN, 'Lankford: "Chris Coons and I are very close friends".'),
 14: (TB, 'MISS: mention sits in host turn after "O`DONNELL:"; the COLON name class [A-Z.\'-] excludes the BACKTICK in "O`DONNELL", so no marker was found.'),
 15: (GEN, 'McConnell: "For the first time in my memory, I agree with Nancy Pelosi."'),
 16: (GEN, 'Hirono: "I have so much faith in Chris Murphy".'),
 17: (GEN, 'AOC: "my bill from 2019 with Senator Sanders".'),
 18: (GEN, 'Garcia: "we asked Chairman Comer ... to ensure this interview is under oath".'),
 19: (GEN, 'Blumenthal listing McCain, Graham, himself, Casey on Iran.'),
 20: (TB, 'MISS: mention sits in host turn after "WALLACE (voice-over):"; qualifies_colon rejects a single-token tag whose surname is not on the member roster (contrast "SULLIVAN (voice-over)", which IS accepted because Sullivan is a roster surname).'),
 21: (GEN, 'Donalds: "That\'s on Chuck Schumer."'),
 22: (GEN, 'Jeffries crediting "great leadership from Speaker Pelosi and Congresswoman Karen Bass".'),
 23: (GEN, 'Klobuchar: "we know what Mitch McConnell did".'),
 24: (GEN, 'Carter: "I APPRECIATE SENATOR LANKFORD" (all-caps C-SPAN caption).'),
 25: (TB, 'MISS: mention inside the host question after "O`DONNELL:" (backtick, same mechanism as row 14).'),
 26: (GEN, 'Jeffries crediting Pelosi, Schiff and "Chairman Nadler".'),
 27: (GEN, 'Coons on "Chairman Graham has been pushing back very hard".'),
 28: (TB, 'MISS: mention inside O\'Donnell\'s monologue after "O`DONNELL:" (backtick).'),
 29: (GEN, 'Tim Scott renaming his prayer breakfast for Graham.'),
 30: (GEN, 'Klobuchar: "It\'s just Josh Hawley dressed up in a different package".'),
 31: (GEN, 'Dingell on what she learned about Nancy Pelosi.'),
 32: (TB, 'MISS: mention inside O\'Donnell\'s monologue after "O`DONNELL:" (backtick).'),
 33: (GEN, 'Correct negative: the mention at 104 precedes the row\'s only marker ("SEN. MITCH" at 221), and the text is Schumer\'s own.'),
 34: (GEN, 'Biggs: "I AM TRYING TO GET MIKE JOHNSON TO BRING THE 12 BUDGET BILLS TO THE FLOOR".'),
 35: (TB, 'MISS: the row is Lawrence O\'Donnell\'s monologue about Thune; mention follows "O`DONNELL:" (backtick).'),
 36: (GEN, 'Barrasso on Democrats "under Speaker Pelosi and Chuck Schumer".'),
 37: (GEN, 'Kelly: "it\'s nothing against Jim Jordan".'),
 38: (GEN, 'Johnson: "Chuck Schumer is a very far left politician".'),
 39: (GEN, 'Schiff: "Chairman Nadler has described the proceedings well."'),
 40: (GEN, 'Raskin on "what Senator Capito from West Virginia\'s saying".'),
}
# ----------------------------------------------------------------------------------------------
# G5b  UNFLAGGED CREC, n=40 : no missed roster artefacts
# ----------------------------------------------------------------------------------------------
G5B = {n: (GEN, 'Substantive floor-speech reference by the speaker; no roster/signature/co-signer list in the window.')
       for n in range(1, 41)}
G5B[5] = (GEN, 'Nearest miss: a speaker-authored thank-you list ("my dear friend Debbie Wasserman Schultz, Brian Fitzpatrick, Leader Hakeem Jeffries, ...") -- 5 distinct roster surnames, ratio 5/53=9.4%, far under both thresholds, but it carries referential intent so it is not the artefact class.')
G5B[25] = (GEN, 'Censure-resolution text naming Representative Cory Mills repeatedly -- legislative text, not a roster/signature list; Mace is the sponsor, so the reference is intentional.')
G5B[30] = (GEN, 'Wicker urging a vote on "Lindsey Graham\'s sanctions bill" -- genuine reference, not a list.')


def load(fn):
    return json.load(io.open(os.path.join(PK, fn), encoding='utf-8'))


def writecsv(fn, rows, cols):
    with io.open(os.path.join(PK, fn), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print('wrote %s (%d rows)' % (fn, len(rows)))


def tally(rows, key='grade'):
    return collections.Counter(r[key] for r in rows)


def ci(k, n, pop, label, width=11):
    lo, hi = cp(k, n)
    print('  %-*s %2d/%-2d = %5.1f%%   95%% CP CI [%5.1f%%, %5.1f%%]%s'
          % (width, label, k, n, 100.0 * k / n, 100 * lo, 100 * hi,
             ('   -> %d-%d of %d (point %d)' % (round(pop * lo), round(pop * hi), pop, round(pop * k / n))
              if pop else '')))
    return lo, hi


print('=' * 100)
print('G2  P2-A PRECISION  (n=40 hit windows, seed 20260918, population 249)')
print('=' * 100)
s = load('G2a_p2_sample40_UNGRADED.json')
r2 = s['rows']
for r in r2:
    g, mv, cls, why = G2[r['n']]
    r['grade'], r['marker_valid'], r['bleed_class'], r['reason'] = g, mv, cls, why
t = tally(r2)
print('grades: %s' % dict(t))
for g in (TB, GEN, UNC):
    ci(t.get(g, 0), 40, s['population'], g)
mvbad = [r['n'] for r in r2 if not r['marker_valid']]
print()
print('  SECOND TAG marker_valid=False (flag fired on a spurious marker, though the mention is')
print('  still outside the attributed speaker\'s turn): rows %s' % mvbad)
ci(40 - len(mvbad), 40, s['population'], 'mech. valid')
print('  bleed_class: %s  (DOC_STRUCTURE = CHRG/CREC whole-document row, not a broadcast turn)'
      % dict(tally(r2, 'bleed_class')))
print('  of the 40, scored into n_scored: %d ; tone classes on those: %s'
      % (sum(1 for r in r2 if r['scored']),
         dict(collections.Counter(r['tone_cls'] for r in r2 if r['scored']))))
writecsv('G2_p2_sample40_GRADED.csv', r2,
         ['n', 'grade', 'marker_valid', 'bleed_class', 'sid', 'src', 'db_member', 'speaker_a',
          'target_b', 'literal', 'mention_off', 'marker_off', 'marker_kind', 'marker_tag',
          'names_target', 'inside_tag', 'scored', 'tone_cls', 'reason'])

print()
print('=' * 100)
print('G3  P3b PRECISION  (n=40 hit windows, seed 20260918, population 749)')
print('=' * 100)
s3 = load('G3_p3b_sample40_UNGRADED.json')
r3 = s3['rows']
for r in r3:
    g, lt, why = G3[r['n']]
    r['grade'], r['list_type'], r['reason'] = g, lt, why
t3 = tally(r3)
print('grades: %s' % dict(t3))
for g in (AR, GEN, UNC):
    ci(t3.get(g, 0), 40, 749, g)
print('  list_type: %s' % dict(tally(r3, 'list_type')))
print('  of the 40, scored into n_scored: %d ; tone classes on those: %s'
      % (sum(1 for r in r3 if r['scored']),
         dict(collections.Counter(r['tone_cls'] for r in r3 if r['scored']))))
writecsv('G3_p3b_sample40_GRADED.csv', r3,
         ['n', 'grade', 'list_type', 'a', 'b', 'src', 'sid', 'pkg', 'date', 'form', 'literal',
          'scored', 'tone_cls', 'edge_shipped', 'reason'])

print()
print('=' * 100)
print('G5a  P2-A RECALL PROBE  (n=40 UNFLAGGED INTERVIEW windows, population 11158)')
print('=' * 100)
s5a = load('G5a_p2_unflagged40_UNGRADED.json')
r5a = s5a['rows']
for r in r5a:
    g, why = G5A[r['n']]
    r['grade'], r['reason'] = g, why
t5a = tally(r5a)
print('grades: %s' % dict(t5a))
for g in (TB, GEN, UNC):
    ci(t5a.get(g, 0), 40, 11158, g)
writecsv('G5a_p2_unflagged40_GRADED.csv', r5a,
         ['n', 'grade', 'a', 'b', 'src', 'sid', 'pkg', 'date', 'literal', 'pos', 'scored',
          'tone_cls', 'edge_shipped', 'reason'])

print()
print('=' * 100)
print('G5b  P3b RECALL PROBE  (n=40 UNFLAGGED CREC windows, population 28153)')
print('=' * 100)
s5b = load('G5b_p3b_unflagged40_UNGRADED.json')
r5b = s5b['rows']
for r in r5b:
    g, why = G5B[r['n']]
    r['grade'], r['reason'] = g, why
t5b = tally(r5b)
print('grades: %s' % dict(t5b))
for g in (AR, GEN, UNC):
    ci(t5b.get(g, 0), 40, 28153, g)
writecsv('G5b_p3b_unflagged40_GRADED.csv', r5b,
         ['n', 'grade', 'a', 'b', 'src', 'sid', 'pkg', 'date', 'form', 'literal', 'scored',
          'tone_cls', 'edge_shipped', 'reason'])

# ----------------------------------------------------------------------------------------------
# G4  scale the prior lane's edge counts by the precision interval, and the EXACT support loss
# ----------------------------------------------------------------------------------------------
print()
print('=' * 100)
print('G4  SCALED WRONG-EDGE ESTIMATES')
print('  ASSUMPTION (stated, not tested): window-level precision is UNIFORM across edges, i.e.')
print('  the probability that an edge\'s contaminating window is truly contaminated equals the')
print('  sampled window precision.  Edges carrying several hits are then slightly UNDER-counted')
print('  as errors (any one true hit contaminates the edge), so these are conservative-low.')
print('=' * 100)
COUNTS = {'P2-A': {'shipped_any_hit': 126, 'shipped_scored_hit': 96, 'signed': 69, 'drawn': 75,
                   'signed_and_drawn': 64},
          'P3b': {'shipped_any_hit': None, 'shipped_scored_hit': 78, 'signed': 72, 'drawn': 77,
                  'signed_and_drawn': None}}
for name, k, n in (('P2-A', t.get(TB, 0), 40), ('P3b', t3.get(AR, 0), 40)):
    lo, hi = cp(k, n)
    pt = k / n
    print()
    print('%s  precision %d/%d = %.1f%%  95%% CP CI [%.1f%%, %.1f%%]' % (name, k, n, 100 * pt, 100 * lo, 100 * hi))
    for lbl, v in COUNTS[name].items():
        if v is None:
            continue
        print('   %-18s %3d shipped edges  ->  wrong: %d-%d  (point %d)'
              % (lbl, v, round(v * lo), round(v * hi), round(v * pt)))

print()
print('=' * 100)
print('G4  EXACT: drawn edges that lose ALL scored support if the detector\'s hits are excluded')
print('=' * 100)
refs = [json.loads(l) for l in io.open(os.path.join(SCRATCH_LB, 'refs.jsonl'), encoding='utf-8')]
art = json.load(io.open(LIVE + r'\member_references.json', encoding='utf-8'))
AE = {(e['a'], e['b']): e for e in art['edges']}
p2hits = json.load(io.open(os.path.join(PK, '04b_p2_union_examples.json'), encoding='utf-8'))
KEY = lambda r: (r['a'], r['b'], r['src'], r['_sid'], r['_pos'], r['_lit'])
P2SET = {KEY(h) for h in p2hits}
s5t = io.open(os.path.join(LB, '05b_p3_graded.py'), encoding='utf-8').read()
H = {'__name__': '_d3'}
exec(compile(s5t[:s5t.index('# --- my grades')], '05b<hdr>', 'exec'), H)
d3a = s5t.index("C = {m['member']: m for m in json.load")
d3b = s5t.index("\nfor r in refs:\n    r['_list'] = is_list(")
exec(compile(s5t[d3a:d3b], '05b<D-P3b>', 'exec'), H)
is_list = H['is_list']

scored_by_edge = collections.defaultdict(list)
for r in refs:
    if r['_counted_scored']:
        scored_by_edge[(r['a'], r['b'])].append(r)
bad = sum(1 for k, v in scored_by_edge.items() if k in AE and len(v) != AE[k]['n_scored'])
print('sanity: shipped edges whose re-derived scored count != artifact n_scored : %d (expect 0)' % bad)

for name, pred in (('P2-A', lambda r: KEY(r) in P2SET),
                   ('P3b', lambda r: is_list(r.get('_raw_w') or r['w']))):
    touched = {}
    for k, v in scored_by_edge.items():
        if k not in AE:
            continue
        hits = [r for r in v if pred(r)]
        if hits:
            touched[k] = (len(v), len(hits))
    drawn = {k: t2 for k, t2 in touched.items() if AE[k]['n_scored'] >= 2}
    zero = [k for k, (tot, h) in drawn.items() if tot - h == 0]
    below = [k for k, (tot, h) in drawn.items() if tot - h < 2]
    zsig = [k for k in zero if AE[k]['pos'] + AE[k]['neg'] > 0]
    print()
    print('%s' % name)
    print('  shipped edges with >=1 SCORED hit                 : %d' % len(touched))
    print('  of those DRAWN (artifact n_scored >= 2)           : %d' % len(drawn))
    print('  DRAWN edges left with ZERO scored support         : %d   (of which SIGNED: %d)'
          % (len(zero), len(zsig)))
    print('  DRAWN edges dropping below n_scored=2 (not drawn) : %d' % len(below))
    for k in sorted(zero)[:12]:
        e = AE[k]
        print('     %-22s -> %-22s n_scored=%d pos=%d neg=%d tone=%s'
              % (k[0][:22], k[1][:22], e['n_scored'], e['pos'], e['neg'], e.get('tone')))
    if len(zero) > 12:
        print('     ... %d more (full list in %s_zero_support_edges.json)' % (len(zero) - 12, name))
    with io.open(os.path.join(PK, 'G4_%s_zero_support_edges.json' % name.replace('-', '')), 'w',
                 encoding='utf-8') as f:
        json.dump({'detector': name,
                   'drawn_zero_support': [{'a': k[0], 'b': k[1], 'n_scored': AE[k]['n_scored'],
                                           'pos': AE[k]['pos'], 'neg': AE[k]['neg'],
                                           'tone': AE[k].get('tone')} for k in sorted(zero)],
                   'drawn_below_two': [{'a': k[0], 'b': k[1], 'n_scored': AE[k]['n_scored'],
                                        'remaining': drawn[k][0] - drawn[k][1]} for k in sorted(below)]},
                  f, ensure_ascii=False, indent=1)
    print('  wrote G4_%s_zero_support_edges.json' % name.replace('-', ''))
print()
print('DONE G4')
