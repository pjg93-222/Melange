#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deliberately refresh the frozen 533-member primacy board fixture.

This script is intentionally not part of the normal pipeline. Run it only
after an authorized integration, then keep the resulting CSV under review so
ordinary surface rebuilds cannot bless an accidental board change.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import tier_util as TU
from paths import ROOT as ROOT_TEXT


ROOT = Path(ROOT_TEXT)
OUTPUT = (
    ROOT / 'fec' / 'tests' / 'fixtures'
    / 'FIXTURE_expected_board.csv'
)
FIELDS = (
    'slot', 'member', 'tier', 'score', 'leg_pct',
    'factor_raw', 'factor_shrunk', 'factor_ranked', 'lambda',
    'agenda_credit',
    'adjudicated_credit', 'adjudicated_score_credit',
    'adjudicated_events',
    'cu_primary_credit', 'letter_credit', 'oppose_credit',
    'score_order', 'gross_severity', 'delivered_credit',
    'net_severity', 'tier_ceiling', 'open_events',
    'delivery_events',
)


def load_json(name):
    with (ROOT / name).open(encoding='utf-8') as handle:
        return json.load(handle)


def number(value, places):
    if value is None or value == '':
        return ''
    return ('%%.%df' % places) % float(value)


def main():
    bundle = load_json('member_desk_bundle.json')
    ranks = load_json('ranks_python.json')
    factors_doc = load_json('data/engine/primacy_factors.json')
    # Mirror the live board's ranking basis: factor mode ranks on the
    # uncertainty-discounted factor_ranked; legxfactor ranks on factor_shrunk.
    rank_field = (
        'factor_ranked' if TU.PRIMACY_BOARD == 'factor'
        else 'factor_shrunk'
    )
    factors = {
        member: row.get(rank_field, row['factor_shrunk'])
        for member, row in factors_doc['members'].items()
    }
    names = [row['name'] for row in bundle['members']]
    scores = TU.primacy_scores(ranks.get('pcts') or {}, factors)
    score_order = sorted(
        [member for member in names if member in scores],
        key=lambda member: (-scores[member], member),
    )
    overrides = TU.load_tier_overrides()
    preliminary = TU.apply_tier_overrides(
        score_order,
        overrides,
        positions=TU.load_tier_positions(),
    )
    # Mirror legislative_press_tiers exactly: the evidence floor sits between
    # placements and the conduct ladder, factor-mode only.
    if TU.PRIMACY_BOARD == 'factor':
        preliminary = TU.apply_evidence_floor(
            preliminary,
            TU.load_primacy_cu_credit(str(ROOT)),
            exempt=set(overrides),
        )
    final, detail = TU.apply_conduct_ladder(
        preliminary,
        TU.load_open_breaches(str(ROOT)),
        TU.load_delivery_credit(str(ROOT)),
        buckets=TU.BUCKETS,
    )
    if len(final) != 533 or sorted(final) != sorted(names):
        raise RuntimeError(
            'refusing fixture update: board is not a 533-member permutation'
        )
    first, second, third = TU._cutoffs(TU.BUCKETS)
    score_positions = {
        member: index + 1
        for index, member in enumerate(score_order)
    }
    rows = []
    for index, member in enumerate(final):
        factor = factors_doc['members'][member]
        mix = factor.get('mix') or {}
        conduct = detail.get(member) or {}
        tier = (
            1 if index < first else
            2 if index < second else
            3 if index < third else 0
        )
        rows.append({
            'slot': index + 1,
            'member': member,
            'tier': tier,
            'score': number(scores[member], 9),
            'leg_pct': number(ranks['pcts'][member]['leg'], 9),
            'factor_raw': number(factor['factor_raw'], 9),
            'factor_shrunk': number(factor['factor_shrunk'], 9),
            'factor_ranked': number(
                factor.get('factor_ranked', factor['factor_shrunk']), 9
            ),
            'lambda': number(factor['lambda'], 6),
            'agenda_credit': number(factor['agenda_credit'], 3),
            'adjudicated_credit': number(
                factor.get('adjudicated_credit', 0), 3
            ),
            'adjudicated_score_credit': number(
                factor.get('adjudicated_score_credit', 0), 3
            ),
            'adjudicated_events': '|'.join(
                factor.get('adjudicated_events') or []
            ),
            'cu_primary_credit': number(mix.get('cu_primary', 0), 2),
            'letter_credit': number(mix.get('letter', 0), 2),
            'oppose_credit': number(mix.get('oppose', 0), 2),
            'score_order': score_positions[member],
            'gross_severity': number(
                conduct.get('gross_severity'), 2
            ),
            'delivered_credit': number(
                conduct.get('delivered_credit'), 2
            ),
            'net_severity': number(
                conduct.get('net_severity'), 2
            ),
            'tier_ceiling': conduct.get('tier_ceiling', ''),
            'open_events': '|'.join(conduct.get('open_events') or []),
            'delivery_events': '|'.join(
                conduct.get('delivery_events') or []
            ),
        })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_name('.%s.%d.tmp' % (
        OUTPUT.name, os.getpid()
    ))
    with temporary.open(
        'w', encoding='utf-8', newline=''
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, OUTPUT)
    print('wrote %s (%d rows)' % (OUTPUT, len(rows)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
