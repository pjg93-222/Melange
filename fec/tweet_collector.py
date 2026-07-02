# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
"""CONGRESSIONAL SOCIAL-MEDIA COLLECTOR + DATABASE (user-directed 2026-07-01: "was the data collector
for politicians tweets included? We need a very robust database").

HONEST CONTEXT: Fink et al. (2023) shipped their collection code (tweet_fetcher.py etc. on Zenodo,
https://zenodo.org/record/8253486), but it targets the 2022-era Twitter API v2 academic track that no
longer exists — X now sells read access in paid tiers, and the community mirrors (e.g. alexlitel/
congresstweets) stopped when that happened.  So this module IS the collector, built for today's reality:
  * X (Twitter) API v2 adapter    — works when X_BEARER_TOKEN is set (paid tier; incremental since_id).
  * Bluesky adapter               — PUBLIC AppView API, NO KEY NEEDED; a growing share of members post
                                     there (coverage skews D — flagged in `status`).
  * Handle registry               — seeded from the canonical unitedstates/congress-legislators
                                     legislators-social-media.json, joined to our 533 by bioguide.
Storage: SQLite `social_media.db` (WAL, UNIQUE-keyed idempotent upserts, per-handle checkpoints) with a
normalized `interactions` table (retweet/quote/reply/mention events) so the Fink influence network and
the Zhou-Elejalde stance-dynamics windows can be built straight off the DB.

Usage:
  python tweet_collector.py init                       # create db + seed handles (533 members)
  python tweet_collector.py fetch --platform bluesky   # keyless; --limit-members N for a smoke run
  python tweet_collector.py fetch --platform x         # needs env X_BEARER_TOKEN
  python tweet_collector.py status                     # coverage + freshness report
  python tweet_collector.py build-influence            # Fink-normalized influence net -> tweet_influence.json
"""
import json,sys,os,sqlite3,time,argparse,datetime,collections,urllib.request,urllib.parse
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=MB_ROOT
DB=B+r'\social_media.db'
UA={'User-Agent':'MelangeSystems-collector/1.0 (research)'}
def db():
    c=sqlite3.connect(DB); c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA foreign_keys=ON')
    try: c.execute('ALTER TABLE members ADD COLUMN truth TEXT')   # migration for pre-truth databases
    except sqlite3.OperationalError: pass
    return c
SCHEMA='''
CREATE TABLE IF NOT EXISTS members(bioguide TEXT PRIMARY KEY, name TEXT, party TEXT, chamber TEXT,
  twitter TEXT, twitter_id TEXT, bluesky TEXT, truth TEXT, facebook TEXT, youtube TEXT, instagram TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS posts(platform TEXT, post_id TEXT, bioguide TEXT, created_at TEXT, text TEXT,
  reply_to TEXT, quote_of TEXT, repost_of TEXT, like_count INT, repost_count INT, reply_count INT,
  fetched_at TEXT, raw TEXT, PRIMARY KEY(platform,post_id));
CREATE TABLE IF NOT EXISTS interactions(platform TEXT, kind TEXT, src_bioguide TEXT, dst_bioguide TEXT,
  post_id TEXT, created_at TEXT, PRIMARY KEY(platform,kind,post_id,dst_bioguide));
CREATE TABLE IF NOT EXISTS fetch_log(platform TEXT, bioguide TEXT, checkpoint TEXT, last_run TEXT,
  n_total INT DEFAULT 0, status TEXT, PRIMARY KEY(platform,bioguide));
CREATE INDEX IF NOT EXISTS ix_posts_member ON posts(bioguide,created_at);
CREATE INDEX IF NOT EXISTS ix_inter ON interactions(src_bioguide,dst_bioguide);'''
def get(url,tries=3,timeout=25):
    for t in range(tries):
        try:
            rq=urllib.request.Request(url,headers=UA)
            if os.environ.get('X_BEARER_TOKEN') and 'api.twitter.com' in url:
                rq.add_header('Authorization','Bearer '+os.environ['X_BEARER_TOKEN'])
            return json.load(urllib.request.urlopen(rq,timeout=timeout))
        except urllib.error.HTTPError as e:
            if e.code==429: time.sleep(min(60,15*(t+1))); continue   # rate limit: back off, honor retry
            if t==tries-1: raise
            time.sleep(3)
        except Exception:
            if t==tries-1: raise
            time.sleep(3)
