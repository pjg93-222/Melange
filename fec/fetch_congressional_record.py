# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT,DRAFT as MB_DRAFT  # centralized root (arch review 2026-07-02)
"""CONGRESSIONAL RECORD + HEARING TRANSCRIPT COLLECTOR (GovInfo) — the trait-corpus upgrade the
Ramey pipeline actually calls for: floor speeches (CREC) and committee hearing transcripts (CHRG),
attributed to members by the Record's speaker headers ("Mr. DURBIN.", "Ms. WARREN of Massachusetts.",
"Chairman HILL.").  Tweets stay in the corpus; this adds the papers' native medium.

Design:
  * Discovery via api.govinfo.gov collections listing (GOVINFO_KEY env; DEMO_KEY works but is
    rate-limited to ~30 req/hr — a free key from https://api.data.gov/signup lifts it to 1,000/hr.
    Discovery needs only a handful of listing calls; CONTENT downloads are keyless).
  * Each package downloads as ONE keyless zip (www.govinfo.gov/content/pkg/<id>.zip); pages are
    parsed locally and the zip is deleted — nothing bulky is kept.
  * CREC: only spoken floor pages (PgH/PgS); Extensions of Remarks (PgE, inserted written matter)
    and the Daily Digest (PgD) are excluded to stay faithful to "floor speech."
  * CHRG: hearing packages filtered to finance-relevant titles (banking/financial services/credit
    union/monetary/housing/securities) — member Q&A turns attribute the same way; witnesses don't
    match the roster and fall away naturally.
  * Attribution: surname (+ optional "of State") -> roster. Ambiguous surnames within a chamber
    require the state tag; unresolvable turns are DROPPED, never guessed.
  * Storage: `speeches` table in social_media.db (WAL), one row per member-turn; `fetch_log` rows
    keyed crec:<pkg>/chrg:<pkg> make the job resumable (rerun skips ingested packages).
Usage:
  python fetch_congressional_record.py crec --since 2025-07-01 [--until 2026-07-02]
  python fetch_congressional_record.py chrg --since 2025-01-01
  python fetch_congressional_record.py status"""
import sys,os,re,json,io,csv,zipfile,sqlite3,datetime,time,argparse,collections
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
import urllib.request
B=MB_ROOT
KEY=os.environ.get('GOVINFO_KEY') or (open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'govinfo_key.txt')).read().strip()
     if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),'govinfo_key.txt')) else 'DEMO_KEY')
DB=B+r'\social_media.db'
UA={'User-Agent':'Mozilla/5.0 (research collector)'}
def db():
    c=sqlite3.connect(DB,timeout=60); c.execute('PRAGMA journal_mode=WAL')
    c.execute('''CREATE TABLE IF NOT EXISTS speeches(member TEXT,date TEXT,source TEXT,chamber TEXT,
                 package TEXT,nwords INTEGER,text TEXT)''')
    c.execute('CREATE INDEX IF NOT EXISTS ix_sp_m ON speeches(member)')
    c.execute('''CREATE TABLE IF NOT EXISTS cr_fetch_log(key TEXT PRIMARY KEY,status TEXT,ts TEXT)''')
    return c
def get(url,binary=False,tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=120) as r:
                d=r.read()
                return d if binary else d.decode('utf-8','replace')
        except Exception as e:
            if i==tries-1: raise
            time.sleep(3*(i+1))
# ---------------- roster: SURNAME(+state) -> canonical member ----------------
C={m['member']:m for m in json.load(open(B+r'\congestion.json'))}
state={}
try:
    for r in csv.DictReader(open(MB_DRAFT+r'\cu_press_stance_tone.csv',encoding='utf-8')):
        if r['member'] in C and r.get('state'): state[r['member']]=r['state'].strip()
except FileNotFoundError: pass
SFIX={'jr','sr','ii','iii','iv'}
def surkeys(m):
    ts=[t for t in m.replace('.','').split() if t.lower().rstrip(',') not in SFIX]
    ks={ts[-1].upper()}
    if len(ts)>=3: ks.add((ts[-2]+' '+ts[-1]).upper())          # VAN ORDEN, DE LA CRUZ...
    if len(ts)>=4: ks.add((ts[-3]+' '+ts[-2]+' '+ts[-1]).upper())
    return {re.sub(r"[^A-Z\- ']",'',k) for k in ks}
