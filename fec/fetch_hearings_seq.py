# -*- coding: utf-8 -*-
"""All-committee hearing DOWNLOAD + TRANSCRIPT-SEQUENCE CACHE (2026-07-10 refinement, user: isolate
member-vs-member antagonism + count member-vs-WITNESS only when HOSTILE — aggressive language, blunt
correction, interrogation — NOT routine procedural time-management, which inflated senior appropriators
like Collins in the v1 prelim).

This is the SLOW part (download), done ONCE and CACHED so the hostility lexicon can be tuned offline
in seconds. Stores a COMPACT ordered turn-sequence per hearing to a SEPARATE hearings_seq.db (keeps the
user's social_media.db unbloated); hearing_meta (chair/contentiousness for confound controls) stays in
the main DB. The BUILDER (hearing_antagonism_build.py) computes refined events from the cache:
  member-vs-member interrupt  = member cuts off a COLLEAGUE (kind is another member) -> clean antagonism
  member-vs-witness HOSTILE   = member turn adjacent to a WITNESS carrying hostile markers (lexicon) OR
                                aggressively cutting off a witness -> counts; procedural time-mgmt does NOT
Compact turn = [kind, party, dash, text]: kind = member-name | 'W'(witness) | 'C'(chair) | 'O'(other);
text stored ONLY for members (what the hostility lexicon reads), capped; party for cross-party detection.
Resume: hearings_seq.db seq_log 'seq:<pid>'. Era: 2019-2024 full HTML (2025+ PDF deferred)."""
import sys, os, re, io, time, json, csv, zipfile, sqlite3, datetime, urllib.request, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
SEQDB = B + r'\hearings_seq.db'
_KF = B + r'\fec\govinfo_key.txt'
KEY = os.environ.get('GOVINFO_KEY') or (open(_KF).read().strip() if os.path.exists(_KF) else 'DEMO_KEY')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) research collector'}
TEXTCAP = 1500

