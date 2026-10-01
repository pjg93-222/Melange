"""Verify retained official downloads and disclose changes to external source files."""
from pathlib import Path

from common import OUT, digest, log, read_json, stamp, write_json


def run():
    counts={};external=[]
    for label,rows in [('acs',read_json(OUT/'demographics_audit_v2.json')['sources']),
         ('introduced_xml',[read_json(p) for p in (OUT/'introduced_xml').glob('*.json')])]:
        seen=set()
        for r in rows:
            if not r.get('sha256'):continue
            path=Path(r['path'])
            if path in seen:continue
            assert digest(path)==r['sha256'],f'Frozen source changed: {path}'
            seen.add(path)
        counts[label]=len(seen)
    for r in read_json(OUT/'external_context_receipt.json')['source_receipts']:
        path=Path(r['path']);current=digest(path) if path.exists() else None
        external.append(dict(path=str(path),frozen_expected_sha256=r['sha256'],current_sha256=current,unchanged=current==r['sha256']))
    write_json(OUT/'raw_source_verification.json',dict(verified_utc=stamp(),retained_official_sources='passed',counts=counts,
        external_current_status=external,note='Historical derived matrices remain frozen even if a separately owned external generation is subsequently replaced.'))
    log(f'Official raw-source hashes verified: {counts}')


if __name__=='__main__':run()
