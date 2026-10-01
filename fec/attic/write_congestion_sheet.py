import shutil,os,json,sys
import win32com.client as w
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
src=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx'
bak=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.PRE-CONGESTION-20260626.xlsx'
tmp=r'C:\Temp\mb_cong.xlsx'
shutil.copy(src,bak); os.makedirs(r'C:\Temp',exist_ok=True); shutil.copy(src,tmp)
M=json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\data\engine\congestion.json'))
M.sort(key=lambda x:-x['total'])
hdr=['Member','Bioguide','Chamber','CU $','Banks $','FinSvc $','Total industry $','Receipts $','Saturation %',
     'CU % raw','Banks % raw','FinSvc % raw','CU % adj','Banks % adj','FinSvc % adj','Industry % adj (B-side weight)','Net lean (CU-industry)']
keys=['member','bioguide','chamber','cu','banks','finserv','total','receipts','saturation','cu_pct','banks_pct','finserv_pct','cu_adj','banks_adj','finserv_adj','industry_adj','net_lean']
xl=w.DispatchEx('Excel.Application'); xl.Visible=False; xl.DisplayAlerts=False
wb=xl.Workbooks.Open(tmp)
for s in list(wb.Worksheets):
    if s.Name=='Congestion': s.Delete()
ws=wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count)); ws.Name='Congestion'
ws.Cells(1,1).Value=('FINANCIAL CONGESTION LAYER  (2024 cycle, FEC PAC contributions, type 24K/24Z).  '
 'Buckets: CU = America’s Credit Unions/CULAC+NAFCU+CU PACs; Banks = F03 commercial banks+ABA/ICBA; FinSvc = F05 finance/credit (Visa,Amex,CapOne,Synchrony,Nelnet...).  '
 'raw% = share of member’s tracked $.  adj% = capacity-adjusted (each bucket / its industry total, then re-shared) — corrects banks’ ~3x larger budget; a CU $ counts 2.9x a bank $.  '
 'B-side weight = Industry%adj (competitor) ; A-side = CU%adj.  Net lean >0 = CU-funded, <0 = industry-captured.')
for c,h in enumerate(hdr,1): ws.Cells(2,c).Value=h
data=[[m.get(k) for k in keys] for m in M]
ws.Range(ws.Cells(3,1),ws.Cells(2+len(data),len(keys))).Value=data
ws.Rows(2).Font.Bold=True
wb.Save(); wb.Close(False); xl.Quit(); shutil.copy(tmp,src)
print('Congestion sheet written:',len(data),'members | backup',os.path.basename(bak))
