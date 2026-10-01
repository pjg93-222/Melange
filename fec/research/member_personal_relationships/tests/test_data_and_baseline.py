import unittest
from fec.research.member_personal_relationships.data import term_at
from fec.research.member_personal_relationships.work import leave_pair_out_rate


class BaselineTests(unittest.TestCase):
    def test_focal_relationship_is_removed_from_its_baseline(self):
        p1=leave_pair_out_rate((30,10),(10,8),(110,30),(10,8))
        p2=leave_pair_out_rate((40,20),(20,18),(120,40),(20,18))
        self.assertAlmostEqual(p1,p2)
        self.assertLess(p1,0.3)

    def test_no_political_comparators_means_unavailable_baseline(self):
        self.assertIsNone(leave_pair_out_rate((10,8),(10,8),(10,8),(10,8)))

    def test_negative_rate_or_mismatched_counts_fail(self):
        with self.assertRaises(ValueError):
            leave_pair_out_rate((10,12),(0,0),(100,20),(0,0))


class ServiceTests(unittest.TestCase):
    def test_house_to_senate_transfer_uses_exact_date_and_chamber(self):
        p={"terms":[dict(start="2023-01-03",end="2024-12-08",chamber="House"),
                    dict(start="2024-12-09",end="2027-01-03",chamber="Senate")]}
        self.assertIsNone(term_at(p,"2024-12-08"))
        self.assertIsNone(term_at(p,"2025-02-01","House"))
        self.assertEqual(term_at(p,"2025-02-01","Senate")["chamber"],"Senate")


if __name__=="__main__":
    unittest.main()
