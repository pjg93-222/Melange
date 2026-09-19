from pathlib import Path
import json, sys, zipfile
from xml.etree import ElementTree as ET

PROJECT = Path(r'C:\Users\pgoff\Mentat\mentat')
sys.path.insert(0, str(PROJECT / 'tools'))
from report_directory import report_directory

ns = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
directory = report_directory()
result = []
for path in sorted(directory.glob('*.xlsx')):
    with zipfile.ZipFile(path) as z:
        xml = ET.fromstring(z.read('xl/workbook.xml'))
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        targets = {r.attrib['Id']: r.attrib['Target'] for r in rels}
        sheets = []
        for s in xml.findall('m:sheets/m:sheet', ns):
            target = targets[s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
            target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            with z.open(target) as stream:
                head = stream.read(8192).decode('utf-8')
            import re
            dimension = re.search(r'<(?:\w+:)?dimension\b[^>]*\bref="([^"]+)"',head)
            sheets.append({'name':s.attrib['name'], 'dimension':dimension.group(1) if dimension else None})
        result.append({'file':str(path), 'bytes':path.stat().st_size, 'sheets':sheets})
output = Path(__file__).parent / 'published_inventory.json'
output.write_text(json.dumps(result, indent=2),encoding='utf-8')
print(json.dumps(result, indent=2))