def cmd_init():
    c=db(); c.executescript(SCHEMA)
    cong={m['member']:m for m in json.load(open(B+r'\congestion.json'))}
    bio={m['bioguide']:n for n,m in cong.items() if m.get('bioguide')}
    smp=B+r'\legislators_social_media.json'
    if not os.path.exists(smp):   # canonical registry (unitedstates/congress-legislators)
        d=urllib.request.urlopen('https://unitedstates.github.io/congress-legislators/legislators-social-media.json',timeout=30).read()
        open(smp,'wb').write(d)
    reg=json.load(open(smp,encoding='utf-8'))
    n=tw=bs=0
    for e in reg:
        bg=e.get('id',{}).get('bioguide')
        if bg not in bio: continue
        s=e.get('social',{})
        c.execute('INSERT INTO members(bioguide,name,twitter,twitter_id,bluesky,facebook,youtube,instagram,updated) '
                  'VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(bioguide) DO UPDATE SET twitter=excluded.twitter,'
                  'twitter_id=excluded.twitter_id,bluesky=excluded.bluesky,updated=excluded.updated',
                  (bg,bio[bg],s.get('twitter'),str(s.get('twitter_id') or ''),s.get('bluesky'),
                   s.get('facebook'),s.get('youtube'),s.get('instagram'),datetime.datetime.now().isoformat()))
        n+=1; tw+=bool(s.get('twitter')); bs+=bool(s.get('bluesky'))
    c.commit()
    print('seeded %d/533 members from the canonical registry: %d twitter handles, %d bluesky handles'%(n,tw,bs))
    if bs==0: print('  (registry carries no bluesky field yet — add handles manually: UPDATE members SET bluesky=? WHERE name=?)')
    print('db: %s'%DB)
def _upsert_post(c,plat,pid,bg,created,text,reply_to,quote_of,repost_of,likes,reposts,replies,raw):
    c.execute('INSERT OR IGNORE INTO posts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (plat,pid,bg,created,text,reply_to,quote_of,repost_of,likes,reposts,replies,
               datetime.datetime.now().isoformat(),json.dumps(raw,ensure_ascii=True)[:4000]))
def _log(c,plat,bg,ck,n,status):
    c.execute('INSERT INTO fetch_log VALUES(?,?,?,?,?,?) ON CONFLICT(platform,bioguide) DO UPDATE SET '
              'checkpoint=excluded.checkpoint,last_run=excluded.last_run,n_total=n_total+excluded.n_total,status=excluded.status',
              (plat,bg,ck,datetime.datetime.now().isoformat(),n,status))
def fetch_bluesky(limit_members=None,pages=3):
    """Public AppView — no auth.  Captures posts + reply/quote/mention edges via facets."""
    c=db(); rows=c.execute("SELECT bioguide,name,bluesky FROM members WHERE bluesky IS NOT NULL AND bluesky!='' AND bluesky!='none-found'").fetchall()
    if os.environ.get('BSKY_SKIP_FETCHED'):   # chunked full sweeps: don't refetch members already logged ok
        done={r[0] for r in c.execute("SELECT bioguide FROM fetch_log WHERE platform='bluesky' AND status='ok'")}
        rows=[r for r in rows if r[0] not in done]
    rows=[(bg,nm,(h or '').split()[0]) for bg,nm,h in rows]   # strip the ' [UNVERIFIED — confirm]' review tag
    if limit_members: rows=rows[:limit_members]
    h2bg={ (r[2] or '').lower():r[0] for r in rows }
    print('bluesky fetch: %d members with handles'%len(rows))
    for bg,name,handle in rows:
        got=0; cursor=None
        try:
            for _ in range(pages):
                u='https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor=%s&limit=100'%urllib.parse.quote(handle)
                if cursor: u+='&cursor='+urllib.parse.quote(cursor)
                d=get(u)
                for it in d.get('feed',[]):
                    p=it.get('post',{}); rec=p.get('record',{})
                    pid=p.get('uri',''); created=rec.get('createdAt',''); text=rec.get('text','')
                    reply=rec.get('reply',{}).get('parent',{}).get('uri')
                    quote=(rec.get('embed',{}) or {}).get('record',{}).get('uri')
                    _upsert_post(c,'bluesky',pid,bg,created,text,reply,quote,None,
                                 p.get('likeCount',0),p.get('repostCount',0),p.get('replyCount',0),{})
                    # mention edges from facets (handle -> member)
                    for f in rec.get('facets',[]) or []:
                        for feat in f.get('features',[]):
                            hm=(feat.get('did') and None) or feat.get('handle') or ''
                            if feat.get('$type','').endswith('#mention'):
                                tgt=h2bg.get((feat.get('handle') or '').lower())
                                if tgt and tgt!=bg:
                                    c.execute('INSERT OR IGNORE INTO interactions VALUES(?,?,?,?,?,?)',
                                              ('bluesky','mention',bg,tgt,pid,created))
                    got+=1
                cursor=d.get('cursor')
                if not cursor: break
            _log(c,'bluesky',bg,cursor or '',got,'ok'); c.commit()
            print('  %-24s +%d posts'%(name,got))
        except Exception as e:
            _log(c,'bluesky',bg,'',got,'ERR:'+str(e)[:80]); c.commit(); print('  %-24s ERROR %s'%(name,str(e)[:80]))
