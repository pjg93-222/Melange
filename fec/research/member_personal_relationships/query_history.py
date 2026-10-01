"""Inspect any roster dyad, including those not on the review shortlist."""
import argparse
import json
from .data import normalize
from .prepare_history import OUT
from .run_history import load_all,make_row,read_rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('actor');parser.add_argument('target');parser.add_argument('--bills',action='store_true')
    args=parser.parse_args();members,traits,ids,w=load_all()
    def resolve(value):
        exact=[a for a in ids if value==a or normalize(value)==normalize(members[a]['name'])]
        candidates=exact or [a for a in ids if normalize(value) in normalize(members[a]['name'])]
        if len(candidates)!=1:parser.error('Specify one member: '+', '.join(members[a]['name'] for a in candidates))
        return candidates[0]
    a,b=resolve(args.actor),resolve(args.target)
    if a==b:parser.error('Choose two different members')
    saved={(r['actor'],r['target']):r for r in read_rows(OUT/'relationships.ndjson')}
    result=saved.get((a,b)) or dict(make_row(ids.index(a),ids.index(b),ids,members,traits,w),friendship='unknown',hostility='unknown',dislike='unknown')
    if args.bills:
        result['shared_bill_list']=[dict(key=x['key'],title=x['title'],url=x['url'],actor_join=x['joins'][a],target_join=x['joins'][b]) for x in read_rows(OUT/'bills.ndjson') if a in x['joins'] and b in x['joins']]
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':main()
