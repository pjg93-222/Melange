from pathlib import Path
import hashlib,json,urllib.request
origin='http://127.0.0.1:8806'
out=Path(__file__).parent
def get(url):
    with urllib.request.urlopen(url,timeout=30) as r:return r.read()
health=json.loads(get(origin+'/api/health'))
assets={}
for name in ['graph.js','graph.css','insights.js','insights.css','evidence.js','evidence-map.js','workspace.css','workspace-polish.css','theme.js']:
    served=get(origin+'/'+name)
    disk=(Path('mentat/app')/name).read_bytes()
    assets[name]={'served_sha256':hashlib.sha256(served).hexdigest(),'disk_sha256':hashlib.sha256(disk).hexdigest(),'equal':served==disk}
receipt={'origin':origin,'health':health,'assets':assets}
(out/'live-build-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
assert all(v['equal'] for v in assets.values()),assets
assert health['assets_sha256']==health['on_disk_assets_sha256_now']
assert health['code_sha256']==health['on_disk_code_sha256_now']
print('PASS: all nine served assets match disk; loaded and on-disk code and asset aggregates match.')
print('pid',health.get('pid'),'port',health.get('port'),'assets',health['assets_sha256'])
