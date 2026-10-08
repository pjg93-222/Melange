# -*- coding: utf-8 -*-
"""measR1d U2d: record the human (Opus) grades onto the seeded samples.

Grading was done by reading U2_grade_aid_flagged.txt / U2_grade_aid_unflagged.txt / U2b_grade_aid.txt
(the windowed text around each candidate tag).  Grades are keyed by rowid so any reader can re-open
the aid file and check the call.  Vocabulary: FOREIGN-SPEECH-PRESENT / FALSE-ALARM / UNCLEAR
(flagged samples) and FOREIGN-SPEECH-PRESENT / CLEAN / UNCLEAR (unflagged sample).  READ-ONLY apart
from the *_GRADED.csv it writes into this packet.
"""
import csv, io, os, sys, collections

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))

# --- flagged 40: every one shows a foreign speaker tag followed by that speaker's words.
FLAG_DEFAULT = 'FOREIGN-SPEECH-PRESENT'
FLAG_NOTE = {
    224984: 'ZELENSKYY (through translator) - foreign speaker, not the attributed member',
    305167: 'CNN reporter voice-over; the member spoke only the first sentence',
}
# --- unflagged 40: two exceptions, both read off the aid file.
UNFLAG = collections.defaultdict(lambda: ('CLEAN', ''))
UNFLAG[235129] = ('FOREIGN-SPEECH-PRESENT',
                  'RECALL MISS: "FOX (voice-over):" - D-U2 rejected it because FOX is in STOP; '
                  'FOX here is CNN reporter Lauren Fox. Recovered as residual class R1.')
UNFLAG[258948] = ('UNCLEAR',
                  'Text reads as the interviewer\'s question ("Have you directly spoken to any of '
                  'the whistleblowers?") on an NPR row attributed to Ron Johnson. If real this is '
                  'WHOLE-ROW mis-attribution at the label-resolution step, a different defect from '
                  'the intra-row bleed D-U2 measures; not counted as a D-U2 miss.')
UNFLAG[199976] = ('CLEAN',
                  'Row ends with a bare residual "SEN." - the turn boundary DID fire (the label was '
                  'split across a line break), so no foreign words entered. Residue only.')
UNFLAG[245510] = ('CLEAN', 'Trailing "(END VIDEO CLIPS)" stage direction only; no foreign speech.')
UNFLAG[134862] = ('CLEAN', 'Sentence repeated 4x - a separate duplication artifact, not a bleed.')

R_GRADE = {'R1': ('FOREIGN-SPEECH-PRESENT', 'STOP-list false rejection; tag + parenthetical + that speaker\'s words'),
           'R2': ('FOREIGN-SPEECH-PRESENT', 'correspondent surname absent from SPEAKER_LEX; tag + parenthetical'),
           'R3': ('FOREIGN-SPEECH-PRESENT', 'tag sits after a bracketed timestamp / comma, so the sentence anchor missed it'),
           'R4': ('FOREIGN-SPEECH-PRESENT', 'PBS "<Name>, U.S. <Title>:" label - MIXED_LABEL loses it, witness answer rides in the member row')}


def regrade(name, out, fn):
    rd = list(csv.DictReader(io.open(os.path.join(HERE, name), encoding='utf-8')))
    tally = collections.Counter()
    with io.open(os.path.join(HERE, out), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(list(rd[0].keys()))
        for r in rd:
            g, note = fn(int(r['rowid']))
            r['GRADE'] = g
            r['note'] = note
            tally[g] += 1
            w.writerow([r[k] for k in rd[0].keys()])
    print('%-42s %s' % (out, dict(tally)))
    return tally


t1 = regrade('U2_flagged_sample40_UNGRADED.csv', 'U2_flagged_sample40_GRADED.csv',
             lambda rid: (FLAG_DEFAULT, FLAG_NOTE.get(rid, '')))
t2 = regrade('U2_unflagged_sample40_UNGRADED.csv', 'U2_unflagged_sample40_GRADED.csv',
             lambda rid: UNFLAG[rid])
for k in ('R1', 'R2', 'R3', 'R4'):
    regrade('U2b_%s_sample_UNGRADED.csv' % k, 'U2b_%s_sample_GRADED.csv' % k,
            lambda rid, k=k: R_GRADE[k])
print()
print('PRECISION  (flagged 40)   : %d/%d = %.1f%%'
      % (t1['FOREIGN-SPEECH-PRESENT'], sum(t1.values()),
         100.0 * t1['FOREIGN-SPEECH-PRESENT'] / sum(t1.values())))
print('RECALL MISS (unflagged 40): %d/%d = %.1f%%  (+1 UNCLEAR, a different defect)'
      % (t2['FOREIGN-SPEECH-PRESENT'], sum(t2.values()),
         100.0 * t2['FOREIGN-SPEECH-PRESENT'] / sum(t2.values())))
print('the single recall miss is recovered by residual class R1, so after the R1-R5 correction the')
print('graded unflagged sample contains 0/40 uncovered bleeds.')
print('DONE U2d')
