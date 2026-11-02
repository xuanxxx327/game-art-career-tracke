"""Check source auto-discovery never promotes an unverified ATS board."""
import unittest
from unittest.mock import patch, Mock

import discover


class DiscoveryTests(unittest.TestCase):
    def test_slug_candidates(self):
        self.assertIn("eleventhhourgames", discover.slugs("Eleventh Hour Games"))
        self.assertIn("eleventh-hour-games", discover.slugs("Eleventh Hour Games"))
        self.assertEqual(discover.slugs("网易互娱"), [])
        self.assertEqual(discover.slugs("EA"), [])

    def test_board_title_identity_guard(self):
        self.assertTrue(discover.strong_identity("Eleventh Hour Games", "Jobs at Eleventh Hour Games"))
        self.assertFalse(discover.strong_identity("Eleventh Hour Games", "Jobs at Another Studio"))
        self.assertFalse(discover.strong_identity("BulletFarm", "Careers at RedHot Games"))
        self.assertFalse(discover.strong_identity("EA", "Careers at EA"))

    def test_only_correct_domain_is_accepted(self):
        bad = Mock()
        bad.url = "https://example.net/fake"
        bad.text = "<title>Jobs at Eleventh Hour Games</title>"
        with patch.object(discover, "get", return_value=bad):
            self.assertIsNone(discover.verified_board("Eleventh Hour Games", "greenhouse", "eleventhhourgames"))

    def test_valid_title_board_can_be_connected(self):
        good = Mock()
        good.url = "https://job-boards.greenhouse.io/eleventhhourgames"
        good.text = "<title>Jobs at Eleventh Hour Games</title>"
        with patch.object(discover, "get", return_value=good):
            result = discover.verified_board("Eleventh Hour Games", "greenhouse", "eleventhhourgames")
        self.assertEqual(result["slug"], "eleventhhourgames")

    def test_no_empty_brand_matches(self):
        self.assertFalse(discover.strong_identity("", "Jobs at Anything"))
        self.assertFalse(discover.strong_identity("Test Games", ""))


if __name__ == "__main__":
    unittest.main()
