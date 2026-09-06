from io import BytesIO
from io import StringIO
from datetime import date
from html.parser import HTMLParser
import re
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from src.analysis import analyze, distances
from src.data_loader import ROOT, clean_detections, demo, load_facilities, load_live, read_csv
from src.map_utils import render_map


class PrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, _, _ = demo()
        with (ROOT / "data/sample/facilities.csv").open("rb") as stream:
            cls.facilities = load_facilities(stream)
        cls.events = analyze(cls.data, cls.facilities)

    def test_demo_scenarios(self):
        expected = {"Refinery incident": "Industrial Fire", "Power plant recurrence": "Persistent Thermal Source",
                    "Forest fire": "Natural Fire", "Agricultural burning": "Unknown", "Unknown signal": "Unknown",
                    "Steel plant recurrence": "Persistent Thermal Source"}
        for scenario, category in expected.items():
            self.assertEqual(set(self.events.loc[self.events.scenario == scenario, "classification"]), {category})
        self.assertTrue(self.events.risk_score.between(0, 100).all())
        self.assertTrue(self.events.confidence_score.between(0, 100).all())
        power = self.events[self.events.scenario == "Power plant recurrence"].iloc[0]
        self.assertEqual((power.active_days, power.detection_count, power.duration_days, power.recurrence_pct), (7, 14, 7, 100))

    def test_distance_and_threshold(self):
        self.assertAlmostEqual(float(distances(0, 0, np.array([0]), np.array([1]))[0]), 111.195, places=2)
        self.assertLess(float(distances(0, 179.999, np.array([0]), np.array([-179.999]))[0]), 1)
        event = self.data[self.data.scenario == "Refinery incident"].iloc[:1]
        self.assertEqual(analyze(event, self.facilities, proximity_km=.001).iloc[0].classification, "Unknown")

    def test_cleaning(self):
        raw = b"latitude,longitude,acq_date,acq_time,confidence,frp\n0,0,2026-09-01,430,h,40\n0,0,2026-09-01,0430,h,40\n91,0,2026-09-01,0430,h,40\n0,0,2026-09-01,2460,h,40\n1,1,2026-09-02,0000,no,-1\n"
        frame, report = clean_detections(read_csv(BytesIO(raw)))
        self.assertEqual(len(frame), 2)
        self.assertEqual(frame.iloc[0].timestamp.hour, 4)
        self.assertEqual(frame.iloc[0].sensor_confidence, 90)
        self.assertTrue(pd.isna(frame.iloc[1].frp))
        self.assertIn("2 invalid", report)
        self.assertIn("1 duplicate", report)
        with self.assertRaises(ValueError):
            clean_detections(pd.DataFrame({"latitude": [0]}))

    def test_missing_data_and_context(self):
        frame, _ = clean_detections(read_csv(BytesIO(b"latitude,longitude,date\n0,0,2026-09-01\n")))
        event = analyze(frame, self.facilities.iloc[:0]).iloc[0]
        self.assertEqual(event.classification, "Unknown")
        self.assertEqual(event.risk_score, 0)
        natural = self.data[self.data.scenario == "Forest fire"].copy()
        natural["context"] = "unknown"
        self.assertEqual(set(analyze(natural, self.facilities).classification), {"Unknown"})

    def test_uploaded_derived_columns_cannot_override_analysis(self):
        frame, _ = clean_detections(read_csv(BytesIO(b"latitude,longitude,date,classification,risk_score\n0,0,2026-09-01,Industrial Fire,100\n")))
        event = analyze(frame, self.facilities).iloc[0]
        self.assertEqual(event.classification, "Unknown")
        self.assertEqual(event.risk_score, 0)

    def test_persistence_counts_days_not_passes(self):
        frame = self.data.iloc[:2].copy()
        frame["timestamp"] = pd.to_datetime(["2026-09-01 04:30", "2026-09-01 16:30"])
        frame["latitude"], frame["longitude"] = 0., 0.
        result = analyze(frame, self.facilities)
        self.assertEqual(result.active_days.tolist(), [1, 1])
        self.assertNotIn("Persistent Thermal Source", result.classification.tolist())

    def test_live_failure_and_empty_success(self):
        with patch("src.data_loader.urlopen", side_effect=TimeoutError("secret key")):
            frame, source, report = load_live("abcdefgh", "68,7,98,36", 3)
            self.assertEqual(len(frame), len(self.data))
            self.assertIn("SYNTHETIC", source)
            self.assertNotIn("secret", report)
        with patch("src.data_loader.urlopen", return_value=BytesIO(b"latitude,longitude,acq_date\n")):
            frame, source, _ = load_live("abcdefgh", "68,7,98,36", 3)
            self.assertTrue(frame.empty)
            self.assertIn("NASA", source)

    def test_facility_validation_and_map(self):
        with self.assertRaises(ValueError):
            load_facilities(BytesIO(b"name,facility_type,latitude,longitude\nx,refinery,91,0\n"))
        malicious = self.facilities.copy()
        malicious.loc[0, "name"] = '<script>alert(1)</script> `${alert(1)}`'
        html = render_map(self.events, malicious)
        self.assertEqual(html.count("L.circleMarker("), len(self.events) + len(self.facilities))
        self.assertFalse(re.search(r'<script[^>]+src=["\']https?://', html))
        class ScriptCounter(HTMLParser):
            starts = ends = 0
            def handle_starttag(self, tag, attrs):
                self.starts += tag == "script"
            def handle_endtag(self, tag):
                self.ends += tag == "script"
        parser = ScriptCounter()
        parser.feed(html)
        self.assertEqual(parser.starts, 4)
        self.assertEqual(parser.starts, parser.ends)
        self.assertNotIn("${alert(1)}", html)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_dashboard_filters_and_fallback(self):
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, str(len(self.data)))
        app.multiselect[0].set_value([]).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "0")
        app.multiselect[0].set_value(["Industrial Fire"]).run()
        self.assertEqual(app.metric[0].value, "2")
        app.radio[0].set_value("NASA FIRMS API").run()
        with patch.dict("os.environ", {"FIRMS_MAP_KEY": ""}):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("SYNTHETIC" in item.value for item in app.info))

    def test_risk_explanations_follow_existing_criteria(self):
        for row in self.events.itertuples():
            self.assertEqual("Close to industrial" in row.risk_explanation, row.distance_km <= 5)
            self.assertEqual("High thermal intensity" in row.risk_explanation, row.frp >= 30 or row.brightness >= 340)
            self.assertEqual("Persistent thermal activity" in row.risk_explanation, row.active_days >= 3)
            self.assertEqual("FIRMS confidence" in row.risk_explanation, row.sensor_confidence >= 50)
        no_facilities = analyze(self.data, self.facilities.iloc[:0])
        self.assertFalse(no_facilities.risk_explanation.str.contains("Close to industrial").any())
        self.assertEqual(set(no_facilities.distance_label), {"Unavailable"})
        steel = self.data[self.data.scenario == "Steel plant recurrence"]
        self.assertTrue(analyze(steel, self.facilities, min_days=4).risk_explanation.str.contains("Persistent thermal activity").all())
        self.assertFalse(analyze(steel, self.facilities, min_days=5).risk_explanation.str.contains("Persistent thermal activity").any())
        refinery = self.data[self.data.scenario == "Refinery incident"].iloc[:1]
        self.assertNotIn("Close to industrial", analyze(refinery, self.facilities, proximity_km=.001).iloc[0].risk_explanation)
        frame, _ = clean_detections(read_csv(BytesIO(b"latitude,longitude,date\n0,0,2026-09-01\n")))
        self.assertTrue(analyze(frame, self.facilities.iloc[:0]).iloc[0].risk_explanation.startswith("No elevated-risk criteria"))

    def test_selected_event_explanations_and_popups(self):
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        for scenario in ["Refinery incident", "Power plant recurrence", "Forest fire", "Agricultural burning", "Unknown signal"]:
            row = self.events[self.events.scenario == scenario].iloc[0]
            app.selectbox[0].set_value(row.event_id).run()
            self.assertFalse(app.exception)
            self.assertIn(row.risk_explanation, [item.value for item in app.text])
            self.assertIn(f"Synthetic scenario: {scenario} · Provided context: {row.context}", [item.value for item in app.text])
            self.assertTrue(any(f"Risk: {row.risk_level.upper()}" in item.value for item in app.markdown))
            html = render_map(self.events[self.events.event_id == row.event_id], self.facilities)
            self.assertIn("Why is this high risk?" if row.risk_level == "High" else "Why this risk?", html)
            self.assertEqual("✓ Close to industrial" in html, row.distance_km <= 5)
            self.assertEqual("✓ Persistent thermal activity" in html, row.active_days >= 3)

    def test_offline_filters_and_csv_export(self):
        with patch("socket.create_connection", side_effect=OSError("Offline")), patch.dict("os.environ", {"FIRMS_MAP_KEY": ""}), patch("streamlit.download_button") as download:
            app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
            self.assertFalse(app.exception)
            exported = pd.read_csv(StringIO(download.call_args.args[1]))
            self.assertEqual(len(exported), 34)
            self.assertTrue(exported.synthetic.all())
            self.assertTrue(exported.data_source.str.contains("SYNTHETIC").all())
            for index, values, column in [(1, ["High"], "risk_level"), (2, ["Steel plant"], "facility_type")]:
                original = app.multiselect[index].value
                app.multiselect[index].set_value(values).run()
                self.assertFalse(app.exception)
                filtered = pd.read_csv(StringIO(download.call_args.args[1]))
                self.assertEqual(set(filtered[column]), set(values))
                app.multiselect[index].set_value(original).run()
            app.date_input[0].set_value((date(2026, 9, 6), date(2026, 9, 6))).run()
            filtered = pd.read_csv(StringIO(download.call_args.args[1]))
            self.assertEqual(len(filtered), 4)
            self.assertTrue(filtered.timestamp.str.startswith("2026-09-06").all())
            app.slider[-1].set_value(100).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value, "0")


if __name__ == "__main__":
    unittest.main()