def fetch_x(limit_members=None):
    """X API v2 — needs env X_BEARER_TOKEN (paid tier).  Incremental via since_id checkpoints; captures
    referenced_tweets (retweet/quote/reply) + entity mentions, mirroring Fink et al.'s request shape."""
    if not os.environ.get('X_BEARER_TOKEN'):
        print('X_BEARER_TOKEN not set — X fetch skipped.  (X read access is paid-tier only since 2023;'); print(' the Bluesky adapter needs no key.)'); return
    c=db(); rows=c.execute("SELECT bioguide,name,twitter_id,twitter FROM members WHERE twitter_id IS NOT NULL AND twitter_id!=''").fetchall()
    if limit_members: rows=rows[:limit_members]
    id2bg={r[2]:r[0] for r in rows}
    for bg,name,uid,handle in rows:
        ck=c.execute('SELECT checkpoint FROM fetch_log WHERE platform=? AND bioguide=?',('x',bg)).fetchone()
        since='&since_id='+ck[0] if ck and ck[0] else ''
        u=('https://api.twitter.com/2/users/%s/tweets?max_results=100&tweet.fields=created_at,referenced_tweets,entities,public_metrics'
           '&expansions=referenced_tweets.id.author_id,entities.mentions.username'%uid)+since
        got=0; newest=None
        try:
            d=get(u)
            for t in d.get('data',[]) or []:
                pid=t['id']; newest=max(newest or pid,pid)
                rt=q=rp=None
                for ref in t.get('referenced_tweets',[]) or []:
                    if ref['type']=='retweeted': rt=ref['id']
                    elif ref['type']=='quoted': q=ref['id']
                    elif ref['type']=='replied_to': rp=ref['id']
                pm=t.get('public_metrics',{})
                _upsert_post(c,'x',pid,bg,t.get('created_at',''),t.get('text',''),rp,q,rt,
                             pm.get('like_count',0),pm.get('retweet_count',0),pm.get('reply_count',0),t)
                # interaction edges: referenced authors + mentions that are members
                for iu in (d.get('includes',{}).get('tweets') or []):
                    if iu['id'] in (rt,q,rp) and iu.get('author_id') in id2bg and id2bg[iu['author_id']]!=bg:
                        kind='retweet' if iu['id']==rt else ('quote' if iu['id']==q else 'reply')
                        c.execute('INSERT OR IGNORE INTO interactions VALUES(?,?,?,?,?,?)',
                                  ('x',kind,bg,id2bg[iu['author_id']],pid,t.get('created_at','')))
                for mn in (t.get('entities',{}).get('mentions') or []):
                    tb=id2bg.get(str(mn.get('id','')))
                    if tb and tb!=bg:
                        c.execute('INSERT OR IGNORE INTO interactions VALUES(?,?,?,?,?,?)',
                                  ('x','mention',bg,tb,pid,t.get('created_at','')))
                got+=1
            _log(c,'x',bg,newest or (ck[0] if ck else ''),got,'ok'); c.commit(); print('  %-24s +%d tweets'%(name,got))
        except Exception as e:
            _log(c,'x',bg,ck[0] if ck else '',got,'ERR:'+str(e)[:80]); c.commit(); print('  %-24s ERROR %s'%(name,str(e)[:80]))
