"""Boundary tests for future-information and label leakage."""
import datetime as dt
import unittest

from audit_data import parse_bill
from build_panel import explicit_stance, label_window, public_features, service_end, term_at
from extend_public import Timeline, direct_stance


class InformationBoundaryTests(unittest.TestCase):
    def test_future_and_same_day_statements_are_unavailable(self):
        evidence=[dict(day=d,topic="banking",bills=["119:hr:1"],stance=1,bill_stance=1)
                  for d in [99,100,101]]
        got=public_features(evidence,100,"119:hr:1","banking")
        import numpy as np
        self.assertTrue(np.allclose(got,np.log1p([1,1,1,0,1,1,0,1,1])))

    def test_missing_statement_is_not_opposition(self):
        self.assertEqual(public_features([],100,"119:hr:1","banking").tolist(),[0]*9)

    def test_thirty_day_boundary_and_censoring(self):
        self.assertEqual(label_window(130,100,150),dict(mature=True,y=1,duration=30,event=1))
        self.assertEqual(label_window(131,100,150),dict(mature=True,y=0,duration=30,event=0))
        self.assertEqual(label_window(None,100,112),dict(mature=False,y=0,duration=12,event=0))
        self.assertEqual(label_window(105,100,112),dict(mature=False,y=1,duration=5,event=1))

    def test_already_signed_rejected(self):
        with self.assertRaises(ValueError):
            label_window(100,100,150)

    def test_departed_or_wrong_chamber_member_ineligible(self):
        p={"terms":[dict(start=1,end=100,chamber="House")]}
        self.assertIsNone(term_at(p,100,"House"))
        self.assertIsNone(term_at(p,90,"Senate"))
        self.assertIsNotNone(term_at(p,99,"House"))

    def test_election_rollover_is_not_a_departure(self):
        t=dict(start=1,end=100,chamber="House")
        p={"terms":[t,dict(start=100,end=200,chamber="House")]}
        self.assertEqual(service_end(p,t),200)

    def test_third_person_and_negation_are_not_support(self):
        self.assertEqual(explicit_stance("The association supports this bill.","hearing"),0)
        self.assertEqual(explicit_stance("I do not support this bill.","hearing"),-1)
        self.assertEqual(explicit_stance("I support this bill.","hearing"),1)
        self.assertEqual(explicit_stance("Smith endorses the bill.","press","Smith"),1)

    def test_strict_position_attribution_rejects_stakeholder_support(self):
        self.assertEqual(direct_stance("Emmer Announces Stakeholder Support for the Act","press","Emmer"),0)
        self.assertEqual(direct_stance("I want to know if you support this bill.","hearing","Smith"),0)
        self.assertEqual(direct_stance("I'm proud to support this bill.","social","Smith"),1)
        self.assertEqual(direct_stance("I do not support this bill.","hearing","Smith"),-1)

    def test_vector_timeline_never_crosses_member_or_date(self):
        import numpy as np
        timeline=Timeline([(1,90,1,0),(1,100,0,1),(2,95,0,1),(2,101,1,0)])
        self.assertEqual(timeline.query(np.array([1,2,3]),100).tolist(),[[1,1,0],[1,0,1],[0,0,0]])
        self.assertEqual(timeline.query(np.array([1,2]),100,7).tolist(),[[0,0,0],[1,0,1]])

    def test_weekly_exposures_preserve_event_and_censor_time(self):
        import numpy as np
        from run_models import prepare_hazard
        from build_panel import FEATURES,BASE
        x=np.zeros((3,len(FEATURES)),dtype=np.float32)
        _,rate,weight=prepare_hazard(x,np.array([1,0,1]),np.ones(3),np.array([2,12,30]),BASE)
        self.assertEqual(float(weight.sum()),44.0)
        self.assertEqual(float((rate*weight).sum()),2.0)

    def test_amendment_cosponsors_never_become_bill_cosponsors(self):
        payload=b'''<billStatus><bill><congress>119</congress><number>1</number><type>HR</type>
        <introducedDate>2025-01-03</introducedDate><originChamber>House</originChamber>
        <sponsors><item><bioguideId>A000001</bioguideId></item></sponsors>
        <cosponsors><item><bioguideId>B000001</bioguideId><sponsorshipDate>2025-02-01</sponsorshipDate>
        <sponsorshipWithdrawnDate>2025-03-01</sponsorshipWithdrawnDate></item></cosponsors>
        <amendments><item><cosponsors><item><bioguideId>C000001</bioguideId></item></cosponsors></item></amendments>
        </bill></billStatus>'''
        b=parse_bill(payload)
        self.assertEqual(len(b["cosponsors"]),1)
        self.assertEqual(b["cosponsors"][0]["member"],"B000001")
        self.assertEqual(b["cosponsors"][0]["withdrawn"],"2025-03-01")
        self.assertFalse(b["finance_at_introduction"])


if __name__=="__main__":
    unittest.main()
