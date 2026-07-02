import openpyxl,sys,glob
from openpyxl.utils import get_column_letter as L
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
nrm=wb['Legislative Score - Normalized']; raw=wb['Legislative Score - Raw']
def findrow(ws,name):
    for r in range(1,ws.max_row+1):
        if ws.cell(r,1).value==name: return r
    return None
rn=findrow(nrm,'Richard Durbin'); rr=findrow(raw,'Richard Durbin')
print('Normalized Durbin row=%s name=%r | Raw Durbin row=%s name=%r'%(rn,nrm.cell(rn,1).value if rn else None,rr,raw.cell(rr,1).value if rr else None))
def show(ws,row,sc,tag):
    print('\n%s  block@%d (%s):'%(tag,sc,L(sc)))
    for o in range(6):
        hdr=ws.cell(1,sc+o).value; sw=ws.cell(2,sc+o).value; v=ws.cell(row,sc+o).value
        print('   col%-3d %-2s  hdr=%-38s subwt=%-7s durbin=%s'%(sc+o,L(sc+o),str(hdr)[:38],str(sw),str(v)))
for sc,tag in [(27,'INTERCHANGE'),(35,'PAYMENTS'),(107,'CREDIT CARD'),(99,'CFPB Restrain')]:
    show(nrm,rn,sc,'NORMALIZED '+tag)
# Raw sheet: show its header layout near interchange to find the right columns
print('\n--- RAW sheet header row scan (cols 1..60 nonempty) ---')
for c in range(1,90):
    h=raw.cell(1,c).value
    if h and ('Interchange' in str(h) or 'Payments' in str(h) or 'Member' in str(h)): print('   col%-3d %-2s %r'%(c,L(c),str(h)[:40]))
