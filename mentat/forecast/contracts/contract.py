"""The shared contract for the Giving Forecast (brain DE-021: one schema + one fixture set, asserted against every producer).

Two documents cross a lane boundary:

* giving-models-v2   written by the R refit pipeline (mentat/forecast/refit), read by mentat/app/giving_forecast.py
* giving-anchors-v1  written by mentat/forecast/anchors (Python, read-only over Mentat), read by mentat/app/giving_forecast.py

This module is the Python side of the contract: the schema loader, a validator for the JSON Schema keyword subset the two
schemas use (see README.md; the R pipeline implements the same subset by hand, because no JSON Schema package is installed
there or here), the shared negative controls, and the cross-field invariants of the anchor snapshot that a schema cannot say.

Nothing here touches Mentat's data or accounting code.
"""
from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

CONTRACT_DIR = Path(__file__).resolve().parent
SCHEMAS = {'models': 'giving-models-v2.schema.json', 'anchors': 'giving-anchors-v1.schema.json'}
EXAMPLES = {'models': 'giving-models-v2.example.json', 'anchors': 'giving-anchors-v1.example.json'}
NEGATIVES = 'negative-controls.json'

SUPPORTED_KEYWORDS = {
    '$schema', '$id', '$defs', '$ref', 'title', 'description', 'type', 'enum', 'const', 'properties', 'required',
    'additionalProperties', 'propertyNames', 'minProperties', 'items', 'minItems', 'minimum', 'maximum', 'exclusiveMinimum',
    'minLength', 'pattern',
}


def read_json(path):
    with Path(path).open(encoding='utf-8-sig') as stream:
        return json.load(stream)


def schema(kind):
    return read_json(CONTRACT_DIR / SCHEMAS[kind])


def example(kind):
    return read_json(CONTRACT_DIR / EXAMPLES[kind])


def negative_controls():
    return read_json(CONTRACT_DIR / NEGATIVES)['controls']


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_integer(value):
    return (isinstance(value, int) and not isinstance(value, bool)) or (isinstance(value, float) and math.isfinite(value) and value.is_integer())


_TYPES = {
    'object': lambda v: isinstance(v, dict),
    'array': lambda v: isinstance(v, list),
    'string': lambda v: isinstance(v, str),
    'boolean': lambda v: isinstance(v, bool),
    'null': lambda v: v is None,
    'number': lambda v: _is_number(v) and math.isfinite(v),
    'integer': _is_integer,
}


def _resolve(ref, root):
    if not ref.startswith('#/$defs/'):
        raise ValueError('Only local $defs references are supported: ' + ref)
    return root['$defs'][ref[len('#/$defs/'):]]


def _check(value, node, root, path, errors):
    if '$ref' in node:
        _check(value, _resolve(node['$ref'], root), root, path, errors)
        return
    unknown = set(node) - SUPPORTED_KEYWORDS
    if unknown:
        raise ValueError('Schema keyword outside the supported subset at ' + (path or '$') + ': ' + ', '.join(sorted(unknown)))
    where = path or '$'
    if 'type' in node:
        wanted = node['type'] if isinstance(node['type'], list) else [node['type']]
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(where + ': non-finite number')
            return
        if not any(_TYPES[t](value) for t in wanted):
            errors.append(where + ': expected ' + '/'.join(wanted) + ', got ' + type(value).__name__)
            return
    if 'const' in node and not (value == node['const'] and type(value) is type(node['const'])):
        errors.append(where + ': must equal ' + json.dumps(node['const']))
    if 'enum' in node and value not in node['enum']:
        errors.append(where + ': must be one of ' + json.dumps(node['enum']))
    if isinstance(value, str):
        if 'pattern' in node and not re.search(node['pattern'], value):
            errors.append(where + ': does not match ' + node['pattern'])
        if 'minLength' in node and len(value) < node['minLength']:
            errors.append(where + ': shorter than ' + str(node['minLength']))
    if _is_number(value) and math.isfinite(value):
        if 'minimum' in node and value < node['minimum']:
            errors.append(where + ': below ' + str(node['minimum']))
        if 'maximum' in node and value > node['maximum']:
            errors.append(where + ': above ' + str(node['maximum']))
        if 'exclusiveMinimum' in node and value <= node['exclusiveMinimum']:
            errors.append(where + ': not above ' + str(node['exclusiveMinimum']))
    if isinstance(value, dict):
        props = node.get('properties', {})
        for key in node.get('required', []):
            if key not in value:
                errors.append(where + ': missing required "' + key + '"')
        extra = node.get('additionalProperties', True)
        if 'minProperties' in node and len(value) < node['minProperties']:
            errors.append(where + ': fewer than ' + str(node['minProperties']) + ' entries')
        names = node.get('propertyNames', {}).get('pattern')
        for key, item in value.items():
            child = (path + '.' if path else '$.') + key
            if names and not re.search(names, key):
                errors.append(child + ': key does not match ' + names)
            if key in props:
                _check(item, props[key], root, child, errors)
            elif extra is False:
                errors.append(child + ': unexpected property')
            elif isinstance(extra, dict):
                _check(item, extra, root, child, errors)
    if isinstance(value, list):
        if 'minItems' in node and len(value) < node['minItems']:
            errors.append(where + ': fewer than ' + str(node['minItems']) + ' items')
        if 'items' in node:
            for index, item in enumerate(value):
                _check(item, node['items'], root, where + '[' + str(index) + ']', errors)


