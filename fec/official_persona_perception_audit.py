# -*- coding: utf-8 -*-
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from paths import ROOT as MB_ROOT
"""Freeze and score the 2026-07-13 official-persona external-perception audit.

The freeze step selects a deterministic random 30-House/10-Senate batch and stores the current
display predictions before any external evidence is coded. The score step compares only clearly
directional model claims with independently sourced professional-persona descriptions. This is a
descriptive corroboration audit, never a psychometric validation or an engine input.
"""
import argparse, hashlib, json, math, os, sys
from urllib.parse import urlparse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from moneyball_core import dump_atomic

SEED = 'official-persona-perception-audit-v1|20260713'
TRAITS = ('E', 'O', 'C', 'A', 'N')
BEHAVIOR = ('cooperation', 'follow_through', 'dominance', 'activity', 'breadth')
BUNDLE = os.path.join(MB_ROOT, 'member_desk_bundle.json')
PREREG = os.path.join(MB_ROOT, 'official_persona_perception_audit_prereg.md')
FROZEN = os.path.join(MB_ROOT, 'official_persona_perception_batch_v1.json.candidate')
EVIDENCE = os.path.join(MB_ROOT, 'official_persona_perception_evidence_v1.json.candidate')
RESULT = os.path.join(MB_ROOT, 'official_persona_perception_result_v1.json.candidate')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def lottery_hash(chamber, name):
    return hashlib.sha256(('%s|%s|%s' % (SEED, chamber, name)).encode('utf-8')).hexdigest().upper()


def locked_prereg(require_unspent=False):
    if not os.path.exists(PREREG):
        raise RuntimeError('prereg absent')
    text = open(PREREG, encoding='utf-8').read()
    if 'STATUS: LOCKED' not in text:
        raise RuntimeError('prereg not LOCKED')
    if require_unspent and '\n## RESULT-PERCEPTION' in text:
        raise RuntimeError('RESULT-PERCEPTION already recorded; one look is spent')


def selected_rows(bundle):
    members = bundle.get('members') or []
    house = sorted((m for m in members if m.get('chamber') == 'House'),
                   key=lambda m: lottery_hash('House', m['name']))
    senate = sorted((m for m in members if m.get('chamber') == 'Senate'),
                    key=lambda m: lottery_hash('Senate', m['name']))
    if len(house) != 433 or len(senate) != 100:
        raise RuntimeError('pinned roster mismatch: House=%d Senate=%d' % (len(house), len(senate)))
    return house[:30] + senate[:10]


def freeze(out_path):
    locked_prereg()
    bundle = json.load(open(BUNDLE, encoding='utf-8'))
    rows = selected_rows(bundle)
    sample = []
    for m in rows:
        psy = m.get('psy') or {}
        big5 = psy.get('big5_pct') or []
        beh = psy.get('behav_pct') or []
        if len(big5) != 5:
            raise RuntimeError('%s has no five-axis Big Five display' % m['name'])
        comm = psy.get('communication_style') or {}
        sample.append({
            'name': m['name'], 'chamber': m['chamber'], 'party': m.get('party'),
            'state': m.get('state'), 'lottery_hash': lottery_hash(m['chamber'], m['name']),
            'model': {
                'big5_EOCAN': dict(zip(TRAITS, big5)),
                'behavior': dict(zip(BEHAVIOR, beh)) if len(beh) == 5 else {},
                'communication_facets': comm.get('facets') or {},
                'e_scope': psy.get('e_public_proxy_scope'),
            },
        })
    sample_fingerprint = hashlib.sha256('\n'.join(
        '%s|%s|%s' % (r['chamber'], r['name'], r['lottery_hash']) for r in sample
    ).encode('utf-8')).hexdigest().upper()
    doc = {
        'schema': 'official-persona-perception-batch-v1',
        'status': 'FROZEN_BLIND_PRE_EVIDENCE',
        'seed': SEED,
        'sample_method': 'smallest SHA-256 lottery hashes within chamber; no replacement',
        'sample_n': len(sample), 'house_n': 30, 'senate_n': 10,
        'source_bundle_sha256': sha256(BUNDLE),
        'sample_fingerprint': sample_fingerprint,
        'model_claim_thresholds': {'low_max': 0.30, 'high_min': 0.70},
        'sample': sample,
    }
    dump_atomic(doc, out_path, indent=1)
    print('%s: frozen 30 House + 10 Senate; model values sealed for blind evidence coding' % os.path.basename(out_path))


