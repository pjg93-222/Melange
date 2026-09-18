"""Add the five ruling tests to tests/test_cross_reference_engine.py and re-pin the
two near-name PAC assertions to the D1 reason code. CRLF preserved."""
import sys
sys.path.insert(0, r"C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-evidence-csv-fetch-streaming-8bedff\5220e1f4-e54b-4766-9d71-2c7770012358\scratchpad")
from patchlib import load, replace_once, save

PATH = r"C:\Users\pgoff\Mentat\mentat\tests\test_cross_reference_engine.py"
text = load(PATH)

# 1. The two near-name PAC rows name the company, so under ruling D1 they are
#    queued as company_named_unverified rather than company_attribution_unverified.
text = replace_once(text, """        near=changed(pac,sub_id='near',transaction_id='near',
                     contributor_name='ACME EMPLOYEE PAC SUPPORTERS')
        self.assertTrue(any(item['reason']=='company_attribution_unverified'
                            for item in analyze([near],affiliations=affiliation)['review_queue']))
""", """        near=changed(pac,sub_id='near',transaction_id='near',
                     contributor_name='ACME EMPLOYEE PAC SUPPORTERS')
        # A near name is not a dated affiliation. It names the company, so it
        # stays counted and queued under the company-named flag (ruling D1).
        self.assertTrue(any(item['reason']=='company_named_unverified'
                            for item in analyze([near],affiliations=affiliation)['review_queue']))
""", "near employee pac")

text = replace_once(text, """        near=changed(pac,sub_id='near-alias',transaction_id='near-alias',
                     contributor_name='ACME LEGACY PAC SUPPORTERS')
        self.assertTrue(any(item['reason']=='company_attribution_unverified'
                            for item in analyze([near],affiliations=affiliation)['review_queue']))
""", """        near=changed(pac,sub_id='near-alias',transaction_id='near-alias',
                     contributor_name='ACME LEGACY PAC SUPPORTERS')
        self.assertTrue(any(item['reason']=='company_named_unverified'
                            for item in analyze([near],affiliations=affiliation)['review_queue']))
""", "near legacy pac")

