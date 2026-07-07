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
import sys, os, re, json, sqlite3, datetime, time, urllib.request, urllib.error, collections, socket
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# GLOBAL socket timeout (2026-07-06: fox wedged with 0 CPU for hours on a hung request — the
# per-call urlopen(timeout=60) did NOT fire, so a bad socket blocked indefinitely and froze the
# leg while cnn-deep carried on. A process-wide default forces EVERY socket op to time out,
# catching the cases the per-request timeout misses). The leg's own retry/skip then continues.
socket.setdefaulttimeout(90)
B = MB_ROOT
DB = B + r'\social_media.db'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36 (research collector)',
      # cbsnews.com 406s requests with no Accept header (content-negotiation WAF, verified 2026-07-05);
      # standard browser Accept headers unblock it and are inert for every other leg.
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.9'}
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

import html as _html
def strip_tags(h):
    h = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', h, flags=re.S)
    h = re.sub(r'<br[^>]*>|</p>|</div>', '\n', h, flags=re.I)
    h = re.sub(r'<[^>]+>', ' ', h)
    return _html.unescape(h)   # QA 2026-07-03: full entity decode (54 PBS rows carried &#039; residue)

STAGE = re.compile(r'\((?:END|BEGIN)\s+(?:VIDEO\s+)?(?:CLIP|TAPE|CLIP MONTAGE)\)|\(COMMERCIAL BREAK\)|\(CROSSTALK\)|\(APPLAUSE\)|\(LAUGHTER\)|\(BEGIN VIDEOTAPE\)|\(END VIDEOTAPE\)', re.I)
INLINE_LABEL = re.compile(r'\s([A-Z][A-Z.\'\-]+(?: [A-Z.,\'()\-]+[A-Z.\'\-]*){0,4}):\s')
_ACRO = {'CIA', 'FBI', 'NATO', 'COVID', 'DOJ', 'DHS', 'ICE', 'IRS', 'GOP', 'US', 'USA', 'U.S.', 'CNN', 'PBS',
         'NPR', 'CBS', 'ABC', 'NBC', 'VA', 'DC', 'AI', 'EPA', 'FDA', 'CDC', 'HHS', 'SNAP', 'NIH', 'FEMA', 'UN'}
def scrub(sp):
    """Remove stage directions AND truncate at a swallowed inline speaker label (QA2: labels not at
    line starts let the NEXT speaker's words ride inside a member's turn — 'MARK STRASSMANN:').
    Acronym-colon constructions in real speech ('the CIA: their view is...') never truncate."""
    sp = STAGE.sub(' ', sp)
    pos = 1
    while True:
        m = INLINE_LABEL.search(sp, pos)
        if not m: break
        words = set(m.group(1).replace(',', '').split())
        if words - _ACRO:                      # at least one non-acronym token -> real speaker label
            sp = sp[:m.start()]; break
        pos = m.end()
    return re.sub(r'\s+', ' ', sp).strip()

# ---------------- roster resolution ----------------
C = {m['member']: m for m in json.load(open(B + r'\congestion.json'))}
TITLE = re.compile(r'^(SEN\.|REP\.|SENATOR|REPRESENTATIVE|SPEAKER OF THE HOUSE|SPEAKER|HOUSE MINORITY LEADER|'
                   r'HOUSE MAJORITY LEADER|SENATE (MAJORITY|MINORITY) LEADER|DEL\.|CONGRESSMAN|CONGRESSWOMAN|DR\.)\s+', re.I)
import unicodedata as _ud
def norm(s):
    s = _ud.normalize('NFD', s)                       # QA2: 'Raúl' must become 'raul', not 'ral'
    s = ''.join(c for c in s if not _ud.combining(c))
    return re.sub(r"[^a-z ]", '', s.lower()).strip()
