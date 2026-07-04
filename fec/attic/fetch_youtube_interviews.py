# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root
"""YOUTUBE INTERVIEW/APPEARANCE COLLECTOR (user-directed 2026-07-03: extend interview coverage to
members cable never books). Uses public captions (youtube_transcript_api) + metadata (yt_dlp search),
NO video download, NO Whisper needed for caption-bearing videos.

ATTRIBUTION HONESTY (the hard part — captions carry NO speaker labels):
  * SOLO tier (source='YOUTUBE'): the member's OWN official channel, or videos whose title is a
    first-person/solo format ("Sen. X on ...", "X floor speech", "Weekly address"), where the
    dominant speaker is unambiguously the member. These enter the trait corpus.
  * PANEL/MIXED videos (multi-guest, debate, host-heavy): captions cannot be attributed per-speaker
    -> STORED SEPARATELY as source='YOUTUBE_UNATTRIB' (never fed to big5) so nothing contaminates
    the personality read. A future Whisper+diarization pass can promote these.
Discovery: per member, yt_dlp search "<name> senator/representative interview" restricted to the
member's own channel handle when known (member_youtube.json map; else title-guarded solo heuristic).
Storage: speeches table; yt_fetch_log(video_id) resumable.
Usage:
  python fetch_youtube_interviews.py --limit 6            # per-member solo videos, title-guarded
  python fetch_youtube_interviews.py --members "Amy Klobuchar,Tim Scott"
  python fetch_youtube_interviews.py status
Requires: pip install youtube-transcript-api yt-dlp"""
import sys, os, re, json, sqlite3, datetime, time, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B = MB_ROOT
DB = B + r'\social_media.db'

def db():
    c = sqlite3.connect(DB, timeout=60); c.execute('PRAGMA journal_mode=WAL')
    c.execute('''CREATE TABLE IF NOT EXISTS speeches(member TEXT,date TEXT,source TEXT,chamber TEXT,
                 package TEXT,nwords INTEGER,text TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS yt_fetch_log(key TEXT PRIMARY KEY,status TEXT,ts TEXT)')
    return c

C = {m['member']: m for m in json.load(open(B + r'\congestion.json'))}
YTMAP = {}
_ym = B + r'\member_youtube.json'
if os.path.exists(_ym): YTMAP = json.load(open(_ym))   # {member: channel handle/id} — optional curated map

def norm(s): return re.sub(r"[^a-z ]", '', s.lower()).strip()
# Audit 2026-07-03 (round 2): title heuristics CANNOT guarantee single-speaker captions. Verified
# contamination — videos titled "full interview"/"sits down"/"one-on-one" are HOST+GUEST with no
# caption speaker separation, so the host's words entered the member's trait corpus. YouTube captions
# carry no speaker labels; the ONLY reliable single-speaker guarantee is the member's OWN official
# channel (weekly addresses, floor speeches, statements they publish). So: in-corpus (source=YOUTUBE)
# requires OWN CHANNEL. Everything else -> YOUTUBE_UNATTRIB quarantine (never fed to big5) for a
# future Whisper+diarization pass. Populate member_youtube.json {member: official-channel handle} to
# turn on the in-corpus tier; until then YouTube contributes ONLY quarantined text (safe by default).
PANEL_HINT = re.compile(r'\b(panel|debate|vs\.?|roundtable|reacts|crossfire|face off|town ?hall|'
                        r'full episode|full show|interview|sits down|one-on-one|joins|guest)\b', re.I)

def title_is_solo(title, member, own_channel=False):
    t = title or ''
    last = norm(member).split()[-1]
    if last not in norm(t): return False
    return bool(own_channel)   # own channel is the only single-speaker guarantee; titles never suffice

def search_videos(query, n):
    from yt_dlp import YoutubeDL
    opts = {'quiet': True, 'skip_download': True, 'extract_flat': True, 'no_warnings': True}
    with YoutubeDL(opts) as y:
        info = y.extract_info('ytsearch%d:%s' % (n, query), download=False)
    return info.get('entries', []) or []

def get_caption(vid):
    """youtube_transcript_api v1.x instance API (audit fix: static get_transcript was removed in 1.0
    -> the whole collector was silently caption-less). Falls back to the legacy static call if an
    old version is present."""
    from youtube_transcript_api import YouTubeTranscriptApi
    try:
        if hasattr(YouTubeTranscriptApi, 'get_transcript'):
            tr = YouTubeTranscriptApi.get_transcript(vid, languages=['en', 'en-US'])
            return ' '.join(seg['text'] for seg in tr if seg.get('text'))
        fetched = YouTubeTranscriptApi().fetch(vid, languages=['en', 'en-US'])
        return ' '.join(sn.text for sn in fetched if getattr(sn, 'text', ''))
    except Exception:
        return None

def collect(members, per):
    con = db(); done = {k for (k,) in con.execute("SELECT key FROM yt_fetch_log WHERE status IN ('ok','skip')")}
    solo = unatt = 0
    for m in members:
        q = '%s %s interview' % (m, 'senator' if C[m].get('chamber', '').lower().startswith('sen') else 'congressman')
        try: ents = search_videos(q, per * 3)
        except Exception as e: print('%s search FAIL %s' % (m, str(e)[:70])); continue
        got = 0
        for e in ents:
            vid = e.get('id')
            if not vid or 'yt:' + vid in done: continue
            title = e.get('title', '')
            if PANEL_HINT.search(title or ''): own = False
            else: own = bool(YTMAP.get(m)) and norm(YTMAP.get(m, '')) in norm(e.get('channel', '') or e.get('uploader', ''))
            is_solo = title_is_solo(title, m, own_channel=own)
            cap = get_caption(vid); time.sleep(0.3)
            if not cap or len(cap.split()) < 120:
                con.execute('INSERT OR REPLACE INTO yt_fetch_log VALUES (?,?,?)', ('yt:' + vid, 'skip', datetime.datetime.now().isoformat())); continue
            src = 'YOUTUBE' if is_solo else 'YOUTUBE_UNATTRIB'
            con.execute('INSERT INTO speeches VALUES (?,?,?,?,?,?,?)',
                        (m, '', src, 'youtube', vid, len(cap.split()), cap))
            con.execute('INSERT OR REPLACE INTO yt_fetch_log VALUES (?,?,?)', ('yt:' + vid, 'ok', datetime.datetime.now().isoformat()))
            con.commit()
            if src == 'YOUTUBE': solo += 1; got += 1
            else: unatt += 1
            if got >= per: break
        print('%-26s solo+%d (running solo %d / unattrib %d)' % (m, got, solo, unatt), flush=True)
    con.close(); print('YouTube done: %d SOLO turns (in corpus) | %d UNATTRIB (quarantined)' % (solo, unatt))

if __name__ == '__main__':
    if 'status' in sys.argv:
        con = db()
        for src, n, dm, w in con.execute("SELECT source, COUNT(*), COUNT(DISTINCT member), SUM(nwords) FROM speeches WHERE source LIKE 'YOUTUBE%' GROUP BY source"):
            print('%-18s %5d videos | %3d members | %.2fM words' % (src, n, dm, (w or 0) / 1e6))
        sys.exit(0)
    per = int(next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--limit'), '5'))
    msel = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--members'), None)
    members = [x.strip() for x in msel.split(',')] if msel else list(C)
    members = [m for m in members if m in C]
    print('YouTube collection: %d members, up to %d solo videos each' % (len(members), per))
    collect(members, per)
