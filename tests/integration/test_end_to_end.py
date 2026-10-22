"""Integration tests verifying the LEAVE_ALIVE synthetic benchmark and B1/B2/B3 baselines."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPO_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.evaluate_baselines import run_full_evaluation


class TestInterframeIntegrationSuite(unittest.TestCase):
    def test_full_evaluation_protocol_and_hypotheses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            eval_res = run_full_evaluation(output_dir=Path(tmp))
            summary = eval_res["benchmark_summary"]
            self.assertEqual(summary["total_sequences"], 25)
            self.assertEqual(summary["total_shot_boundaries"], 100)
            self.assertEqual(summary["total_seeded_faults"], 105)

            b1 = eval_res["baselines"]["B1_RULES_ONLY"]
            b2 = eval_res["baselines"]["B2_IMAGE_ONLY"]
            b3 = eval_res["baselines"]["B3_HYBRID"]

            # B3 Hybrid must detect all 105 seeded faults with high precision
            self.assertGreaterEqual(b3["precision"], 0.95)
            self.assertGreaterEqual(b3["recall"], 0.95)
            self.assertGreater(b3["recall"], b1["recall"])
            self.assertGreater(b3["precision"], b2["precision"])
            self.assertTrue(eval_res["hypothesis_gates"]["H1_engine_metadata_reduces_fp_vs_image_only"]["passed"])
            self.assertTrue(eval_res["hypothesis_gates"]["H2_mvp_saves_review_time"]["h2_pass"])

    def test_cli_analyze_and_review_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            # Pick any generated manifest or build one via evaluate_baselines
            manifest_dir = REPO_ROOT / "rules" / "fixtures"
            manifests = sorted(manifest_dir.glob("*.json"))
            self.assertTrue(len(manifests) > 0, "Run evaluation before or during integration test")

            out_json = tmp_p / "out.json"
            out_csv = tmp_p / "out.csv"
            out_html = tmp_p / "out.html"
            db_file = tmp_p / "cli.sqlite"

            cli_script = REPO_ROOT / "python" / "interframe_engine" / "cli.py"
            cmd = [
                sys.executable,
                str(cli_script),
                "analyze",
                "--manifest",
                str(manifests[0]),
                "--out",
                str(out_json),
                "--csv",
                str(out_csv),
                "--html",
                str(out_html),
                "--db",
                str(db_file),
                "--mode",
                "B3_HYBRID",
                "--run-id",
                "cli-int-001",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.assertIn("Analyzed", proc.stdout)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_csv.exists())
            self.assertTrue(out_html.exists())

            report = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertGreater(report["total_issues"], 0)
            first_issue_id = report["issues"][0]["issue_id"]

            rev_cmd = [
                sys.executable,
                str(cli_script),
                "review",
                "--db",
                str(db_file),
                "--issue-id",
                first_issue_id,
                "--decision",
                "true_positive",
                "--reviewer",
                "qa_lead",
                "--notes",
                "Confirmed in Sequencer cut track",
            ]
            rev_proc = subprocess.run(rev_cmd, capture_output=True, text=True, check=True)
            self.assertIn("true_positive", rev_proc.stdout)


if __name__ == "__main__":
    unittest.main()