# QA3 2026-07-04 (nomological-fix session): nickname equivalence classes. 'BERNIE SANDERS' failed
# to resolve to roster 'Bernard Sanders' (prefix test covers tom~thomas but not bernie~bernard) —
# Sanders/Murphy had 1 interview row each while dominating cable news. Equivalence is applied BOTH
# directions (roster stores 'Chuck Grassley'; transcripts may say 'CHARLES GRASSLEY').
NICK_SETS = [
    {'bernard', 'bernie'}, {'charles', 'chuck', 'charlie'}, {'christopher', 'chris'},
    {'richard', 'dick', 'rich', 'rick'}, {'michael', 'mike'}, {'james', 'jim', 'jimmy'},
    {'robert', 'bob', 'rob', 'bobby'}, {'thomas', 'tom', 'tommy'}, {'daniel', 'dan', 'danny'},
    {'joseph', 'joe', 'joey'}, {'timothy', 'tim'}, {'patrick', 'pat'},
    {'william', 'bill', 'will', 'billy'}, {'edward', 'ed', 'ted', 'eddie'},
    {'theodore', 'ted'}, {'elizabeth', 'liz', 'beth', 'betty'}, {'katherine', 'kathryn', 'katie', 'kate', 'kathy'},
    {'margaret', 'maggie', 'meg'}, {'benjamin', 'ben'}, {'alexander', 'alex'},
    {'anthony', 'tony'}, {'andrew', 'andy', 'drew'}, {'matthew', 'matt'}, {'jonathan', 'jon'},
    {'nicholas', 'nick'}, {'gregory', 'greg'}, {'lawrence', 'larry'}, {'gerald', 'jerry'},
    {'ronald', 'ron', 'ronny'}, {'donald', 'don'}, {'kenneth', 'ken'}, {'stephen', 'steven', 'steve'},
    {'david', 'dave'}, {'samuel', 'sam'}, {'frederick', 'fred'}, {'susan', 'sue', 'suzy'},
    {'deborah', 'debbie', 'deb'}, {'cynthia', 'cindy'}, {'jacquelyn', 'jacqueline', 'jackie'},
    {'raphael', 'rafael', 'raffi'}, {'joshua', 'josh'}, {'zachary', 'zach', 'zack'},
    {'abigail', 'abby'}, {'rebecca', 'becca', 'becky'}, {'jefferson', 'jeff'}, {'jeffrey', 'jeff'},
    {'mitchell', 'mitch'}, {'randall', 'randy'}, {'terrence', 'terri', 'terry'}, {'vincent', 'vince'},
]
NICK = {}
for s in NICK_SETS:
    for a in s: NICK.setdefault(a, set()).update(s)
def _variants(first):
    return NICK.get(first, set()) | {first}
FULL = {}
for m in C:
    p = norm(m).split()
    if len(p) >= 2:
        for v in _variants(p[0]): FULL.setdefault((v, p[-1]), m)
SUR = collections.defaultdict(list)
for m in C:
    SUR[norm(m).split()[-1]].append(m)
# rank-scoped surname pools (user rule 2026-07-06: 'Speaker Johnson refers to only one person' —
# the rank word carries disambiguating information the flat pool discards). Verified on the live
# roster: 'senator johnson' -> Ron Johnson uniquely (the 4 other Johnsons are House); 'senator
# scott' stays ambiguous (Rick+Tim) and correctly never binds.
SUR_SEN = collections.defaultdict(list); SUR_HOU = collections.defaultdict(list)
for m in C:
    (SUR_SEN if (C[m].get('chamber') == 'Senate') else SUR_HOU)[norm(m).split()[-1]].append(m)
# 119th-Congress floor-leadership singletons (role data isn't in the roster; these constants are
# exactly as current as the roster file itself — refresh alongside it at the next Congress).
LEADERSHIP = ['Mike Johnson', 'John Thune', 'Charles Schumer', 'Steve Scalise', 'Hakeem Jeffries',
              'John Barrasso', 'Richard Durbin', 'Tom Emmer', 'Katherine Clark']
LEAD_SUR = {norm(m).split()[-1]: [m] for m in LEADERSHIP if m in C}

def _firstname_compatible(a, b):
    """'tom'~'thomas' yes; nickname classes (bernie~bernard) yes; 'raul'~'adelita' NO
    (QA2: succession-seat misattribution guard)."""
    a, b = a.lower(), b.lower()
    return a == b or a.startswith(b) or b.startswith(a) or bool(_variants(a) & _variants(b))

