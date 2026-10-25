"""Unit tests for CLI parsing behavior and manifest schema validation."""

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPO_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

import jsonschema

from collector.sequencer_collector import SequencerManifestCollector
from interframe_engine.cli import main as cli_main


class TestCliAndSchema(unittest.TestCase):
    def setUp(self) -> None:
        self.collector = SequencerManifestCollector()

    def test_cli_version_flag(self) -> None:
        stdout_buf = io.StringIO()
        with redirect_stdout(stdout_buf), self.assertRaises(SystemExit) as cm:
            cli_main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("interframe 1.0.0", stdout_buf.getvalue())

    def test_cli_short_version_flag(self) -> None:
        stdout_buf = io.StringIO()
        with redirect_stdout(stdout_buf), self.assertRaises(SystemExit) as cm:
            cli_main(["-v"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("interframe 1.0.0", stdout_buf.getvalue())

    def test_cli_missing_command_exits(self) -> None:
        stderr_buf = io.StringIO()
        with redirect_stderr(stderr_buf), self.assertRaises(SystemExit) as cm:
            cli_main([])
        self.assertEqual(cm.exception.code, 2)

    def test_cli_unknown_subcommand_exits(self) -> None:
        stderr_buf = io.StringIO()
        with redirect_stderr(stderr_buf), self.assertRaises(SystemExit) as cm:
            cli_main(["nonexistent_subcommand"])
        self.assertEqual(cm.exception.code, 2)

    def test_schema_validation_success_on_valid_manifest(self) -> None:
        valid_manifest = self.collector.build_manifest_from_scene_spec(
            project_name="ValidProj",
            sequence_id="LS_Valid",
            sequence_path="/Game/Cinematics/LS_Valid",
            shot_list=[
                {
                    "shot_id": "SH_01",
                    "start_frame": 0,
                    "end_frame": 24,
                    "frame_rate": 24.0,
                    "camera_binding": {
                        "camera_guid": "cam-1",
                        "camera_name": "CineCam_01",
                        "focal_length_mm": 35.0,
                        "aperture_fstop": 2.8,
                        "transform": {"location_cm": [0.0, 0.0, 0.0], "rotation_deg": [0.0, 0.0, 0.0]},
                    },
                    "actor_bindings": [],
                    "expected_state_rule_ids": [],
                    "evidence_capture_config": {
                        "sampled_frames": [0],
                        "rgb_frames": {},
                        "reference_rgb_frames": {},
                        "object_id_masks": {},
                    },
                }
            ],
        )
        # Should not raise
        self.collector.validate_manifest(valid_manifest)

    def test_schema_validation_fails_on_missing_required_field(self) -> None:
        invalid_manifest = {
            "schema_version": "1.0.0",
            # Missing required fields like project_id_hash, sequence_id, shot_list
        }
        with self.assertRaises(jsonschema.ValidationError):
            self.collector.validate_manifest(invalid_manifest)

    def test_schema_validation_fails_on_invalid_shot_structure(self) -> None:
        invalid_manifest = {
            "schema_version": "1.0.0",
            "project_id_hash": "a1b2c3d4e5f6",
            "engine_version": "5.8.0",
            "source_control_revision": "HEAD",
            "sequence_id": "LS_Invalid",
            "sequence_path": "/Game/Cinematics/LS_Invalid",
            "shot_list": "not-a-list",  # Must be an array
            "render_profile_id": "Default",
            "collection_timestamp": "2026-10-25T00:00:00Z",
            "collector_version": "1.0.0",
        }
        with self.assertRaises(jsonschema.ValidationError):
            self.collector.validate_manifest(invalid_manifest)


if __name__ == "__main__":
    unittest.main()
