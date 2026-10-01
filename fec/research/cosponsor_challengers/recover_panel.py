"""Recover metadata after a pandas allocation failure; never recompute feature rows."""
import collections
import csv
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from audit_data import OUT,ROOT,digest
from build_panel import (get_bills,get_members,term_at,service_end,label_window,CUTOFF,AGES,
                         FEATURES,BASE,ENHANCED,DYNAMIC,PUBLIC,META_COLUMNS,META_DTYPE,RECEIPTS)


def recover():
    bykey={b["key"]:b for b in get_bills()}
    members,_=get_members()
    mids=sorted(members)
    midcodes={mid:i for i,mid in enumerate(mids)}
    billkeys=sorted(k for k,b in bykey.items() if b["congress"]>=117 and b["finance_at_introduction"])
    billcodes={key:i for i,key in enumerate(billkeys)}
    scores={}
    source=Path(os.environ["LOCALAPPDATA"])/"Melange/lda_rebuild/derived/cosponsor_sc/cosponsor_scores.csv"
    scorehash=digest(source)
    with source.open(newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["candidate_configuration"]=="same_chamber_only" and r["congress"]=="119" and r["bill"].startswith(("HR ","S ")):
                kind,number=r["bill"].split()
                scores[(f"119:{kind.lower()}:{int(number)}",r["member"])]=float(r["predicted_probability"])
    assert digest(source)==scorehash
    path=OUT/"meta_119.recovered.raw"
    count=0
    with path.open("wb") as mf:
        selected=[bykey[k] for k in billkeys if k.startswith("119:")]
        for bi,b in enumerate(selected):
            sponsor=members.get(b["sponsor"])
            if sponsor is None:
                continue
            for age in AGES:
                day=b["intro"]+age
                if day>=min(CUTOFF,b["end_congress"]-1,b["enacted"]):
                    continue
                st=term_at(sponsor,day,b["chamber"]) or term_at(sponsor,b["intro"],b["chamber"])
                if not st:
                    continue
                joined={mid:d for mid,d in b["joins"].items() if d<day}
                group=billcodes[b["key"]]*len(AGES)+AGES.index(age)
                rows=[]
                for mid in mids:
                    if mid==b["sponsor"] or b["joins"].get(mid,10**9)<=day:
                        continue
                    person=members[mid]
                    term=term_at(person,day,b["chamber"])
                    if not term:
                        continue
                    obs_end=min(CUTOFF,b["end_congress"]-1,service_end(person,term)-1)
                    label=label_window(b["joins"].get(mid),day,obs_end)
                    if not label:
                        continue
                    rows.append((billcodes[b["key"]],midcodes[mid],group,day,age,label["mature"],label["y"],label["duration"],
                                 label["event"],int(term["party"]=="Democrat"),int(b["chamber"]=="Senate"),len(joined),
                                 scores.get((b["key"],mid),np.nan)))
                if rows:
                    np.asarray(rows,dtype=META_DTYPE).tofile(mf)
                    count+=len(rows)
            if (bi+1)%500==0:
                print("RECOVER",bi+1,count,flush=True)
    expected=(OUT/"X_119.f32").stat().st_size//(len(FEATURES)*4)
    assert count==expected,(count,expected)
    raw=np.memmap(path,dtype=META_DTYPE,mode="r")
    frame=pd.DataFrame({name:raw[name] for name in META_COLUMNS},copy=False)
    frame.to_parquet(OUT/"meta_119.parquet",index=False)
    splits={}
    for cg in (117,118,119):
        m=pd.read_parquet(OUT/f"meta_{cg}.parquet")
        splits[str(cg)]=dict(rows=len(m),mature_rows=int(m.mature.sum()),mature_events=int(m.y[m.mature==1].sum()),
                            bills=sum(key.startswith(str(cg)+":") for key in billkeys),features=len(FEATURES),
                            x_sha256=digest(OUT/f"X_{cg}.f32"),meta_sha256=digest(OUT/f"meta_{cg}.parquet"))
    (OUT/"feature_names.json").write_text(json.dumps(dict(base=BASE,enhanced=ENHANCED,dynamic=DYNAMIC,public=PUBLIC,all=FEATURES),indent=2))
    (OUT/"identifiers.json").write_text(json.dumps(dict(bills=billkeys,members=mids,member_names={m:members[m]["name"] for m in mids}),indent=2))
    audit=json.loads((OUT/"data_audit.json").read_text())
    for input in audit["sources"]:
        assert digest(input["path"])==input["sha256"],"Source changed since audit: "+input["path"]
    record=dict(splits=splits,sources=RECEIPTS+audit["sources"]+[dict(path=str(source),sha256=scorehash)],
                protocol_sha256=digest(Path(__file__).parent/"PROTOCOL.md"),build_script_sha256=digest(Path(__file__).parent/"build_panel.py"),
                cutoff="2026-09-03",ages=AGES,recovery="Initial 119 pandas consolidation exceeded available memory. Metadata reconstructed in the identical deterministic ordering; feature bytes retained unchanged. Builder changed to stream metadata for future reproduction.")
    (OUT/"panel_receipt.json").write_text(json.dumps(record,indent=2))
    print("RECOVERY COMPLETE",splits,flush=True)


if __name__=="__main__":
    recover()
