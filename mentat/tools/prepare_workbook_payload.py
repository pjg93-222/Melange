"""Project large payloads onto the exact raw fields used by formula-fact Excel views.

The complete enriched source remains unchanged. All analytical arrays, excluded
cycle rows, and the original source hash remain available for audit.
"""
import argparse
import hashlib
import json
from pathlib import Path
from fec_transfer_graph import atomic_json

RAW_FIELDS = frozenset(('cycle','cycle_label','source_cycle','source_id','company',
    'company_match_status','include_in_analysis','amount','employee_tier','party',
    'recipient_category','person_key','contributor','recipient_key','recipient',
    'committee_id','category_source','party_source'))
ENRICHMENT_ONLY = ('candidate_master','candidate_committee_links','transfer_edges')


def project(payload):
    payload['raw_rows']=[{key:value for key,value in row.items() if key in RAW_FIELDS}
                         for row in payload['raw_rows']]
    for key in ENRICHMENT_ONLY:payload.pop(key,None)
    payload['metadata']['workbook_projection']='formula-facts-v1'
    return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.source.resolve()==args.output.resolve():raise ValueError('Keep the full source payload unchanged')
    with args.source.open('rb') as stream:signature=hashlib.file_digest(stream,'sha256').hexdigest()
    value=project(json.loads(args.source.read_text(encoding='utf-8-sig')))
    value['metadata'].update(full_payload_path=str(args.source.resolve()),full_payload_sha256=signature)
    atomic_json(args.output,value)
    if args.output.stat().st_size>=480*1024*1024:
        raise ValueError('Workbook projection still exceeds the safe JSON size; build individual cycles')
    print(f'Workbook payload: {args.source.stat().st_size:,} -> {args.output.stat().st_size:,} bytes; full source preserved',flush=True)


if __name__=='__main__':main()
