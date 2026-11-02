import unittest
from unittest.mock import patch
import monitor

NOW = "2026-11-03T00:00:00+00:00"
SOURCE = {"name": "Example Studio", "group": "foreign_overseas", "source": "lever"}

def sample(title, employment_type=""):
    return {"source_id": title, "title": title, "location": "Gent", "employment_type": employment_type, "department": "Environment Art", "url": "https://example.com/jobs/123"}

class JobClassificationTests(unittest.TestCase):
    def test_internship(self):
        job = monitor.normalize(SOURCE, sample("Environment Artist - Internship"), NOW)
        self.assertEqual(job["track"], "internship")
        self.assertEqual(job["eligibility"], "needs_verification")

    def test_campus(self):
        job = monitor.normalize(SOURCE, sample("Junior Environment Artist - New Graduate"), NOW)
        self.assertEqual(job["track"], "campus")

    def test_full_time_is_not_campus(self):
        self.assertIsNone(monitor.normalize(SOURCE, sample("Environment Artist", "Full-time"), NOW))

    def test_senior_not_student_role(self):
        self.assertIsNone(monitor.normalize(SOURCE, sample("Senior Environment Artist Intern"), NOW))

    def test_unrelated_role(self):
        self.assertIsNone(monitor.normalize(SOURCE, sample("Software Engineering Internship"), NOW))

    def test_lever_work_type(self):
        job = monitor.normalize(SOURCE, sample("Environment Artist", "Internship"), NOW)
        self.assertEqual(job["track"], "internship")

    def test_http_links_rejected(self):
        s = sample("Environment Artist Intern")
        s["url"] = "http://example.com/jobs/123"
        self.assertIsNone(monitor.normalize(SOURCE, s, NOW))

if __name__ == "__main__":
    unittest.main()
