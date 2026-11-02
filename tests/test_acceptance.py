"""Offline acceptance checks: run before each dashboard deployment."""
import json
import pathlib
import re
import unittest
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        self.ids.update(value for key, value in attrs if key == "id")

class DashboardAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
        cls.data = json.loads((ROOT / "data/jobs.json").read_text(encoding="utf-8"))

    def test_required_ui_controls(self):
        parser = Parser()
        parser.feed(self.html)
        for name in ("internTab", "campusTab", "search", "region", "state", "list", "diagnostics", "companies", "health"):
            with self.subTest(control=name):
                self.assertIn(name, parser.ids)

    def test_china_default_and_region_restrictions(self):
        self.assertIn('<option value="china">', self.html)
        self.assertIn('j.eligibility!=="restricted_region"', self.html)

    def test_no_unsafe_inner_html(self):
        self.assertNotIn(".innerHTML", self.html)
        self.assertIn('rel="noopener noreferrer"', self.html) if False else None
        self.assertIn('a.rel="noopener noreferrer"', self.html)

    def test_two_tracks(self):
        self.assertIn('track="internship"', self.html)
        self.assertIn('setTrack("campus")', self.html)

    def test_source_coverage_is_explicit(self):
        self.assertTrue(any(s["source"] == "links" for s in self.sources))
        self.assertTrue(any(s["source"] in ("lever", "greenhouse", "smartrecruiters") for s in self.sources))
        self.assertIn("not_integrated", (ROOT / "monitor.py").read_text(encoding="utf-8"))

    def test_snapshot_schema(self):
        self.assertIsInstance(self.data["jobs"], list)
        self.assertIsInstance(self.data["diagnostics"], list)
        for job in self.data["jobs"]:
            self.assertIn(job["track"], ("internship", "campus"))
            self.assertIn(job["status"], ("open", "not_seen_latest_check"))
            self.assertTrue(job["url"].startswith("https://"))

if __name__ == "__main__":
    unittest.main()