def wilson(successes, n, z=1.959963984540054):
    if not n:
        return [None, None]
    p = successes / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    return [round(center - half, 4), round(center + half, 4)]


def domain(url):
    return (urlparse(url).hostname or '').lower().removeprefix('www.')


def validate_evidence(doc, frozen):
    if doc.get('schema') != 'official-persona-perception-evidence-v1':
        raise RuntimeError('evidence schema mismatch')
    if doc.get('coding_status') != 'FROZEN_BEFORE_MODEL_UNBLINDING':
        raise RuntimeError('evidence was not frozen under the blind-coding contract')
    expected = {r['name'] for r in frozen['sample']}
    got = set((doc.get('members') or {}).keys())
    if got != expected:
        raise RuntimeError('evidence member set mismatch: missing=%s extra=%s' %
                           (sorted(expected - got), sorted(got - expected)))
    errors = []
    for name, row in doc['members'].items():
        sources = row.get('sources') or []
        ids = {s.get('id') for s in sources}
        domains = {domain(s.get('url') or '') for s in sources if domain(s.get('url') or '')}
        if len(sources) < 2 or len(domains) < 2 or not any(s.get('independent') is True for s in sources):
            errors.append('%s source floor' % name)
        for trait, coded in (row.get('traits') or {}).items():
            if trait not in TRAITS or coded.get('direction') not in (-1, 0, 1):
                errors.append('%s malformed %s' % (name, trait)); continue
            refs = coded.get('source_ids') or []
            if coded.get('direction') and (not refs or any(x not in ids for x in refs)):
                errors.append('%s unsupported %s' % (name, trait)); continue
            if coded.get('direction'):
                support = [s for s in sources if s.get('id') in refs]
                if not any(s.get('independent') is True for s in support):
                    errors.append('%s %s lacks independent support' % (name, trait))
    if errors:
        raise RuntimeError('evidence contract errors: ' + '; '.join(errors[:12]))