# ---- CU-domain relevance (Khan et al.: domain keyword/hashtag scoping of the collection) ----
import re as _re
CU_TERMS=_re.compile(r'credit union|\bncua\b|\bcfpb\b|interchange|credit card competition|\bccca\b|durbin|'
    r'tax exempt|tax status|field of membership|\bcdfi\b|overdraft|swipe fee|late fee|debit card|'
    r'consumer financial protection|share insurance|community bank|big bank',_re.I)
def relevance(text): return 1 if CU_TERMS.search(text or '') else 0
def fetch_truth(limit_members=None,pages=3):
    """Truth Social — a Mastodon fork, so the Mastodon client API shapes apply
    (/api/v1/accounts/lookup, /api/v1/accounts/:id/statuses with max_id paging; reblog/reply fields;
    mentions in the status entities).  UNLIKE Bluesky there is no public unauthenticated AppView:
    you need an account token in env TRUTH_TOKEN (Authorization: Bearer), and Cloudflare may still
    challenge datacenter IPs — run from a residential connection.  Respect ToS/rate limits; this is
    low-volume research collection of PUBLIC official-account posts, mirroring the Twitter-API terms
    the Fink/Khan datasets operated under.  Handles: fill members.truth manually or via probe —
    coverage is heavily R-skewed (the D skew of Bluesky, mirrored), so use BOTH platforms before
    inferring anything population-level."""
    tok=os.environ.get('TRUTH_TOKEN')
    if not tok:
        print('TRUTH_TOKEN not set — Truth Social fetch skipped.  Create an account, pull the OAuth bearer'); print(' from the web app (Network tab), set TRUTH_TOKEN, and fill members.truth handles.'); return
    c=db(); rows=c.execute("SELECT bioguide,name,truth FROM members WHERE truth IS NOT NULL AND truth!=''").fetchall()
    rows=[(bg,nm,(h or '').split()[0].lstrip('@')) for bg,nm,h in rows]
    if limit_members: rows=rows[:limit_members]
    h2bg={r[2].lower():r[0] for r in rows}
    def tget(u):
        rq=urllib.request.Request(u,headers={**UA,'Authorization':'Bearer '+tok})
        return json.load(urllib.request.urlopen(rq,timeout=25))
    print('truth social fetch: %d members with handles'%len(rows))
    for bg,name,handle in rows:
        got=0
        try:
            acct=tget('https://truthsocial.com/api/v1/accounts/lookup?acct='+urllib.parse.quote(handle))
            aid=acct['id']; max_id=None
            for _ in range(pages):
                u='https://truthsocial.com/api/v1/accounts/%s/statuses?limit=40&exclude_replies=false'%aid
                if max_id: u+='&max_id='+max_id
                sts=tget(u)
                if not sts: break
                for s in sts:
                    pid=s['id']; max_id=pid
                    txt=_re.sub(r'<[^>]+>',' ',s.get('content') or '')
                    rb=(s.get('reblog') or {}).get('id'); rp=s.get('in_reply_to_account_id')
                    _upsert_post(c,'truth',pid,bg,s.get('created_at',''),txt,rp,None,rb,
                                 s.get('favourites_count',0),s.get('reblogs_count',0),s.get('replies_count',0),{})
                    for mn in s.get('mentions',[]) or []:
                        tb=h2bg.get((mn.get('acct') or '').lower())
                        if tb and tb!=bg:
                            c.execute('INSERT OR IGNORE INTO interactions VALUES(?,?,?,?,?,?)',
                                      ('truth','mention',bg,tb,pid,s.get('created_at','')))
                    got+=1
                time.sleep(1.0)   # be gentle: no published rate limits; Mastodon default is 300/5min
            _log(c,'truth',bg,max_id or '',got,'ok'); c.commit(); print('  %-24s +%d truths'%(name,got))
        except Exception as e:
            _log(c,'truth',bg,'',got,'ERR:'+str(e)[:80]); c.commit(); print('  %-24s ERROR %s'%(name,str(e)[:80]))
