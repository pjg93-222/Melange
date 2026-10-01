"""Freeze a read-only source extraction for the isolated experiment."""
import argparse
from pathlib import Path
from .data import (ROOT, SOURCES, digest, extract_candidates, load_members, load_traits,
                   read_bills, write_json, write_ndjson)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="outputs/member_personal_relationships/20260910_pilot")
    parser.add_argument("--as-of",default="2026-09-10")
    parser.add_argument("--start",default="2024-09-10")
    args=parser.parse_args()
    out=ROOT/args.out
    out.mkdir(parents=True,exist_ok=True)
    print("Hashing source inputs",flush=True)
    before={p:digest(ROOT/p) for p in SOURCES}
    production={p:digest(ROOT/p) for p in ["ranks_python.json","member_references.json"] if (ROOT/p).exists()}
    print("Reading dated membership",flush=True)
    members,aliases,roster_audit=load_members(args.as_of)
    traits,trait_audit=load_traits(members)
    write_json(out/"members.json",members)
    write_json(out/"traits.json",traits)
    print(f"Extracting candidate statements for {len(members)} dated members",flush=True)
    events,coverage,speech_audit=extract_candidates(members,aliases,args.as_of,args.start)
    write_ndjson(out/"candidates.ndjson",events)
    write_ndjson(out/"coverage.ndjson",coverage)
    print(f"Reading all-topic bills; {len(events)} statement candidates retrieved",flush=True)
    bills,bill_audit=read_bills(members,args.as_of)
    write_ndjson(out/"bills.ndjson",bills)
    after={p:digest(ROOT/p) for p in SOURCES}
    manifest=dict(schema="member-personal-relationships-pilot-v1",as_of=args.as_of,start=args.start,
                  source_sha256=before,inputs_unchanged=before==after,production_sha256=production,
                  roster=roster_audit,personality=trait_audit,speeches=speech_audit,bills=bill_audit,
                  prediction_status="exploratory_unfitted",human_gold_labels=0,
                  relationship_validation="not_estimated",production_write=False)
    write_json(out/"source_manifest.json",manifest)
    write_ndjson(out/"sources.ndjson",[dict(path=p,sha256=h) for p,h in before.items()])
    write_json(out/"retrieval_review_sample.json",events[:60])
    manifest["frozen_artifact_sha256"]={p:digest(out/p) for p in
        ["members.json","traits.json","candidates.ndjson","coverage.ndjson","bills.ndjson"]}
    write_json(out/"source_manifest.json",manifest)
    print(manifest,flush=True)


if __name__=="__main__":
    main()
