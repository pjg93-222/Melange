# -*- coding: utf-8 -*-
"""Prep for the LLM text-N instrument on Washington Journal hot-seat transcripts (2026-07-11, user:
'apply the API to the WJ articles' -- test N for the member in the hot seat). WJ = the member as GUEST
being pressed by host + callers; the mechanical reactivity_z (interruption adjacency) is a crude read of
this. An LLM READING how the member handles the pressure is the stronger text-N instrument round-6's
power gate said we need. Extracts each member's GUEST turns -> capped sample -> chunk files (4 members
each) for a Haiku scoring workflow. Incremental: skips members already in wj_n_labels.json."""
import os, sys, json, sqlite3, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
SCRATCH = r'C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-clever-elbakyan-15fa11\4551680e-cf3a-40bd-ba1a-4c2b67b144b0\scratchpad'
CAP = 11000   # chars per member (a representative sample of their hot-seat responses)

def run():
    con = sqlite3.connect(B + r'\social_media.db', timeout=60); con.execute('PRAGMA query_only=1')
    rows = con.execute("SELECT member, text FROM speeches WHERE chamber='washington-journal' ORDER BY member").fetchall()
    con.close()
    bym = collections.defaultdict(list)
    for m, t in rows:
        if t and len(t.split()) >= 8: bym[m].append(t)     # substantive turns only
    labp = os.path.join(SCRATCH, 'wj_n_labels.json')
    done = set(json.load(open(labp, encoding='utf-8')).keys()) if os.path.exists(labp) else set()
    items = []
    for m, turns in bym.items():
        if len(turns) < 6 or m in done:
            continue
        # sample turns spread across the member's appearances, cap total chars
        text = ''; step = max(1, len(turns) // 40)
        for t in turns[::step]:
            if len(text) + len(t) > CAP: break
            text += t.strip() + '\n---\n'
        items.append({'member': m, 'text': text[:CAP]})
    cdir = os.path.join(SCRATCH, 'wj_n_chunks'); os.makedirs(cdir, exist_ok=True)
    for f in os.listdir(cdir):
        os.remove(os.path.join(cdir, f))
    CH = 4; n = 0
    for i in range(0, len(items), CH):
        json.dump(items[i:i + CH], open(os.path.join(cdir, 'chunk_%03d.json' % n), 'w', encoding='utf-8'))
        n += 1
    print('WJ-N prep: %d members (>=6 substantive turns, %d already scored) -> %d chunks in %s' % (len(items), len(done), n, cdir))

if __name__ == '__main__':
    run()
