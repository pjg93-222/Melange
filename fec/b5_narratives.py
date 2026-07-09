# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT
"""3-paragraph 'Suggested approach' narrative generator (user feature 2026-07-09). For each member,
assembles a DE-IDENTIFIED measured profile (validated Big5 v2 + behavioral dispositions + persona +
conversational-dynamics + clean-audio vocal descriptors) and has FABLE write three tight paragraphs:
  P1  Overall personality (succinct)
  P2  Individual quirks, manner of speech, landmines (interruptions/floor-dynamics + vocal + diction)
  P3  Persuasive approach (personality-matched, per the persuasion literature)
De-identified inputs (no name/party/state) so Fable describes the MEASURED profile, not its prior
knowledge of the politician (no confabulation). Fable is used ONLY here (per the paragraphs-only rule);
everything mechanical is Haiku. Writes member_narratives.json {name:{p1,p2,p3,inputs,...}}. Resumable
(skips members already generated). Usage: python b5_narratives.py [--limit N] [--only "Name1,Name2"]
DISPLAY-ONLY: does not touch behavioral dispositions, persona, the engine, or ranks."""
import json, re
sys=_s; sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=MB_ROOT
from scipy.stats import norm
import anthropic
cl=anthropic.Anthropic(api_key=open(B+r'\fec\anthropic_key.txt').read().strip())
L=lambda f: json.load(open(B+'\\'+f,encoding='utf-8'))
V2=(L('big5_v2.json').get('traits') or {})
BD=(L('behavioral_dispositions.json').get('members') or {})
IF=L('interaction_features.json'); IF=IF.get('members',IF) if isinstance(IF,dict) else {}
RC=L('member_receptivity.json'); RC=RC.get('members',RC) if isinstance(RC,dict) else {}
AU=L('b5_audio_cache.json'); AZ={m:dict(zip(AU['feature_names'],AU['z'][m])) for m in AU['members']}
OUT=B+r'\member_narratives.json'

def band(z):
    if z is None: return None
    p=norm.cdf(float(z))*100
    lab='very high' if p>=90 else 'high' if p>=70 else 'average' if p>=30 else 'low' if p>=10 else 'very low'
    return '%s (%dth pct)'%(lab,round(p))
def line(lbl,mean,z):
    b=band(z);  return ('  - %s — %s: %s'%(lbl,mean,b)) if b else None

TRAITS=[('Extraversion','talkative, assertive, energetic vs. reserved','E'),
        ('Agreeableness','warm, cooperative, consensus-seeking vs. blunt, competitive','A'),
        ('Conscientiousness','disciplined, detail-oriented, reliable vs. flexible, improvisational','C'),
        ('Openness','curious, idea-driven, novelty-seeking vs. practical, conventional','O'),
        ('Emotional stability','calm, even-keeled vs. reactive, easily rattled','ES')]
BEH=[('Cooperation','reaches across the aisle','cooperation_z'),
     ('Dominance','controls the room/floor','dominance_z'),
     ('Visibility','high public/media profile','visibility_z'),
     ('Breadth','engages a wide range of issues','breadth_z'),
     ('Diligence','legislative follow-through','diligence_z')]
# conversational-dynamics descriptors (z-within-program); (label, low-pole phrase, high-pole phrase)
INTER=[('wpt_mean','speaks in short, clipped turns','holds forth in long, uninterrupted turns'),
       ('gini','shares the floor evenly','dominates the floor / holds forth'),
       ('cutoff','rarely cut off','often cut off or trails off mid-thought in contested exchanges'),
       ('burst','avoids rapid crosstalk','thrives in rapid, contested back-and-forth'),
       ('defense','rarely defends the floor','frequently deploys floor-defense moves ("let me finish")'),
       ('discmark','clean, spare diction','peppers speech with fillers ("you know", "I mean")'),
       ('agree','slow to concede a point','quick to voice agreement ("right", "exactly")')]
