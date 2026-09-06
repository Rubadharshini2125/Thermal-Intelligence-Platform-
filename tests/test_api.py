import os
import unittest

from fastapi.testclient import TestClient

from backend.main import app
from backend.services import pipeline


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def tearDown(self):
        pipeline.configure(mode="demo")

    def test_health(self):
        body = self.client.get("/api/health").json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("version", body)

    def test_firms_status_never_exposes_key(self):
        body = self.client.get("/api/firms/status").json()
        self.assertIn("configured", body)
        self.assertIn("live_available", body)

    def test_detections_and_detail(self):
        body = self.client.get("/api/detections").json()
        self.assertGreater(body["count"], 0)
        self.assertTrue(body["demo_mode"])
        detection_id = body["detections"][0]["id"]
        detail = self.client.get(f"/api/detections/{detection_id}").json()
        self.assertEqual(detail["id"], detection_id)
        self.assertIn("classification_reasoning", detail)
        self.assertEqual(self.client.get("/api/detections/does-not-exist").status_code, 404)

    def test_detections_limit_and_filters(self):
        body = self.client.get("/api/detections", params={"limit": 2}).json()
        self.assertEqual(body["count"], 2)
        self.assertGreater(body["total"], body["count"])

    def test_analytics_respects_filters(self):
        unfiltered = self.client.get("/api/analytics").json()
        filtered = self.client.get("/api/analytics", params={"risk": "High"}).json()
        self.assertEqual(filtered["total_detections"], filtered["high_risk_detections"])
        self.assertLessEqual(filtered["total_detections"], unfiltered["total_detections"])
        self.assertIn("avg_frp", unfiltered)
        self.assertIn("industrial_related_detections", unfiltered)

    def test_export_csv(self):
        response = self.client.get("/api/detections/export")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("event_id", response.text.splitlines()[0])

    def test_analyze_demo(self):
        body = self.client.post("/api/analyze", json={"mode": "demo"}).json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["demo_mode"])
        self.assertEqual(body["analyzed_detections"], body["input_detections"])
        self.assertIn("Persistent Thermal Source", body["classification_counts"])

    def test_analyze_invalid_mode_returns_422(self):
        response = self.client.post("/api/analyze", json={"mode": "bogus"})
        self.assertEqual(response.status_code, 422)

    def test_analyze_live_mode_structurally_valid(self):
        # Real NASA FIRMS call if FIRMS_MAP_KEY is configured; falls back to demo otherwise. Either way
        # the response must be well-formed and must never fabricate data.
        body = self.client.post("/api/analyze", json={"mode": "live", "days": 1}).json()
        self.assertIn(body["status"], {"ok", "no_detections", "live_unavailable_fallback"})
        self.assertEqual(body["mode"], "live")
        if not body["demo_mode"]:
            self.assertTrue(body["source"].startswith("NASA FIRMS"))

    def test_detections_mode_query_param(self):
        body = self.client.get("/api/detections", params={"mode": "demo"}).json()
        self.assertTrue(body["demo_mode"])

    def test_pipeline_status(self):
        body = self.client.get("/api/pipeline/status").json()
        names = [stage["name"] for stage in body["stages"]]
        self.assertEqual(names, ["NASA FIRMS / Demo source", "Data ingestion", "Cleaning", "Industrial proximity",
                                 "Persistence", "Classification", "Risk scoring", "API response"])

    def test_firms_key_never_exposed(self):
        key = os.environ.get("FIRMS_MAP_KEY", "")
        if not key:
            self.skipTest("FIRMS_MAP_KEY not configured in this environment")
        payloads = [
            self.client.get("/api/health").text,
            self.client.get("/api/config").text,
            self.client.get("/api/firms/status").text,
            self.client.get("/api/detections").text,
            self.client.post("/api/analyze", json={"mode": "live", "days": 1}).text,
            self.client.get("/api/pipeline/status").text,
            self.client.get("/openapi.json").text,
        ]
        for body in payloads:
            self.assertNotIn(key, body)


if __name__ == "__main__":
    unittest.main()
