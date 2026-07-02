import json,sys,os,shutil,datetime,win32com.client as win32
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
M=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx'
D=json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\category_stance.json'))
cats=D['cats']; matrix=D['matrix']
def rgb(r,g,b): return b*65536+g*256+r
TIER={'Champion':rgb(0x63,0xBE,0x7B),'Defender':rgb(0x2D,0xD4,0xBF),'Ally':rgb(0xC6,0xEF,0xCE),
      'Highly Persuadable':rgb(0xBD,0xD7,0xEE),'True Neutral':rgb(0xE7,0xE7,0xE7),'Lean Skeptic':rgb(0xFC,0xE4,0xD6),
      'Neutral':rgb(0xFF,0xFF,0xFF),'Skeptic':rgb(0xFF,0xC7,0xCE),'Opponent':rgb(0xF8,0x69,0x6B),'—':rgb(0xF2,0xF2,0xF2)}
bk=M.replace('.xlsx','.PRE-CATSTANCE-%s.xlsx'%datetime.date.today().strftime('%Y%m%d'))
shutil.copy2(M,bk); print('backup:',os.path.basename(bk))
xl=win32.DispatchEx('Excel.Application'); xl.Visible=False; xl.DisplayAlerts=False
try:
    wb=xl.Workbooks.Open(M)
    bm=wb.Worksheets('Blended Model'); ra=wb.Worksheets('Rank & Allocation')
    members=[bm.Cells(r,1).Value for r in range(3,536) if bm.Cells(r,1).Value]
    gen={ra.Cells(r,1).Value:ra.Cells(r,7).Value for r in range(3,536) if ra.Cells(r,1).Value}
    for nm in ['Category Stance']:
        try: wb.Worksheets(nm).Delete()
        except: pass
    ws=wb.Worksheets.Add(After=wb.Worksheets('Signed Coalitions')); ws.Name='Category Stance'
    hdr=['Member','General Stance']+cats
    data=[hdr]
    for m in members:
        data.append([m,gen.get(m,'')]+[matrix.get(m,{}).get(c,'—') for c in cats])
    nr=len(data); nc=len(hdr)
    ws.Range(ws.Cells(1,1),ws.Cells(nr,nc)).Value=data
    # header styling + freeze
    h=ws.Range(ws.Cells(1,1),ws.Cells(1,nc)); h.Font.Bold=True; h.Interior.Color=rgb(0x25,0x3A,0x5A); h.Font.Color=rgb(255,255,255)
    h.WrapText=True; ws.Rows(1).RowHeight=46
    ws.Range('C1').Select(); xl.ActiveWindow.FreezePanes=False
    ws.Application.ActiveWindow.SplitColumn=2; ws.Application.ActiveWindow.SplitRow=1; ws.Application.ActiveWindow.FreezePanes=True
    ws.Columns(1).ColumnWidth=22; ws.Columns(2).ColumnWidth=13
    for c in range(3,nc+1): ws.Columns(c).ColumnWidth=11
    # conditional color by tier (fast: 6 FormatConditions on the body)
    body=ws.Range(ws.Cells(2,3),ws.Cells(nr,nc))
    body.HorizontalAlignment=-4108  # center
    xl.ScreenUpdating=False; xl.Calculation=-4135  # manual, speed COM
    COLORME={'Champion','Defender','Ally','Highly Persuadable','True Neutral','Lean Skeptic','Skeptic','Opponent'}
    for ri,m in enumerate(members):
        row=matrix.get(m,{})
        for ci,c in enumerate(cats):
            t=row.get(c,'—')
            if t in COLORME:
                cell=ws.Cells(2+ri,3+ci); cell.Interior.Color=TIER[t]
                if t in ('Champion','Opponent'): cell.Font.Bold=True
    xl.Calculation=-4105; xl.ScreenUpdating=True  # back to automatic
    # legend below
    lr=nr+2; ws.Cells(lr,1).Value='Legend (stance toward the CU position, per category):'; ws.Cells(lr,1).Font.Bold=True
    for i,t in enumerate(['Champion','Defender','Ally','Highly Persuadable','True Neutral','Lean Skeptic','Skeptic','Opponent','—']):
        ws.Cells(lr+1,1+i).Value=t; ws.Cells(lr+1,1+i).Interior.Color=TIER[t]
    ws.Cells(lr+2,1).Value='Build: 0.55*legislative + 0.35*press + 0.10*votes(n>=5); votes cover ~9/17 categories.'
    wb.Save(); print('Category Stance sheet written: %d members x %d categories'%(len(members),len(cats)))
finally:
    wb.Close(SaveChanges=True); xl.Quit()
