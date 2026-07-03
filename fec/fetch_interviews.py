# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root
"""BROADCAST INTERVIEW COLLECTOR (user-directed 2026-07-03: B&L found interviews the most authentic
personality medium — "see where they source the interviews from and lets add those"; their 99
interviews came from five German broadcast formats, so this is the U.S. mapping).

Sources (adapters):
  * CNN  — transcripts.cnn.com/date/YYYY-MM-DD -> /show/<code>/date/<d>/segment/NN. Full daily
           archive across ALL CNN shows. Labels: "MARKWAYNE MULLIN, U.S. SECRETARY...:" on first
           mention, "MULLIN:" after — intros build a per-segment surname alias map.
  * MTP  — nbcnews.com Meet the Press weekly transcript pages (hub + archive page discovery).
           Labels: "SEN. ELIZABETH WARREN:" (title-prefixed full names).
Attribution: normalized full-name match against the 533 roster (titles stripped); surname-only
continuation labels resolve ONLY via the segment's own intro aliases; unresolvable speakers are
DROPPED, never guessed (same discipline as fetch_congressional_record). Host/anchor speech never
enters the corpus. Storage: speeches table, source='INTERVIEW' (big5_traits and the per-source
validity harness pick these up automatically); iv_fetch_log makes reruns resumable.
Usage:
  python fetch_interviews.py cnn --since 2025-01-01 [--until 2026-07-03]
  python fetch_interviews.py mtp
  python fetch_interviews.py status
Politeness: ~0.7s between requests, honest UA. Internal research use."""
import sys, os, re, json, sqlite3, datetime, time, urllib.request, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B = MB_ROOT
DB = B + r'\social_media.db'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36 (research collector)'}
PAUSE = 0.7

