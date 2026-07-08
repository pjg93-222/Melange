# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT
"""Audio-prosody pilot — SOLO-audio acquisition (big5_audio_prereg.md @3c94fc7). HANDOFF/background
stage: run where web egress works (the collector environment) — the interactive sandbox 403s YouTube
+ C-SPAN media. Manifest-driven for robustness: b5_audio_sources.json = {member: [urls]} of SOLO
clips (own-channel YouTube / C-SPAN / direct media — single-speaker is the prereg guarantee). Fetches
each via yt-dlp -> wav (duration-capped), resumable via b5_audio_fetch_log.json, into
audio_pilot/<member>/. Then run b5_audio_build.py -> b5_audio_eval.py (the one look).
Modes:
  --eligible [N]   rank pilot-eligible members (have Pink+Blue+behavioral) by visibility (proxy for
                   public-audio availability); print top N (default 80 — power fix, prereg Addendum 3;
                   n=40 was underpowered) + seed b5_audio_sources.json
  (default)        fetch audio for every member with URLs in b5_audio_sources.json"""
import os, json, subprocess
sys = _s; sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B = MB_ROOT
ADIR = os.path.join(B, 'audio_pilot'); LOG = os.path.join(B, 'b5_audio_fetch_log.json')
SRC = os.path.join(B, 'b5_audio_sources.json')
PER_CLIP_SEC = 600     # cap any single clip at 10 min of audio
def _ff():
    try:
        import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception: return None

def eligible(topn=80):
    pink = (json.load(open(B + r'\big5_llm_opus.json', encoding='utf-8')).get('traits') or {})
    v2 = (json.load(open(B + r'\big5_v2.json', encoding='utf-8')).get('traits') or {})
    bd = (json.load(open(B + r'\behavioral_dispositions.json')).get('members') or {})
    NEED = ('cooperation_z', 'diligence_z', 'visibility_z', 'breadth_z')
    elig = []
    for m in pink:
        if (pink[m].get('n_chunks', 0) or 0) < 1: continue
        if m not in v2: continue
        b = bd.get(m) or {}
        if any(b.get(k) is None for k in NEED): continue
        elig.append((b['visibility_z'], m))            # visibility = proxy for public-audio availability
    elig.sort(reverse=True)
    top = [m for _, m in elig[:topn]]
    print('pilot-eligible members (Pink+Blue+behavioral): %d; top %d by visibility:' % (len(elig), len(top)))
    for i, m in enumerate(top, 1): print('  %2d. %s' % (i, m))
    if not os.path.exists(SRC):
        json.dump({m: [] for m in top}, open(SRC, 'w'), indent=1)
        print('\nseeded %s — populate each member with SOLO clip URLs (own-channel/C-SPAN/direct), then run without --eligible' % os.path.basename(SRC))
    else:
        print('\n%s exists — not overwritten' % os.path.basename(SRC))

def fetch():
    ff = _ff()
    if not ff: print('!! imageio-ffmpeg not available — pip install imageio-ffmpeg'); return
    if not os.path.exists(SRC): print('!! %s missing — run --eligible first, then populate URLs' % os.path.basename(SRC)); return
    srcs = json.load(open(SRC)); log = json.load(open(LOG)) if os.path.exists(LOG) else {}
    done = set(log.get('done', []))
    n_ok = 0
    for member, urls in srcs.items():
        md = os.path.join(ADIR, member); os.makedirs(md, exist_ok=True)
        for j, url in enumerate(urls or []):
            key = '%s|%s' % (member, url)
            if key in done: continue
            out = os.path.join(md, 'clip%02d.%%(ext)s' % j)
            cmd = [sys.executable, '-m', 'yt_dlp', '-q', '--no-warnings', '-f', 'bestaudio',
                   '-x', '--audio-format', 'wav', '--ffmpeg-location', ff,
                   '--postprocessor-args', 'ffmpeg:-t %d -ac 1 -ar 16000' % PER_CLIP_SEC,
                   '-o', out, url]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if r.returncode == 0: done.add(key); n_ok += 1; print('  ok  %s <- %s' % (member, url[:60]))
                else: print('  FAIL %s <- %s (%s)' % (member, url[:50], (r.stderr or '').strip().splitlines()[-1][:80] if r.stderr else '?'))
            except Exception as e:
                print('  ERR %s <- %s (%s)' % (member, url[:50], str(e)[:60]))
    json.dump({'done': sorted(done)}, open(LOG, 'w'), indent=1)
    print('fetched %d new clips; %d member dirs. Next: python fec/b5_audio_build.py' % (n_ok, len(srcs)))

if __name__ == '__main__':
    if '--eligible' in sys.argv:
        n = 80
        for a in sys.argv:
            if a.isdigit(): n = int(a)
        eligible(n)
    else:
        fetch()
