"""M5a gates over the LIVE admissions generation (read-only). Skipped unless MELANGE_LIVE_ROOT names a root holding
data/legislation/sentinel_admissions.json and its evidence.

1. Zero churn: every verdict that carries evidence re-fingerprints, under this code, to the fingerprint it was sealed
   with -- none of them was selected, so none is reclassified.
2. CU-quote recall: forcing S2 and S3 on every admitted include keeps every category quote (D-366 reversal condition:
   the design must never drop credit-union-relevant text).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from legislation import refresh_sentinel_admissions as R  # noqa: E402
from legislation import sentinel_evidence_selection as SEL  # noqa: E402
from paths import to_host  # noqa: E402

LIVE = os.environ.get('MELANGE_LIVE_ROOT')
pytestmark = pytest.mark.skipif(not LIVE, reason='MELANGE_LIVE_ROOT not set')


@pytest.fixture(scope='module')
def generation():
    return json.loads((Path(LIVE) / 'data/legislation/sentinel_admissions.json').read_text(encoding='utf-8'))


def test_every_sealed_verdict_keeps_its_fingerprint(generation):
    sealed = {k: d for k, d in generation['decisions'].items() if d.get('evidence') and d.get('evidence_fingerprint')}
    assert sealed, 'no sealed verdicts found'
    changed = []
    for key, decision in sorted(sealed.items()):
        assert not decision.get('evidence_selection')
        texts = R.bound_decision_texts(decision)
        parameters = decision.get('fingerprint_parameters') or {}
        model = parameters.get('model') or (decision.get('classifier') or {}).get('model')
        transport = parameters.get('transport') or (decision.get('classifier') or {}).get('transport', 'api')
        if decision['evidence_fingerprint'] not in (R.evidence_fingerprint(texts, model=model, transport=transport),
                                                    R.evidence_fingerprint(texts, model=model, transport=transport, legacy=True)):
            changed.append(key)
    print('sealed verdicts re-fingerprinted:', len(sealed), 'changed:', len(changed))
    assert changed == []


def test_forced_selection_keeps_every_admitted_quote(generation):
    config = SEL.load_config()[0]
    includes = {k: d for k, d in generation['decisions'].items() if d.get('disposition') == 'include' and d.get('evidence')}
    kept = total = 0
    lost = []
    for key, decision in sorted(includes.items()):
        texts = R.bound_decision_texts(decision)
        raw_bills = {s['url']: Path(to_host(s['path'])).read_bytes() for s in decision['evidence']
                     if s['url'].startswith('https://www.govinfo.gov/content/pkg/BILLS-')}
        statutes = {s['url']: R.SEL.statute_id(s['title'], s['section']) for s in decision['evidence'] if s.get('kind') == 'statute'}
        cited = R.statute_references({u: texts[u] for u in raw_bills})
        keep_statutes, _ = SEL.relevant_statutes(config, raw_bills, texts, cited, R.statute_references)
        selected, _ = SEL.select_sections(config, texts, raw_bills)
        for row in decision['categories']:
            total += 1
            url, quote = row['source_url'], row['quote']
            ok = (quote in selected.get(url, '')) if url in raw_bills else statutes.get(url) in keep_statutes
            kept += ok
            if not ok:
                lost.append((key, row['category'], quote[:80]))
    print('admitted includes:', len(includes), 'category quotes kept:', kept, 'of', total)
    assert lost == [] and total >= 38
