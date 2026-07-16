# -*- coding: utf-8 -*-
"""TDD contracts for the integrate-phase CU-stance channels (hearings / interviews / bluesky), 2026-07-15.

Each channel mirrors the speech CU-stance channel; these tests lock the integration contract so the
mirror cannot silently drift.  Dependency-light — source-text assertions plus light functional checks
that import ONLY the API-free stance stacks (they read the small cu_valence_registry.json at import and
nothing else) — mirroring tests/test_recorrection_contracts.py.

Run from the fec dir (where the tests package resolves):
    cd fec && python -m unittest tests.test_channel_gold_queues -v
"""
from __future__ import annotations
import hashlib, importlib, re, sys, unittest
from pathlib import Path

FEC = Path(__file__).resolve().parents[1]
ROOT = FEC.parent
sys.path.insert(0, str(FEC))


def source(name: str) -> str:
    return (FEC / name).read_text(encoding="utf-8-sig")


# the canonical 12 gold-queue columns, EXACT order — identical to speech_gold_queue.csv so Paul's
# labeling workflow is identical across every channel.
CANON_COLS = ['id', 'bioguide', 'member', 'date', 'source', 'chamber', 'categories',
              'registry_target', 'registry_valence', 'prelabel_stance', 'gold_stance', 'text_snippet']

# per channel: (gold-queue builder file, stance-stack module, build_media_blend env gate)
CHANNELS = [
    ('build_hearing_gold_queue.py',   'hearing_stance_stack',   'CU_HEARING_CHANNEL'),
    ('build_interview_gold_queue.py', 'interview_stance_stack', 'CU_INTERVIEW_CHANNEL'),
    ('build_bluesky_gold_queue.py',   'bluesky_stance_stack',   'CU_BLUESKY_CHANNEL'),
]

# the ONE content-hash id formula both the builder and the stack must use, byte-for-byte.
ID_FORMAT = "'%s|%s|%s' %"
ID_TAIL = ".encode('utf-8', 'replace')).hexdigest()[:12]"
# 2026-07-15: the id is x-hardened. A leading 'x' makes it non-numeric so Excel cannot coerce it into
# scientific notation ("8.02E+58") and silently break a hand label's binding (which cost 2 speech labels).
X_PREFIX = "'x' + hashlib.md5("


def canonical_id(bio, date, text):
    """'x' + md5(bioguide|date|text)[:12] — the exact formula the stacks' row_id() and the builders share.
    The leading 'x' keeps the id non-numeric so a spreadsheet round-trip cannot mangle it."""
    return 'x' + hashlib.md5(('%s|%s|%s' % (bio or '', date or '', text or ''))
                             .encode('utf-8', 'replace')).hexdigest()[:12]


class IdHashParity(unittest.TestCase):
    """(a) builder + stance stack use the SAME id formula md5(bioguide|date|text)[:12]."""

    def test_stack_row_id_is_canonical(self):
        # functional: each stack's row_id() must equal the canonical md5(bioguide|date|text)[:12].
        samples = [('B001234', '2025-01-02', 'hello world'),
                   ('', '', ''),
                   ('X000042', '2024-12-31', 'unicodé — em dash & pipe|inside'),
                   ('A000360', '2023-06-15', 'rein in the rogue CFPB')]
        for _builder, stackmod, _gate in CHANNELS:
            mod = importlib.import_module(stackmod)
            for bio, date, text in samples:
                self.assertEqual(mod.row_id(bio, date, text), canonical_id(bio, date, text),
                                 '%s.row_id() diverges from md5(bioguide|date|text)[:12]' % stackmod)

    def test_builder_and_stack_share_id_formula_in_source(self):
        # source-text: both the builder and the stack must spell the SAME hash expression, so a gold
        # label written by the builder binds to the row the stack scores.
        for builder, stackmod, _gate in CHANNELS:
            for tag, src in (('builder', source(builder)), ('stack', source(stackmod + '.py'))):
                self.assertIn(ID_FORMAT, src, '%s (%s): id format string missing' % (stackmod, tag))
                self.assertIn(ID_TAIL, src, '%s (%s): id tail (.hexdigest()[:12]) missing' % (stackmod, tag))
                self.assertIn(X_PREFIX, src, '%s (%s): id not x-hardened (Excel-proof prefix missing)' % (stackmod, tag))
                seg = src[src.index(ID_FORMAT):src.index(ID_FORMAT) + 200]
                self.assertTrue(0 <= seg.index('bioguide') < seg.index('date') < seg.index('text'),
                                '%s (%s): id args not in order bioguide|date|text' % (stackmod, tag))


class GoldQueueColumns(unittest.TestCase):
    """(b) the 12 canonical gold-queue columns appear in order in the builder's column list."""

    def test_builder_cols_are_canonical_in_order(self):
        for builder, _stackmod, _gate in CHANNELS:
            src = source(builder)
            m = re.search(r"cols\s*=\s*\[(.*?)\]", src, re.S)
            self.assertIsNotNone(m, '%s: cols = [...] list not found' % builder)
            cols = re.findall(r"'([^']*)'", m.group(1))
            self.assertEqual(cols, CANON_COLS,
                             '%s: gold-queue columns must be the 12 canonical columns in order' % builder)


