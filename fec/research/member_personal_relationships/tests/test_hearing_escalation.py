import unittest
from fec.research.member_personal_relationships.hearing_escalation import assess,pair_patterns,OUT,read_json,digest
from fec.research.member_personal_relationships.run_history import read_rows


def case(**kw):
    return dict(eligible_member_pair=True,target_clear=True,personal_content='clear',
                personal_types=['appearance_ridicule'],markers=['reciprocal_conflict'])|kw


class HearingEscalationTests(unittest.TestCase):
    def test_personal_attack_plus_exchange_qualifies(self):
        self.assertEqual(assess(case()),'documented_personal_escalation')

    def test_yelling_and_procedure_without_personal_content_do_not(self):
        self.assertEqual(assess(case(personal_content='none',personal_types=[],yelling=True)),
                         'no_personal_attack_in_selected_segment')

    def test_one_jab_does_not_manufacture_a_mutual_confrontation(self):
        self.assertEqual(assess(case(markers=[])),'personal_jab')

    def test_quotes_do_not_assign_the_original_insult_to_the_reader(self):
        self.assertEqual(assess(case(quotation_only=True)),'quoted_or_reported_not_authored')

    def test_nearest_name_is_not_automatically_the_personal_target(self):
        self.assertEqual(assess(case(target_clear=False)),'attribution_unresolved')

    def test_dialect_and_tone_ambiguity_require_review(self):
        self.assertEqual(assess(case(personal_content='ambiguous')),'needs_context_review')

    def test_chair_ruling_and_party_do_not_change_content_decision(self):
        self.assertEqual(assess(case(chair_ruling='permitted',same_party=True)),
                         assess(case(chair_ruling='forbidden',same_party=False)))

    def test_raised_voices_are_not_required(self):
        self.assertEqual(assess(case(yelling=False)),'documented_personal_escalation')

    def test_disputed_threat_can_be_personal_without_proving_violence(self):
        c=case(personal_types=['personal_confrontational_challenge'],markers=['explicit_confrontation'],threat_status='disputed')
        self.assertEqual(assess(c),'documented_personal_escalation')

    def test_nonmembers_are_not_member_network_edges(self):
        self.assertEqual(assess(case(eligible_member_pair=False)),'outside_member_pair_scope')

    def test_repeated_clips_and_reverse_direction_are_one_episode(self):
        a=dict(actor='a',target='b',episode_id='e1',date='2024-01-01',current_roster_pair=True,decision='documented_personal_escalation')
        result=pair_patterns([a,a,a|dict(actor='b',target='a')])[0]
        self.assertEqual(result['independent_episode_count'],1)
        self.assertTrue(result['mutually_personal_in_reviewed_episode'])
        self.assertFalse(result['repeated_across_dates'])

    def test_later_independent_incident_is_a_pattern(self):
        a=dict(actor='a',target='b',episode_id='e1',date='2024-01-01',current_roster_pair=True,decision='documented_personal_escalation')
        result=pair_patterns([a,a|dict(episode_id='e2',date='2025-01-01')])[0]
        self.assertTrue(result['repeated_across_dates'])
        self.assertFalse(result['mutually_personal_in_reviewed_episode'])


@unittest.skipUnless((OUT/'results.json').exists(),'run hearing pilot first')
class HearingOutputTests(unittest.TestCase):
    def test_new_pair_identity_and_current_roster_are_resolved(self):
        results=read_json(OUT/'results.json');cases=read_rows(OUT/'reviewed_cases.ndjson')
        self.assertEqual(results['current_roster_qualifying_pairs'],3)
        new=next(c for c in cases if c['id']=='luna_to_goldman_status_escalation')
        self.assertEqual(new['actor_id'],'L000596')
        self.assertEqual(new['target_id'],'G000599')
        self.assertFalse(new['already_in_regression_anchor_pairs'])

    def test_every_cue_reviewed_once_without_raw_hit_counting_as_edges(self):
        queue=read_rows(OUT/'reviewed_cue_queue.ndjson');results=read_json(OUT/'results.json')
        self.assertEqual(len(queue),32)
        self.assertEqual({r['cue_id'] for r in queue},set(range(32)))
        self.assertEqual(sum(results['cue_dispositions'].values()),32)
        self.assertEqual(results['qualifying_pairs'],5)
        self.assertIsNone(results['independent_accuracy_estimate'])

    def test_pages_and_download_hashes_are_real(self):
        sources={s['id']:s for s in read_json(OUT/'source_manifest.json')}
        for source in sources.values():self.assertEqual(digest(source['local_path']),source['sha256'])
        for case in read_rows(OUT/'reviewed_cases.ndjson'):
            self.assertTrue(all(1<=p<=sources[case['source_id']]['pdf_pages'] for p in case['pdf_pages']))


if __name__=='__main__':unittest.main()
