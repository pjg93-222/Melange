# -*- coding: utf-8 -*-
"""F2 verification: (a) the P2-A hit file my re-run produced is byte-identical to lane B's, so the
seeded sample is drawn from the same population IN THE SAME ORDER and is reproducible from either
copy; (b) the two recall-miss mechanisms I read off lane B's regexes are real, tested against the
regexes themselves rather than inferred.  READ-ONLY."""
import hashlib, io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LB = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\laneB\receipts')
PK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\F2\receipts')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


print('(a) P2-A hit file identity')
a = os.path.join(LB, '04b_p2_union_examples.json')
b = os.path.join(PK, '04b_p2_union_examples.json')
ha, hb = sha(a), sha(b)
print('    laneB sha256 %s (%d bytes)' % (ha, os.path.getsize(a)))
print('    F2    sha256 %s (%d bytes)' % (hb, os.path.getsize(b)))
print('    IDENTICAL: %s' % (ha == hb))

s4 = io.open(os.path.join(LB, '04b_p2_colonless.py'), encoding='utf-8').read()
H = {'__name__': '_v'}
exec(compile(s4[:s4.index('\nrefs = [json.loads(l)')], '04b<prelude>', 'exec'), H)
COLON, qual, SUR, bnd = H['COLON'], H['qualifies_colon'], H['SURNAMES'], H['boundaries']
print()
print('(b) recall-miss mechanisms')
for probe in ('O`DONNELL: Joining us now a member of the committee, Congressman Raja Krishnamoorthi.',
              "O'DONNELL: Joining us now a member of the committee, Congressman Raja Krishnamoorthi.",
              'WALLACE (voice-over): We will discuss compromise with House Democratic Leader Nancy Pelosi.',
              'SULLIVAN (voice-over): The announcement comes after House Speaker Mike Johnson tweeted.'):
    m = COLON.search(probe)
    print('    %-92s COLON=%s qualifies=%s boundaries=%d'
          % (probe[:92], (m.group(1) if m else None), (qual(m.group(1)) if m else '-'), len(bnd(probe))))
print()
print("    'o`donnell' char U+%04X between O and D : backtick is NOT in the name class [A-Z.'-]"
      % ord('`'))
print('    roster surname? wallace=%s sullivan=%s odonnell=%s donnell=%s'
      % ('wallace' in SUR, 'sullivan' in SUR, 'odonnell' in SUR, 'donnell' in SUR))
print()
print('(c) population arithmetic')
refs_n = 53011
print('    INTERVIEW raw mentions 11365 - P2-A INTERVIEW hits 207 = %d (G5a population)' % (11365 - 207))
print('    CREC      raw mentions 28720 - P3b CREC hits 567       = %d (G5b population)' % (28720 - 567))
print('    total re-derived mentions: %d' % refs_n)
print('DONE G6')