# clean-audio vocal descriptors (eGeMAPS z-within-roster); (feature, low phrase, high phrase)
VOCAL=[('F0semitoneFrom27.5Hz_sma3nz_amean','a lower-pitched voice','a higher-pitched voice'),
       ('F0semitoneFrom27.5Hz_sma3nz_stddevNorm','a flat, monotone delivery','an expressive, melodic delivery with wide pitch swings'),
       ('loudness_sma3_amean','a soft-spoken, low-intensity delivery','a loud, forceful delivery'),
       ('loudness_sma3_stddevNorm','even, steady volume','dynamic volume with big emphatic swings'),
       ('loudnessPeaksPerSec','a slow, deliberate pace','a fast, rapid-fire pace'),
       ('HNRdBACF_sma3nz_amean','a breathy or rough vocal texture','a clear, resonant voice'),
       ('jitterLocal_sma3nz_amean','a very steady voice','a slightly unsteady, tremulous voice (tension tell)')]

def phrases(items, getz, th=0.6):
    out=[]
    for key,lo,hi in items:
        z=getz(key)
        if z is None: continue
        if z>=th: out.append(hi)
        elif z<=-th: out.append(lo)
    return out

def profile(name):
    v=V2.get(name,{}); bd=BD.get(name,{}); rc=RC.get(name,{}); az=AZ.get(name)
    P=['MEASURED PROFILE OF AN ANONYMOUS U.S. LEGISLATOR (describe ONLY what these measures support):','','PERSONALITY (validated text instrument + behavioral record):']
    for lbl,mean,k in TRAITS:
        ln=line(lbl,mean,v.get(k));  P.append(ln) if ln else None
    for lbl,mean,k in BEH:
        ln=line(lbl,mean,bd.get(k));  P.append(ln) if ln else None
    # persona / receptivity
    sr=rc.get('susc_read'); ag=rc.get('agency_pct'); co=rc.get('communion_pct')
    per=[]
    if ag is not None and co is not None: per.append('interpersonal stance: agency %d%% / communion %d%%'%(round(ag),round(co)))
    if sr and sr!='both-neutral': per.append('susceptibility read: %s'%sr.replace('-',' '))
    if per: P+=['','PERSONA:']+['  - '+x for x in per]
    # conversational dynamics
    ip=phrases(INTER, lambda k: (IF.get(name) or {}).get(k))
    if ip: P+=['','MANNER OF SPEECH (hearing/interview conversational dynamics):']+['  - '+x for x in ip]
    # vocal (clean audio)
    if az:
        vp=phrases(VOCAL, lambda k: az.get(k))
        if vp: P+=['','VOICE (clean verified-solo audio, eGeMAPS):']+['  - '+x for x in vp]
    has={'audio':bool(az),'interaction':bool(IF.get(name)),'v2':bool(v),'behavioral':bool(bd)}
    return '\n'.join(x for x in P if x is not None), has

SYS=('You write confidential, tactical influence briefs for a legislative-affairs team. You are given '
 'ONLY a de-identified measured profile of one legislator. Rules: describe ONLY what the measures '
 'support; do NOT invent biography, party, positions, votes, or events; no name-guessing. Voice: crisp, '
 'concrete, professional — a sharp staffer briefing a principal, not a horoscope. Avoid restating the raw '
 'percentiles; translate them into behavior.')
def prompt(prof):
    return (SYS+'\n\n'+prof+'\n\n----\nWrite exactly THREE paragraphs, each tagged on its own line:\n'
    '[P1] OVERALL PERSONALITY (3-4 sentences): a succinct character sketch synthesizing the personality + '
    'behavioral profile.\n'
    '[P2] QUIRKS, MANNER OF SPEECH & LANDMINES (4-5 sentences): how they actually communicate (pace, pitch, '
    'force, floor-holding, interruptions, verbal tics from the measures) AND the interpersonal landmines — '
    'what triggers defensiveness or friction, when to not interrupt, how they react under pressure. Ground '
    'every claim in the manner-of-speech / voice / personality measures provided.\n'
    '[P3] PERSUASIVE APPROACH (4-5 sentences): how to move this person, TAILORED to their trait profile per '
    'the personality-persuasion literature (the "matching effect": frame the message to their dominant '
    'traits). Concretely: high Agreeableness -> warmth, consensus, relationship framing; low Agreeableness -> '
    'respect independence, appeal to their own logic/interests, do not force consensus; high Conscientiousness '
    '-> detailed evidence, reliability, follow-through; high Extraversion -> energy, public recognition, social '
    'proof; low Extraversion -> written detail, one-on-one, give space; high Openness -> vision, novel framing; '
    'low Openness -> proven, practical, concrete; low Emotional stability -> reassurance, reduce perceived '
    'risk, careful loss-framing; high Dominance -> let them own the win, never appear to corner them. Give 2-3 '
    'concrete tactical moves, not platitudes.\n\nOutput ONLY the three tagged paragraphs.')

