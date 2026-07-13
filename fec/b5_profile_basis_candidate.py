# -*- coding: utf-8 -*-
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from paths import ROOT as MB_ROOT
"""Build a display-only, construct-honest profile basis candidate (2026-07-13 user directive).

The promoted Blue E score is trained on visibility_z and is therefore a public-exposure proxy, not
an independent Extraversion measure.  This candidate never exposes that score as personality: it
keeps visibility under PUBLIC ROLE / EXPOSURE and emits Extraversion as explicitly unknown.  Audio
is admitted only from the separately verified v2 candidate artifact.  The output is consumed by
NOTHING until user-ratified promotion.

Usage:
  python b5_profile_basis_candidate.py --self-test
  python b5_profile_basis_candidate.py --out profile_basis_v2.json.candidate [--only "Name,..."]
"""
import argparse, hashlib, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from moneyball_core import dump_atomic

DEFAULT_OUT = os.path.join(MB_ROOT, 'profile_basis_v2.json.candidate')
AUDIO_CANDIDATE = os.path.join(MB_ROOT, 'b5_audio_descriptors_v2.json.candidate')


def _load(name, default=None):
    path = os.path.join(MB_ROOT, name)
    if not os.path.exists(path):
        return {} if default is None else default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def member_basis(name, blue, dispositions, roles, audio):
    """Return only constructs whose labels match their evidence source."""
    b = blue.get(name) or {}
    d = dispositions.get(name) or {}
    r = roles.get(name) or {}
    a = audio.get(name) or None
    return {
        'personality_facets': {
            # These remain current Blue reads, but every value carries its actual criterion scope.
            'Openness': {
                'z': b.get('O'),
                'scope': 'text read anchored to legislative issue breadth; not private curiosity',
            },
            'Conscientiousness': {
                'z': b.get('C'),
                'scope': 'text read anchored to legislative diligence; not general reliability',
            },
            'Agreeableness_low_antagonism': {
                'z': b.get('A'),
                'scope': 'low-antagonism interview language; not warmth or bipartisan cooperation',
            },
            'Neuroticism_affective_content': {
                'z': b.get('N'),
                'scope': 'negative-affect/stress language; not private vulnerability or diagnosis',
            },
            # Never substitute visibility, interview count, dominance, or expressiveness here.
            'Extraversion': {
                'z': None,
                'status': 'unknown_no_independent_measure',
                'scope': 'visibility and speaking-role measures are explicitly excluded',
            },
        },
        'public_role_exposure': {
            'visibility_z': d.get('visibility_z'),
            'meaning': 'observed public/media exposure and activity; not Extraversion',
        },
        'behavioral_record': {
            'cooperation_z': d.get('cooperation_z'),
            'breadth_z': d.get('breadth_z'),
            'diligence_z': d.get('diligence_z'),
        },
        'observed_conversation': {
            'dominance_z': r.get('dominance_v2'),
            'expressiveness_z': r.get('expressiveness_v2'),
            'meaning': 'venue-bound turn behavior; neither field is Extraversion',
        },
        'verified_audio_v2': a,
    }


def build(only=None):
    blue_doc = _load('big5_blue_validated.json')
    disp_doc = _load('behavioral_dispositions.json')
    # Consume the already-audited display bundle rather than becoming a new direct consumer of the
    # qualified roles study artifact.  audit_full proves this bundle is an exact display propagation.
    desk_doc = _load('member_desk_bundle.json')
    audio_doc = _load('b5_audio_descriptors_v2.json.candidate') if os.path.exists(AUDIO_CANDIDATE) else {}
    blue = blue_doc.get('traits') or {}
    dispositions = disp_doc.get('members') or {}
    desk_rows = desk_doc.get('members') if isinstance(desk_doc, dict) else desk_doc
    desk_rows = desk_rows if isinstance(desk_rows, list) else []
    roles = {}
    for row in desk_rows:
        psy = (row or {}).get('psy') or {}
        if (row or {}).get('name'):
            roles[row['name']] = {'dominance_v2': psy.get('dominance_v2_z'),
                                  'expressiveness_v2': psy.get('expressiveness_v2_z')}
    audio = audio_doc.get('members') or {}
    roster = sorted(set(blue) | set(dispositions) | set(roles))
    if only:
        wanted = {x.strip() for x in only.split(',') if x.strip()}
        roster = [m for m in roster if m in wanted]
    members = {m: member_basis(m, blue, dispositions, roles, audio) for m in roster}
    inputs = {}
    for name in ('big5_blue_validated.json', 'behavioral_dispositions.json', 'member_desk_bundle.json'):
        path = os.path.join(MB_ROOT, name)
        if os.path.exists(path):
            inputs[name] = _sha256(path)
    if os.path.exists(AUDIO_CANDIDATE):
        inputs[os.path.basename(AUDIO_CANDIDATE)] = _sha256(AUDIO_CANDIDATE)
    return {
        'schema': 'profile-basis-v2-candidate',
        'status': 'CANDIDATE_CONSUMED_BY_NOTHING_AWAITING_USER_RATIFICATION',
        'construct_contract': {
            'legacy_blue_E': 'retired from personality display because it predicts visibility_z',
            'visibility': 'public/media exposure and activity only',
            'Extraversion': 'unknown unless a future independent, role-controlled measure passes',
            'dominance': 'observed floor-holding/defense only',
            'expressiveness': 'observed turn elaboration only',
            'audio': 'direct delivery observations only; absent unless audio-v2 verification passes',
        },
        'inputs_sha256': inputs,
        'members': members,
    }


def self_test():
    row = member_basis(
        'Example',
        {'Example': {'O': 0.1, 'C': -0.2, 'E': 4.9, 'A': 0.3, 'N': -0.4}},
        {'Example': {'visibility_z': 3.2, 'breadth_z': 0.4}},
        {'Example': {'dominance_v2': 1.1, 'expressiveness_v2': -0.7}},
        {},
    )
    assert row['personality_facets']['Extraversion']['z'] is None
    assert row['personality_facets']['Extraversion']['status'] == 'unknown_no_independent_measure'
    assert row['public_role_exposure']['visibility_z'] == 3.2
    assert row['observed_conversation']['dominance_z'] == 1.1
    assert 'E' not in row['personality_facets']
    raw = json.dumps(row, sort_keys=True)
    assert '4.9' not in raw                       # legacy Blue E cannot leak into the payload
    assert row['verified_audio_v2'] is None       # missing candidate audio stays missing
    print('b5_profile_basis_candidate self-test: 7 passed, 0 FAILED')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--out', help='candidate output path; required for a real build')
    ap.add_argument('--only', help='comma-separated member names')
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.out:
        ap.error('--out is required; candidate builds never write implicitly')
    out = args.out if os.path.isabs(args.out) else os.path.join(MB_ROOT, args.out)
    doc = build(args.only)
    dump_atomic(doc, out, indent=1)
    print('%s: %d candidate profiles; Extraversion unknown; consumed by nothing' %
          (os.path.basename(out), len(doc['members'])))


if __name__ == '__main__':
    main()