def resolve_full(label):
    """'SEN. ELIZABETH WARREN' / 'THOM TILLIS' -> roster member or None (never guess).
    QA2 hardening: the unique-surname fallback fires ONLY when the label's first name is
    COMPATIBLE with the roster member's (nickname/prefix) — a mismatched first name means a
    DIFFERENT person (predecessor, relative) and must never bind."""
    s = TITLE.sub('', label.strip())
    s = re.sub(r'\(.*?\)', '', s)               # (D-MA)
    p = norm(s).split()
    if len(p) >= 2:
        m = FULL.get((p[0], p[-1]))
        if m: return m
        cands = SUR.get(p[-1], [])
        if (len(cands) == 1 and re.match(r'^(SEN|REP|SENATOR|REPRESENTATIVE|CONGRESS)', label.strip(), re.I)
                and _firstname_compatible(p[0], norm(cands[0]).split()[0])):
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
    alias = {}; _ambig = set()
    for lab, _ in turns:
        base = lab.split(',')[0].strip()          # "MARKWAYNE MULLIN, U.S. ...:" -> full-name part
        m = resolve_full(base)
        if m and len(norm(base).split()) >= 2:
            sur = norm(base).split()[-1]
            if sur in alias and alias[sur] != m: _ambig.add(sur)   # QA2: Mike + Ron Johnson in one segment
            alias[sur] = m
    for sur in _ambig: alias.pop(sur, None)       # ambiguous surnames never bind continuations
    out = []
    for lab, sp in turns:
        base = lab.split(',')[0].strip()
        m = resolve_full(base)
        if not m:
            k = norm(base).split()
            m = alias.get(k[-1]) if len(k) == 1 else None
        if m:
            sp = scrub(sp)
            if len(sp.split()) >= 8:              # drop micro-interjections
                out.append((m, sp))
    return out

def store(con, rows, date, show, url):
    # QA 2026-07-07: some source pages embed the transcript body TWICE in one document (observed on
    # Fox, e.g. .../why-do-we-still-not-know-... carried the whole Carlson show verbatim twice) ->
    # parse_turns faithfully returned every turn twice -> store double-inserted. Dedup within the
    # page on (member, exact text): a real interview never has one member repeat a turn verbatim,
    # so this only ever removes source-side duplication. Shared by all 8 legs, so it hardens each.
    n = 0; seen = set()
    for m, sp in rows:
        k = (m, sp)
        if k in seen: continue
        seen.add(k)
        con.execute('INSERT INTO speeches VALUES (?,?,?,?,?,?,?)',
                    (m, date, 'INTERVIEW', show, url, len(sp.split()), sp))
        n += 1
    return n

