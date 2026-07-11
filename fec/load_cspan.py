# -*- coding: utf-8 -*-
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
from paths import ROOT as MB_ROOT  # centralized root
"""C-SPAN LOADER (bridge from the R/chromote scraper into the model).

The scraper (cspan/cspan_scrape.R) writes transcripts/<id>.json with EVERY
speaker turn labelled (host, callers, mis-captioned news-clips, and the member
guest). This loader digests those files into the `speeches` table, resolving
each turn's speaker to the 533-member roster with the SAME drop-never-guess
resolver the broadcast-interview collectors use (fetch_interviews.resolve_full)
-- so host/caller/clip turns don't resolve and are dropped, never guessed.

Rows are written source='INTERVIEW' by DEFAULT (user decision 2026-07-11: treat
C-SPAN Washington Journal as the same broadcast-interview genre as the CNN/MTP/
etc. legs, so it feeds EVERY consumer -- big5_traits, references, co-appearance,
the volume dispositions, and the reactivity MEM_N gate -- with no consumer edits;
C-SPAN packages bucket into program_of()'s "other" cell exactly like the existing
CBS/ABC/Fox/Hewitt/MSNOW legs already do). Pass `--source CSPAN` instead to keep
it a distinct, separately-auditable genre (then it reaches only the unfiltered
readers: big5_traits, agency_communion, member_references). NOTE: with the
default, C-SPAN turns raise the reactivity MEM_N (currently 216, gate 250) -- run
the chain and check MEM_N before/after so the gate crossing is observed.

Storage mirrors fetch_interviews.store(): one row per member TURN, per-video
(member, text) dedup, dateless rows refused (they starve co-appearance/recency),
resumable via cspan_fetch_log (key 'cspan:<video-id>').

Usage:
  python load_cspan.py --dir <cspan_out> [--source INTERVIEW|CSPAN] [--min-words 8]
  python load_cspan.py status [--source INTERVIEW]
  python load_cspan.py --dir <cspan_out> --db <path>   # load into an alternate DB (testing)
"""
import sys, os, re, json, sqlite3, datetime, glob, hashlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from fetch_interviews import resolve_full, scrub   # reuse roster resolver + stage-direction scrub

B = MB_ROOT
DB = os.environ.get('MONEYBALL_DB', B + r'\social_media.db')
DEFAULT_DIR = os.path.join(B, 'cspan_out')

def db(path=None):
    c = sqlite3.connect(path or DB, timeout=60); c.execute('PRAGMA journal_mode=WAL')
    c.execute('''CREATE TABLE IF NOT EXISTS speeches(member TEXT,date TEXT,source TEXT,chamber TEXT,
                 package TEXT,nwords INTEGER,text TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS cspan_fetch_log(key TEXT PRIMARY KEY,status TEXT,ts TEXT)')
    return c

def show_of(url):
    m = re.search(r'/program/([^/]+)/', url or '')
    return m.group(1) if m else 'c-span'

# C-SPAN labels guests with credential / generational suffixes ("Rich McCormick
# M.D.", "Mark Green M.D.", "... Jr.") that resolve_full can't see past -- the
# suffix becomes the surname token and the (first,last) roster match fails. Strip
# trailing suffixes here (loader-local; the shared resolver stays untouched).
_SUFFIX = re.compile(r'[\s,]+(?:M\.?D\.?|Ph\.?D\.?|D\.?D\.?S\.?|D\.?O\.?|J\.?D\.?|M\.?P\.?H\.?|R\.?N\.?|Esq\.?|Jr\.?|Sr\.?|I{2,3}|IV)\.?$', re.I)
def clean_name(name):
    s = (name or '').strip()
    for _ in range(3):                       # peel up to 3 stacked suffixes
        s2 = _SUFFIX.sub('', s).strip()
        if s2 == s:
            break
        s = s2
    return s

def load(dir_, source='CSPAN', min_words=8, dbpath=None):
    con = db(dbpath)
    done = {k for (k,) in con.execute("SELECT key FROM cspan_fetch_log WHERE status='ok'")}
    files = sorted(glob.glob(os.path.join(dir_, 'transcripts', '*.json')))
    print('cspan loader: %d transcript files in %s (source=%s, min_words=%d)' % (len(files), dir_, source, min_words), flush=True)
    tot = vids = novid = nodate = 0
    for fp in files:
        vid = os.path.splitext(os.path.basename(fp))[0]
        key = 'cspan:%s' % vid
        if key in done: continue
        try:
            rec = json.load(open(fp, encoding='utf-8'))
        except Exception as e:
            con.execute('INSERT OR REPLACE INTO cspan_fetch_log VALUES (?,?,?)', (key, 'err:' + str(e)[:40], datetime.datetime.now().isoformat())); con.commit(); continue
        date = (rec.get('date') or '')[:10]
        url = rec.get('url') or ''
        show = show_of(url)
        if not re.match(r'\d{4}-\d{2}-\d{2}$', date):   # NEVER store dateless rows
            con.execute('INSERT OR REPLACE INTO cspan_fetch_log VALUES (?,?,?)', (key, 'nodate', datetime.datetime.now().isoformat())); con.commit(); nodate += 1; continue
        rows = []; seen = set()
        for t in (rec.get('turns') or []):
            m = resolve_full(clean_name(t.get('name')))          # drop-never-guess
            if not m: continue
            sp = scrub(re.sub(r'\s+', ' ', t.get('text') or '').strip())
            if len(sp.split()) < min_words: continue             # drop micro-interjections
            h = (m, hashlib.md5(sp.encode('utf-8', 'replace')).hexdigest())
            if h in seen: continue                                # per-video (member,text) dedup
            seen.add(h)
            rows.append((m, date, source, show, url, len(sp.split()), sp))
        con.executemany('INSERT INTO speeches VALUES (?,?,?,?,?,?,?)', rows)
        con.execute('INSERT OR REPLACE INTO cspan_fetch_log VALUES (?,?,?)', (key, 'ok', datetime.datetime.now().isoformat()))
        con.commit()
        tot += len(rows); vids += 1
        if not rows: novid += 1
        elif len(rows): print('cspan %s (%s): %d member turns -> %s (total %d)' % (vid, date, len(rows), ','.join(sorted(set(r[0] for r in rows)))[:60], tot), flush=True)
    con.close()
    print('CSPAN load done: %d member turns from %d videos (%d had no roster member, %d dateless skipped)' % (tot, vids, novid, nodate))

def status(source='CSPAN', dbpath=None):
    con = db(dbpath)
    row = con.execute("SELECT COUNT(*), COUNT(DISTINCT member), COALESCE(SUM(nwords),0) FROM speeches WHERE source=?", (source,)).fetchone()
    print('source=%-9s %6d turns | %3d members | %.2fM words' % (source, row[0], row[1], row[2] / 1e6))
    for st, n in con.execute("SELECT status, COUNT(*) FROM cspan_fetch_log GROUP BY status"):
        print('  fetch_log %-8s %d' % (st, n))
    con.close()

if __name__ == '__main__':
    a = sys.argv
    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default
    dbpath = opt('--db')
    source = opt('--source', 'INTERVIEW')   # user decision 2026-07-11 (see module docstring)
    if 'status' in a:
        status(source, dbpath)
    else:
        d = opt('--dir', DEFAULT_DIR)
        load(d, source=source, min_words=int(opt('--min-words', '8')), dbpath=dbpath)
