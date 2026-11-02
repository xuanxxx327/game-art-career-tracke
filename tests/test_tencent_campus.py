"""Mocked tests for Tencent public campus and internship API normalization."""
import unittest
from unittest.mock import Mock, patch
import monitor


class TencentCampusTests(unittest.TestCase):
    def test_paginated_campus_and_internship_feed(self):
        rows = [
            {"postId":"101","projectId":2,"positionTitle":"游戏场景美术实习生",
             "workCities":"深圳","bgs":"IEG","projectName":"日常实习"},
            {"postId":"102","projectId":1,"positionTitle":"场景建模师",
             "workCities":"广州","bgs":"天美工作室","projectName":"校园招聘"},
            {"postId":"103","projectId":5,"positionTitle":"资深场景美术",
             "workCities":"深圳","bgs":"IEG","projectName":"社会招聘"},
        ]
        payload = {"status":0,"data":{"positionList":rows,"count":3}}
        resp = Mock()
        resp.json.return_value = payload
        resp.raise_for_status.return_value = None
        with patch.object(monitor.SESSION,"post",return_value=resp) as post:
            jobs=list(monitor.tencent_campus({"name":"Tencent Games"}))
        self.assertEqual(len(jobs),2)
        self.assertEqual(jobs[0]["employment_type"],"Internship")
        self.assertEqual(jobs[1]["employment_type"],"Campus Recruitment")
        self.assertIn("postid=101",jobs[0]["url"])
        self.assertEqual(post.call_count,7)

    def test_intern_is_china_even_when_city_missing(self):
        source={"name":"Tencent Games","source":"tencent_campus","group":"domestic_major"}
        entry={"source_id":"104","title":"场景美术","location":"",
               "employment_type":"Internship","department":"IEG",
               "url":"https://join.qq.com/post_detail.html?postid=104"}
        result=monitor.normalize(source,entry,"2026-11-03T00:00:00+00:00")
        self.assertEqual(result["region"],"china")
        self.assertEqual(result["track"],"internship")
        self.assertEqual(result["eligibility"],"check_job_requirements")

    def test_api_error_not_treated_as_zero_positions(self):
        response=Mock()
        response.json.return_value={"status":-1,"message":"not available"}
        response.raise_for_status.return_value=None
        with patch.object(monitor.SESSION,"post",return_value=response):
            with self.assertRaises(ValueError):
                list(monitor.tencent_campus({"name":"Tencent Games"}))


if __name__=="__main__":
    unittest.main()