# ---------------- adapters ----------------
def run_cnn(since, until, verify=False):
    """Coverage-audit hardening 2026-07-06: (1) a failed SEGMENT no longer poisons coverage
    silently — the day is marked 'partial' (not 'ok') so future runs revisit it; (2) day re-walks
    are idempotent — segments already stored for that day are skipped, never duplicated; (3)
    --verify re-walks EVERY day in range (index fetch each, segments only where missing) to
    repair the historical ok-on-partial losses the old code could not see."""
    con = db(); done = {k for (k,) in con.execute("SELECT key FROM iv_fetch_log WHERE status='ok'")}
    done_seg = {k for (k,) in con.execute("SELECT key FROM iv_fetch_log WHERE key LIKE 'cnnseg:%'")}
    d = datetime.date.fromisoformat(since); end = datetime.date.fromisoformat(until)
    tot = repaired = 0
    while d <= end:
        key = 'cnn:%s' % d.isoformat()
        if key in done and not verify: d += datetime.timedelta(days=1); continue
        try:
            idx = get('https://transcripts.cnn.com/date/%s' % d.isoformat()); time.sleep(PAUSE)
            segs = sorted(set(re.findall(r'href="(/show/[^"]+/date/%s/segment/[^"]+)"' % d.isoformat(), idx)))
            have = {p for (p,) in con.execute("SELECT DISTINCT package FROM speeches WHERE package LIKE 'https://transcripts.cnn.com%' AND date=?", (d.isoformat(),))}
            new = [s for s in segs if ('https://transcripts.cnn.com' + s) not in have and ('cnnseg:' + s) not in done_seg]
            nd = fails = 0
            for s in new:
                try:
                    page = get('https://transcripts.cnn.com' + s); time.sleep(PAUSE)
                    rows = parse_turns(strip_tags(page))
                    n0 = store(con, rows, d.isoformat(), s.split('/')[2], 'https://transcripts.cnn.com' + s)
                    if n0 == 0:   # zero-yield marker (verify lesson 2026-07-06: 21k historically-empty
                        # segments were refetched because 'stored nothing' looked like 'never fetched')
                        con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)',
                                    ('cnnseg:' + s, 'empty', datetime.datetime.now().isoformat()))
                    nd += n0
                    con.commit()   # SHORT transactions: a day-long write TX starved the CREC collector's lock (2026-07-03)
                except Exception:
                    fails += 1
            con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)',
                        (key, 'ok' if fails == 0 else 'partial', datetime.datetime.now().isoformat()))
            con.commit(); tot += nd
            if verify and new: repaired += len(new) - fails
            if new or not verify:
                print('%s: %d segments (%d new, %d failed), %d member turns (total %d)' % (
                    d.isoformat(), len(segs), len(new), fails, nd, tot), flush=True)
        except Exception as e:
            print('%s: FAIL %s' % (d.isoformat(), str(e)[:90]), flush=True)
        d += datetime.timedelta(days=1)
    con.close()
    print('CNN done: %d member turns added%s' % (tot, (' | verify repaired %d segments' % repaired) if verify else ''))

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
    # DEEP enumeration (coverage audit 2026-07-06: the hubs only expose RECENT transcripts — the
    # stored corpus was 19 pages / Jan-Jun 2026 only). NBC's monthly article sitemaps carry every
    # episode page under TWO patterns: legacy 'meet-the-press/meet-press-<date>-nID' (verified
    # parseable: Sanders 5 turns on 2024-10-27) and current 'meet-the-press/transcripts/<slug>'.
    today = datetime.date.today()
    y, m = 2014, 1
    while (y, m) <= (today.year, today.month):
        try:
            sm = get('https://www.nbcnews.com/sitemap/nbcnews/sitemap-%04d-%02d-article.xml' % (y, m))
            links |= set(re.findall(r'<loc>(https://www\.nbcnews\.com/meet-the-press/(?:transcripts/|meet-press-)[^<]+)</loc>', sm))
        except Exception:
            pass   # months with no sitemap (pre-CMS) are expected
        time.sleep(PAUSE)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    links = {u for u in links if 'transcripts-n51976' not in u and 'transcripts-archive' not in u}
    print('MTP transcript pages discovered: %d (hubs + 2014->now monthly sitemaps)' % len(links))
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
        if m:
            sp = scrub(sp)
            if len(sp.split()) >= 8:
                out.append((m, sp))
    return out

def run_cbs():
    con = db(); done = {k for (k,) in con.execute("SELECT key FROM iv_fetch_log WHERE status='ok'")}
    idx = ['https://www.cbsnews.com/face-the-nation/transcripts/'] + \
          ['https://www.cbsnews.com/news/face-the-nation-transcripts-%d' % y for y in range(2019, 2027)]   # probe 2026-07-03: year archives exist back to at least 2019 (~150 eps each)
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
            if not date:   # QA: guest pages without URL dates -> page metadata
                mp = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', page)
                date = mp.group(1) if mp else ''
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
            mp = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', page)   # QA: ABC stored empty dates
            rows = parse_turns(strip_tags(page))
            n = store(con, rows, mp.group(1) if mp else '', 'this-week', u)
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

NPR_PROGRAMS = ('morning-edition', 'all-things-considered', 'weekend-edition-saturday', 'weekend-edition-sunday')
def run_npr(since, until):
    """NPR program archives -> per-story /transcripts/ pages (CAPS labels incl. 'NAME, BYLINE:' —
    the standard parse_turns handles them; hosts/reporters don't resolve to the roster and drop)."""
    con = db(); done = {k for (k,) in con.execute("SELECT key FROM iv_fetch_log WHERE status='ok'")}
    d = datetime.date.fromisoformat(since); end = datetime.date.fromisoformat(until)
    tot = 0
    while d <= end:
        for prog in NPR_PROGRAMS:
            key = 'npr:%s:%s' % (prog, d.isoformat())
            if key in done: continue
            try:
                idx = get('https://www.npr.org/programs/%s/archive?date=%s' % (prog, d.strftime('%m-%d-%Y'))); time.sleep(PAUSE)
                links = sorted(set(re.findall(r'href="(https://www\.npr\.org/transcripts/[^"#?]+)"', idx)))
                nd = 0
                for u in links:
                    tkey = 'nprtx:' + u.rsplit('/', 1)[-1]
                    if tkey in done: continue
                    try:
                        page = get(u); time.sleep(PAUSE)
                        # NPR wraps labels inline (<b>GONYEA:</b> mid-paragraph) — every tag must
                        # become a NEWLINE or only the first label sits at a line start.
                        body = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', page, flags=re.S)
                        body = re.sub(r'<[^>]+>', '\n', body)
                        rows = parse_turns(body)
                        nd += store(con, rows, d.isoformat(), 'npr-' + prog, u)
                        con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', (tkey, 'ok', datetime.datetime.now().isoformat()))
                        con.commit()
                        done.add(tkey)
                    except Exception:
                        continue
                con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', (key, 'ok', datetime.datetime.now().isoformat()))
                con.commit(); tot += nd
                if nd: print('npr %s %s: %d member turns (total %d)' % (prog[:14], d.isoformat(), nd, tot), flush=True)
            except Exception as e:
                print('npr %s %s FAIL %s' % (prog[:14], d.isoformat(), str(e)[:70]), flush=True)
        d += datetime.timedelta(days=1)
    con.close(); print('NPR done: %d member turns' % tot)