ROSTER=collections.defaultdict(list)   # (surname_key, chamber) -> [member]
for m in C:
    ch=(C[m].get('chamber') or '').lower()
    for k in surkeys(m): ROSTER[(k,ch)].append(m)
# CREC says "of California"; the roster carries two-letter codes -> full-name map for disambiguation
ST2AB={'alabama':'AL','alaska':'AK','arizona':'AZ','arkansas':'AR','california':'CA','colorado':'CO',
'connecticut':'CT','delaware':'DE','florida':'FL','georgia':'GA','hawaii':'HI','idaho':'ID','illinois':'IL',
'indiana':'IN','iowa':'IA','kansas':'KS','kentucky':'KY','louisiana':'LA','maine':'ME','maryland':'MD',
'massachusetts':'MA','michigan':'MI','minnesota':'MN','mississippi':'MS','missouri':'MO','montana':'MT',
'nebraska':'NE','nevada':'NV','new hampshire':'NH','new jersey':'NJ','new mexico':'NM','new york':'NY',
'north carolina':'NC','north dakota':'ND','ohio':'OH','oklahoma':'OK','oregon':'OR','pennsylvania':'PA',
'rhode island':'RI','south carolina':'SC','south dakota':'SD','tennessee':'TN','texas':'TX','utah':'UT',
'vermont':'VT','virginia':'VA','washington':'WA','west virginia':'WV','wisconsin':'WI','wyoming':'WY',
'puerto rico':'PR','guam':'GU','american samoa':'AS','virgin islands':'VI','district of columbia':'DC',
'northern mariana islands':'MP'}
def resolve(sur,st,chamber):
    sur=re.sub(r"[^A-Z\- ']",'',sur.upper()).strip()
    ab=ST2AB.get((st or '').lower(),st)
    for ch in ([chamber] if chamber else ['senate','house']):
        cand=ROSTER.get((sur,ch),[])
        if not cand: continue
        if len(cand)==1 and not st: return cand[0]
        if ab:
            hit=[m for m in cand if state.get(m,'').upper()==str(ab).upper()]
            if len(hit)==1: return hit[0]
        if len(cand)==1: return cand[0]
    return None
# ---------------- speaker-turn parser ----------------
TURN=re.compile(r'(?m)^ {0,6}(?:The )?(Mr|Mrs|Ms|Miss|Senator|Chairman|Chairwoman|Chair)\.?[ ]+'
                r"([A-Z][A-Za-z'\-]+(?:[ \-][A-Za-z'\-]+){0,2}?)"
                r'(?: of ([A-Z][a-z]+(?: [A-Z][a-z]+)?))?[.,] ')
NONSPK={'SPEAKER','PRESIDENT','PRESIDING','CLERK','ACTING','VICE','CHAIR','CHAIRMAN','SECRETARY'}
def upperish(s):
    letters=[c for c in s if c.isalpha()]
    return letters and sum(1 for c in letters if c.isupper())/len(letters)>=0.6
def parse_pages(texts,chamber_of,date,source,pkg,cur):
    rows=0; agg=collections.Counter()
    for fname,txt in texts:
        ch=chamber_of(fname)
        txt=re.sub(r'<[^>]+>',' ',txt)
        # CHRG-only: hearing witnesses can share a member's surname (Gov. Michael Barr before Rep. Andy
        # Barr) — harvest witness surnames from the STATEMENT OF/TESTIMONY OF headers and EXCLUDE those
        # surnames for this hearing entirely (honest drop beats mis-attribution).
        wit=set()
        if source=='CHRG':
            for w in re.findall(r'(?:STATEMENT|TESTIMONY) OF ([A-Z][A-Z .,\'\-]{3,60})',txt):
                toks=[t.strip('.,') for t in w.split() if t.strip('.,').isalpha()]
                if toks: wit.add(toks[-1].upper())
        ms=list(TURN.finditer(txt))
        for i,mt in enumerate(ms):
            sur=mt.group(2)
            # CREC prints speakers in ALL CAPS; hearing prints use mixed case -> caps filter is CREC-only
            if source!='CHRG' and not upperish(sur): continue
            if sur.upper().split()[0] in NONSPK: continue
            if source=='CHRG' and sur.upper().split()[-1] in wit: continue
            who=resolve(sur,mt.group(3),ch)
            if not who: continue
            seg=txt[mt.end():ms[i+1].start() if i+1<len(ms) else min(len(txt),mt.end()+20000)]
            # presiding-officer/clerk interjections aren't the member's words — cut the segment there
            seg=re.split(r'The (?:PRESIDING OFFICER|SPEAKER|ACTING PRESIDENT|VICE PRESIDENT|CLERK|CHAIR)\b',seg)[0]
            seg=re.sub(r'\s+',' ',seg).strip()
            seg=re.sub(r'\[\[Page [^\]]+\]\]','',seg); seg=seg.replace('____________________',' ')
            if len(seg)<150: continue                     # procedural one-liners
            cur.execute('INSERT INTO speeches VALUES(?,?,?,?,?,?,?)',
                        (who,date,source,ch or '',pkg,len(seg.split()),seg))
            rows+=1; agg[who]+=len(seg.split())
    return rows,agg
