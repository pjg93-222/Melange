import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import politico_profile_crawl_api as api
import verify_politico_profile_crawl as verify

class ApiNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.expected={'profile_uuid':'abc','name':'Test Person','roles':[],'issue_areas':[],'partition':'Unknown'}
        self.evidence={'status':200,'url':api.API_BASE+'abc','data':{
            'lexiconId':'abc','name':{'displayName':'Test Person'},
            'stafferPositions':[{'title':'Advisor','member':{'name':{'displayName':'Sen. Example'}}}],
            'employmentItems':[{'title':'Advisor','employerName':'Sen. Example','startDate':'2025-05'},
                               {'title':'Analyst','employerName':'Example Firm','startDate':'2020','endDate':'2025'}],
            'educationItems':[{'institution':'University','degree':'BA','startDate':'2016','endDate':'2020'}],
            'issueAreas':[{'slug':'1','label':'Defense'}]}}

    def test_preserves_source_fields_and_date_precision(self):
        row=api.normalize(self.evidence,self.expected)
        self.assertEqual(row['employment_history'],[
            {'title':'Advisor','employer':'Sen. Example','date_text':'May 2025 - Present'},
            {'title':'Analyst','employer':'Example Firm','date_text':'2020 - 2025'}])
        self.assertEqual(row['current_header_positions'],['Advisor for Sen. Example'])
        self.assertEqual(row['profile_issue_areas'],['Defense'])
        self.assertEqual(row['explicit_side_labels'],[])
        self.assertNotIn('observed_source_url',row)
        self.assertEqual(row['extraction_method'],'AUTHENTICATED_PERSON_API_V1')

    def test_wrong_endpoint_uuid_and_error_response_rejected(self):
        for field,value in [('status',401),('url',api.API_BASE+'wrong')]:
            data=copy.deepcopy(self.evidence); data[field]=value
            with self.assertRaises(ValueError): api.normalize(data,self.expected)
        data=copy.deepcopy(self.evidence); data['data']['lexiconId']='wrong'
        with self.assertRaises(ValueError): api.normalize(data,self.expected)

    def test_source_omissions_are_not_filled_from_roster(self):
        for field in ['employmentItems','stafferPositions']:
            data=copy.deepcopy(self.evidence); del data['data'][field]
            with self.assertRaisesRegex(ValueError,'API required content:'):
                api.normalize(data,self.expected)

    def test_name_changes_remain_review_exceptions(self):
        self.evidence['data']['name']['displayName']='Changed Person'
        row=api.normalize(self.evidence,self.expected)
        self.assertEqual(row['identity_status'],'LIVE_NAME_CHANGED_SAME_UUID')
        self.assertEqual(row['review_status'],'IDENTITY_EXCEPTION_REVIEW_REQUIRED')

    def test_partial_historical_entry_retained_and_flagged(self):
        del self.evidence['data']['employmentItems'][1]['title']
        row=api.normalize(self.evidence,self.expected)
        self.assertEqual(len(row['employment_history']),2)
        self.assertEqual(row['employment_history'][1]['title'],'')
        self.assertEqual(row['source_field_gaps'],[{'collection':'employment_history','ordinal':2,'missing_fields':['title']}])

    def test_institutional_office_is_a_current_employer(self):
        self.evidence['data']['stafferPositions']=[{'title':'Outreach Coordinator','office':{'label':'House Information Resources Office'}}]
        row=api.normalize(self.evidence,self.expected)
        self.assertEqual(row['current_header_positions'],['Outreach Coordinator for House Information Resources Office'])

    def test_source_gap_is_bound_to_an_actual_absent_collection(self):
        del self.evidence['data']['stafferPositions']
        row=api.normalize(self.evidence,self.expected,allow_source_gaps=True)
        evidence={verify.evidence_digest(self.evidence['data']):self.evidence}
        self.assertTrue(verify.validate_api_source(row,evidence))
        self.assertEqual(row['source_missing_collections'],['current_header_positions'])
        self.assertEqual(len(row['employment_history']),2)
        self.assertFalse(verify.validate_api_source(row,{}))
        self.evidence['data']['stafferPositions']=[{'title':'Advisor'}]
        row['projected_api_sha256']=verify.evidence_digest(self.evidence['data'])
        self.assertFalse(verify.validate_api_source(row,{row['projected_api_sha256']:self.evidence}))

    def test_legacy_numeric_identifier_must_match_exact_source_id(self):
        self.expected['profile_uuid']='4'
        self.evidence['url']=api.API_BASE+'4'
        self.evidence['data'].pop('lexiconId')
        self.evidence['data']['id']='4'
        row=api.normalize(self.evidence,self.expected)
        self.assertEqual(row['source_api_person_id'],'4')
        self.evidence['data']['id']='5'
        with self.assertRaises(ValueError): api.normalize(self.evidence,self.expected)

    def test_api404_requires_exact_observation_binding(self):
        observation={'profile_uuid':'abc','status':404,'source_api_url':api.API_BASE+'abc','observed_at':'2026-09-05T00:00:00Z'}
        row={**observation,'profile_api_status':404,'api_observation_sha256':verify.evidence_digest(observation)}
        self.assertTrue(verify.validate_api_404(row,{row['api_observation_sha256']:observation}))
        row['source_api_url']=api.API_BASE+'wrong'
        self.assertFalse(verify.validate_api_404(row,{row['api_observation_sha256']:observation}))

    def test_telephone_and_mobile_job_titles_are_preserved(self):
        self.evidence['data']['employmentItems'][0]['title']='Telephone Operator'
        self.evidence['data']['employmentItems'][1]['title']='Mobile Communications Specialist'
        row=api.normalize(self.evidence,self.expected)
        self.assertEqual([x['title'] for x in row['employment_history']],['Telephone Operator','Mobile Communications Specialist'])
        self.evidence['data']['employmentItems'][0]['title']='user@example.org'
        with self.assertRaises(ValueError): api.normalize(self.evidence,self.expected)

if __name__=='__main__': unittest.main()
