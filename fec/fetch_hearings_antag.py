# -*- coding: utf-8 -*-
"""All-committee committee-hearing ANTAGONISM/DEFIANCE collector (user directive 2026-07-10:
"go over hearings again, even out of our domain if they contain the members"). Measures the member
as AGGRESSOR/NORM-BREAKER — interruptions GIVEN, cross-party clashes, chair-defiance, procedural
combat — a candidate behavioral Agreeableness (antagonism) / ES (disinhibition) signal. This is the
GIVEN direction, distinct from the cutoff-RECEIVED direction the reactivity code excludes as
role/target-driven (Miller & Sutherland); given-interruption/norm-defiance is agentic and the user
correctly flagged it was never considered.

SCOPE: drops the finance-only title filter (fetch_congressional_record.FINRX) — ALL committees.
STORAGE: dedicated tables only (hearing_antag, hearing_meta). Deliberately does NOT write member
turns into speeches — dumping all-committee hearing text into the Big-Five text corpus would silently
alter the validated text measures; that is a separate, deliberate decision, not a side effect here.
Confounds to resolve in the BUILDER (not here): chair role inflates counts; majority/minority dynamics
drive interruptions; hearing contentiousness varies — meta columns (chair_party, n_named_turns) are
stored so the builder can residualize. Resume: cr_fetch_log key 'antag:<pid>'.
"""
import sys, os, re, io, time, json, csv, zipfile, sqlite3, datetime, urllib.request, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from paths import ROOT
B = ROOT
_KF = B + r'\fec\govinfo_key.txt'   # live tree; the key is gitignored so it is not in the worktree checkout
KEY = os.environ.get('GOVINFO_KEY') or (open(_KF).read().strip() if os.path.exists(_KF) else 'DEMO_KEY')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) research collector'}
PAUSE = 1.0

def _strip_api_key(url):   # keep the secret OUT of the request URL (logs/proxies) — mirrors CREC collector
    import urllib.parse as _up
    p = _up.urlsplit(url or '')
    q = [(k, v) for k, v in _up.parse_qsl(p.query, keep_blank_values=True) if k.lower() not in ('api_key', 'key', 'token')]
    return _up.urlunsplit((p.scheme, p.netloc, p.path, _up.urlencode(q), p.fragment))
def get(url, binary=False, tries=4, api_key=None):
    headers = dict(UA)
    if api_key: headers['X-Api-Key'] = api_key       # govinfo key in HEADER, never the URL
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(_strip_api_key(url), headers=headers), timeout=120) as r:
                d = r.read(); return d if binary else d.decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            if e.code in (404, 410): raise
            if i == tries - 1: raise
            time.sleep(4 * (i + 1))
        except Exception:
            if i == tries - 1: raise
            time.sleep(4 * (i + 1))

# ---- roster + party (inlined; avoids fetch_congressional_record import-time argparse) ----
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

TURN = re.compile(r'(?m)^ {0,6}(?:The )?(Mr|Mrs|Ms|Miss|Senator|Chairman|Chairwoman|Chair)\.?[ ]+'
                  r"([A-Z][A-Za-z'\-]+(?:[ \-][A-Za-z'\-]+){0,2}?)"
                  r'(?: of ([A-Z][a-z]+(?: [A-Z][a-z]+)?))?[.,] ')
NONSPK = {'SPEAKER', 'PRESIDENT', 'PRESIDING', 'CLERK', 'ACTING', 'VICE', 'CHAIR', 'CHAIRMAN', 'SECRETARY'}
FRICTION = re.compile(r'reclaim\w+ my time|regular order|will not yield|decline to yield|point of order|regain my time', re.I)
YIELDBACK = re.compile(r'yield back|i yield the balance', re.I)
GAVEL = re.compile(r'time (has )?expired|will suspend|is not recognized|not in order|gentlem[ae][ns].{0,25}(suspend|expired|not recognized)', re.I)
ENDDASH = re.compile(r'-{2,}\s*$')

def parse_sequence(txt):
    txt = re.sub(r'<[^>]+>', ' ', txt)
    wit = set()
    for w in re.findall(r'(?:STATEMENT|TESTIMONY) OF ([A-Z][A-Z .,\'\-]{3,60})', txt):
        toks = [t.strip('.,') for t in w.split(',')[0].split() if t.strip('.,').isalpha()]   # 3rd-pass S3 fix: split on comma FIRST so the surname (not a trailing title/org word like BANK) is captured, mirroring fetch_hearings_seq.py
        if toks: wit.add(toks[-1].upper())
    ms = list(TURN.finditer(txt)); seq = []
    for i, mt in enumerate(ms):
        pre, sur = mt.group(1), mt.group(2)
        role = 'chair' if re.match(r'Chair', pre, re.I) else 'spk'
        seg = txt[mt.end():ms[i + 1].start() if i + 1 < len(ms) else min(len(txt), mt.end() + 20000)]
        segc = re.sub(r'\s+', ' ', re.sub(r'\[\[Page [^\]]+\]\]', '', seg)).strip()
        dash = bool(ENDDASH.search(seg.strip()))
        if sur.upper().split()[0] in NONSPK and role != 'chair':
            seq.append((None, 'other', '?', segc, dash)); continue
        if sur.upper().split()[-1] in wit:
            seq.append((None, 'witness', '?', segc, dash)); continue
        who = resolve(sur)
        seq.append((who, role, party_of(who) if who else '?', segc, dash))
    return seq