def fetch_keywords(limit=100):
    """Khan et al.'s SECOND collection channel: domain keyword/hashtag search (their #ImranKhan/#PMLN ->
    our CU_TERMS), so the corpus captures the DEBATE around members, not just their own accounts.
    X recent-search endpoint (paid tier).  Posts land with bioguide=NULL; the stance classifier +
    mention extraction attribute them afterward."""
    if not os.environ.get('X_BEARER_TOKEN'): print('X_BEARER_TOKEN not set — keyword search skipped.'); return
    c=db()
    q=urllib.parse.quote('("credit union" OR NCUA OR CFPB OR interchange OR "Credit Card Competition Act") lang:en -is:retweet')
    d=get('https://api.twitter.com/2/tweets/search/recent?query=%s&max_results=%d&tweet.fields=created_at,author_id,public_metrics'%(q,min(100,limit)))
    got=0
    for t in d.get('data',[]) or []:
        pm=t.get('public_metrics',{})
        _upsert_post(c,'x',t['id'],None,t.get('created_at',''),t.get('text',''),None,None,None,
                     pm.get('like_count',0),pm.get('retweet_count',0),pm.get('reply_count',0),t); got+=1
    c.commit(); print('keyword search: +%d domain posts (unattributed; classify + attribute downstream)'%got)
def cmd_status():
    c=db()
    for plat in ('x','bluesky'):
        n=c.execute('SELECT COUNT(*),COUNT(DISTINCT bioguide) FROM posts WHERE platform=?',(plat,)).fetchone()
        i=c.execute('SELECT COUNT(*) FROM interactions WHERE platform=?',(plat,)).fetchone()[0]
        print('%-8s %6d posts from %3d members | %5d member-member interaction events'%(plat,n[0],n[1],i))
    h=c.execute("SELECT SUM(twitter IS NOT NULL AND twitter!=''),SUM(bluesky IS NOT NULL AND bluesky!='' AND bluesky!='none-found'),COUNT(*) FROM members").fetchone()
    print('handles: twitter %s / bluesky %s of %s members  (bluesky coverage skews D — check before inference)'%h)
    for r in c.execute("SELECT platform,COUNT(*) FROM fetch_log WHERE status LIKE 'ERR%' GROUP BY platform"): print('errors:',r)
def cmd_influence(min_posts=int(os.environ.get('TW_MIN_POSTS','25'))):
    """Fink et al. 2023, verbatim: P(i influences j) = (# of j's retweets/quotes/replies/mentions of i)
    / (# posts issued by i), with a minimum-activity floor (theirs: 100 tweets; dial TW_MIN_POSTS)."""
    c=db()
    items=dict(c.execute('SELECT bioguide,COUNT(*) FROM posts GROUP BY bioguide').fetchall())
    eng=collections.Counter()
    for src,dst in c.execute('SELECT src_bioguide,dst_bioguide FROM interactions'): eng[(dst,src)]+=1   # dst engaged BY src -> dst influences src
    cong={m['bioguide']:m['member'] for m in json.load(open(B+r'\congestion.json')) if m.get('bioguide')}
    out=[]
    for (i,j),n in eng.items():
        if items.get(i,0)>=min_posts:
            out.append({'src':cong.get(i,i),'dst':cong.get(j,j),'p':round(min(1.0,n/items[i]),4),'events':n})
    json.dump({'method':'Fink et al. 2023: engagements normalized by author volume; floor %d posts'%min_posts,
               'edges':sorted(out,key=lambda e:-e['p'])},open(B+r'\tweet_influence.json','w'),indent=1)
    print('wrote tweet_influence.json (%d directed influence edges) — feed to build_multilayer_network.py when ready'%len(out))
