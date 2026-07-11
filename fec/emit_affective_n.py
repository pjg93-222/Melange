# -*- coding: utf-8 -*-
"""Regenerate affective_n.json — the engine N-slot input (round-7 promotion 2026-07-11, gate 5/5).
Combines the Pennebaker LIWC base (transparent, deterministic, from the interview corpus) with the LLM
affective facets (scratchpad/interview_n_affective.json — Haiku pessimism/anxiety/depression/volatility,
policy-stripped), averaged and party-controlled. reactivity_z retired as Extraversion-contaminated.
LIWC is deterministic; the LLM labels are the one non-deterministic input (regenerate via
interview_llm_n_prep.py + the interview-n-affective-facets workflow if absent)."""
import os, sys, json, re, collections, sqlite3, csv
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
B = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
SC = r'C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-clever-elbakyan-15fa11\4551680e-cf3a-40bd-ba1a-4c2b67b144b0\scratchpad'
FPS = re.compile(r'\b(i|me|my|mine|myself)\b', re.I)
NEG = re.compile(r'\b(worri\w+|afraid|anxi\w+|scared|nervous|fear\w*|dread|panic|hopeless|helpless|overwhelm\w+|exhaust\w+|struggl\w+|suffer\w+|sad\w*|depress\w+|miserable|upset|frustrat\w+|hurt|alone|lonely|devastat\w+|painful)\b', re.I)
POS = re.compile(r'\b(happy|glad|great|wonderful|excited|hopeful|optimis\w+|proud|grateful|thrilled|fantastic|excellent|enjoy\w+|confident|encourag\w+|thank\w+|appreciat\w+|fortunate)\b', re.I)
WORD = re.compile(r'\b\w+\b')

def z(x):
    x = np.array(x, float); s = np.nanstd(x); return (x - np.nanmean(x)) / (s or 1)

def run():
    llmp = os.path.join(SC, 'interview_n_affective.json')
    if not os.path.exists(llmp):
        print('  !! interview_n_affective.json missing — run interview_llm_n_prep.py + the affective-facets workflow first'); return
    S = json.load(open(llmp, encoding='utf-8'))
    con = sqlite3.connect(B + r'\social_media.db', timeout=60); con.execute('PRAGMA query_only=1')
    ag = collections.defaultdict(lambda: [0, 0, 0, 0])
    for m, t in con.execute("SELECT member, text FROM speeches WHERE source='INTERVIEW'"):
        if not t: continue
        w = len(WORD.findall(t))
        if w < 20: continue
        a = ag[m]; a[0] += len(FPS.findall(t)); a[1] += len(NEG.findall(t)); a[2] += len(POS.findall(t)); a[3] += w
    con.close()
    lm = [m for m in ag if ag[m][3] >= 800]
    fps = z([ag[m][0] / ag[m][3] for m in lm]); neg = z([ag[m][1] / ag[m][3] for m in lm]); pos = z([ag[m][2] / ag[m][3] for m in lm])
    liwc = {m: float(fps[i] + neg[i] - pos[i]) for i, m in enumerate(lm)}
    llm = {m: S[m]['pessimism'] + S[m]['anxiety'] + S[m]['depression'] + S[m]['volatility'] for m in S}
    Cj = {m['member']: m for m in json.load(open(B + r'\congestion.json'))}; bio = {m: Cj[m].get('bioguide') for m in Cj}
    PP = {}
    for r in csv.DictReader(open(B + r'\fec\legislators.csv', encoding='utf-8')):
        if r.get('bioguide_id'): PP[r['bioguide_id']] = (r.get('party') or '')[:1]
    pty = {m: PP.get(bio.get(m), '?') for m in Cj}
    mem = [m for m in S if m in liwc]
    comb = z([llm[m] for m in mem]) + z([liwc[m] for m in mem])   # LIWC + LLM affective, equal weight
    Rp = np.array([1.0 if pty.get(m) == 'R' else 0.0 for m in mem])
    X = np.column_stack([np.ones(len(comb)), Rp]); combc = comb - X @ np.linalg.lstsq(X, comb, rcond=None)[0]   # party-controlled
    combc = z(combc)
    out = {m: round(float(combc[i]), 3) for i, m in enumerate(mem)}
    json.dump({'members': out, 'n': len(out), 'basis': 'affective-content N: Pennebaker LIWC + LLM facets, party-controlled, z-scored',
               'promotion': 'round-7 2026-07-11 gate 5/5; retired E-contaminated reactivity_z'}, open(B + r'\affective_n.json', 'w'), indent=0)
    print('affective_n.json: %d members' % len(out))
    o = sorted(mem, key=lambda m: -out[m])
    print('highest N:', ', '.join('%s(%s)' % (m, pty.get(m)) for m in o[:6]))

if __name__ == '__main__':
    run()
