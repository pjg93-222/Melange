"""Exercise the new negative controls against the proposed committed modules."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
for name in ('staffer_payroll_identity', 'staffer_identity_auto', 'staffer_routing', 'staffer_overlap_routes', 'staffer_live_service'):
    qualified = 'fec.surfaces.' + name
    spec = importlib.util.spec_from_file_location(qualified, OUT / 'commit_shadow/fec/surfaces' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    import fec.surfaces
    setattr(fec.surfaces, name, module)
import pytest
raise SystemExit(pytest.main([str(ROOT / 'fec/tests/surfaces/test_staffer_evidence_boundaries.py'), '-q']))