def db():
    c = sqlite3.connect(DB, timeout=60); c.execute('PRAGMA journal_mode=WAL')
    c.execute('''CREATE TABLE IF NOT EXISTS speeches(member TEXT,date TEXT,source TEXT,chamber TEXT,
                 package TEXT,nwords INTEGER,text TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS iv_fetch_log(key TEXT PRIMARY KEY,status TEXT,ts TEXT)')
    return c

def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception:
            if i == tries - 1: raise
            time.sleep(3 * (i + 1))

def strip_tags(h):
    h = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', h, flags=re.S)
    h = re.sub(r'<br[^>]*>|</p>|</div>', '\n', h, flags=re.I)
    h = re.sub(r'<[^>]+>', ' ', h)
    h = h.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    return h

# ---------------- roster resolution ----------------
C = {m['member']: m for m in json.load(open(B + r'\congestion.json'))}
TITLE = re.compile(r'^(SEN\.|REP\.|SENATOR|REPRESENTATIVE|SPEAKER OF THE HOUSE|SPEAKER|HOUSE MINORITY LEADER|'
                   r'HOUSE MAJORITY LEADER|SENATE (MAJORITY|MINORITY) LEADER|DEL\.|CONGRESSMAN|CONGRESSWOMAN|DR\.)\s+', re.I)
def norm(s): return re.sub(r"[^a-z ]", '', s.lower()).strip()
FULL = {}
for m in C:
    p = norm(m).split()
    if len(p) >= 2: FULL[(p[0], p[-1])] = m
SUR = collections.defaultdict(list)
for m in C:
    SUR[norm(m).split()[-1]].append(m)

def resolve_full(label):
    """'SEN. ELIZABETH WARREN' / 'THOM TILLIS' -> roster member or None (never guess)."""
    s = TITLE.sub('', label.strip())
    s = re.sub(r'\(.*?\)', '', s)               # (D-MA)
    p = norm(s).split()
    if len(p) >= 2:
        m = FULL.get((p[0], p[-1]))
        if m: return m
        cands = SUR.get(p[-1], [])
        if len(cands) == 1 and re.match(r'^(SEN|REP|SENATOR|REPRESENTATIVE|CONGRESS)', label.strip(), re.I):
            return cands[0]
    return None

LABEL = re.compile(r'^\s*([A-Z][A-Z .,\'()\-]{1,70}?):\s', re.M)
def parse_turns(text):
    """Split transcript text into (label, speech) turns; build intro alias map for surname labels."""
    turns = []
    pos = [(m.start(), m.group(1)) for m in LABEL.finditer(text)]
    for i, (st, lab) in enumerate(pos):
        end = pos[i + 1][0] if i + 1 < len(pos) else len(text)
        sp = text[st:end]
        sp = sp[sp.index(':') + 1:].strip()
        turns.append((lab.strip(), re.sub(r'\s+', ' ', sp)))
    alias = {}
    for lab, _ in turns:
        base = lab.split(',')[0].strip()          # "MARKWAYNE MULLIN, U.S. ...:" -> full-name part
        m = resolve_full(base)
        if m and len(norm(base).split()) >= 2:
            alias[norm(base).split()[-1]] = m     # surname -> member for continuations
    out = []
    for lab, sp in turns:
        base = lab.split(',')[0].strip()
        m = resolve_full(base)
        if not m:
            k = norm(base).split()
            m = alias.get(k[-1]) if len(k) == 1 else None
        if m and len(sp.split()) >= 8:            # drop micro-interjections
            out.append((m, sp))
    return out

def store(con, rows, date, show, url):
    n = 0
    for m, sp in rows:
        con.execute('INSERT INTO speeches VALUES (?,?,?,?,?,?,?)',
                    (m, date, 'INTERVIEW', show, url, len(sp.split()), sp))
        n += 1
    return n

# ---------------- adapters ----------------
def run_cnn(since, until):
    con = db(); done = {k for (k,) in con.execute("SELECT key FROM iv_fetch_log WHERE status='ok'")}
    d = datetime.date.fromisoformat(since); end = datetime.date.fromisoformat(until)
    tot = 0
    while d <= end:
        key = 'cnn:%s' % d.isoformat()
        if key in done: d += datetime.timedelta(days=1); continue
        try:
            idx = get('https://transcripts.cnn.com/date/%s' % d.isoformat()); time.sleep(PAUSE)
            segs = sorted(set(re.findall(r'href="(/show/[^"]+/date/%s/segment/[^"]+)"' % d.isoformat(), idx)))
            nd = 0
            for s in segs:
                try:
                    page = get('https://transcripts.cnn.com' + s); time.sleep(PAUSE)
                    rows = parse_turns(strip_tags(page))
                    nd += store(con, rows, d.isoformat(), s.split('/')[2], 'https://transcripts.cnn.com' + s)
                    con.commit()   # SHORT transactions: a day-long write TX starved the CREC collector's lock (2026-07-03)
                except Exception:
                    continue
            con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', (key, 'ok', datetime.datetime.now().isoformat()))
            con.commit(); tot += nd
            print('%s: %d segments, %d member turns (total %d)' % (d.isoformat(), len(segs), nd, tot), flush=True)
        except Exception as e:
            print('%s: FAIL %s' % (d.isoformat(), str(e)[:90]), flush=True)
        d += datetime.timedelta(days=1)
    con.close(); print('CNN done: %d member turns added' % tot)

def run_mtp():
    con = db(); done = {k for (k,) in con.execute("SELECT key FROM iv_fetch_log WHERE status='ok'")}
    hubs = ['https://www.nbcnews.com/meet-the-press/meet-press-transcripts-n51976',
            'https://www.nbcnews.com/meet-the-press/news/meet-the-press-transcripts-archive-rcna254151']
    links = set()
    for h in hubs:
        try:
            page = get(h); time.sleep(PAUSE)
            links |= set(re.findall(r'href="(https://www\.nbcnews\.com/meet-the-press/transcripts/[^"]+)"', page))
        except Exception as e:
            print('hub FAIL %s %s' % (h, str(e)[:80]))
    print('MTP transcript pages discovered: %d' % len(links))
    tot = 0
    for u in sorted(links):
        key = 'mtp:' + u.rsplit('/', 1)[-1]
        if key in done: continue
        try:
            page = get(u); time.sleep(PAUSE)
            md = re.search(r'(\d{4}-\d{2}-\d{2})', page)
            date = md.group(1) if md else ''
            rows = parse_turns(strip_tags(page))
            n = store(con, rows, date, 'meet-the-press', u)
            con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', (key, 'ok', datetime.datetime.now().isoformat()))
            con.commit(); tot += n
            print('%s: %d member turns' % (u.rsplit('/', 1)[-1][:60], n), flush=True)
        except Exception as e:
            print('%s FAIL %s' % (u[-50:], str(e)[:80]), flush=True)
    con.close(); print('MTP done: %d member turns added' % tot)

MIXED_LABEL = re.compile(r'^\s*((?:Sen\.|Rep\.|Del\.|Gov\.|Speaker|Leader|Dr\.)?\s*[A-Z][A-Za-z.\'\-]+(?: [A-Z][A-Za-z.\'\-]+){0,3}(?:\s*\([A-Za-z.\- ]+\))?):\s', re.M)   # PBS: "Rep. Tom Kean (R-NJ):"
def parse_turns_mixed(text):
    """PBS-style mixed-case labels ('Rep. Tom Kean:'); same drop-never-guess discipline."""
    turns = []
    pos = [(m.start(), m.group(1)) for m in MIXED_LABEL.finditer(text)]
    out = []
    for i, (st, lab) in enumerate(pos):
        end = pos[i + 1][0] if i + 1 < len(pos) else len(text)
        sp = text[st:end]; sp = sp[sp.index(':') + 1:].strip()
        m = resolve_full(lab)
        if m and len(sp.split()) >= 8:
            out.append((m, re.sub(r'\s+', ' ', sp)))
    return out

def run_cbs():
    con = db(); done = {k for (k,) in con.execute("SELECT key FROM iv_fetch_log WHERE status='ok'")}
    idx = ['https://www.cbsnews.com/face-the-nation/transcripts/'] + \
          ['https://www.cbsnews.com/news/face-the-nation-transcripts-%d' % y for y in (2024, 2025, 2026)]
    arts = set()
    for u in idx:
        try:
            page = get(u); time.sleep(PAUSE)
            for h in re.findall(r'href="(https?://(?:www\.)?cbsnews\.com/news/[^"]*transcript[^"]*)"', page):
                arts.add(h.split('?')[0])
        except Exception as e:
            print('cbs index FAIL %s %s' % (u[-40:], str(e)[:70]), flush=True)
    print('CBS transcript articles discovered: %d' % len(arts))
    tot = 0
    for u in sorted(arts):
        key = 'cbs:' + u.rstrip('/').rsplit('/', 1)[-1][:80]
        if key in done: continue
        try:
            page = get(u); time.sleep(PAUSE)
            md = re.search(r'(\d{2})-(\d{2})-(\d{4})', u)
            date = '%s-%s-%s' % (md.group(3), md.group(1), md.group(2)) if md else ''
            rows = parse_turns(strip_tags(page))
            n = store(con, rows, date, 'face-the-nation', u)
            con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', (key, 'ok', datetime.datetime.now().isoformat()))
            con.commit(); tot += n
            print('cbs %s: %d turns' % (key[4:60], n), flush=True)
        except Exception as e:
            print('cbs %s FAIL %s' % (u[-50:], str(e)[:70]), flush=True)
    con.close(); print('CBS done: %d member turns' % tot)

def run_abc():
    con = db(); done = {k for (k,) in con.execute("SELECT key FROM iv_fetch_log WHERE status='ok'")}
    try:
        page = get('https://abcnews.go.com/Politics/week-transcript-archive/story?id=16614108'); time.sleep(PAUSE)
    except Exception as e:
        print('abc archive FAIL', str(e)[:80]); return
    links = set()
    for h in re.findall(r'href="([^"]*week-transcript[^"]*/story\?id=\d+)"', page):
        if h.startswith('//'): h = 'https:' + h
        elif h.startswith('/'): h = 'https://abcnews.go.com' + h
        elif not h.startswith('http'): h = 'https://' + h
        links.add(h.replace('abcnews.com', 'abcnews.go.com'))
    print('ABC transcript stories discovered: %d' % len(links))
    tot = 0
    for u in sorted(links):
        key = 'abc:' + u.rsplit('=', 1)[-1]
        if key in done: continue
        try:
            page = get(u); time.sleep(PAUSE)
            rows = parse_turns(strip_tags(page))
            n = store(con, rows, '', 'this-week', u)
            con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', (key, 'ok', datetime.datetime.now().isoformat()))
            con.commit(); tot += n
            print('abc %s: %d turns' % (key, n), flush=True)
        except Exception as e:
            print('abc %s FAIL %s' % (u[-40:], str(e)[:70]), flush=True)
    con.close(); print('ABC done: %d member turns' % tot)

MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
def run_pbs(since, until):
    con = db(); done = {k for (k,) in con.execute("SELECT key FROM iv_fetch_log WHERE status='ok'")}
    d = datetime.date.fromisoformat(since); end = datetime.date.fromisoformat(until)
    tot = 0
    while d <= end:
        key = 'pbs:%s' % d.isoformat()
        if key in done: d += datetime.timedelta(days=1); continue
        slugs = ['%s-%d-%d-pbs-news-hour-full-episode' % (MONTHS[d.month - 1], d.day, d.year),
                 '%s-%d-%d-pbs-news-weekend-full-episode' % (MONTHS[d.month - 1], d.day, d.year),
                 '%s-%d-%d-pbs-newshour-full-episode' % (MONTHS[d.month - 1], d.day, d.year)]
        nd = 0; found = False
        for slug in slugs:
            try:
                page = get('https://www.pbs.org/newshour/show/' + slug); time.sleep(PAUSE)
            except Exception:
                continue
            found = True
            segs = sorted(set(re.findall(r'href="(https://www\.pbs\.org/newshour/show/[a-z0-9\-]+)"', page)))
            segs = [s for s in segs if 'full-episode' not in s][:30]
            for s in segs:
                skey = 'pbsseg:' + s.rsplit('/', 1)[-1][:90]
                if skey in done: continue
                try:
                    sp = get(s); time.sleep(PAUSE)
                    i = sp.find('class="video-transcript')   # probe 2026-07-03: transcript div class (no id anchor)
                    if i < 0: i = sp.find('id="transcript"')
                    if i < 0: continue
                    body = re.sub(r'<[^>]+>', '\n', sp[i:i + 200000])
                    rows = parse_turns_mixed(body)
                    nd += store(con, rows, d.isoformat(), 'pbs-newshour', s)
                    con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', (skey, 'ok', datetime.datetime.now().isoformat()))
                    con.commit()   # short transactions (lock hygiene)
                except Exception:
                    continue
            break
        con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', (key, 'ok' if found else 'noep', datetime.datetime.now().isoformat()))
        con.commit(); tot += nd
        if found: print('pbs %s: %d member turns (total %d)' % (d.isoformat(), nd, tot), flush=True)
        d += datetime.timedelta(days=1)
    con.close(); print('PBS done: %d member turns' % tot)

if __name__ == '__main__':
    if 'status' in sys.argv:
        con = db()
        for src, n, dm, w in con.execute("SELECT source, COUNT(*), COUNT(DISTINCT member), SUM(nwords) FROM speeches GROUP BY source"):
            print('%-10s %6d turns | %3d members | %.2fM words' % (src, n, dm, (w or 0) / 1e6))
        sys.exit(0)
    ap = {a.split('=')[0]: a for a in sys.argv}
    since = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--since'), '2025-01-01')
    until = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--until'), datetime.date.today().isoformat())
    if 'cnn' in sys.argv: run_cnn(since, until)
    elif 'mtp' in sys.argv: run_mtp()
    elif 'cbs' in sys.argv: run_cbs()
    elif 'abc' in sys.argv: run_abc()
    elif 'pbs' in sys.argv: run_pbs(since, until)
    else: print('usage: fetch_interviews.py [cnn|mtp|cbs|abc|pbs|status] [--since YYYY-MM-DD] [--until YYYY-MM-DD]')
    # NOTE (2026-07-03): Fox News Sunday examined — no public transcript archive exists anymore
    # (show page + /transcript both empty of transcript links); route later via YouTube captions.
