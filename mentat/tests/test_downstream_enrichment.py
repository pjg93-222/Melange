from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from enrich_downstream import enrich


class EnrichmentTests(unittest.TestCase):
    def payload(self):
        return {'metadata':{'industry':'Fixture','transfer_coverage':[{'cycle':2024,'status':'missing_transfer_source'}]},
            'cycles':[{'cycle':2024}],'raw_rows':[],'committee_map':[],
            'downstream_activity':[],'candidate_committee_links':[]}

    def test_ambiguous_candidate_link_preserves_unresolved_funding(self):
        payload=self.payload()
        payload['raw_rows']=[{'cycle':2024,'committee_id':'C1','amount':125,'include_in_analysis':'Yes'}]
        payload['candidate_committee_links']=[{'cycle':2024,'committee_id':'C1','designation':'A','candidate_id':candidate} for candidate in ('H1','H2')]
        with tempfile.TemporaryDirectory() as directory:result=enrich(payload,Path(directory))
        self.assertEqual(result['attribution_summary'],[])
        coverage=result['allocation_coverage'][0]
        self.assertEqual(coverage['unresolved'],125)
        self.assertEqual(coverage['model_funding'],125)
        self.assertEqual(coverage['estimated_candidate_activity'],0)
        self.assertFalse(result['quality_checks'][0]['passed'])

    def test_opposition_is_not_credited_to_the_target_or_a_rival(self):
        payload=self.payload()
        payload['raw_rows']=[{'cycle':2024,'committee_id':'PAC','amount':100,'include_in_analysis':'Yes'}]
        payload['downstream_activity']=[{'cycle':2024,'source_committee_id':'PAC','candidate_id':'H1','support_oppose':'Oppose','preliminary_included_amount':60},
            {'cycle':2024,'source_committee_id':'PAC','candidate_id':'H2','support_oppose':'Support','preliminary_included_amount':40}]
        with tempfile.TemporaryDirectory() as directory:result=enrich(payload,Path(directory))
        rows={row['candidate_id']:row for row in result['attribution_summary']}
        self.assertEqual(rows['H1']['estimated_opposition'],60)
        self.assertEqual(rows['H1']['direct_plus_estimated_non_opposition'],0)
        self.assertEqual(rows['H2']['direct_plus_estimated_non_opposition'],40)


if __name__=='__main__':unittest.main()
