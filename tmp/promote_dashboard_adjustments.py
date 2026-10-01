from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
STAGE = (ROOT / "tmp" / "dashboard_adjustments_preview").resolve()
FEC = ROOT / "fec"
if str(FEC) not in sys.path:
    sys.path.insert(0, str(FEC))

from run_pipeline import pipeline_run_lock
from legislation.update_bill_repository import _atomic_copy


ARTIFACTS = (
    "category_stance.json",
    "dashboard_data.json",
    "bipartisan.json",
    "Moneyball Dashboard.html",
    "member_desk_bundle.json",
    "cu-member-desk.html",
    "dashboard_exclusion_reconciliation.json",
    "dashboard_integrity_report.json",
    "dashboard_integrity_state.json",
    "Moneyball.html",
)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main() -> None:
    if STAGE.parent != (ROOT / "tmp").resolve():
        raise RuntimeError("staging directory escaped the workspace")
    missing = [name for name in ARTIFACTS if not (STAGE / name).is_file()]
    if missing:
        raise RuntimeError("missing staged artifacts: " + ", ".join(missing))

    backup = STAGE / (
        ".prior_live_python_" + time.strftime("%Y%m%d_%H%M%S")
    )
    backup.mkdir()
    present = {
        name: (ROOT / name).is_file()
        for name in ARTIFACTS
    }
    promoted: list[str] = []
    with pipeline_run_lock():
        for name, exists in present.items():
            if exists:
                shutil.copy2(ROOT / name, backup / name)
        try:
            for name in ARTIFACTS:
                _atomic_copy(STAGE / name, ROOT / name)
                promoted.append(name)
        except Exception:
            for name in reversed(promoted):
                target = ROOT / name
                if present[name]:
                    _atomic_copy(backup / name, target)
                elif target.exists():
                    target.unlink()
            raise

    mismatched = [
        name for name in ARTIFACTS
        if digest(STAGE / name) != digest(ROOT / name)
    ]
    if mismatched:
        raise RuntimeError(
            "post-promotion hash mismatch: " + ", ".join(mismatched)
        )
    print(f"PROMOTED={len(promoted)}")
    print(f"BACKUP={backup}")


if __name__ == "__main__":
    main()