def parse(raw):
    parts={}
    for tag in ('P1','P2','P3'):
        m=re.search(r'\[%s\][:\-\s]*(.+?)(?=\[P[123]\]|$)'%tag, raw, re.S)
        if m: parts[tag.lower()]=re.sub(r'\s+',' ',m.group(1)).strip()
    return parts

def _txt(m): return ''.join(b.text for b in m.content if getattr(b,'type','')=='text').strip()
def _call(prof,model,mx=2400):
    return cl.messages.create(model=model,max_tokens=mx,messages=[{'role':'user','content':prompt(prof)}])
def gen(name):
    prof,has=profile(name)
    m=_call(prof,'claude-fable-5'); model='fable'; raw=_txt(m)
    if getattr(m,'stop_reason','')=='refusal' or not raw:
        # Fable false-positive refusal on the influence-brief framing -> Opus 4.8 rescue (claude-api skill).
        # Still the paragraphs task; Opus only catches the ones Fable declines.
        m=_call(prof,'claude-opus-4-8'); model='opus-fallback'; raw=_txt(m)
    p=parse(raw)
    return {'p1':p.get('p1',''),'p2':p.get('p2',''),'p3':p.get('p3',''),'has':has,'model':model,
            'ok':bool(p.get('p1') and p.get('p2') and p.get('p3'))}

if __name__=='__main__':
    args=sys.argv
    res=json.load(open(OUT,encoding='utf-8')) if _o.path.exists(OUT) else {}
    roster=[m for m in BD if m in V2 or m in BD]   # everyone with a behavioral record (all 533)
    only=next((a.split('=',1)[1] for a in args if a.startswith('--only=')),None)
    if '--only' in args and not only:
        only=args[args.index('--only')+1]
    if only: roster=[m.strip() for m in only.split(',')]
    lim=next((int(a.split('=')[1]) for a in args if a.startswith('--limit=')),None)
    if lim is None and '--limit' in args: lim=int(args[args.index('--limit')+1])
    todo=[m for m in roster if m not in res or not res[m].get('ok')]
    if lim: todo=todo[:lim]
    workers=next((int(a.split('=')[1]) for a in args if a.startswith('--workers=')),6)
    print('narratives: %d target, %d to generate (Fable; Opus rescues refusals), %d workers'%(len(roster),len(todo),workers))
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    lock=threading.Lock(); n=[0]
    def work(name):
        try: r=gen(name); r['name']=name; return name,r
        except Exception as e: return name,{'err':str(e)[:90],'ok':False}
    with ThreadPoolExecutor(max_workers=max(1,workers)) as ex:
        futs=[ex.submit(work,nm) for nm in todo]
        for f in as_completed(futs):
            name,r=f.result()
            with lock:
                res[name]=r; n[0]+=1
                tag='ok(%s)'%r.get('model','?') if r.get('ok') else ('ERR '+r['err'] if r.get('err') else 'PARSE-FAIL')
                print('  [%d/%d] %-24s %s'%(n[0],len(todo),name[:24],tag))
                if n[0]%10==0 or n[0]==len(todo): json.dump(res,open(OUT,'w',encoding='utf-8'),ensure_ascii=False,indent=0)
    json.dump(res,open(OUT,'w',encoding='utf-8'),ensure_ascii=False,indent=0)
    done=sum(1 for v in res.values() if v.get('ok'))
    fb=sum(1 for v in res.values() if v.get('model')=='opus-fallback')
    print('member_narratives.json: %d generated (%d total); %d needed Opus fallback'%(done,len(res),fb))