def run_fox():
    """Fox News transcript archive (foxnews.com/transcript/...). REVISED FINDING 2026-07-05 (the
    2026-07-03 'no public archive' note was wrong — the category page is JS-rendered, which made
    it LOOK empty): full-episode transcripts exist back to ~2018 but Fox STOPPED POSTING them
    ~2024-10, and the article-search API no longer honors its offset param. Enumeration therefore
    walks the article SITEMAPS (~166 pages, one fetch each) and filters /transcript/ URLs — the
    archive is historical; if Fox resumes publishing, re-runs pick new URLs up automatically.
    Old interviews of CURRENT members are valid personality/relational text (RKH used 1996-2014);
    non-roster guests drop at parse_turns (drop-never-guess). Post-2024-10 Fox stays unavailable
    until a YouTube-caption diarization build exists (captions carry no speaker labels)."""
    # QA 2026-07-07 (user-approved): the Fox archive holds thousands of long-removed transcript URLs
    # that now 404 (dead 2004-era campaign posts); with no skip-marker each run re-fetched every one.
    # Skip keys marked 'ok' (collected) OR 'gone' (a CONFIRMED hard 404/410 — see the except below).
    # 'gone' is written ONLY for HTTP 404/410; a timeout / connection error / 5xx / 429 is NEVER
    # marked, so a slow-loading article that times out stays retryable and is re-attempted next run.
    con = db(); done = {k for (k,) in con.execute("SELECT key FROM iv_fetch_log WHERE status IN ('ok','gone')")}
    MONTHS = {m: i for i, m in enumerate(('january', 'february', 'march', 'april', 'may', 'june', 'july',
                                          'august', 'september', 'october', 'november', 'december'), 1)}
    try:
        idx = get('https://www.foxnews.com/sitemap.xml'); time.sleep(PAUSE)
    except Exception as e:
        print('fox sitemap index FAIL %s' % str(e)[:80]); con.close(); return
    pages = [u.replace('&amp;', '&') for u in re.findall(r'<loc>([^<]+type=articles[^<]*)</loc>', idx)]
    urls = []
    for i, p in enumerate(pages):
        try:
            urls += re.findall(r'<loc>(https://www\.foxnews\.com/transcript/[^<]+)</loc>', get(p))
        except Exception as e:
            print('fox sitemap page %d FAIL %s' % (i, str(e)[:60]), flush=True)
        time.sleep(PAUSE)
    urls = sorted(set(urls))
    print('fox: %d transcript urls enumerated from %d sitemap pages' % (len(urls), len(pages)), flush=True)
    tot = 0
    for u in urls:
        slug = u.rstrip('/').rsplit('/', 1)[-1]
        if 'local-air-times' in slug: continue
        key = 'fox:%s' % slug[:180]
        if key in done: continue
        try:
            page = get(u); time.sleep(PAUSE)
            md = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)-(\d{1,2})-(\d{4})', slug)
            date = '%04d-%02d-%02d' % (int(md.group(3)), MONTHS[md.group(1)], int(md.group(2))) if md else ''
            if not date:   # audit 2026-07-06: most Fox slugs carry no date — the page's JSON-LD does
                mp = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', page)
                if mp: date = mp.group(1)
            show = (slug[:md.start()].rstrip('-') if md else re.sub(r'-\d.*$', '', slug)) or 'fox'
            n = store(con, parse_turns(strip_tags(page)), date, show, u)
            con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', (key, 'ok', datetime.datetime.now().isoformat()))
            con.commit(); tot += n
            if n: print('fox %s: %d turns (total %d)' % (slug[:60], n, tot), flush=True)
        except Exception as e:
            # Mark PERMANENT-absence only: a hard 404 (Not Found) or 410 (Gone) after get()'s 3 retries.
            # Everything else (socket/read timeout on a slow page, connection reset, 5xx, 429, 403) is
            # transient -> left UNmarked so the next run retries it. This is the safety the user asked for:
            # a slow-to-load article is never mistaken for a dead one.
            if isinstance(e, urllib.error.HTTPError) and e.code in (404, 410):
                con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)',
                            (key, 'gone', datetime.datetime.now().isoformat()))
                con.commit()
            print('fox %s FAIL %s' % (slug[:50], str(e)[:80]), flush=True)
    con.close(); print('fox done: %d member turns' % tot)

