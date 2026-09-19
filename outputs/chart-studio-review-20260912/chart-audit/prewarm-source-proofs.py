"""Prewarm the runtime guard using independently audited current source hashes."""
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'mentat/app'))
import contribution_source_guard as guard

output=Path(__file__).with_name('runtime-source-proofs.jsonl')
with output.open('w',encoding='utf-8') as receipt:
    for line in Path(__file__).with_name('recovered-source-lineage.jsonl').read_text(encoding='utf-8').splitlines():
        audit=json.loads(line);start=time.monotonic()
        source={'industry':audit['industry'],'database':Path(audit['source']),
                'database_sha256':audit['current_database_sha256'],
                'original_database_sha256':audit['original_database_sha256'],
                'hydration_manifest':Path(audit['source']+'.hydration.json')}
        proof=guard.verify(source)
        result={'industry':source['industry'],'seconds':round(time.monotonic()-start,3),'proof':proof}
        text=json.dumps(result,sort_keys=True);receipt.write(text+'\n');receipt.flush();print(text,flush=True)