class BlendGates(unittest.TestCase):
    """(c) build_media_blend.py contains each channel's env gate name and defaults it to '0'."""

    def test_blend_defines_each_gate_off_by_default(self):
        src = source('build_media_blend.py')
        for _builder, stackmod, gate in CHANNELS:
            pat = re.compile(r"os\.environ\.get\(\s*['\"]%s['\"]\s*,\s*['\"]0['\"]\s*\)" % re.escape(gate))
            self.assertRegex(src, pat,
                             'build_media_blend.py must read %s defaulting to "0" (gated OFF)' % gate)


class WiringContract(unittest.TestCase):
    """Own-source injection wiring: hearings + interviews are injected; bluesky is quarantined
    (already present in the SOCIAL corpus) so it must NOT be injected — no double count."""

    def test_hearing_and_interview_are_injected(self):
        src = source('build_media_blend.py')
        self.assertIn('hearingvals[m]/hsp', src, 'hearing own-source injection missing from the blend loop')
        self.assertIn('interviewvals[m]/isp', src, 'interview own-source injection missing from the blend loop')
        self.assertIn('HEARING_W', src)
        self.assertIn('INTERVIEW_W', src)

    def test_bluesky_gate_present_but_not_injected(self):
        src = source('build_media_blend.py')
        # gate exposed for parity, defaulted OFF ...
        self.assertRegex(src, r"os\.environ\.get\(\s*['\"]CU_BLUESKY_CHANNEL['\"]\s*,\s*['\"]0['\"]\s*\)")
        # ... but deliberately NOT wired into the per-member blend math (would double-count the social corpus)
        self.assertNotIn('blueskyvals', src,
                         'bluesky must NOT be injected — it already rides the social corpus (double-count)')
        self.assertIn('double-count', src.lower(),
                      'the bluesky quarantine rationale (double-count) must be documented in-source')


class RelaxedCfpbPinAndGoldPrecedence(unittest.TestCase):
    """(d) each stance stack composes at valence -1 for cfpb* families (relaxed pin) and applies
    gold precedence (gold beats the heuristic)."""

    def test_compose_at_valence_minus1(self):
        # valence -1 target: supporting an anti-CU target = anti-CU (oppose); opposing it = pro-CU (support).
        for _builder, stackmod, _gate in CHANNELS:
            mod = importlib.import_module(stackmod)
            self.assertEqual(mod.compose('support', -1), 'oppose', '%s compose(support,-1)' % stackmod)
            self.assertEqual(mod.compose('oppose', -1), 'support', '%s compose(oppose,-1)' % stackmod)
            self.assertEqual(mod.compose('neutral', -1), 'neutral', '%s compose(neutral,-1)' % stackmod)

    def test_relaxed_cfpb_pin_direction(self):
        # RELAXED CFPB pin: attacking/defunding the CFPB agency = pro-CU (support); defending it = anti-CU
        # (oppose).  Both texts match a policy_force cfpb family (valence 0) but the relaxed pin trusts the
        # windowed cue at valence -1.
        attack = 'Congress must rein in the rogue CFPB and defund it entirely.'
        defend = 'We must protect and defend the CFPB from these cuts.'
        for _builder, stackmod, _gate in CHANNELS:
            mod = importlib.import_module(stackmod)
            self.assertEqual(mod.score_row({'bioguide': 'B', 'date': '2025-01-02', 'text': attack}, {}),
                             ('support', 'review'), '%s: attack-CFPB must score support (pro-CU)' % stackmod)
            self.assertEqual(mod.score_row({'bioguide': 'B', 'date': '2025-01-02', 'text': defend}, {}),
                             ('oppose', 'review'), '%s: defend-CFPB must score oppose (anti-CU)' % stackmod)

    def test_relaxed_pin_line_in_source(self):
        for _builder, stackmod, _gate in CHANNELS:
            src = source(stackmod + '.py')
            self.assertIn("startswith('cfpb')", src, '%s: cfpb relaxed-pin guard missing' % stackmod)
            self.assertIn('compose(s, -1)', src, '%s: relaxed pin must compose at valence -1' % stackmod)

    def test_gold_precedence_beats_heuristic(self):
        # the defend text scores 'oppose' heuristically; a filled gold 'support' must WIN and be tier 'gold'.
        defend = 'We must protect and defend the CFPB from these cuts.'
        for _builder, stackmod, _gate in CHANNELS:
            mod = importlib.import_module(stackmod)
            rid = mod.row_id('B', '2025-01-02', defend)
            self.assertEqual(mod.score_row({'bioguide': 'B', 'date': '2025-01-02', 'text': defend}, {rid: 'support'}),
                             ('support', 'gold'), '%s: gold must override the heuristic' % stackmod)


if __name__ == '__main__':
    unittest.main(verbosity=2)