# 2. Five new tests before the module guard.
NEW_TESTS = '''
    def test_text_naming_another_organization_contradicts_the_attribution(self):
        # Ruling D1 (2026-09-17): a row whose own reported text names an
        # organization that is not the listed company or any of its supplied
        # names is a contradiction, not an ambiguity. It leaves the totals with
        # its evidence; a proven duplicate is the other kind of contradiction.
        names={'Citibank':['Citi','Citibank','Citigroup']}
        pac=changed(row('pac',5000),company='Citibank',entity_type='PAC',contributor_name='END CITIZENS UNITED',
                    company_match_status='review',company_match_reason='corporate_name_not_verified')
        result=analyze([pac],company_names=names)
        decision=result['decisions'][0]
        self.assertEqual(decision['counted_cents'],0)
        self.assertEqual(decision['pac_activity_cents'],0)
        self.assertEqual(decision['status'],'excluded_with_evidence')
        self.assertEqual(decision['bucket'],'excluded_company_match')
        self.assertIn('attribution_contradicted_by_text',decision['reasons'])
        self.assertNotIn('company_attribution_unverified',decision['reasons'])
        self.assertFalse(result['review_queue'])
        self.assertEqual(result['totals']['provisional_original_giving_cents'],0)
        self.assertEqual(result['changes'][0]['delta_cents'],-500000)
        # The company's own label is a name even when no roster is supplied.
        self.assertEqual(analyze([pac])['decisions'][0]['status'],'excluded_with_evidence')

    def test_text_naming_the_company_stays_counted_while_a_stranger_is_excluded(self):
        names={'Citibank':['Citi','Citibank','Citigroup']}
        rows=[changed(row('named'),company='Citibank',contributor_employer='CITIBANK N A',contributor_occupation='BANKER',
                      company_match_status='review',company_match_reason='prefix_with_unverified_trailing_tokens:N A'),
              changed(row('stranger'),company='Citibank',contributor_employer='CITIZENS BUSINESS BANK',contributor_occupation='BANKER',
                      company_match_status='review',company_match_reason='squashed_prefix_unverified_remainder:ZENSBUSINESSBANK'),
              changed(row('blank'),company='Citibank',contributor_employer='',contributor_occupation='',company_match_status='review'),
              changed(row('none'),company='Citibank',contributor_employer='NOT EMPLOYED',contributor_occupation='RETIRED',
                      company_match_status='review'),
              changed(row('short'),company='Citibank',contributor_employer='CITI TRENDS',contributor_occupation='CLERK',
                      company_match_status='review')]
        result=analyze(rows,company_names=names)
        decisions={d['source_id']:d for d in result['decisions']}
        queued={}
        for item in result['review_queue']:queued.setdefault(item['reason'],[]).extend(item['source_ids'])
        for sid in ('named','short'):
            self.assertEqual(decisions[sid]['counted_cents'],10000)
            self.assertEqual(decisions[sid]['attribution_status'],'unverified')
            self.assertIn('company_named_unverified',decisions[sid]['reasons'])
            self.assertEqual(decisions[sid]['status'],'needs_review')
        for sid in ('blank','none'):
            self.assertEqual(decisions[sid]['counted_cents'],10000)
            self.assertEqual(decisions[sid]['attribution_status'],'unverified')
            self.assertIn('company_attribution_unverified',decisions[sid]['reasons'])
        self.assertEqual(decisions['stranger']['counted_cents'],0)
        self.assertEqual(decisions['stranger']['status'],'excluded_with_evidence')
        self.assertIn('attribution_contradicted_by_text',decisions['stranger']['reasons'])
        self.assertEqual(sorted(queued['company_named_unverified']),['named','short'])
        self.assertEqual(sorted(queued['company_attribution_unverified']),['blank','none'])
        self.assertNotIn('stranger',[sid for ids in queued.values() for sid in ids])
        self.assertEqual(result['totals']['provisional_original_giving_cents'],40000)
        self.assertEqual(result['totals']['unresolved_positive_cents'],40000)

    def test_recipient_company_pac_supports_an_unverified_attribution(self):
        # Ruling (2026-09-17): another employer is fine when the money goes to
        # something affiliated with the listed company. The register or the FEC
        # connected-organization field proves the recipient side; the employer
        # field does not have to.
        names={'Citibank':['Citi','Citibank','Citigroup']}
        affiliation={'records':[dict(company='Citibank',entity_id='C00008474',entity_name='CITIGROUP INC. PAC',
            relationship='connected_pac',valid_from='2021-01-01',source_url='https://fec.gov/fixture',evidence_id='citi-pac')]}
        registered=changed(row('registered'),company='Citibank',committee_id='C00008474',contributor_employer='ACME WIDGETS INC',
                           contributor_occupation='ENGINEER',company_match_status='review')
        connected=changed(row('connected'),company='Citibank',committee_id='C00039305',contributor_employer='ACME WIDGETS INC',
                          contributor_occupation='ENGINEER',company_match_status='review')
        stranger=changed(row('stranger'),company='Citibank',committee_id='C00000001',contributor_employer='ACME WIDGETS INC',
                         contributor_occupation='ENGINEER',company_match_status='review')
        result=analyze([registered,connected,stranger],affiliations=affiliation,company_names=names,
                       committee_connected_orgs={'C00039305':['CITIGROUP INC.']})
        decisions={d['source_id']:d for d in result['decisions']}
        self.assertEqual(decisions['registered']['counted_cents'],10000)
        self.assertEqual(decisions['registered']['attribution_status'],'recipient_supported')
        self.assertIn('recipient_is_dated_company_pac',decisions['registered']['reasons'])
        self.assertEqual(decisions['registered']['funding_direction'],'employee_to_company_pac')
        self.assertEqual(decisions['connected']['counted_cents'],10000)
        self.assertEqual(decisions['connected']['attribution_status'],'recipient_supported')
        self.assertIn('recipient_connected_organization_resolves_to_company',decisions['connected']['reasons'])
        for sid in ('registered','connected'):
            self.assertIn('company_attribution_unverified',decisions[sid]['reasons'])
            self.assertEqual(decisions[sid]['status'],'needs_review')
        self.assertEqual(decisions['stranger']['counted_cents'],0)
        self.assertIn('attribution_contradicted_by_text',decisions['stranger']['reasons'])
        self.assertEqual(result['totals']['provisional_original_giving_cents'],20000)

    def test_role_marker_with_the_company_named_is_role_supported(self):
        # Ruling D3 (2026-09-17): advisor, adviser, advisory, consultant,
        # consulting, contractor, trustee, partner, counsel and board are the
        # adjacent-position markers; DIRECTOR and RETIRED are not. The route
        # changes the verification status only; the text test decides dollars.
        names={'Citibank':['Citi','Citibank','Citigroup'],'Wells Fargo Bank NA':['Wells Fargo']}
        consultant=changed(row('consultant'),company='Citibank',contributor_employer='SELF-EMPLOYED',
                           contributor_occupation='CONSULTANT TO CITIBANK',company_match_status='review')
        retired=changed(row('retired'),company='Wells Fargo Bank NA',contributor_employer='WELLS FARGO BANK RETIRED',
                        contributor_occupation='RETIRED',company_match_status='review')
        director=changed(row('director'),company='Citibank',contributor_employer='ACME CAPITAL',
                         contributor_occupation='MANAGING DIRECTOR',company_match_status='review')
        advisor=changed(row('advisor'),company='Citibank',contributor_employer='ACME CAPITAL',
                        contributor_occupation='ADVISOR TO CITI',company_match_status='review')
        result=analyze([consultant,retired,director,advisor],company_names=names)
        decisions={d['source_id']:d for d in result['decisions']}
        for sid in ('consultant','advisor'):
            self.assertEqual(decisions[sid]['counted_cents'],10000)
            self.assertEqual(decisions[sid]['attribution_status'],'role_supported')
            self.assertIn('role_marker_with_company_named',decisions[sid]['reasons'])
            self.assertIn('company_named_unverified',decisions[sid]['reasons'])
        self.assertEqual(decisions['retired']['counted_cents'],10000)
        self.assertEqual(decisions['retired']['attribution_status'],'unverified')
        self.assertIn('company_named_unverified',decisions['retired']['reasons'])
        self.assertNotIn('role_marker_with_company_named',decisions['retired']['reasons'])
        self.assertEqual(decisions['director']['counted_cents'],0)
        self.assertIn('attribution_contradicted_by_text',decisions['director']['reasons'])
        self.assertEqual(result['totals']['provisional_original_giving_cents'],30000)

    def test_proven_duplicate_memo_leg_stays_excluded_under_the_text_test(self):
        names={'Citibank':['Citi','Citibank','Citigroup']}
        parent=changed(row('a'),company='Citibank',contributor_employer='CITIBANK',company_match_status='review',
                       transaction_id='SA11AI.TX')
        memo=changed(row('b'),company='Citibank',contributor_employer='CITIBANK',company_match_status='review',
                     memo_code='X',memo_text='[SA11AI:TX]')
        result=analyze([parent,memo],company_names=names)
        decisions={d['source_id']:d for d in result['decisions']}
        self.assertEqual(decisions['a']['counted_cents'],10000)
        self.assertIn('company_named_unverified',decisions['a']['reasons'])
        self.assertEqual(decisions['b']['counted_cents'],0)
        self.assertEqual(decisions['b']['status'],'excluded_with_evidence')
        self.assertIn('explicit_same_filing_memo_reference',decisions['b']['reasons'])
        self.assertEqual([link['kind'] for link in result['links']],['memo'])
        self.assertEqual(result['totals']['provisional_original_giving_cents'],10000)
'''

text = replace_once(text, """        self.assertEqual(result['decisions'][0]['receipt_verification_status'],'source_verified')


if __name__ == '__main__':
    unittest.main()
""", """        self.assertEqual(result['decisions'][0]['receipt_verification_status'],'source_verified')
""" + NEW_TESTS + """

if __name__ == '__main__':
    unittest.main()
""", "module guard")

save(PATH, text)
