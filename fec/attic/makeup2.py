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
rows=list(csv.reader(open('legislators.csv',encoding='utf-8'))); Hh=rows[0]
li,fri,bi,ty=Hh.index('last_name'),Hh.index('first_name'),Hh.index('bioguide_id'),Hh.index('type')
fec2bio={}; bylast=collections.defaultdict(list); bio2type={}
for r in rows[1:]:
    bio2type[r[bi]]=r[ty]
    for c in re.findall(r'[HSP]\d[A-Z0-9]{2}\d{5}',r[Hh.index('fec_ids')]): fec2bio[c]=r[bi]
    bylast[norm(r[li])].append((r[bi],norm(r[fri]),norm(r[nk if False else Hh.index('nickname')])))
agg=collections.defaultdict(lambda:{'banks':0.0,'finserv':0.0,'cu':0.0})
for line in open('itpas2.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)<17 or p[0] not in grp or p[5] not in ('24K','24Z') or (len(p)>19 and p[19]=='X'): continue
    if p[16] in fec2bio:
        try: agg[fec2bio[p[16]]][grp[p[0]]]+=float(p[14])
        except: pass
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; cen=wb['Centrality']
name2bio={cen.cell(r,2).value:cen.cell(r,1).value for r in range(2,cen.max_row+1) if cen.cell(r,2).value}
def resolve(nm):
    if nm in name2bio: return name2bio[nm]
    nn=norm(nm); toks=nn.split()
    for k in (3,2,1):
        if len(toks)>k:
            cands=bylast.get(' '.join(toks[-k:]),[])
            if len(cands)==1: return cands[0][0]
            for b,f,nck in cands:
                if f[:3]==toks[0][:3] or nck[:3]==toks[0][:3]: return b
    return None
out=[]
for r in range(3,536):
    nm=bm.cell(r,1).value
    if not nm: continue
    b=resolve(nm); a=agg.get(b,{'banks':0,'finserv':0,'cu':0})
    cu=max(0,a['cu']); bk=max(0,a['banks']); fs=max(0,a['finserv']); tot=cu+bk+fs
    rec={'member':nm,'bioguide':b,'chamber':'House' if bio2type.get(b)=='rep' else 'Senate','cu':round(cu),'banks':round(bk),'finserv':round(fs),'total':round(tot)}
    if tot>0:
        rec['cu_pct']=round(100*cu/tot,1); rec['banks_pct']=round(100*bk/tot,1); rec['finserv_pct']=round(100*fs/tot,1)
    else: rec['cu_pct']=rec['banks_pct']=rec['finserv_pct']=None
    out.append(rec)
json.dump(out,open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\data\engine\congestion.json','w'))
totcu=sum(x['cu'] for x in out); totbk=sum(x['banks'] for x in out); totfs=sum(x['finserv'] for x in out)
got=[x for x in out if x['total']>0]; withcu=[x for x in got if x['cu']>0]
print('members with tracked $: %d/533 | totals: CU $%s  Banks $%s  FinSvc $%s'%(len(got),f'{totcu:,}',f'{totbk:,}',f'{totfs:,}'))
print('members receiving ANY CU money: %d'%len(withcu))
print('\nHighest CU share:')
for x in sorted(withcu,key=lambda x:-x['cu_pct'])[:12]:
    print('   %-22s CU %5s%% / Banks %5s%% / FinSvc %5s%%  (CU $%s | Bk $%s | FS $%s)'%(x['member'],x['cu_pct'],x['banks_pct'],x['finserv_pct'],f"{x['cu']:,}",f"{x['banks']:,}",f"{x['finserv']:,}"))
print('\nReference members:')
for n in ['Tina Smith','Brad Sherman','Young Kim','Pete Aguilar','Maxine Waters','Andy Barr','Bill Huizenga','French Hill']:
    x=[y for y in out if y['member']==n]
    if x:
        x=x[0]; print('   %-18s CU %s%% / Banks %s%% / FinSvc %s%%  (CU $%s Bk $%s FS $%s)'%(n,x['cu_pct'],x['banks_pct'],x['finserv_pct'],f"{x['cu']:,}",f"{x['banks']:,}",f"{x['finserv']:,}"))