def run_hewitt():
    """Hugh Hewitt Show (user 2026-07-05: 'we need some other Republican leaning news sources') —
    R-leaning radio, senator-dense, and CURRENT (unlike Fox's archive, Hewitt still posts full
    transcripts). FORMAT: host turns 'HH:', guest turns labeled by INITIALS ('JT:' = John Thune),
    guest named in the post title. ATTRIBUTION RULE (drop-never-guess): the title/slug must
    resolve to exactly ONE roster member via the full-name scan, AND the body label must match
    that member's initials (or caps surname / full name); everything else drops — multi-guest,
    surname-only-title, and non-member posts yield zero rows by design.
    Enumeration: the on-site interview archive page (~2k posts); dates from WP post-sitemaps."""
    con = db(); done = {k for (k,) in con.execute("SELECT key FROM iv_fetch_log WHERE status='ok'")}
    # dates: enumerate ALL post-sitemaps from the WP index (audit 2026-07-06 S2 fix: the first
    # build hardcoded post-sitemap 1-4, which cover 2005-era posts — every RECENT interview post
    # missed the map and 559/559 rows stored dateless, starving co-appearance/recency consumers).
    dates = {}
    try:
        wpidx = get('https://hughhewitt.com/wp-sitemap.xml'); time.sleep(PAUSE)
        smaps = [u for u in re.findall(r'<loc>([^<]+)</loc>', wpidx) if 'post-sitemap' in u]
    except Exception as e:
        smaps = []; print('hh wp-sitemap index FAIL (%s) — dates degrade to blank' % str(e)[:60], flush=True)
    for su in smaps:
        try:
            sm = get(su); time.sleep(PAUSE)
            for mu, md in re.findall(r'<url>\s*<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>', sm):
                dates[mu.rstrip('/')] = md[:10]
        except Exception:
            print('hh %s FAIL (some dates blank)' % su.rsplit('/', 1)[-1], flush=True)
    print('hewitt: date map covers %d posts from %d sitemaps' % (len(dates), len(smaps)), flush=True)
    try:
        idx = get('https://hughhewitt.com/hugh-hewitt-show-interview-archive'); time.sleep(PAUSE)
    except Exception as e:
        print('hh archive index FAIL %s' % str(e)[:80]); idx = ''
    posts = [u.rstrip('/') for u in dict.fromkeys(re.findall(r'href="(https://hughhewitt\.com/[^"#?]+)"', idx))
             if not re.search(r'/(category|tag|page|author|about|shows?|transcripts|wp-)', u)]
    # LIVE STREAM (audit run-5b S2-02 fix): the interview-archive page above is a HISTORICAL
    # snapshot — every post it yielded dated 2011-2014, and the 2026 Thune post had 0 stored
    # rows. The paginated /transcripts listing is the live index (~360 pages x 23 posts,
    # 2005->today); walk it and union with the archive page.
    try:
        first = get('https://hughhewitt.com/transcripts'); time.sleep(PAUSE)
        maxp = max([int(x) for x in re.findall(r'/transcripts/page/(\d+)', first)] or [1])
        stream = re.findall(r'href="(https://hughhewitt\.com/[^"#?]+)"', first)
        for pn in range(2, maxp + 1):
            try:
                stream += re.findall(r'href="(https://hughhewitt\.com/[^"#?]+)"',
                                     get('https://hughhewitt.com/transcripts/page/%d/' % pn))
            except Exception:
                print('hh transcripts page %d FAIL (continuing)' % pn, flush=True)
            time.sleep(PAUSE)
        posts += [u.rstrip('/') for u in dict.fromkeys(stream)
                  if not re.search(r'/(category|tag|page|author|about|shows?|transcripts|wp-|video|podcasts)', u)]
    except Exception as e:
        print('hh transcripts stream FAIL %s (archive-page set only)' % str(e)[:60], flush=True)
    posts = list(dict.fromkeys(posts))
    # SLUG PREFILTER: only fetch posts whose slug already points at a roster member (full name,
    # or rank word + known surname). Hewitt names the guest in the slug as the norm; fetching all
    # ~8k stream posts blind would take hours. Final attribution still runs the strict slug+title
    # resolution + body-label gate after the fetch — the prefilter only saves fetches.
    def _slug_hits(slug):
        pr = ' ' + re.sub(r'\s+', ' ', norm(slug.replace('-', ' '))) + ' '
        if any((' %s %s ' % (fn, ln)) in pr for (fn, ln) in FULL): return True
        for tm in re.finditer(r'\b(?:senator|sen|congressman|congresswoman|representative|rep|speaker|'
                              r'majority leader|minority leader|leader|whip|chairman|chairwoman)\s+([a-z]+)', pr):
            if tm.group(1) in SUR: return True
        return False
    pre = len(posts)
    posts = [u for u in posts if _slug_hits(u.rsplit('/', 1)[-1])]
    print('hewitt: %d member-candidate posts (of %d enumerated, archive+stream)' % (len(posts), pre), flush=True)
    tot = 0
    for u in posts:
        slug = u.rsplit('/', 1)[-1]
        key = 'hh:%s' % slug[:180]
        if key in done: continue
        try:
            page = get(u); time.sleep(PAUSE)
            title = (re.search(r'<title>([^<]+)</title>', page) or [None, ''])[1]
            probe = ' ' + re.sub(r'\s+', ' ', norm(slug.replace('-', ' ') + ' ' + title)) + ' '
            guests = {mem for (fn, ln), mem in FULL.items() if (' %s %s ' % (fn, ln)) in probe}
            # rank+surname titles ('majority leader thune on...', 'speaker johnson...') — run-4z4/4z5:
            # pass 1 required a FULL name in the title (17 members from 653 posts). The rank word
            # scopes the surname pool (user 2026-07-06: 'Speaker Johnson refers to only one person'):
            # senator->Senate pool, congressman/rep->House pool, speaker/leader/whip->119th floor-
            # leadership singletons, chair->global. Ambiguous-within-pool never binds ('senator
            # scott'), and the body-label conjunction below still gates every stored turn (a wrong
            # title-guess finds no matching initials/surname labels -> zero rows).
            for tm in re.finditer(r'\b(senator|sen|congressman|congresswoman|representative|rep|speaker|'
                                  r'majority leader|minority leader|leader|whip|chairman|chairwoman)\s+([a-z]+)', probe):
                rank, cand = tm.group(1), tm.group(2)
                pool = (SUR_SEN if rank in ('senator', 'sen') else
                        SUR_HOU if rank in ('congressman', 'congresswoman', 'representative', 'rep') else
                        LEAD_SUR if rank in ('speaker', 'majority leader', 'minority leader', 'leader', 'whip') else
                        SUR)
                cands = pool.get(cand, []) if hasattr(pool, 'get') else []
                if len(cands) == 1: guests.add(cands[0])
            if len(guests) != 1:
                con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', (key, 'ok', datetime.datetime.now().isoformat()))
                con.commit(); continue   # zero or ambiguous guest -> drop, never guess
            guest = next(iter(guests)); parts = norm(guest).split()
            accept = {(parts[0][0] + parts[-1][0]).upper(), parts[-1].upper(),
                      (parts[0] + ' ' + parts[-1]).upper()}
            text = strip_tags(page)
            pos = [(m.start(), m.group(1)) for m in LABEL.finditer(text)]
            rows = []
            for i2, (st, lab) in enumerate(pos):
                if lab.split(',')[0].strip() not in accept: continue
                end = pos[i2 + 1][0] if i2 + 1 < len(pos) else len(text)
                sp = text[st:end]; sp = scrub(re.sub(r'\s+', ' ', sp[sp.index(':') + 1:].strip()))
                if len(sp.split()) >= 8: rows.append((guest, sp))
            n = store(con, rows, dates.get(u, ''), 'hugh-hewitt', u)
            con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', (key, 'ok', datetime.datetime.now().isoformat()))
            con.commit(); tot += n
            if n: print('hh %s: %d turns (total %d)' % (slug[:55], n, tot), flush=True)
        except Exception as e:
            print('hh %s FAIL %s' % (slug[:50], str(e)[:80]), flush=True)
    con.close(); print('hewitt done: %d member turns' % tot)

