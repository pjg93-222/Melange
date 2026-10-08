"""Resuming must preserve every pending UUID, including earlier exceptions."""
import unittest
from audits.staffer_network.politico_profile_crawl_playwright import rotate_resume_queue


class ResumeQueueTests(unittest.TestCase):
    def setUp(self):
        self.source = [{"profile_uuid": str(i)} for i in range(8)]
        self.pending = [self.source[i] for i in (0, 2, 5, 6, 7)]

    def ids(self, rows):
        return [row["profile_uuid"] for row in rows]

    def test_legacy_resume_continues_after_last_success_and_retains_exceptions(self):
        result = rotate_resume_queue(self.pending, self.source, last_completed_uuid="4")
        self.assertEqual(self.ids(result), ["5", "6", "7", "0", "2"])
        self.assertCountEqual(result, self.pending)

    def test_explicit_next_cursor_wins(self):
        result = rotate_resume_queue(self.pending, self.source, next_uuid="6", last_completed_uuid="4")
        self.assertEqual(self.ids(result), ["6", "7", "0", "2", "5"])
        self.assertCountEqual(result, self.pending)

    def test_only_earlier_exceptions_wrap_back_without_loss(self):
        result = rotate_resume_queue(self.pending, self.source, last_completed_uuid="7")
        self.assertEqual(result, self.pending)

    def test_unknown_cursor_does_not_drop_rows(self):
        result = rotate_resume_queue(self.pending, self.source, next_uuid="missing")
        self.assertEqual(result, self.pending)

    def test_empty_queue(self):
        self.assertEqual(rotate_resume_queue([], self.source, next_uuid="5"), [])


if __name__ == "__main__":
    unittest.main()
