import csv,sys,re,collections,json,unicodedata,openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def norm(s): return ''.join(c for c in unicodedata.normalize('NFKD',str(s)) if not unicodedata.combining(c)).lower().strip()
BANKS={'C00336768','C00104299','C00128512','C00379693','C00034595','C00300178','C00429852','C00004275','C00043489','C00364778','C00009639','C00386524','C00008474','C00039305','C00032698','C00035519','C00186064','C00018036','C00488882','C00432252','C00648345','C00501429','C00890707'}
FINSERV={'C00438051','C00040535','C00365122','C00326595','C00038604','C00410274','C00879890','C00579540','C00589119','C00370015'}
CU={'C00007880','C00040659','C00390633','C00402107','C00430066','C00326132','C70006317','C00409342','C00360610','C00235929','C00751214'}
grp={}
for c in BANKS: grp[c]='banks'
for c in FINSERV: grp[c]='finserv'
for c in CU: grp[c]='cu'
rows=list(csv.reader(open('legislators.csv',encoding='utf-8'))); H=rows[0]
li,fri,bi,ty,nk=H.index('last_name'),H.index('first_name'),H.index('bioguide_id'),H.index('type'),H.index('nickname')
fec2bio={}; bio2cands=collections.defaultdict(list); bylast=collections.defaultdict(list); bio2type={}
for r in rows[1:]:
    bio2type[r[bi]]=r[ty]
    for c in re.findall(r'[HSP]\d[A-Z0-9]{2}\d{5}',r[H.index('fec_ids')]): fec2bio[c]=r[bi]; bio2cands[r[bi]].append(c)
    bylast[norm(r[li])].append((r[bi],norm(r[fri]),norm(r[nk])))
receipts={}
for line in open('weball24.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)>5:
        try: receipts[p[0]]=float(p[5])
        except: pass
agg=collections.defaultdict(lambda:{'banks':0.0,'finserv':0.0,'cu':0.0})
for line in open('itpas2.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)<17 or p[0] not in grp or p[5] not in ('24K','24Z') or (len(p)>19 and p[19]=='X'): continue
    if p[16] in fec2bio:
        try: agg[fec2bio[p[16]]][grp[p[0]]]+=float(p[14])
        except: pass
recbio={b:sum(receipts.get(c,0) for c in cs) for b,cs in bio2cands.items()}
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; cen=wb['Centrality']
name2bio={cen.cell(r,2).value:cen.cell(r,1).value for r in range(2,cen.max_row+1) if cen.cell(r,2).value}
def resolve(nm):
    if nm in name2bio: return name2bio[nm]
    toks=norm(nm).split()
    for k in (3,2,1):
        if len(toks)>k:
            cands=bylast.get(' '.join(toks[-k:]),[])
            if len(cands)==1: return cands[0][0]
            for b,f,nck in cands:
                if f[:3]==toks[0][:3] or nck[:3]==toks[0][:3]: return b
    return None
members=[]
for r in range(3,536):
    nm=bm.cell(r,1).value
    if not nm: continue
    b=resolve(nm); a=agg.get(b,{'banks':0,'finserv':0,'cu':0})
    members.append({'member':nm,'bioguide':b,'chamber':'House' if bio2type.get(b)=='rep' else 'Senate',
        'cu':max(0,round(a['cu'])),'banks':max(0,round(a['banks'])),'finserv':max(0,round(a['finserv'])),
        'receipts':round(recbio.get(b,0))})
TCU=sum(m['cu'] for m in members) or 1; TBK=sum(m['banks'] for m in members) or 1; TFS=sum(m['finserv'] for m in members) or 1
for m in members:
    tot=m['cu']+m['banks']+m['finserv']; m['total']=tot
    m['saturation']=round(100*tot/m['receipts'],2) if m['receipts']>=100000 else None
    if tot>0:
        m['cu_pct']=round(100*m['cu']/tot,1); m['banks_pct']=round(100*m['banks']/tot,1); m['finserv_pct']=round(100*m['finserv']/tot,1)
        cw,bw,fw=m['cu']/TCU,m['banks']/TBK,m['finserv']/TFS; sw=cw+bw+fw
        m['cu_adj']=round(100*cw/sw,1); m['banks_adj']=round(100*bw/sw,1); m['finserv_adj']=round(100*fw/sw,1)
        m['industry_adj']=round(m['banks_adj']+m['finserv_adj'],1)            # B-side competitor weight
        m['net_lean']=round(m['cu_adj']-m['industry_adj'],1)                  # + = CU-leaning, - = captured
    else:
        for k in ('cu_pct','banks_pct','finserv_pct','cu_adj','banks_adj','finserv_adj','industry_adj','net_lean'): m[k]=None
json.dump(members,open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congestion.json','w'))
print('members:',len(members),'| industry totals CU $%s Banks $%s FinSvc $%s'%(f'{TCU:,}',f'{TBK:,}',f'{TFS:,}'))
print('\nmost CU-leaning (net_lean, adj):')
for m in sorted([x for x in members if x['net_lean'] is not None],key=lambda x:-x['net_lean'])[:6]:
    print('   %-20s net %+5.0f  (adj CU %s / ind %s)  $tot %s'%(m['member'],m['net_lean'],m['cu_adj'],m['industry_adj'],f"{m['total']:,}"))
print('most CAPTURED (net_lean):')
for m in sorted([x for x in members if x['net_lean'] is not None],key=lambda x:x['net_lean'])[:6]:
    print('   %-20s net %+5.0f  (adj CU %s / ind %s)  $tot %s'%(m['member'],m['net_lean'],m['cu_adj'],m['industry_adj'],f"{m['total']:,}"))
