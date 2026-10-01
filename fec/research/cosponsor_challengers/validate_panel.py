"""Independent structural and sampled event checks on the frozen research panel."""
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from audit_data import OUT,digest
from build_panel import FEATURES


def validate():
    ids=json.loads((OUT/"identifiers.json").read_text())
    receipt=json.loads((OUT/"panel_receipt.json").read_text())
    bill_data={}
    for line in (OUT/"bills.jsonl").open(encoding="utf-8"):
        b=json.loads(line)
        bill_data[b["key"]]=b
    assert len(bill_data)==61085, "Bill identity duplication or unexpected frozen audit size"
    results={}
    rng=np.random.default_rng(919)
    for cg in (117,118,119):
        meta=pd.read_parquet(OUT/f"meta_{cg}.parquet")
        x=np.memmap(OUT/f"X_{cg}.f32",dtype=np.float32,mode="r",shape=(len(meta),len(FEATURES)))
        assert (OUT/f"X_{cg}.f32").stat().st_size==len(meta)*len(FEATURES)*4
        assert digest(OUT/f"X_{cg}.f32")==receipt["splits"][str(cg)]["x_sha256"]
        assert digest(OUT/f"meta_{cg}.parquet")==receipt["splits"][str(cg)]["meta_sha256"]
        assert not meta.duplicated(["bill","member","day"]).any()
        for start in range(0,len(meta),100000):
            assert np.isfinite(x[start:start+100000]).all()
        assert meta.duration.between(1,30).all()
        assert (meta.y==meta.event).all()
        assert ((meta.mature==0)|(meta.event==1)|(meta.duration==30)).all()
        chosen=rng.choice(len(meta),min(2500,len(meta)),replace=False)
        for row in meta.iloc[chosen].itertuples(index=False):
            key,member=ids["bills"][row.bill],ids["members"][row.member]
            bill=bill_data[key]
            assert member!=bill["sponsor"]
            assert (bill["chamber"]=="Senate")==bool(row.senate)
            days=[dt.date.fromisoformat(c["date"]).toordinal() for c in bill["cosponsors"] if c["member"]==member]
            joined=min(days) if days else None
            assert joined is None or joined>row.day
            if row.mature:
                expected=int(joined is not None and row.day<joined<=row.day+30)
                assert row.y==expected,(key,member,row.day)
            prior_joins=len({c["member"] for c in bill["cosponsors"] if dt.date.fromisoformat(c["date"]).toordinal()<row.day})
            assert row.n_joined==prior_joins
        results[str(cg)]={"rows":len(meta),"sampled_event_checks":len(chosen),"all_features_finite":True,"unique_risk_rows":True,"source_and_matrix_hashes_match":True}
    (OUT/"panel_validation.json").write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2),flush=True)


if __name__=="__main__":
    validate()
