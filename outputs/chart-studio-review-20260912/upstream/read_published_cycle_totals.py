from pathlib import Path
import json,sys,zipfile,xml.etree.ElementTree as ET
sys.path.insert(0,'mentat/app');import contribution_data as c
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def totals(path):
 with zipfile.ZipFile(path) as z:
  book=ET.fromstring(z.read('xl/workbook.xml'));rel=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
  links={r.get('Id'):r.get('Target') for r in rel}
  sheet=next(s for s in book.find('m:sheets',NS) if s.get('name') in ('Spending Overview','Crypto Spending Overview'))
  member=links[sheet.get('{'+NS['r']+'}id')];member=member.lstrip('/') if member.startswith('/') else 'xl/'+member
  table=ET.fromstring(z.read(member));cells={};needed=set()
  for row in table.findall('m:sheetData/m:row',NS):
   rn=int(row.get('r'))
   if not 5<=rn<=52:continue
   for cell in row:
    ref=cell.get('r');col=''.join(x for x in ref if x.isalpha())
    if col not in ('A','B','C'):continue
    value=cell.find('m:v',NS)
    if cell.get('t')=='s' and value is not None:
     cells[ref]=('s',int(value.text));needed.add(int(value.text))
    elif cell.get('t')=='inlineStr':cells[ref]=('v',''.join(cell.itertext()))
    elif value is not None:cells[ref]=('v',value.text)
  shared={}
  if needed:
   with z.open('xl/sharedStrings.xml') as stream:
    i=0
    for event,e in ET.iterparse(stream,events=('end',)):
     if e.tag=='{'+NS['m']+'}si':
      if i in needed:shared[i]=''.join(t.text or '' for t in e.iter('{'+NS['m']+'}t'))
      e.clear();i+=1
      if i>max(needed):break
  def val(ref):
   kind,v=cells.get(ref,('v',''));return shared.get(v,'') if kind=='s' else v
  return {val('A'+str(r)):c._cents(val('C'+str(r))) for r in range(6,53) if val('B'+str(r))=='Total Giving'}
directory=Path(r'C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files');results=[]
for source in c._sources(directory):
 actual=totals(source['workbook']);expected={k:c._cents(v) for k,v in source['expected_cycle_totals'].items()}
 r={'industry':source['id'],'workbook':str(source['workbook']),'workbook_sha256':source['workbook_sha256'],'source_database_sha256':source['database_sha256'],'published_cycle_cents':actual,'payload_cycle_cents':expected,'matches':actual==expected}
 results.append(r);print(json.dumps(r),flush=True)
Path('outputs/chart-studio-implementation-20260912/published-workbook-reconciliation.json').write_text(json.dumps(results,indent=2))
