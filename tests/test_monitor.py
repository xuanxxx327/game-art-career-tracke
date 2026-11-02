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

    def test_chinese_scenario_research_not_environment_art(self):
        for title in (
            "元宝-复杂场景下的知识消歧与推理能力优化研究",
            "混元多模态-3D场景生成算法研究",
            "面向超大规模 AAA 级游戏场景的 3DGS重建及游戏引擎的高性能渲染管线",
            "混元多模态-高清物理级纹理材质生成研究",
        ):
            with self.subTest(title=title):
                self.assertIsNone(monitor.normalize(SOURCE, sample(title, "Campus Recruitment"), NOW))

    def test_chinese_environment_art_matches(self):
        for title in ("3D场景设计", "场景建模师", "道具美术", "材质美术", "地编美术"):
            with self.subTest(title=title):
                result = monitor.normalize(SOURCE, sample(title, "Internship"), NOW)
                self.assertIsNotNone(result)
                self.assertEqual(result["track"], "internship")

    def test_lever_work_type(self):
        job = monitor.normalize(SOURCE, sample("Environment Artist", "Internship"), NOW)
        self.assertEqual(job["track"], "internship")

    def test_http_links_rejected(self):
        s = sample("Environment Artist Intern")
        s["url"] = "http://example.com/jobs/123"
        self.assertIsNone(monitor.normalize(SOURCE, s, NOW))

if __name__ == "__main__":
    unittest.main()