# STONES EXAMINED AND CLOSED (2026-07-03, REVISED 07-05): YouTube captions (post-2024-10 Fox,
# podcasts) have NO speaker labels — multi-speaker attribution would require diarization;
# harvesting them would violate the drop-never-guess discipline, so they stay out until a
# diarization pass exists. C-SPAN transcripts are access-restricted. Fox's PUBLISHED archive
# (through ~2024-10) is now covered by run_fox above; Hewitt (current, R) by run_hewitt.
# Newsmax/OANN/Fox Business publish no transcripts (verified 07-05); MSNBC's transcript section
# exists but is JS-rendered — sitemap-enumeration candidate if the user wants the L-flank.

def _keep_awake():
    """User directive 2026-07-06 ('put in checks so it doesn't fall asleep'): the 01:10 machine
    sleep suspended NPR+Fox mid-crawl for 5h. Hold a SYSTEM wake lock for the life of the leg —
    the OS clears it automatically when the process exits, and the display may still sleep
    (ES_SYSTEM_REQUIRED only). Non-Windows / failure degrades to a printed warning."""
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        r = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        print('keep-awake: system wake lock held for this crawl' if r else 'keep-awake: call returned 0 (no lock)', flush=True)
    except Exception as e:
        print('keep-awake unavailable (%s) — machine may sleep mid-crawl' % str(e)[:60], flush=True)