def score(evidence_path, frozen_path, out_path):
    locked_prereg(require_unspent=True)
    frozen = json.load(open(frozen_path, encoding='utf-8'))
    if frozen.get('source_bundle_sha256') != '33F0C4305F07FCA24AEF3098FEB47633E1AEC3FD7880617D5FE7180EA367147A':
        raise RuntimeError('frozen bundle fingerprint differs from prereg')
    evidence = json.load(open(evidence_path, encoding='utf-8'))
    validate_evidence(evidence, frozen)
    by_name = evidence['members']
    per_trait = {t: {'agree': 0, 'disagree': 0, 'evaluable': 0} for t in TRAITS}
    people = {}
    all_hits = []
    for row in frozen['sample']:
        name = row['name']; coded = (by_name[name].get('traits') or {})
        comparisons = []
        for trait in TRAITS:
            value = (row['model']['big5_EOCAN'] or {}).get(trait)
            external = (coded.get(trait) or {}).get('direction', 0)
            model_dir = 1 if value is not None and value >= .70 else (-1 if value is not None and value <= .30 else 0)
            if not model_dir or not external:
                continue
            agree = model_dir == external
            comparisons.append({'trait': trait, 'model_percentile': value,
                                'model_direction': model_dir, 'external_direction': external,
                                'agree': agree, 'basis': coded[trait].get('basis'),
                                'source_ids': coded[trait].get('source_ids') or []})
            per_trait[trait]['evaluable'] += 1
            per_trait[trait]['agree' if agree else 'disagree'] += 1
            all_hits.append(1 if agree else 0)
        a = sum(c['agree'] for c in comparisons); d = len(comparisons) - a
        verdict = 'thin_external_overlap'
        if len(comparisons) >= 2:
            verdict = 'match' if a > d else ('mismatch' if d > a else 'mixed')
        people[name] = {'chamber': row['chamber'], 'party': row.get('party'),
                        'evaluable': len(comparisons), 'agree': a, 'disagree': d,
                        'agreement_rate': round(a / len(comparisons), 4) if comparisons else None,
                        'verdict': verdict, 'comparisons': comparisons,
                        'sources': by_name[name].get('sources') or [],
                        'external_summary': by_name[name].get('external_summary')}
    evaluable_people = [p for p in people.values() if p['evaluable']]
    macro = sum(p['agreement_rate'] for p in evaluable_people) / len(evaluable_people) if evaluable_people else 0.0
    micro = sum(all_hits) / len(all_hits) if all_hits else 0.0
    decided = [p for p in people.values() if p['verdict'] in ('match', 'mixed', 'mismatch')]
    mismatches = sum(p['verdict'] == 'mismatch' for p in decided)
    mismatch_rate = mismatches / len(decided) if decided else 1.0
    trait_alert = any(v['evaluable'] >= 6 and v['agree'] / v['evaluable'] < .50 for v in per_trait.values())
    if len(all_hits) < 30 or len(evaluable_people) < 25:
        verdict = 'INSUFFICIENT EXTERNAL EVIDENCE'
    elif macro >= .65 and micro >= .65 and mismatch_rate <= .25 and not trait_alert:
        verdict = 'CHECKS OUT DESCRIPTIVELY'
    elif macro < .50 or micro < .50 or mismatch_rate > .40:
        verdict = 'DOES NOT CHECK OUT'
    else:
        verdict = 'MIXED'
    for t, v in per_trait.items():
        v['agreement_rate'] = round(v['agree'] / v['evaluable'], 4) if v['evaluable'] else None
        v['wilson_95'] = wilson(v['agree'], v['evaluable'])
    result = {
        'schema': 'official-persona-perception-result-v1',
        'status': 'ONE_LOOK_CONSUMED_PENDING_PREREG_RECORD',
        'verdict': verdict,
        'scope': 'descriptive external-perception corroboration; not psychometric validation',
        'input_fingerprints': {'frozen_sha256': sha256(frozen_path),
                               'evidence_sha256': sha256(evidence_path)},
        'coverage': {'sample_n': 40, 'evaluable_member_n': len(evaluable_people),
                     'evaluable_claim_n': len(all_hits), 'decided_member_n': len(decided)},
        'overall': {'micro_agreement': round(micro, 4),
                    'micro_wilson_95': wilson(sum(all_hits), len(all_hits)),
                    'member_macro_agreement': round(macro, 4),
                    'member_mismatch_rate': round(mismatch_rate, 4)},
        'per_trait': per_trait, 'members': people,
        'limitations': [
            'external descriptions are selective public narratives, not self-report or informant ratings',
            'the E slot is role-adjusted public exposure, not intrinsic Extraversion',
            'middle 30th-70th percentile model values make no directional claim and are not scored',
            'source-sparse members are never replaced',
        ],
    }
    dump_atomic(result, out_path, indent=1)
    print('%s: %s; %d claims across %d members; micro %.3f macro %.3f' %
          (os.path.basename(out_path), verdict, len(all_hits), len(evaluable_people), micro, macro))


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--freeze', action='store_true')
    g.add_argument('--score', action='store_true')
    ap.add_argument('--frozen', default=FROZEN)
    ap.add_argument('--evidence', default=EVIDENCE)
    ap.add_argument('--out')
    args = ap.parse_args()
    if args.freeze:
        freeze(args.out or args.frozen)
    else:
        score(args.evidence, args.frozen, args.out or RESULT)


if __name__ == '__main__':
    main()