# ---------------- CREC ----------------
def list_packages(coll,since):
    # offsetMark cursor pagination — plain offset paging 500s on large collections (CHRG)
    url='https://api.govinfo.gov/collections/%s/%sT00:00:00Z?offsetMark=*&pageSize=1000&api_key=%s'%(coll,since,KEY)
    out=[]
    while url:
        j=json.loads(get(url)); out+=j.get('packages',[])
        url=j.get('nextPage'); url=url+'&api_key='+KEY if url and 'api_key' not in url else url
        time.sleep(0.3)
    return out
def run_crec(since,until):
    con=db(); cur=con.cursor()
    # CREC package ids are DATE-BASED (CREC-YYYY-MM-DD), so discovery needs NO API call at all: generate
    # every date in [since, until] and try the keyless content zip; non-session days 404 and are marked.
    # (The API collections listing filters by lastModified, not dateIssued — it fed us 1995 Records once,
    # and DEMO_KEY 429s under any real backfill. Keyless is both safer and unthrottled.)
    d0=datetime.date.fromisoformat(since); d1=datetime.date.fromisoformat(until)
    dates=[(d0+datetime.timedelta(days=i)).isoformat() for i in range((d1-d0).days+1)]
    done={r[0] for r in cur.execute("SELECT key FROM cr_fetch_log WHERE status IN ('ok','nosession')")}
    # STORED-PACKAGE GUARD (integrity fix 2026-07-06: the 4-year backfill re-inserted 922 exact-dup
    # rows because a date whose rows were committed but whose cr_fetch_log 'ok' mark was lost — a kill
    # in the commit->mark window, or an overlap with the original ingest — got re-processed. A CREC
    # package is atomic per date, so if ANY row for it is already stored, don't re-insert; just mark done).
    have_pkg={p for (p,) in cur.execute("SELECT DISTINCT package FROM speeches WHERE source='CREC'")}
    todo=[d for d in dates if 'crec:CREC-'+d not in done]
    print('CREC: %d candidate dates %s..%s, %d to try'%(len(dates),since,until,len(todo)))
    for date in todo:
        pid='CREC-'+date
        if pid in have_pkg:   # already stored -> mark done, never duplicate
            cur.execute("INSERT OR REPLACE INTO cr_fetch_log VALUES(?,?,?)",('crec:'+pid,'ok',datetime.datetime.now().isoformat()))
            con.commit(); continue
        try:
            try:
                z=zipfile.ZipFile(io.BytesIO(get('https://www.govinfo.gov/content/pkg/%s.zip'%pid,binary=True,tries=1)))
            except Exception as e:
                if '404' in str(e):
                    cur.execute("INSERT OR REPLACE INTO cr_fetch_log VALUES(?,?,?)",('crec:'+pid,'nosession',datetime.datetime.now().isoformat()))
                    con.commit(); continue
                raise
            texts=[]
            for n in z.namelist():
                b=os.path.basename(n)
                if b.endswith('.htm') and ('-PgH' in b or '-PgS' in b):
                    texts.append((b,z.read(n).decode('utf-8','replace')))
            cham=lambda f:'house' if '-PgH' in f else 'senate'
            rows,agg=parse_pages(texts,cham,date,'CREC',pid,cur)
            cur.execute("INSERT OR REPLACE INTO cr_fetch_log VALUES(?,?,?)",('crec:'+pid,'ok',datetime.datetime.now().isoformat()))
            con.commit()
            print('  %s: %3d pages -> %4d member turns (%d members)'%(pid,len(texts),rows,len(agg)))
        except Exception as e:
            cur.execute("INSERT OR REPLACE INTO cr_fetch_log VALUES(?,?,?)",('crec:'+pid,'err:%s'%str(e)[:80],datetime.datetime.now().isoformat()))
            con.commit(); print('  !!',pid,str(e)[:100])