if __name__ == '__main__':
    if any(l in sys.argv for l in ('cnn', 'mtp', 'cbs', 'abc', 'pbs', 'npr', 'fox', 'hewitt')):
        _keep_awake()
    if 'status' in sys.argv:
        con = db()
        for src, n, dm, w in con.execute("SELECT source, COUNT(*), COUNT(DISTINCT member), SUM(nwords) FROM speeches GROUP BY source"):
            print('%-10s %6d turns | %3d members | %.2fM words' % (src, n, dm, (w or 0) / 1e6))
        sys.exit(0)
    ap = {a.split('=')[0]: a for a in sys.argv}
    since = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--since'), '2025-01-01')
    until = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--until'), datetime.date.today().isoformat())
    # completion sentinel (2026-07-06, 'do whatever is best for the data collection'): the
    # collector_supervisor scheduled task distinguishes 'finished cleanly' from 'died' by this
    # flag — a leg only writes it if run_* returns without exception. Deep CNN backfill gets its
    # own sentinel (cnn-deep) so it doesn't collide with the incremental daily cnn leg.
    _leg = next((l for l in ('cnn', 'mtp', 'cbs', 'abc', 'pbs', 'npr', 'fox', 'hewitt') if l in sys.argv), None)
    if _leg == 'cnn' and until <= '2024-06-01' and '--verify' not in sys.argv: _leg = 'cnn-deep'
    def _sentinel():
        try:
            sd = os.path.join(B, 'collector_sentinels'); os.makedirs(sd, exist_ok=True)
            open(os.path.join(sd, _leg + '.done'), 'w').write(datetime.datetime.now().isoformat())
        except Exception: pass
    if 'cnn' in sys.argv: run_cnn(since, until, verify='--verify' in sys.argv); _sentinel()
    elif 'mtp' in sys.argv: run_mtp(); _sentinel()
    elif 'cbs' in sys.argv: run_cbs(); _sentinel()
    elif 'abc' in sys.argv: run_abc(); _sentinel()
    elif 'pbs' in sys.argv: run_pbs(since, until); _sentinel()
    elif 'npr' in sys.argv: run_npr(since, until); _sentinel()
    elif 'fox' in sys.argv: run_fox(); _sentinel()
    elif 'hewitt' in sys.argv: run_hewitt(); _sentinel()
    else: print('usage: fetch_interviews.py [cnn|mtp|cbs|abc|pbs|npr|fox|hewitt|status] [--since YYYY-MM-DD] [--until YYYY-MM-DD]')
