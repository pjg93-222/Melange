"""Second opinion on a bundle: validate it (schema + cross-field invariants) with the contract's own Python validator (contracts/contract.py) and apply every shared
negative control of target 'models'. Verification tool only (the pipeline itself is R).
usage: python check_bundle_contract.py <giving-models-v2.json> [<contracts dir>]   exit 0 = valid and every control rejected
"""
import json
import sys
from pathlib import Path

bundle = Path(sys.argv[1])
contracts = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[2] / 'contracts'
sys.path.insert(0, str(contracts))
import contract  # noqa: E402

doc = json.loads(bundle.read_text(encoding='utf-8'))
schema = contract.schema('models')
problems = contract.validate(doc, schema) or contract.check_model_invariants(doc)
print('problems:', len(problems))
for p in problems[:10]:
    print('  ', p)
accepted = []
for control in contract.negative_controls():
    if control['target'] != 'models':
        continue
    mutated = contract.apply_mutation(doc, control)
    if not (contract.validate(mutated, schema) or contract.check_model_invariants(mutated)):
        accepted.append(control['id'])
print('negative controls accepted (must be none):', accepted)
sys.exit(0 if not problems and not accepted else 1)