def cmd_discover(limit=None):
    """Probe Bluesky for member handles.  Official congressional accounts verify via DOMAIN handles
    (@warren.senate.gov style) — those are cryptographically domain-verified, so a resolve hit IS the
    member and is auto-accepted.  Plain {name}.bsky.social pattern hits are recorded as 'unverified?'
    for the user to confirm (a fan account can squat a name)."""
    c=db(); rows=c.execute("SELECT bioguide,name,twitter FROM members WHERE bluesky IS NULL OR bluesky=''").fetchall()
    if limit: rows=rows[:limit]
    allnames=[r[1] for r in c.execute('SELECT bioguide,name FROM members')]
    surcount=collections.Counter(n.split()[-1].lower() for n in allnames)
    taken={ (r[0] or '').split()[0].lower() for r in c.execute("SELECT bluesky FROM members WHERE bluesky IS NOT NULL AND bluesky!=''") }
    found=0
    for bg,name,tw in rows:
        last=name.split()[-1].lower().replace("'",'')
        amb=surcount[last]>1     # surname shared by >1 member: bare-surname domain patterns are unsafe (both Smiths -> smith.senate.gov)
        cands=[(None if amb else '%s.senate.gov'%last,'verified'),(None if amb else 'rep%s.house.gov'%last,'verified'),
               (((tw or '').lower()+'.bsky.social') if tw else None,'unverified?'),
               (None if amb else 'rep%s.bsky.social'%last,'unverified?')]
        cands=[(cd,tg) for cd,tg in cands if cd and cd.lower() not in taken]
        hit=False
        for cand,tag in cands:
            if not cand: continue
            try:
                d=get('https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle='+urllib.parse.quote(cand),tries=1,timeout=10)
                if d.get('did'):
                    hit=True
                    c.execute('UPDATE members SET bluesky=? WHERE bioguide=?',(cand+('' if tag=='verified' else ' [UNVERIFIED — confirm]'),bg))
                    c.commit()   # commit per hit: chunked/interrupted runs keep their progress
                    taken.add(cand.lower()); print('  %-24s -> @%s (%s)'%(name,cand,tag),flush=True); found+=1; break
            except Exception: continue
        if not hit:
            c.execute("UPDATE members SET bluesky='none-found' WHERE bioguide=?",(bg,)); c.commit()   # sentinel: don't re-probe on the next chunk
        time.sleep(0.15)
    c.commit(); print('discovered %d handles over %d probed members (verified = domain handle; confirm the unverified ones)'%(found,len(rows)))
def cmd_classify():
    """Score every collected post with the domain stance classifier (train_stance_domain.py --save) +
    the relevance filter -> member-level social stance signals, same shape stance_dynamics.py consumes."""
    import pickle
    pk=B+r'\stance_clf_composed.pkl'
    if not os.path.exists(pk): print('train first: python train_stance_domain.py --save'); return
    clf=pickle.load(open(pk,'rb')); c=db()
    rows=c.execute('SELECT platform,post_id,bioguide,created_at,text FROM posts').fetchall()
    rel=[(p,pid,bg,dt,tx) for p,pid,bg,dt,tx in rows if relevance(tx)]
    print('posts: %d total, %d CU-relevant (CU_TERMS filter)'%(len(rows),len(rel)))
    if not rel: return
    preds=clf.predict(['target: Credit Unions (direct). speaker: member. '+tx for *_,tx in rel])
    out=[{'platform':p,'post_id':pid,'bioguide':bg,'date':dt,'stance':st,'text':tx[:280]}
         for (p,pid,bg,dt,tx),st in zip(rel,preds)]
    json.dump(out,open(B+r'\social_stance_signals.json','w'),indent=1)
    agg=collections.Counter((r['bioguide'],r['stance']) for r in out if r['bioguide'])
    print('wrote social_stance_signals.json (%d scored posts, %d member-stance cells) — a NEW evidence'%(len(out),len(agg)))
    print('channel for the press pillar / stance_dynamics, provenance=social (user adjudicates adoption)')
ap=argparse.ArgumentParser(); ap.add_argument('cmd',choices=['init','fetch','status','build-influence','discover-bluesky','search','classify'])
ap.add_argument('--platform',default='bluesky',choices=['bluesky','x','truth']); ap.add_argument('--limit-members',type=int)
a=ap.parse_args()
if a.cmd=='init': cmd_init()
elif a.cmd=='fetch': {'bluesky':fetch_bluesky,'x':fetch_x,'truth':fetch_truth}[a.platform](a.limit_members)
elif a.cmd=='status': cmd_status()
elif a.cmd=='discover-bluesky': cmd_discover(a.limit_members)
elif a.cmd=='search': fetch_keywords()
elif a.cmd=='classify': cmd_classify()
else: cmd_influence()
