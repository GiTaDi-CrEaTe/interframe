"""Unit test suite for Interframe schemas, collector, deterministic rules, CV worker, and SQLite store."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPO_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from collector.mrq_orchestrator import MRQRenderOrchestrator
from collector.sequencer_collector import SequencerManifestCollector
from interframe_engine.hybrid_pipeline import InterframeHybridPipeline
from interframe_engine.persistence import InterframeStore
from interframe_engine.rule_engine import DeterministicRuleEngine
from vision_worker.comparator import ControlledRenderComparator
from vision_worker.model_adapters import FoundationModelRegistry


class TestInterframeUnitSuite(unittest.TestCase):
    def setUp(self) -> None:
        self.collector = SequencerManifestCollector()
        self.rule_engine = DeterministicRuleEngine()
        self.pipeline = InterframeHybridPipeline()
        self.comparator = ControlledRenderComparator()

    def _make_clean_manifest(self) -> dict:
        shot_list = [
            {
                "shot_id": "SH_001",
                "start_frame": 0,
                "end_frame": 47,
                "frame_rate": 24.0,
                "continuity_anchor": "continuous_action",
                "camera_binding": {
                    "camera_guid": "cam-01",
                    "camera_name": "CineCam_01",
                    "focal_length_mm": 35.0,
                    "aperture_fstop": 2.8,
                    "transform": {"location_cm": [-200.0, 0.0, 140.0], "rotation_deg": [0.0, 0.0, 0.0]},
                },
                "actor_bindings": [
                    {
                        "actor_guid": "actor-hero-01",
                        "actor_label": "BP_Hero",
                        "asset_path": "/Game/Chars/BP_Hero",
                        "asset_exists_in_registry": True,
                        "bound_in_sequencer": True,
                        "visibility_state": True,
                        "mesh_id": "SK_Hero",
                        "material_ids": ["MI_Hero_Armor"],
                        "stencil_object_id": 1,
                        "transform_samples": [
                            {"frame": 0, "time_seconds": 0.0, "location_cm": [0.0, 0.0, 0.0], "rotation_deg": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0]},
                            {"frame": 47, "time_seconds": 1.958, "location_cm": [10.0, 0.0, 0.0], "rotation_deg": [0.0, 5.0, 0.0], "scale": [1.0, 1.0, 1.0]},
                        ],
                    }
                ],
                "expected_state_rule_ids": ["r_bound", "r_asset"],
                "evidence_capture_config": {"sampled_frames": [0, 47], "rgb_frames": {}, "reference_rgb_frames": {}, "object_id_masks": {}},
            },
            {
                "shot_id": "SH_002",
                "start_frame": 48,
                "end_frame": 95,
                "frame_rate": 24.0,
                "continuity_anchor": "continuous_action",
                "camera_binding": {
                    "camera_guid": "cam-02",
                    "camera_name": "CineCam_02",
                    "focal_length_mm": 50.0,
                    "aperture_fstop": 2.8,
                    "transform": {"location_cm": [-180.0, 20.0, 140.0], "rotation_deg": [0.0, -5.0, 0.0]},
                },
                "actor_bindings": [
                    {
                        "actor_guid": "actor-hero-01",
                        "actor_label": "BP_Hero",
                        "asset_path": "/Game/Chars/BP_Hero",
                        "asset_exists_in_registry": True,
                        "bound_in_sequencer": True,
                        "visibility_state": True,
                        "mesh_id": "SK_Hero",
                        "material_ids": ["MI_Hero_Armor"],
                        "stencil_object_id": 1,
                        "transform_samples": [
                            {"frame": 48, "time_seconds": 2.0, "location_cm": [12.0, 0.0, 0.0], "rotation_deg": [0.0, 6.0, 0.0], "scale": [1.0, 1.0, 1.0]},
                            {"frame": 95, "time_seconds": 3.958, "location_cm": [20.0, 0.0, 0.0], "rotation_deg": [0.0, 8.0, 0.0], "scale": [1.0, 1.0, 1.0]},
                        ],
                    }
                ],
                "expected_state_rule_ids": ["r_bound", "r_asset"],
                "evidence_capture_config": {"sampled_frames": [48, 95], "rgb_frames": {}, "reference_rgb_frames": {}, "object_id_masks": {}},
            },
        ]
        expected_rules = [
            {
                "rule_instance_id": "r_bound",
                "rule_id": "IF-002",
                "target_actor_guid": "actor-hero-01",
                "target_actor_label": "BP_Hero",
            },
            {
                "rule_instance_id": "r_asset",
                "rule_id": "IF-007",
                "target_actor_guid": "actor-hero-01",
                "target_actor_label": "BP_Hero",
                "expected_mesh_id": "SK_Hero",
                "expected_material_ids": ["MI_Hero_Armor"],
            },
        ]
        return self.collector.build_manifest_from_scene_spec(
            project_name="UnitTestProject",
            sequence_id="LS_UnitTest_01",
            sequence_path="/Game/Cinematics/LS_UnitTest_01",
            shot_list=shot_list,
            expected_state_rules=expected_rules,
        )

    def test_clean_manifest_produces_zero_issues(self) -> None:
        manifest = self._make_clean_manifest()
        issues = self.pipeline.run(manifest, mode="B3_HYBRID", run_id="unit-clean")
        self.assertEqual(len(issues), 0)

    def test_if001_missing_asset_reference(self) -> None:
        manifest = self._make_clean_manifest()
        manifest["shot_list"][0]["actor_bindings"][0]["asset_exists_in_registry"] = False
        issues = self.rule_engine.evaluate(manifest)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["rule_id"], "IF-001")
        self.assertEqual(issues[0]["severity"], "Critical")

    def test_if002_unbound_expected_actor(self) -> None:
        manifest = self._make_clean_manifest()
        manifest["shot_list"][1]["actor_bindings"][0]["bound_in_sequencer"] = False
        issues = self.rule_engine.evaluate(manifest)
        self.assertTrue(any(i["rule_id"] == "IF-002" and i["shot_id"] == "SH_002" for i in issues))

    def test_if003_unexpected_state_change_and_declared_transition_override(self) -> None:
        manifest = self._make_clean_manifest()
        manifest["shot_list"][1]["actor_bindings"][0]["visibility_state"] = False
        issues = self.rule_engine.evaluate(manifest)
        self.assertTrue(any(i["rule_id"] == "IF-003" for i in issues))

        # Now declare SH_002 as an allowed intentional transition
        manifest["expected_state_rules"].append(
            {
                "rule_instance_id": "r_allow_sh002",
                "rule_id": "IF-003",
                "target_actor_guid": "actor-hero-01",
                "allowed_transition_shots": ["SH_002"],
            }
        )
        issues_after = self.rule_engine.evaluate(manifest)
        self.assertFalse(any(i["rule_id"] == "IF-003" for i in issues_after))

    def test_if004_transform_discontinuity(self) -> None:
        manifest = self._make_clean_manifest()
        manifest["shot_list"][1]["actor_bindings"][0]["transform_samples"][0]["location_cm"] = [150.0, 0.0, 0.0]
        issues = self.rule_engine.evaluate(manifest)
        self.assertTrue(any(i["rule_id"] == "IF-004" for i in issues))

    def test_if005_and_if006_visual_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ref_img = np.full((80, 120, 3), 100, dtype=np.uint8)
            cv2.circle(ref_img, (60, 40), 18, (50, 200, 50), -1)

            curr_img = ref_img.copy()
            # Corrupt appearance inside actor stencil 1
            cv2.circle(curr_img, (60, 40), 18, (220, 20, 220), -1)

            mask_visible = np.zeros((80, 120), dtype=np.uint8)
            cv2.circle(mask_visible, (60, 40), 18, 1, -1)

            mask_occluded = np.zeros((80, 120), dtype=np.uint8)

            ref_p = tmp_path / "ref.png"
            curr_p = tmp_path / "curr.png"
            mask_vis_p = tmp_path / "mask_vis.png"
            mask_occ_p = tmp_path / "mask_occ.png"

            cv2.imwrite(str(ref_p), ref_img)
            cv2.imwrite(str(curr_p), curr_img)
            cv2.imwrite(str(mask_vis_p), mask_visible)
            cv2.imwrite(str(mask_occ_p), mask_occluded)

            vis_ok = self.comparator.check_actor_visibility_in_mask(mask_vis_p, 1)
            self.assertTrue(vis_ok.passed)

            vis_fail = self.comparator.check_actor_visibility_in_mask(mask_occ_p, 1)
            self.assertFalse(vis_fail.passed)

            app_fail = self.comparator.compare_controlled_renders(curr_p, ref_p, mask_vis_p, 1)
            self.assertFalse(app_fail.passed)

    def test_persistence_versioning_and_reviewer_disposition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.sqlite"
            store = InterframeStore(db_path)
            manifest = self._make_clean_manifest()
            manifest["shot_list"][0]["actor_bindings"][0]["asset_exists_in_registry"] = False
            issues = self.pipeline.run(manifest, mode="B3_HYBRID", run_id="run-1")
            store.save_run("run-1", manifest, issues)

            issue_id = issues[0]["issue_id"]
            store.update_reviewer_disposition(issue_id, "intentional_change", reviewer_id="lead_qa", notes="Approved plot effect")

            # Run a second build; verify first_seen_build is preserved and disposition carries over
            manifest["source_control_revision"] = "git-second-build"
            issues_run2 = self.pipeline.run(manifest, mode="B3_HYBRID", run_id="run-2")
            store.save_run("run-2", manifest, issues_run2)

            loaded_run2 = store.get_issues_for_run("run-2")
            self.assertEqual(loaded_run2[0]["first_seen_build"], "git-8f4a2c1")
            self.assertEqual(loaded_run2[0]["reviewer_status"], "intentional_change")
            history = store.get_issue_history(issue_id)
            self.assertEqual(len(history), 2)

    def test_mrq_orchestrator_and_model_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            orch = MRQRenderOrchestrator(Path(tmp))
            manifest = self._make_clean_manifest()
            manifest["expected_state_rules"].append(
                {
                    "rule_instance_id": "r_vis_cam",
                    "rule_id": "IF-005",
                    "target_actor_guid": "actor-hero-01",
                    "must_be_visible_in_camera": True,
                }
            )
            manifest["shot_list"][0]["expected_state_rule_ids"].append("r_vis_cam")
            jobs = orch.plan_render_jobs_for_manifest(manifest, only_shots_with_visual_rules=True)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].shot_id, "SH_001")

            self.assertTrue(
                FoundationModelRegistry.verify_checkpoint_policy("opencv-controlled-comparator-v1")
            )
            self.assertFalse(
                FoundationModelRegistry.verify_checkpoint_policy("sam2-hiera-base-plus", allow_commercial_unreviewed=False)
            )


if __name__ == "__main__":
    unittest.main()
