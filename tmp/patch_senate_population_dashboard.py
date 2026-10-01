from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
FEC = ROOT / "fec"
if str(FEC) not in sys.path:
    sys.path.insert(0, str(FEC))

import dashboard_integrity as DI
import district.demographic_normalization as DN
import moneyball_core as MC
from run_pipeline import pipeline_run_lock
from legislation.update_bill_repository import _atomic_copy


DEMO_AXES = (
    "income",
    "pct_finance",
    "pct_ownerocc_mort",
    "pct_costburden",
    "establishments",
    "constituents",
)
OUTPUTS = (
    "member_desk_bundle.json",
    "cu-member-desk.html",
    "dashboard_exclusion_reconciliation.json",
    "dashboard_integrity_report.json",
    "dashboard_integrity_state.json",
    "Moneyball.html",
)


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def patch_bundle(bundle):
    members = bundle["members"]
    adjusted = 0
    for member in members:
        demo = member.get("demo") or {}
        industry = member.get("industry") or {}
        basis = DN.senate_population_basis(
            demo.get("constituents"),
            member.get("chamber"),
            industry.get("geo"),
        )
        member["demo_population_normalization"] = basis
        adjusted += int(basis is not None)

    for key in DEMO_AXES:
        values = []
        for index, member in enumerate(members):
            value = (member.get("demo") or {}).get(key)
            if key == "constituents":
                basis = member.get("demo_population_normalization") or {}
                value = basis.get("normalization_population", value)
            if value is not None:
                values.append((index, value))
        ranks = DN.midrank_percentiles(values)
        axis = DEMO_AXES.index(key)
        for index, percentile in ranks.items():
            member = members[index]
            radar = list(member.get("demo_radar") or [0] * len(DEMO_AXES))
            radar[axis] = round(percentile, 3)
            member["demo_radar"] = radar

    bundle.setdefault("freshness", {})["generated_at"] = (
        datetime.now().astimezone().isoformat(timespec="seconds")
    )
    return adjusted


def main():
    bundle = load_json(ROOT / "member_desk_bundle.json")
    prior_report = load_json(ROOT / "dashboard_integrity_report.json")
    adjusted = patch_bundle(bundle)
    if adjusted != 100:
        raise RuntimeError(
            f"expected 100 senators with adjusted population, observed {adjusted}"
        )

    with tempfile.TemporaryDirectory(
        prefix=".senate-population-promotion-",
        dir=ROOT,
    ) as temporary:
        stage = Path(temporary)
        prior_desk_out = os.environ.get("DESK_OUT")
        os.environ["DESK_OUT"] = str(stage)
        try:
            validation = DI.postflight(
                bundle,
                prior_report.get("preflight") or {},
            )
        finally:
            if prior_desk_out is None:
                os.environ.pop("DESK_OUT", None)
            else:
                os.environ["DESK_OUT"] = prior_desk_out
        bundle.setdefault("integrity", {})["validation"] = validation

        MC.dump_atomic(
            bundle,
            stage / "member_desk_bundle.json",
            separators=(",", ":"),
            ensure_ascii=False,
        )
        template = (
            FEC / "templates" / "make_member_desk_00.tpl"
        ).read_text(encoding="utf-8")
        payload = MC.json_for_script(
            bundle,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        MC.write_text_atomic(
            template.replace("__BUNDLE__", payload),
            stage / "cu-member-desk.html",
        )
        shutil.copy2(
            ROOT / "Moneyball Dashboard.html",
            stage / "Moneyball Dashboard.html",
        )
        environment = {
            **os.environ,
            "MONEYBALL_ROOT": str(stage),
            "COMBINED_STALE_OK": "0",
        }
        subprocess.run(
            [sys.executable, str(FEC / "surfaces" / "make_combined.py")],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        missing = [name for name in OUTPUTS if not (stage / name).is_file()]
        if missing:
            raise RuntimeError("staged outputs missing: " + ", ".join(missing))

        backup = stage / ".prior"
        backup.mkdir()
        present = {name: (ROOT / name).is_file() for name in OUTPUTS}
        promoted = []
        with pipeline_run_lock():
            for name, exists in present.items():
                if exists:
                    shutil.copy2(ROOT / name, backup / name)
            try:
                for name in OUTPUTS:
                    _atomic_copy(stage / name, ROOT / name)
                    promoted.append(name)
            except Exception:
                for name in reversed(promoted):
                    target = ROOT / name
                    if present[name]:
                        _atomic_copy(backup / name, target)
                    elif target.exists():
                        target.unlink()
                raise

    print(json.dumps({
        "status": "PASS",
        "senators_adjusted": adjusted,
        "integrity": validation["status"],
        "promoted": list(OUTPUTS),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