# ---------------- CHRG (hearings) ----------------
FINRX=re.compile(r'banking|financial (service|institution|stability)|credit union|monetary|housing|securities|consumer (financial|credit)|capital market|fintech|digital asset|insurance fund',re.I)
def run_chrg(since,until):
    con=db(); cur=con.cursor()
    pkgs=[p for p in list_packages('CHRG',since) if since<=p['dateIssued']<=until and FINRX.search(p.get('title') or '')]
    done={r[0] for r in cur.execute("SELECT key FROM cr_fetch_log WHERE status='ok'")}
    have_pkg={p for (p,) in cur.execute("SELECT DISTINCT package FROM speeches WHERE source='CHRG'")}   # stored-package guard (2026-07-06)
    todo=[p for p in sorted(pkgs,key=lambda p:p['dateIssued']) if 'chrg:'+p['packageId'] not in done]
    print('CHRG: %d finance-relevant hearings since %s, %d to ingest'%(len(pkgs),since,len(todo)))
    for p in todo:
        pid=p['packageId']; date=p['dateIssued']
        if pid in have_pkg:   # already stored -> mark done, never duplicate
            cur.execute("INSERT OR REPLACE INTO cr_fetch_log VALUES(?,?,?)",('chrg:'+pid,'ok',datetime.datetime.now().isoformat()))
            con.commit(); continue
        try:
            z=zipfile.ZipFile(io.BytesIO(get('https://www.govinfo.gov/content/pkg/%s.zip'%pid,binary=True)))
            texts=[(os.path.basename(n),z.read(n).decode('utf-8','replace')) for n in z.namelist() if n.endswith('.htm')]
            rows,agg=parse_pages(texts,lambda f:'',date,'CHRG',pid,cur)
            cur.execute("INSERT OR REPLACE INTO cr_fetch_log VALUES(?,?,?)",('chrg:'+pid,'ok',datetime.datetime.now().isoformat()))
            con.commit()
            print('  %s [%s]: %d member turns'%(pid,(p.get('title') or '')[:60],rows))
        except Exception as e:
            cur.execute("INSERT OR REPLACE INTO cr_fetch_log VALUES(?,?,?)",('chrg:'+pid,'err:%s'%str(e)[:80],datetime.datetime.now().isoformat()))
            con.commit(); print('  !!',pid,str(e)[:100])
def status():
    con=db()
    for src in ('CREC','CHRG'):
        r=con.execute("SELECT COUNT(*),COUNT(DISTINCT member),COALESCE(SUM(nwords),0),MIN(date),MAX(date) FROM speeches WHERE source=?",(src,)).fetchone()
        print('%s: %d turns | %d members | %s words | %s..%s'%(src,r[0],r[1],f'{r[2]:,}',r[3],r[4]))
    t=con.execute("SELECT member,SUM(nwords) w FROM speeches GROUP BY member ORDER BY w DESC LIMIT 5").fetchall()
    print('top speakers:',', '.join('%s %s'%(m,f'{w:,}') for m,w in t))
def _keep_awake():
    """User directive 2026-07-06 ('put in checks so it doesn't fall asleep'): hold a system wake
    lock while a backfill runs; the OS clears it on process exit; display may still sleep."""
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        print('keep-awake: system wake lock held')
    except Exception as e:
        print('keep-awake unavailable (%s)' % str(e)[:60])

ap=argparse.ArgumentParser(); ap.add_argument('cmd',choices=['crec','chrg','status'])
ap.add_argument('--since',default='2025-07-01'); ap.add_argument('--until',default=str(datetime.date.today()))
a=ap.parse_args()
if a.cmd=='crec': _keep_awake(); run_crec(a.since,a.until); status()
elif a.cmd=='chrg': _keep_awake(); run_chrg(a.since,a.until); status()
else: status()
