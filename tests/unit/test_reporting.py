"""Unit tests for Interframe reporting and export functionality."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from interframe_engine.reporting import InterframeReportExporter


class TestInterframeReporting(unittest.TestCase):
    def setUp(self) -> None:
        self.sample_issues = [
            {
                "issue_id": "ISS-TEST-001",
                "rule_id": "IF-001",
                "issue_type": "invalid_missing_asset",
                "severity": "Critical",
                "confidence": 1.0,
                "status": "active",
                "sequence_id": "LS_TestScene",
                "sequence_path": "/Game/Cinematics/LS_TestScene",
                "shot_id": "shot_010",
                "frame_time": {"frame": 24, "seconds": 1.0},
                "actor_label": "HeroProp",
                "actor_guid": "1111-2222-3333",
                "asset_path": "/Game/Props/SM_HeroProp",
                "one_sentence_explanation": "Asset reference not found in registry.",
                "reviewer_status": "unresolved",
                "first_seen_build": "CL-100",
                "run_id": "run-test-001",
                "evidence_uri": "file:///tmp/evidence.png",
            }
        ]

    def test_json_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.json"
            result = InterframeReportExporter.export_json(
                self.sample_issues, out_path, metadata={"run_id": "run-test-001"}
            )
            self.assertEqual(result, out_path)
            self.assertTrue(out_path.exists())

            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(data["metadata"]["run_id"], "run-test-001")
            self.assertEqual(data["total_issues"], 1)
            self.assertEqual(data["issues"][0]["issue_id"], "ISS-TEST-001")

    def test_csv_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.csv"
            result = InterframeReportExporter.export_csv(self.sample_issues, out_path)
            self.assertEqual(result, out_path)
            self.assertTrue(out_path.exists())

            with open(out_path, mode="r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                self.assertEqual(len(reader), 1)
                self.assertEqual(reader[0]["issue_id"], "ISS-TEST-001")
                self.assertEqual(reader[0]["rule_id"], "IF-001")
                self.assertEqual(reader[0]["frame"], "24")

    def test_html_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.html"
            result = InterframeReportExporter.export_html(
                self.sample_issues, out_path, title="Custom Interframe QA Report"
            )
            self.assertEqual(result, out_path)
            self.assertTrue(out_path.exists())

            html_text = out_path.read_text(encoding="utf-8")
            self.assertIn("Custom Interframe QA Report", html_text)
            self.assertIn("ISS-TEST-001", html_text)
            self.assertIn("Critical", html_text)


if __name__ == "__main__":
    unittest.main()
