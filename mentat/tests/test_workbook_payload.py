from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_workbook_payload import project, RAW_FIELDS


class WorkbookProjectionTests(unittest.TestCase):
    def test_projection_preserves_financial_and_identity_inputs(self):
        raw={'cycle':2024,'cycle_label':'2023-2024','company':'Fixture','amount':-125.75,
             'employee_tier':'Employee','party':'D','recipient_category':'Carey',
             'include_in_analysis':'Yes','company_match_status':'accepted',
             'person_key':'person:one','contributor':'PERSON, ONE',
             'recipient_key':'FEC:C1','recipient':'COMMITTEE','committee_id':'C1',
             'category_source':'official','party_source':'official','source_cycle':2024,
             'source_id':'12345678901234567890','unused_explanation':'long source text'}
        payload={'metadata':{},'raw_rows':[raw],
                 'cycle_exceptions':[{'source_id':'outside','amount':100}],
                 'allocation_estimates':[{'root':'C1','estimated_amount':25}],
                 'candidate_master':[{'candidate_id':'H1'}]}
        baseline=deepcopy(payload)
        result=project(payload)
        self.assertEqual(result['raw_rows'][0],{key:value for key,value in raw.items() if key in RAW_FIELDS})
        self.assertEqual(result['cycle_exceptions'],baseline['cycle_exceptions'])
        self.assertEqual(result['allocation_estimates'],baseline['allocation_estimates'])
        self.assertNotIn('candidate_master',result)
        self.assertEqual(result['metadata']['workbook_projection'],'formula-facts-v1')

    def test_projection_preserves_fine_grain_detail_frames(self):
        # The console can only chart columns a worksheet publishes, and the two
        # detail frames are the only published home for committee type, ZIP,
        # city, state, employer and occupation - none of which are in
        # RAW_FIELDS. They ride their own payload keys, so the projection that
        # strips raw_rows must leave them byte-for-byte alone.
        detail={'recipient_detail':[{'cycle':2024,'cycle_label':'2023-2024',
                    'company':'Fixture','committee_id':'C1','recipient':'COMMITTEE',
                    'committee_type':'O','designation':'U',
                    'committee_type_label':'Independent expenditure-only (Super PAC)',
                    'designation_label':'Unauthorized','recipient_category':'Super PAC',
                    'party':'D','total_giving':-125.75,'gift_count':2,'contributors':1,
                    'first_date':'2023-01-05','last_date':'2024-11-02','folded_rows':0}],
                'contributor_detail':[{'cycle':2024,'cycle_label':'2023-2024',
                    'company':'Fixture','state':'MA','city':'Boston','zip5':'02134',
                    'employer':'Fixture','occupation':'Engineer','total_giving':125.75,
                    'gift_count':1,'contributors':1,'folded_rows':0}]}
        payload={'metadata':{},'raw_rows':[],**deepcopy(detail)}
        result=project(payload)
        self.assertEqual(result['recipient_detail'],detail['recipient_detail'])
        self.assertEqual(result['contributor_detail'],detail['contributor_detail'])
        for field in ('zip5','city','state','employer','occupation','committee_type'):
            self.assertNotIn(field,RAW_FIELDS)
        # A leading-zero ZIP stays a string; coerced to a number it becomes 2134.
        self.assertEqual(result['contributor_detail'][0]['zip5'],'02134')


if __name__=='__main__':unittest.main()