def validate(instance, doc):
    """Problems of `instance` against schema `doc` (a loaded schema document); empty list = valid."""
    errors = []
    _check(instance, doc, doc, '', errors)
    return errors


def validate_kind(instance, kind):
    return validate(instance, schema(kind))


# --- shared negative controls -------------------------------------------------------------------------------------------
NONFINITE = {'NaN': float('nan'), 'Infinity': float('inf'), '-Infinity': float('-inf')}


def _walk(doc, steps):
    node = doc
    for step in steps:
        node = node[step]
    return node


def apply_mutation(document, mutation):
    """Apply one negative-control mutation to a deep copy. ops: delete, set, add_key. A value {"$nonfinite": "NaN"} means a
    non-finite number (JSON cannot carry one; each language substitutes its own NaN / Inf)."""
    out = copy.deepcopy(document)
    path = mutation['path']
    parent = _walk(out, path[:-1])
    key = path[-1]
    op = mutation['op']
    if op == 'delete':
        del parent[key]
        return out
    value = copy.deepcopy(mutation.get('value'))
    if isinstance(value, dict) and set(value) == {'$nonfinite'}:
        value = NONFINITE[value['$nonfinite']]
    parent[key] = value
    return out


# --- anchor snapshot invariants (cross-field rules a schema cannot express) ----------------------------------------------
def _sum_dr(block):
    return sum(block[k] for k in ('D', 'R', 'other'))


def check_anchor_invariants(snapshot, tolerance=0.011):
    """Cross-field rules of a schema-valid anchor snapshot. Returns a list of problems (empty = consistent)."""
    problems = []
    threshold = snapshot['thin_base_threshold_usd']
    for ident, ind in snapshot['industries'].items():
        tag = 'industries.' + ident
        cov = ind['coverage']
        if cov['coverage_end'] > cov['rule_coverage_end']:
            problems.append(tag + '.coverage: coverage_end is later than the rule coverage end')
        if cov['coverage_end'] > cov['collection_date']:
            problems.append(tag + '.coverage: coverage_end is after the collection date')
        for measure in ('general_giving', 'candidate_receipts', 'pac_to_candidates'):
            block = ind[measure]
            if block['status'] != ind['status'][measure]:
                problems.append(tag + '.' + measure + ': status differs from the industry status map')
            cuts = block.get('observed', [])
            if block['status'] == 'ready' and not cuts:
                problems.append(tag + '.' + measure + ': ready without observed cuts')
            dates = [c['through'] for c in cuts]
            if dates != sorted(dates) or len(set(dates)) != len(dates):
                problems.append(tag + '.' + measure + '.observed: cut dates must be strictly increasing')
            if dates and dates[-1] != cov['coverage_end']:
                problems.append(tag + '.' + measure + '.observed: the last cut must be the coverage end')
            if any(not re.search(r'-(01|02|03|04|05|06|07|08|09|10|11|12)-\d\d$', d) for d in dates):
                problems.append(tag + '.' + measure + '.observed: malformed cut date')
        pac = ind['pac_to_candidates']
        if pac['committee_count'] != len(pac['committees']):
            problems.append(tag + '.pac_to_candidates: committee_count differs from the committee list')
        if pac['single_pac'] != (pac['committee_count'] == 1):
            problems.append(tag + '.pac_to_candidates: single_pac must be true exactly when one committee is listed')
        for cyc, row in pac['cycles'].items():
            hs = _sum_dr(row['House']) + _sum_dr(row['Senate'])
            if abs(hs - row['to_house_senate']) > tolerance:
                problems.append(tag + '.pac_to_candidates.cycles.' + cyc + ': to_house_senate differs from the House + Senate parts')
            if abs(row['to_house_senate'] + row['presidential'] + row['no_candidate'] - row['all_recipients']) > tolerance:
                problems.append(tag + '.pac_to_candidates.cycles.' + cyc + ': all_recipients differs from its parts')
        for cut in pac['observed']:
            hs = _sum_dr(cut['House']) + _sum_dr(cut['Senate'])
            if abs(hs - cut['to_house_senate']) > tolerance:
                problems.append(tag + '.pac_to_candidates.observed ' + cut['through'] + ': to_house_senate differs from its parts')
        for label, block in (('candidate_receipts', ind['candidate_receipts']), ('pac_to_candidates', pac)):
            for cyc, flags in block['thin_base'].items():
                for chamber in ('House', 'Senate'):
                    row = block['cycles'].get(cyc, {}).get(chamber)
                    if row is None:
                        problems.append(tag + '.' + label + '.thin_base.' + cyc + ': no cycle row')
                        continue
                    expected = (row['D'] + row['R']) < threshold
                    if flags[chamber] != expected:
                        problems.append(tag + '.' + label + '.thin_base.' + cyc + '.' + chamber + ': flag disagrees with the D+R total and the threshold')
        lda = ind['lda']
        if lda['status'] == 'ready':
            for sid, series in lda['series'].items():
                partial = series['partial']
                if partial is not None and abs(sum(partial['quarters'].values()) - partial['total']) > tolerance:
                    problems.append(tag + '.lda.series.' + sid + ': partial total differs from its quarters')
                if partial is not None and str(partial['year']) in series['annual']:
                    problems.append(tag + '.lda.series.' + sid + ': a partial year must not also be listed as a complete annual value')
    return problems
