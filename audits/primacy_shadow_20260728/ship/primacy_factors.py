#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRIMACY FACTORS — producer for the Legislative+Press display tier.

Reads  : member_desk_bundle.json          (act universe, 614 keys / 533 members)
         bill_beneficiary_tags.ndjson     (one row per act: class + authority + rationale)
         acu_legislation_search_registry.json  (acu_position — authoritative for OPPOSE)
Writes : primacy_factors.json             (per-member factor_raw / factor_shrunk / mix)

Pure. No network. Chain-independent. Recomputes nothing upstream: ranks_python.json is
read-only and MUST remain byte-identical (zero rank delta is the acceptance test).

Spec: audits/primacy_shadow_20260728/PRIMACY_IMPLEMENTATION_SPEC_2026-07-28.md
"""
from __future__ import annotations
import json, os, re, collections

# ---- ratified constants -----------------------------------------------------
ROLE_W = {'sponsor': 1.0, 'original': 0.5, 'cosponsor': 0.25}   # unknown role -> 0.25
ACT_W = {
    'cu_primary':     1.00,
    'shared':         0.50,   # sits at the roster baseline: the neutral bucket by construction
    'bank_primary':   0.15,
    'crypto_primary': 0.15,
    'fintech':        0.15,
    'offtopic':       0.00,
    'oppose':        -1.00,   # registry acu_position == OPPOSE; symmetric with cu_primary
}
LETTER_W      = float(os.environ.get('PRIMACY_LETTER_W', '0.60'))  # ACU advocacy letters (calibrated)
SHRINK_ANCHOR = float(os.environ.get('PRIMACY_SHRINK', '15.0'))    # empirical-Bayes anchor on agenda credit
DEFAULT_ROLE_W = 0.25


def load_tags(path):
    """{(bill, congress): {'class':..., 'act_weight':...}} from bill_beneficiary_tags.ndjson."""
    out = {}
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            out['%s|%s' % (str(r['bill']).strip(), str(r['congress']).strip())] = r
    if not out:
        raise ValueError('beneficiary tag file is empty; refusing to score an unclassified universe')
    return out


def is_letter(bill_key):
    return bill_key.split('|')[0].startswith('LTR-')


def act_weight(tag, bill_key):
    """Letters are their own class; otherwise the beneficiary class decides."""
    if is_letter(bill_key):
        return LETTER_W
    cls = tag['class']
    if cls not in ACT_W:
        raise ValueError('unknown beneficiary class %r on %s' % (cls, bill_key))
    return ACT_W[cls]


def compute(bundle, tags):
    """Returns (members, roster_baseline). members[name] = factor_raw / agenda_credit / mix."""
    mem = {}
    for rec in bundle['members']:
        num = den = 0.0
        mix = collections.defaultdict(float)
        for b in (rec.get('bills') or []):
            key = '%s|%s' % (str(b.get('bill') or '').strip(), str(b.get('congress') or '').strip())
            tag = tags.get(key)
            if tag is None:
                raise KeyError('act %s is in the bundle but not in the tag file — '
                               'classification and universe are out of sync' % key)
            rw = ROLE_W.get(b.get('role'), DEFAULT_ROLE_W)
            w = act_weight(tag, key)
            den += rw
            num += rw * w
            mix['letter' if is_letter(key) else tag['class']] += rw
        mem[rec['name']] = {
            'factor_raw': (num / den) if den else 1.0,   # no file -> neutral, then shrunk to baseline
            'agenda_credit': round(den, 3),
            'mix': {k: round(v, 2) for k, v in mix.items()},
        }
    tot = sum(v['agenda_credit'] for v in mem.values())
    if tot <= 0:
        raise ValueError('roster has zero total agenda credit')
    baseline = sum(v['factor_raw'] * v['agenda_credit'] for v in mem.values()) / tot
    for v in mem.values():
        lam = min(1.0, v['agenda_credit'] / SHRINK_ANCHOR)
        v['lambda'] = round(lam, 6)
        v['factor_shrunk'] = baseline + lam * (v['factor_raw'] - baseline)
    return mem, baseline


def main(root='.'):
    p = lambda *a: os.path.join(root, *a)
    bundle = json.load(open(p('member_desk_bundle.json'), encoding='utf-8'))
    tags = load_tags(p('bill_beneficiary_tags.ndjson'))
    mem, baseline = compute(bundle, tags)
    doc = {
        '_doc': 'Primacy factors for the Legislative+Press display tier. Producer: fec/primacy_factors.py',
        '_constants': {'role_weights': ROLE_W, 'act_weights': ACT_W, 'letter_weight': LETTER_W,
                       'shrink_anchor': SHRINK_ANCHOR, 'roster_baseline': round(baseline, 6)},
        'members': {k: {kk: (round(vv, 6) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                    for k, v in sorted(mem.items())},
    }
    try:
        from moneyball_core import dump_atomic
        dump_atomic(doc, p('primacy_factors.json'))
    except Exception:
        with open(p('primacy_factors.json'), 'w', encoding='utf-8') as fh:
            json.dump(doc, fh, indent=1)
    print('primacy_factors: %d members | baseline %.6f | letter_w %.2f | shrink %.1f'
          % (len(mem), baseline, LETTER_W, SHRINK_ANCHOR))
    return doc


if __name__ == '__main__':
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
