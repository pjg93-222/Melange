# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT
"""Audio-prosody feature builder (big5_audio_prereg.md @3c94fc7). Scans audio_pilot/<member>/*.wav
(solo clips; single-speaker by construction — see prereg), extracts eGeMAPS v02 (88 functionals,
openSMILE) per clip, duration-weighted mean-pool per member, z-within-source across members, writes
b5_audio_cache.json. Mirrors b5_emb_build.py. No download here (acquisition = b5_audio_fetch.py, a
handoff/background job); this stage is deterministic + offline-testable.
Usage: python b5_audio_build.py            (--test injects a synthetic member to prove the pipeline)"""
import os, json, glob, wave, contextlib
import numpy as np
sys = _s; sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B = MB_ROOT
ADIR = os.path.join(B, 'audio_pilot')
MIN_SEC = 180.0   # prereg: >= 3 minutes of solo audio per member

def clip_seconds(path):
    try:
        with contextlib.closing(wave.open(path, 'rb')) as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except Exception:
        return 0.0

def build(members_dirs):
    import opensmile
    smile = opensmile.Smile(feature_set=opensmile.FeatureSet.eGeMAPSv02,
                            feature_level=opensmile.FeatureLevel.Functionals)
    feats = {}; secs = {}; names = None
    for member, wavs in members_dirs.items():
        vecs = []; ws = []; tot = 0.0
        for wv in wavs:
            d = clip_seconds(wv)
            if d < 1.0: continue
            try:
                df = smile.process_file(wv)
            except Exception as e:
                print('  !! %s: eGeMAPS fail on %s (%s)' % (member, os.path.basename(wv), str(e)[:50])); continue
            if names is None: names = list(df.columns)
            vecs.append(df.values[0].astype(float)); ws.append(d); tot += d
        if not vecs:
            print('  skip %s: no usable audio' % member); continue
        if tot < MIN_SEC:
            print('  skip %s: %.0fs < %.0fs minimum' % (member, tot, MIN_SEC)); continue
        w = np.array(ws); V = np.array(vecs)
        feats[member] = (V * w[:, None]).sum(0) / w.sum()   # duration-weighted mean
        secs[member] = tot
    if not feats:
        print('no members cleared the audio minimum — nothing written'); return
    # z-within-source (single pilot source): standardize each functional across members
    M = np.array([feats[m] for m in feats]); mu = M.mean(0); sd = M.std(0, ddof=1); sd[sd == 0] = 1
    Z = {m: ((feats[m] - mu) / sd).round(5).tolist() for m in feats}
    from moneyball_core import dump_atomic
    dump_atomic({'members': sorted(feats), 'feature_names': names,
                 'z': Z, 'seconds': {m: round(secs[m], 1) for m in secs},
                 'feature_set': 'eGeMAPSv02', 'n_features': len(names), 'min_sec': MIN_SEC,
                 'note': 'audio-prosody pilot; solo clips; duration-weighted mean, z-within-source. prereg @3c94fc7'},
                os.path.join(B, 'b5_audio_cache.json'))
    print('wrote b5_audio_cache.json: %d members, %d features (eGeMAPSv02)' % (len(feats), len(names)))

def scan():
    md = {}
    for d in sorted(glob.glob(os.path.join(ADIR, '*'))):
        if os.path.isdir(d):
            wavs = sorted(glob.glob(os.path.join(d, '*.wav')))
            if wavs: md[os.path.basename(d)] = wavs
    return md

if __name__ == '__main__':
    if '--test' in sys.argv:
        # synthetic solo clip -> prove eGeMAPS -> cache end to end, offline
        import soundfile as sf
        td = os.path.join(ADIR, '__test__'); os.makedirs(td, exist_ok=True)
        sr = 16000; import numpy as _np
        for i in range(2):
            t = _np.linspace(0, 100, 100 * sr, endpoint=False)
            sig = 0.3 * _np.sin(2 * _np.pi * (120 + 15 * i) * t) * (1 + 0.25 * _np.sin(2 * _np.pi * 3 * t))
            sf.write(os.path.join(td, 'clip%d.wav' % i), sig.astype('float32'), sr)
        build({'__test__': sorted(glob.glob(os.path.join(td, '*.wav')))})
    else:
        md = scan()
        print('audio_pilot members with wav: %d' % len(md))
        build(md)
