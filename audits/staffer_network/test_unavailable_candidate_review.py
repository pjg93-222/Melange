import politico_profile_crawl_api as api
from verify_unavailable_candidates_20260905 import classify,role_key

def fixtures():
    expected={'name':'Kaylin Henderson','roles':['Legislative Correspondent for Rep. Christian MenefeeDemocraticTX-18']}
    hit={'lexiconId':'candidate','displayName':'Kaylin Henderson','employments':[{'title':'Legislative Correspondent','employer':'Rep. Christian Menefee'}]}
    evidence={'status':200,'url':api.API_BASE+'candidate','data':{'lexiconId':'candidate','id':123,'name':{'displayName':'Kaylin Henderson'},'stafferPositions':[{'title':'Legislative Correspondent','member':{'name':{'displayName':'Rep. Christian Menefee'}}}], 'employmentItems':[]}}
    return expected,hit,evidence

def test_three_way_agreement_is_only_probable_replacement():
    result=classify(*fixtures())
    assert result['classification']=='PROBABLE_REPLACEMENT_EXACT_NAME_CURRENT_ROLE_AND_EMPLOYER'

def test_name_alone_does_not_merge():
    expected,hit,evidence=fixtures()
    expected['roles']=['Intern for Rep. Somebody ElseDemocraticTX-18']
    assert classify(expected,hit,evidence)['classification']=='SAME_NAME_DIFFERENT_OR_UNCONFIRMED_EMPLOYMENT_REVIEW_REQUIRED'

def test_unbound_id_does_not_match():
    expected,hit,evidence=fixtures()
    evidence['data']['lexiconId']='wrong'
    assert classify(expected,hit,evidence)['classification']=='SEARCH_HIT_NOT_AN_IDENTITY_MATCH'

def test_search_employment_must_agree_with_profile():
    expected,hit,evidence=fixtures()
    evidence['data']['stafferPositions'][0]['title']='Intern'
    assert not classify(expected,hit,evidence)['matching_current_roles']

def test_no_prefix_employer_match():
    assert role_key('Intern for Rep. Smith')!=role_key('Intern for Rep. Smithson')

def test_different_name_search_hit_not_identity():
    expected,hit,evidence=fixtures()
    evidence['data']['name']['displayName']='Different Person'
    assert classify(expected,hit,evidence)['classification']=='SEARCH_HIT_NOT_AN_IDENTITY_MATCH'