def hearing_events(seq):
    ev = collections.defaultdict(lambda: collections.Counter())
    chair_turns = collections.Counter()
    for i, (who, role, pty, text, dash) in enumerate(seq):
        if who is None: continue
        if role == 'chair': chair_turns[who] += 1
        ev[who]['turns'] += 1
        if i > 0:
            pw, prole, ppty, ptext, pdash = seq[i - 1]
            if pdash and pw is not None and pw != who:
                ev[who]['intr'] += 1
                if ppty in ('D', 'R') and pty in ('D', 'R') and ppty != pty: ev[who]['xparty'] += 1
            if prole == 'chair' and GAVEL.search(ptext): ev[who]['defiance'] += 1
        if FRICTION.search(text): ev[who]['friction'] += 1
        if YIELDBACK.search(text): ev[who]['yieldback'] += 1
    chair = chair_turns.most_common(1)[0][0] if chair_turns else None
    return ev, chair

def db():
    con = sqlite3.connect(B + r'\social_media.db', timeout=60)
    con.execute("CREATE TABLE IF NOT EXISTS hearing_antag(package TEXT, date TEXT, member TEXT, "
                "turns INT, intr INT, xparty INT, friction INT, defiance INT, yieldback INT)")
    con.execute("CREATE TABLE IF NOT EXISTS hearing_meta(package TEXT PRIMARY KEY, date TEXT, title TEXT, "
                "chair_member TEXT, chair_party TEXT, n_named_turns INT, n_members INT)")
    return con

def list_packages(since):
    url = 'https://api.govinfo.gov/collections/CHRG/%sT00:00:00Z?offsetMark=*&pageSize=1000' % since
    out = []
    while url:
        j = json.loads(get(url, api_key=KEY)); out += j.get('packages', [])
        url = _strip_api_key(j.get('nextPage')) if j.get('nextPage') else None
        time.sleep(0.3)
    return out

def run(since, until):
    con = db(); cur = con.cursor()
    done = {r[0] for r in cur.execute("SELECT key FROM cr_fetch_log WHERE status IN ('ok','nopage')")}
    pkgs = [p for p in list_packages(since) if since <= p['dateIssued'] <= until]
    todo = [p for p in sorted(pkgs, key=lambda p: p['dateIssued']) if 'antag:' + p['packageId'] not in done]
    print('HEARINGS(antag): %d all-committee hearings %s..%s, %d to ingest' % (len(pkgs), since, until, len(todo)), flush=True)
    tot_ev = 0
    for k, p in enumerate(todo):
        pid, date = p['packageId'], p['dateIssued']
        try:
            z = zipfile.ZipFile(io.BytesIO(get('https://www.govinfo.gov/content/pkg/%s.zip' % pid, True)))
            time.sleep(PAUSE)
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                cur.execute("INSERT OR REPLACE INTO cr_fetch_log VALUES(?,?,?)", ('antag:' + pid, 'nopage', datetime.datetime.now().isoformat())); con.commit()
            continue
        except Exception as e:
            cur.execute("INSERT OR REPLACE INTO cr_fetch_log VALUES(?,?,?)", ('antag:' + pid, 'err:%s' % str(e)[:60], datetime.datetime.now().isoformat())); con.commit()
            continue
        agg = collections.defaultdict(lambda: collections.Counter()); chair = None; named = 0
        for n in z.namelist():
            if not n.endswith('.htm'): continue
            seq = parse_sequence(z.read(n).decode('utf-8', 'replace'))
            ev, ch = hearing_events(seq)
            if ch and not chair: chair = ch
            for m, c in ev.items():
                for kk, vv in c.items(): agg[m][kk] += vv
            named += sum(1 for s in seq if s[0])
        for m, c in agg.items():
            cur.execute("INSERT INTO hearing_antag VALUES(?,?,?,?,?,?,?,?,?)",
                        (pid, date, m, c['turns'], c['intr'], c['xparty'], c['friction'], c['defiance'], c['yieldback']))
            tot_ev += c['intr'] + c['friction'] + c['defiance']
        cur.execute("INSERT OR REPLACE INTO hearing_meta VALUES(?,?,?,?,?,?,?)",
                    (pid, date, (p.get('title') or '')[:200], chair, party_of(chair) if chair else '?', named, len(agg)))
        cur.execute("INSERT OR REPLACE INTO cr_fetch_log VALUES(?,?,?)", ('antag:' + pid, 'ok', datetime.datetime.now().isoformat()))
        con.commit()
        if k % 50 == 0 or len(agg) > 0:
            print('  [%d/%d] %s %s: %d members, %d antag-events (running %d)' % (k + 1, len(todo), date, pid[:20], len(agg), sum(c['intr'] + c['friction'] + c['defiance'] for c in agg.values()), tot_ev), flush=True)
    con.close(); print('HEARINGS(antag) done: %d antagonism events across hearings' % tot_ev)

if __name__ == '__main__':
    since = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--since'), '2023-01-01')
    until = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--until'), datetime.date.today().isoformat())
    run(since, until)