def get(url, binary=False, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                d = r.read(); return d if binary else d.decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            if e.code in (404, 410): raise
            if i == tries - 1: raise
            time.sleep(4 * (i + 1))
        except Exception:
            if i == tries - 1: raise
            time.sleep(4 * (i + 1))

C = {m['member']: m for m in json.load(open(B + r'\congestion.json'))}
SFIX = {'jr', 'sr', 'ii', 'iii', 'iv'}
def surkeys(m):
    ts = [t for t in m.replace('.', '').split() if t.lower().rstrip(',') not in SFIX]
    ks = {ts[-1].upper()}
    if len(ts) >= 3: ks.add((ts[-2] + ' ' + ts[-1]).upper())
    if len(ts) >= 4: ks.add((ts[-3] + ' ' + ts[-2] + ' ' + ts[-1]).upper())
    return {re.sub(r"[^A-Z\- ']", '', k) for k in ks}
ROSTER = collections.defaultdict(list)
for m in C:
    ch = (C[m].get('chamber') or '').lower()
    for k in surkeys(m): ROSTER[(k, ch)].append(m)
def resolve(sur, chamber=None):
    sur = re.sub(r"[^A-Z\- ']", '', sur.upper()).strip()
    for ch in ([chamber] if chamber else ['senate', 'house']):
        cand = ROSTER.get((sur, ch), [])
        if len(cand) == 1: return cand[0]
    return None
PARTY = {}
for r in csv.DictReader(open(B + r'\fec\legislators.csv', encoding='utf-8')):
    if r.get('bioguide_id'): PARTY[r['bioguide_id']] = (r.get('party') or '')[:1].upper()
BIO = {m: C[m].get('bioguide') for m in C}
def party_of(m): return PARTY.get(BIO.get(m), '?')

# Broadened speaker capture: members AND witnesses (govt/military/state/expert/judicial honorifics) so
# a member grilling 'Secretary Driscoll' or 'General George' is no longer INVISIBLE. Witness turns get a
# TYPE code (user 2026-07-10: control for business execs vs state/govt officials; substance shapes the
# partisan/antagonism read). Type from honorific + the 'STATEMENT OF ..., <title>' header.
MEMBER_HON = r'Mr|Mrs|Ms|Miss|Senator|Representative|Congressman|Congresswoman|Chairman|Chairwoman|Chair'
WIT_HON = (r'Secretary|Under Secretary|Deputy Secretary|Administrator|Deputy Administrator|Acting Administrator|'
           r'Director|Deputy Director|Acting Director|Commissioner|Ambassador|Comptroller|Inspector General|'
           r'General|Lieutenant General|Major General|Brigadier General|Admiral|Vice Admiral|Rear Admiral|'
           r'Colonel|Lieutenant Colonel|Lieutenant|Captain|Major|Commander|Sergeant|'
           r'Governor|Lieutenant Governor|Mayor|Dr|Professor|Justice|Judge|Chief|Sheriff|Honorable')
SPEAKER = re.compile(r'(?m)^ {0,6}(?:The )?(%s|%s)\.?[ ]+'
                     r"([A-Z][A-Za-z'\-]+(?:[ \-][A-Za-z'\-]+){0,2}?)"
                     r'(?: of ([A-Z][a-z]+(?: [A-Z][a-z]+)?))?[.,] ' % (MEMBER_HON, WIT_HON))
MEMBER_RE = re.compile(r'^(Mr|Mrs|Ms|Miss|Senator|Representative|Congressman|Congresswoman|Chairman|Chairwoman|Chair)$')
NONSPK = {'SPEAKER', 'PRESIDING', 'CLERK', 'VICE'}
ENDDASH = re.compile(r'-{2,}\s*$')

def hon_type(pre):
    """Witness TYPE from honorific alone (strong for non-Mr/Ms)."""
    p = pre.lower()
    if re.search(r'general|admiral|colonel|lieutenant|captain|major|commander|sergeant', p): return 'M'   # military
    if re.search(r'governor|mayor|sheriff', p): return 'S'                                                # state/local
    if re.search(r'dr|professor', p): return 'E'                                                          # expert/academic
    if re.search(r'justice|judge', p): return 'J'                                                         # judicial
    if re.search(r'secretary|administrator|director|commissioner|ambassador|comptroller|inspector|chief|honorable', p): return 'G'  # federal govt
    return '?'   # Mr/Ms witness -> resolve via STATEMENT OF title

def title_type(t):
    """Witness TYPE from a STATEMENT OF title/org string (for Mr/Ms witnesses)."""
    t = t.lower()
    if re.search(r'chief executive|c\.?e\.?o|chief financial|chief operating|chief technology|founder|'
                 r'president and ceo|chairman and ceo|executive vice president|\b(inc|corp|corporation|company|'
                 r'llc|holdings|bank|industries|motors|technologies|pharmaceutic|capital|partners|group)\b', t): return 'B'
    if re.search(r'governor|mayor|state (senator|representative|treasurer|attorney)|county|sheriff|city of', t): return 'S'
    if re.search(r'general|admiral|colonel|army|navy|air force|marine|joint chiefs', t): return 'M'
    if re.search(r'professor|ph\.?d|fellow|scholar|economist|university\b', t): return 'E'
    if (re.search(r'president|executive director|director|chair', t) and
            re.search(r'associat|union|coalition|federat|alliance|society|council|foundation|institut|'
                      r'center for|committee for|advocat|project|network|league|conference', t)): return 'A'
    if re.search(r'secretary|administrator|commissioner|inspector general|comptroller|department of|'
                 r'\bu\.?s\.?\b|federal|bureau|agency|office of', t): return 'G'
    return '?'

def parse_seq(txt):
    """Compact ordered turns. member: [name, party, dash, text, 'M'/'C']; witness: ['W', typecode, dash, '']."""
    txt = re.sub(r'<[^>]+>', ' ', txt)
    wit_type = {}   # witness surname -> type, from any 'Name, <title/org>' witness-intro span (format-robust)
    for hd in re.findall(r'(?:STATEMENT|TESTIMONY|PREPARED STATEMENT) OF ([A-Z][A-Za-z .,\'\-]{3,120})', txt):
        toks = [t.strip('.,') for t in hd.split(',')[0].split() if t.strip('.,').isalpha()]
        if toks:
            sur = toks[-1].upper(); t = title_type(hd[len(hd.split(',')[0]):])
            if t != '?': wit_type[sur] = t
    # document-wide 'Mr./Ms./Dr. First Last, <title>' scan (catches witness lists + in-line intros; the
    # 'STATEMENT OF' anchor is absent in many hearings, so this is the primary business/advocate signal)
    for nm, title in re.findall(r'\b(?:Mr|Ms|Mrs|Dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-zA-Z\'\-\.]+){1,2}),\s+([^,\n]{4,90})', txt):
        sur = nm.split()[-1].upper(); t = title_type(title)
        if t != '?' and sur not in wit_type: wit_type[sur] = t
    ms = list(SPEAKER.finditer(txt)); out = []; chair_ct = collections.Counter()
    for i, mt in enumerate(ms):
        pre, sur = mt.group(1), mt.group(2)
        is_member_hon = bool(MEMBER_RE.match(pre))
        is_chair = bool(re.match(r'Chair', pre, re.I))
        seg = txt[mt.end():ms[i + 1].start() if i + 1 < len(ms) else min(len(txt), mt.end() + 20000)]
        segc = re.sub(r'\s+', ' ', re.sub(r'\[\[Page [^\]]+\]\]', '', seg)).strip()
        dash = 1 if ENDDASH.search(seg.strip()) else 0
        surU = sur.upper(); surlast = surU.split()[-1]
        who = resolve(sur) if is_member_hon else None
        if who:
            if is_chair: chair_ct[who] += 1
            out.append([who, party_of(who), dash, segc[:TEXTCAP], 'C' if is_chair else 'M'])
        elif is_chair or surU.split()[0] in NONSPK:
            out.append(['C' if is_chair else 'O', '?', dash, ''])
        else:
            # witness: type from honorific, else STATEMENT OF title, else '?'
            t = hon_type(pre)
            if t == '?': t = wit_type.get(surlast, '?')
            out.append(['W', t, dash, ''])
    chair = chair_ct.most_common(1)[0][0] if chair_ct else None
    return out, chair

REPAIR_HON = (r'Mr|Mrs|Ms|Miss|Senator|Representative|Chairman|Chairwoman|Chair|Admiral|General|Secretary|'
              r'Colonel|Governor|Dr|Professor|Ambassador|Lieutenant|Captain|Major|Commander|Commissioner|'
              r'Administrator|Director|Justice|Judge|Honorable|Hon')
def repair_pdf(t):
    """119th (2025+) hearings are PDF-only: pypdf DEFAULT-mode splits the small-caps surname's drop-cap
    initial off its remainder ('Mr. C\\nROW.' = Mr. CROW; 'Admiral H OLSEY.' = Admiral HOLSEY). Rejoin
    those, and de-hyphenate words broken across line-wraps, so the HTML-era parse_seq works unchanged."""
    t = re.sub(r'\b(%s)\.[ ]+([A-Z])[ \t]*\n?[ \t]*([A-Z][A-Z\'\-]+)' % REPAIR_HON,
               lambda m: '%s. %s%s' % (m.group(1), m.group(2), m.group(3).title()), t)
    t = re.sub(r'([a-z])-\n([a-z])', r'\1\2', t)      # de-hyphenate line-wrapped words
    return t

def fetch_one_pdf(p):
    """2025+ path: api zip endpoint -> pdf/*.pdf -> pypdf -> repair -> same parse_seq."""
    pid, date = p['packageId'], p['dateIssued']
    try:
        raw = get('https://api.govinfo.gov/packages/%s/zip?api_key=%s' % (pid, KEY), True)
    except urllib.error.HTTPError as e:
        return {'pid': pid, 'status': 'nopage' if e.code in (404, 410) else 'err:%d' % e.code}
    except Exception as e:
        return {'pid': pid, 'status': 'err:%s' % str(e)[:40]}
    try:
        import pypdf
        z = zipfile.ZipFile(io.BytesIO(raw))
        pdfs = [n for n in z.namelist() if n.lower().endswith('.pdf')]
        if not pdfs:
            return {'pid': pid, 'status': 'nopdf'}
        r = pypdf.PdfReader(io.BytesIO(z.read(pdfs[0])))
        txt = '\n'.join(pg.extract_text() for pg in r.pages)
        seq, chair = parse_seq(repair_pdf(txt))
        named = sum(1 for t in seq if t[0] not in ('W', 'C', 'O'))
        if named < 3:
            return {'pid': pid, 'status': 'err:pdf:%d-named' % named}   # bad extraction -> flag, don't cache junk
        return {'pid': pid, 'date': date, 'title': (p.get('title') or '')[:200], 'status': 'ok',
                'seq': seq, 'chair': chair, 'named': named}
    except Exception as e:
        return {'pid': pid, 'status': 'err:pdf:%s' % str(e)[:40]}

def fetch_one(p):
    pid, date = p['packageId'], p['dateIssued']
    try:
        raw = get('https://www.govinfo.gov/content/pkg/%s.zip' % pid, True)
    except urllib.error.HTTPError as e:
        return {'pid': pid, 'status': 'nopage' if e.code in (404, 410) else 'err:%d' % e.code}
    except Exception as e:
        return {'pid': pid, 'status': 'err:%s' % str(e)[:40]}
    try:
        z = zipfile.ZipFile(io.BytesIO(raw)); seq = []; chair = None; named = 0
        for n in z.namelist():
            if not n.endswith('.htm'): continue
            s, ch = parse_seq(z.read(n).decode('utf-8', 'replace'))
            if ch and not chair: chair = ch
            named += sum(1 for t in s if t[0] not in ('W', 'C', 'O'))
            seq += s
        return {'pid': pid, 'date': date, 'title': (p.get('title') or '')[:200], 'status': 'ok',
                'seq': seq, 'chair': chair, 'named': named}
    except Exception as e:
        return {'pid': pid, 'status': 'err:parse:%s' % str(e)[:40]}

def seqdb():
    con = sqlite3.connect(SEQDB, timeout=120)
    con.execute("PRAGMA journal_mode=WAL"); con.execute("PRAGMA busy_timeout=120000")
    con.execute("CREATE TABLE IF NOT EXISTS hearing_seq(package TEXT PRIMARY KEY, date TEXT, seq TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS seq_log(package TEXT PRIMARY KEY, status TEXT)")
    return con

def maindb():
    con = sqlite3.connect(B + r'\social_media.db', timeout=120)
    con.execute("PRAGMA busy_timeout=120000")
    con.execute("CREATE TABLE IF NOT EXISTS hearing_meta(package TEXT PRIMARY KEY, date TEXT, title TEXT, "
                "chair_member TEXT, chair_party TEXT, n_named_turns INT, n_members INT)")
    return con

def list_packages(since):
    url = 'https://api.govinfo.gov/collections/CHRG/%sT00:00:00Z?offsetMark=*&pageSize=1000&api_key=%s' % (since, KEY)
    out = []
    while url:
        j = json.loads(get(url)); out += j.get('packages', [])
        url = j.get('nextPage'); url = url + '&api_key=' + KEY if url and 'api_key' not in url else url
        time.sleep(0.3)
    return out

def run(since, until, workers=6):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    sc = seqdb(); mc = maindb()
    done = {r[0] for r in sc.execute("SELECT package FROM seq_log WHERE status IN ('ok','nopage')")}
    pkgs = [p for p in list_packages(since) if since <= p['dateIssued'] <= until]
    # EXPEDITE-THE-VERDICT (2026-07-10): the substance-shaped antagonism signal (personal hostility)
    # lives in CONTENTIOUS hearings; genial approps/noms contribute ~0. Front-load likely-contentious
    # titles so the signal-bearing data lands first (full collection still completes -- reorder, not skip).
    CONTENTIOUS = re.compile(r'oversight|judiciar|weaponi|border|afghan|censor|\bfbi\b|department of justice|'
                             r'big tech|social media|radical|accountab|failure|crisis|scandal|hunter|impeach|'
                             r'testimony of|examining|threat|extremis|antisemit|fentanyl|cartel|hamas|'
                             r'\bccp\b|homeland|whistleblow|misconduct|abuse|corrupt', re.I)
    def prio(p): return (0 if CONTENTIOUS.search(p.get('title') or '') else 1, p['dateIssued'])
    todo = [p for p in sorted(pkgs, key=prio) if p['packageId'] not in done]
    ncont = sum(1 for p in todo if CONTENTIOUS.search(p.get('title') or ''))
    print('  (%d likely-contentious hearings front-loaded)' % ncont, flush=True)
    print('SEQ-CACHE: %d hearings %s..%s, %d to cache (%d workers)' % (len(pkgs), since, until, len(todo), workers), flush=True)
    k = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(fetch_one_pdf if p['dateIssued'] >= '2025-01-01' else fetch_one, p) for p in todo]
        for fut in as_completed(futs):
            r = fut.result(); k += 1; pid = r['pid']
            if r['status'] != 'ok':
                sc.execute("INSERT OR REPLACE INTO seq_log VALUES(?,?)", (pid, r['status'])); sc.commit(); continue
            sc.execute("INSERT OR REPLACE INTO hearing_seq VALUES(?,?,?)", (pid, r['date'], json.dumps(r['seq'], separators=(',', ':'))))
            sc.execute("INSERT OR REPLACE INTO seq_log VALUES(?,?)", (pid, 'ok')); sc.commit()
            mc.execute("INSERT OR REPLACE INTO hearing_meta VALUES(?,?,?,?,?,?,?)",
                       (pid, r['date'], r['title'], r['chair'], party_of(r['chair']) if r['chair'] else '?', r['named'], 0)); mc.commit()
            if k % 100 == 0:
                print('  [%d/%d] %s cached' % (k, len(todo), r['date']), flush=True)
    sc.close(); mc.close(); print('SEQ-CACHE done: %d processed' % k)

if __name__ == '__main__':
    since = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--since'), '2019-01-01')
    until = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--until'), '2024-12-31')
    run(since, until)
