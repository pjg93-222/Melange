import csv,sys,re,collections,json
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
BANK={'C00336768','C00104299','C00128512','C00379693','C00034595','C00300178','C00429852','C00004275',
'C00043489','C00364778','C00009639','C00386524','C00008474','C00039305','C00032698','C00035519','C00186064',
'C00018036','C00488882','C00432252','C00648345','C00501429','C00890707','C00438051','C00040535','C00365122',
'C00326595','C00038604','C00410274','C00879890','C00579540','C00589119','C00370015'}
# legislators: fec_id->bio, (LAST,FIRST)->bio (+state), bio->name
fec2bio={}; nf2bio=collections.defaultdict(list); bio2name={}
with open('legislators.csv',encoding='utf-8') as f:
    r=csv.reader(f); h=next(r)
    fi=h.index('fec_ids');ni=h.index('full_name');bi=h.index('bioguide_id');li=h.index('last_name');fir=h.index('first_name')
    si=h.index('state') if 'state' in h else None
    for row in r:
        bio2name[row[bi]]=row[ni]
        for cid in re.findall(r'[HSP]\d[A-Z0-9]{2}\d{5}',row[fi]): fec2bio[cid]=row[bi]
        st=row[si] if si is not None else ''
        nf2bio[(row[li].upper(),row[fir].upper())].append((row[bi],st))
candname={}; candstate={}
for line in open('cn.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)>13: candname[p[0]]=p[1]; candstate[p[0]]=p[13]
def resolve(cand):
    if cand in fec2bio: return fec2bio[cand]
    nm=candname.get(cand,'')
    if ',' in nm:
        last=nm.split(',')[0].strip().upper(); first=nm.split(',')[1].strip().split()[0].upper() if len(nm.split(','))>1 and nm.split(',')[1].strip() else ''
        cands=nf2bio.get((last,first),[])
        st=cand[1:3] if len(cand)>3 else ''  # H2GA -> GA at pos1-2? actually cand_id[2:4]
        st=cand[2:4]
        if len(cands)==1: return cands[0][0]
        for b,s in cands:
            if s==st: return b
    return None
bankc=collections.defaultdict(float); reclaimed=collections.defaultdict(float); stillunmapped=collections.defaultdict(float)
for line in open('itpas2.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)<17 or p[0] not in BANK or p[5] not in ('24K','24Z'): continue
    if len(p)>19 and p[19]=='X': continue
    cand=p[16]
    try: amt=float(p[14])
    except: continue
    bio=resolve(cand)
    if bio: 
        bankc[bio]+=amt
        if cand not in fec2bio: reclaimed[cand]+=amt
    elif cand: stillunmapped[cand]+=amt
print(f'bank $ to mapped members: ${sum(bankc.values()):,.0f} | members: {sum(1 for v in bankc.values() if v>0)}')
print(f'RECLAIMED via name+state fallback: ${sum(reclaimed.values()):,.0f} across {len(reclaimed)} sitting members')
for c,a in sorted(reclaimed.items(),key=lambda x:-x[1])[:6]: print(f'   {candname.get(c):30s} ${a:>8,.0f} -> {bio2name.get(resolve(c))}')
print(f'\nstill unmapped (genuine non-members): ${sum(stillunmapped.values()):,.0f} / {len(stillunmapped)} cands')
for c,a in sorted(stillunmapped.items(),key=lambda x:-x[1])[:6]: print(f'   {candname.get(c):30s} ${a:>8,.0f}')
json.dump({b:round(v) for b,v in bankc.items()}, open('bank_by_bio.json','w'))
print('\nwrote bank_by_bio.json')
