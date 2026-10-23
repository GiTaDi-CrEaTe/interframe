"""End-to-end continuity diagnostic pipeline.

Supports three execution modes matching the scientific evaluation baselines:
- `B1_RULES_ONLY`: Deterministic Unreal metadata & invariant rules only (`IF-001`..`IF-004`, `IF-007`, `IF-008`).
- `B2_IMAGE_ONLY`: Unmasked frame-to-frame / reference image diff without engine metadata or masks.
- `B3_HYBRID`: Full Interframe pipeline combining deterministic engine data with
  Object-ID segmentation visibility checks (`IF-005`) and controlled masked appearance
  regression checks (`IF-006`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import jsonschema

from vision_worker.comparator import ControlledRenderComparator
from .rule_engine import DeterministicRuleEngine

ExecutionMode = Literal["B1_RULES_ONLY", "B2_IMAGE_ONLY", "B3_HYBRID"]


class InterframeHybridPipeline:
    """Combines Unreal Engine metadata rules with controlled rendered visual checks."""

    def __init__(
        self,
        schemas_dir: Optional[Path] = None,
        rules_config_path: Optional[Path] = None,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        self.schemas_dir = schemas_dir or (root / "schemas")
        with open(self.schemas_dir / "manifest.v1.json", "r", encoding="utf-8") as f:
            self.manifest_schema = json.load(f)
        with open(self.schemas_dir / "issue.v1.json", "r", encoding="utf-8") as f:
            self.issue_schema = json.load(f)

        self.rule_engine = DeterministicRuleEngine(rules_config_path=rules_config_path)
        self.cv_comparator = ControlledRenderComparator()

    def validate_manifest(self, manifest: Dict[str, Any]) -> None:
        jsonschema.validate(instance=manifest, schema=self.manifest_schema)

    def validate_issues(self, issues: List[Dict[str, Any]]) -> None:
        for issue in issues:
            jsonschema.validate(instance=issue, schema=self.issue_schema)

    def run(
        self,
        manifest: Dict[str, Any],
        mode: str = "B3_HYBRID",
        run_id: str = "run-20261022-001",
    ) -> List[Dict[str, Any]]:
        """Runs the continuity check pipeline in the requested baseline mode."""
        self.validate_manifest(manifest)

        if mode == "B1_RULES_ONLY":
            issues = self.rule_engine.evaluate(manifest, run_id=run_id)
            self.validate_issues(issues)
            return issues

        if mode == "B2_IMAGE_ONLY":
            issues = self._run_image_only_baseline(manifest, run_id=run_id)
            self.validate_issues(issues)
            return issues

        if mode == "B3_HYBRID":
            issues = self.rule_engine.evaluate(manifest, run_id=run_id)
            cv_issues = self._run_hybrid_visual_checks(manifest, run_id=run_id)
            all_issues = issues + cv_issues
            self.validate_issues(all_issues)
            return all_issues

        raise ValueError(f"Unsupported execution mode: {mode}")

    def _run_hybrid_visual_checks(
        self,
        manifest: Dict[str, Any],
        run_id: str,
    ) -> List[Dict[str, Any]]:
        """Runs IF-005 (Object-ID camera visibility) and IF-006 (Controlled render appearance check)."""
        cv_issues: List[Dict[str, Any]] = []
        rules_by_instance = {
            r["rule_instance_id"]: r for r in manifest.get("expected_state_rules", [])
        }

        for shot in manifest.get("shot_list", []):
            shot_id = shot["shot_id"]
            start_frame = int(shot["start_frame"])
            fps = float(shot.get("frame_rate", 24.0))
            start_sec = start_frame / max(fps, 1.0)
            ev_cfg = shot.get("evidence_capture_config", {})
            rgb_frames = ev_cfg.get("rgb_frames", {})
            ref_frames = ev_cfg.get("reference_rgb_frames", {})
            mask_frames = ev_cfg.get("object_id_masks", {})

            frame_key = str(start_frame)
            rgb_path = rgb_frames.get(frame_key)
            ref_path = ref_frames.get(frame_key)
            mask_path = mask_frames.get(frame_key)

            actors_by_guid = {a["actor_guid"]: a for a in shot.get("actor_bindings", [])}

            for r_inst_id in shot.get("expected_state_rule_ids", []):
                rule = rules_by_instance.get(r_inst_id)
                if not rule:
                    continue
                r_id = rule["rule_id"]
                target_guid = rule.get("target_actor_guid", "")
                actor = actors_by_guid.get(target_guid)
                if actor is None or not actor.get("bound_in_sequencer", True):
                    continue

                # IF-005: Expected prop not visible in camera despite engine visibility_state=True
                if r_id == "IF-005" or rule.get("must_be_visible_in_camera") is True:
                    if actor.get("visibility_state", True) and mask_path and Path(mask_path).exists():
                        stencil_id = int(actor.get("stencil_object_id", 1))
                        res = self.cv_comparator.check_actor_visibility_in_mask(
                            mask_path=mask_path,
                            stencil_object_id=stencil_id,
                        )
                        if not res.passed:
                            ev_uri = rgb_path or str(mask_path)
                            issue_id = self.rule_engine.make_issue_id(
                                manifest["sequence_id"], shot_id, start_frame, target_guid, "IF-005"
                            )
                            cv_issues.append(
                                {
                                    "issue_id": issue_id,
                                    "project_hash": manifest["project_id_hash"],
                                    "engine_version": manifest["engine_version"],
                                    "sequence_id": manifest["sequence_id"],
                                    "sequence_path": manifest["sequence_path"],
                                    "shot_id": shot_id,
                                    "frame_time": {
                                        "frame": start_frame,
                                        "seconds": round(start_sec, 4),
                                    },
                                    "actor_guid": target_guid,
                                    "actor_label": actor["actor_label"],
                                    "asset_path": actor["asset_path"],
                                    "rule_id": "IF-005",
                                    "issue_type": "Expected prop not visible",
                                    "rule_version": self.rule_engine.RULE_ENGINE_VERSION,
                                    "model_version": self.cv_comparator.MODEL_VERSION,
                                    "severity": "Major",
                                    "confidence": res.confidence,
                                    "confidence_band": "Medium",
                                    "status": "needs_review",
                                    "observation": res.explanation,
                                    "one_sentence_explanation": (
                                        f"Expected prop/actor '{actor['actor_label']}' is active in Sequencer "
                                        f"for {shot_id} but is fully occluded or absent in the rendered camera view."
                                    ),
                                    "expected_state": {
                                        "visibility_state": True,
                                        "min_mask_coverage_ratio": self.cv_comparator.min_mask_pixel_ratio,
                                    },
                                    "actual_state": {
                                        "visibility_state": True,
                                        "rendered_mask_pixels": res.mask_pixel_count,
                                        "rendered_mask_coverage_ratio": res.mask_coverage_ratio,
                                    },
                                    "evidence_uri": str(ev_uri),
                                    "supporting_evidence": {
                                        "detection_source": "hybrid_metadata_plus_cv",
                                        "rgb_frame_uri": str(rgb_path or ""),
                                        "reference_frame_uri": str(ref_path or ""),
                                        "object_id_mask_uri": str(mask_path),
                                        "visual_metrics": res.metrics,
                                    },
                                    "engine_project_revision": manifest["source_control_revision"],
                                    "collector_version": manifest["collector_version"],
                                    "reviewer_status": "unresolved",
                                    "reviewer_disposition": {
                                        "decision": "unresolved",
                                        "reviewer_id": "unassigned",
                                        "updated_at": manifest["collection_timestamp"],
                                        "notes": "",
                                    },
                                    "first_seen_build": manifest["source_control_revision"],
                                    "run_id": run_id,
                                }
                            )

                # IF-006: Appearance regression in same shot under controlled render comparison
                if r_id == "IF-006":
                    if rgb_path and ref_path and Path(rgb_path).exists() and Path(ref_path).exists():
                        stencil_id = actor.get("stencil_object_id")
                        res = self.cv_comparator.compare_controlled_renders(
                            current_rgb_path=rgb_path,
                            reference_rgb_path=ref_path,
                            mask_path=mask_path,
                            stencil_object_id=stencil_id,
                        )
                        if not res.passed:
                            issue_id = self.rule_engine.make_issue_id(
                                manifest["sequence_id"], shot_id, start_frame, target_guid, "IF-006"
                            )
                            cv_issues.append(
                                {
                                    "issue_id": issue_id,
                                    "project_hash": manifest["project_id_hash"],
                                    "engine_version": manifest["engine_version"],
                                    "sequence_id": manifest["sequence_id"],
                                    "sequence_path": manifest["sequence_path"],
                                    "shot_id": shot_id,
                                    "frame_time": {
                                        "frame": start_frame,
                                        "seconds": round(start_sec, 4),
                                    },
                                    "actor_guid": target_guid,
                                    "actor_label": actor["actor_label"],
                                    "asset_path": actor["asset_path"],
                                    "rule_id": "IF-006",
                                    "issue_type": "Appearance regression in same shot",
                                    "rule_version": self.rule_engine.RULE_ENGINE_VERSION,
                                    "model_version": self.cv_comparator.MODEL_VERSION,
                                    "severity": "Minor",
                                    "confidence": res.confidence,
                                    "confidence_band": "Candidate / Needs Review",
                                    "status": "needs_review",
                                    "observation": res.explanation,
                                    "one_sentence_explanation": (
                                        f"Actor '{actor['actor_label']}' in {shot_id} exhibits a visual appearance "
                                        f"regression against the controlled reference render (SSIM={res.structural_similarity:.3f})."
                                    ),
                                    "expected_state": {
                                        "min_structural_similarity": self.cv_comparator.min_structural_similarity,
                                        "max_chromatic_shift": self.cv_comparator.max_chromatic_shift,
                                    },
                                    "actual_state": {
                                        "structural_similarity": res.structural_similarity,
                                        "chromatic_delta": res.chromatic_delta,
                                        "gradient_similarity": res.gradient_similarity,
                                    },
                                    "evidence_uri": str(rgb_path),
                                    "supporting_evidence": {
                                        "detection_source": "hybrid_metadata_plus_cv",
                                        "rgb_frame_uri": str(rgb_path),
                                        "reference_frame_uri": str(ref_path),
                                        "object_id_mask_uri": str(mask_path or ""),
                                        "visual_metrics": res.metrics,
                                    },
                                    "engine_project_revision": manifest["source_control_revision"],
                                    "collector_version": manifest["collector_version"],
                                    "reviewer_status": "unresolved",
                                    "reviewer_disposition": {
                                        "decision": "unresolved",
                                        "reviewer_id": "unassigned",
                                        "updated_at": manifest["collection_timestamp"],
                                        "notes": "",
                                    },
                                    "first_seen_build": manifest["source_control_revision"],
                                    "run_id": run_id,
                                }
                            )

        return cv_issues

    def _run_image_only_baseline(
        self,
        manifest: Dict[str, Any],
        run_id: str,
    ) -> List[Dict[str, Any]]:
        """Runs Baseline B2 (Image-only): compares adjacent shot frames and reference frames without metadata."""
        b2_issues: List[Dict[str, Any]] = []
        shots = manifest.get("shot_list", [])

        for idx, shot in enumerate(shots):
            shot_id = shot["shot_id"]
            start_frame = int(shot["start_frame"])
            fps = float(shot.get("frame_rate", 24.0))
            start_sec = start_frame / max(fps, 1.0)
            ev_cfg = shot.get("evidence_capture_config", {})
            rgb_frames = ev_cfg.get("rgb_frames", {})
            ref_frames = ev_cfg.get("reference_rgb_frames", {})

            curr_rgb = rgb_frames.get(str(start_frame))
            ref_rgb = ref_frames.get(str(start_frame))

            # 1. Image-only reference vs current comparison (unmasked)
            if curr_rgb and ref_rgb and Path(curr_rgb).exists() and Path(ref_rgb).exists():
                res = self.cv_comparator.compute_naive_image_only_diff(curr_rgb, ref_rgb)
                if not res.passed:
                    first_actor = (
                        shot["actor_bindings"][0]
                        if shot.get("actor_bindings")
                        else {"actor_guid": "unknown", "actor_label": "SceneFrame", "asset_path": "/Game/Scene"}
                    )
                    issue_id = self.rule_engine.make_issue_id(
                        manifest["sequence_id"], shot_id, start_frame, first_actor["actor_guid"], "IF-006"
                    )
                    b2_issues.append(
                        {
                            "issue_id": issue_id,
                            "project_hash": manifest["project_id_hash"],
                            "engine_version": manifest["engine_version"],
                            "sequence_id": manifest["sequence_id"],
                            "sequence_path": manifest["sequence_path"],
                            "shot_id": shot_id,
                            "frame_time": {"frame": start_frame, "seconds": round(start_sec, 4)},
                            "actor_guid": first_actor["actor_guid"],
                            "actor_label": first_actor["actor_label"],
                            "asset_path": first_actor["asset_path"],
                            "rule_id": "IF-006",
                            "issue_type": "Appearance regression in same shot",
                            "rule_version": self.rule_engine.RULE_ENGINE_VERSION,
                            "model_version": "b2-naive-image-diff-1.0",
                            "severity": "Minor",
                            "confidence": res.confidence,
                            "confidence_band": "Candidate / Needs Review",
                            "status": "needs_review",
                            "observation": res.explanation,
                            "one_sentence_explanation": f"Unmasked frame diff exceeded threshold in {shot_id} (RawL1={res.raw_pixel_l1:.2f}).",
                            "expected_state": {"raw_pixel_l1_max": 8.5},
                            "actual_state": {"raw_pixel_l1": res.raw_pixel_l1, "ssim": res.structural_similarity},
                            "evidence_uri": str(curr_rgb),
                            "supporting_evidence": {
                                "detection_source": "cv_only",
                                "rgb_frame_uri": str(curr_rgb),
                                "reference_frame_uri": str(ref_rgb),
                                "object_id_mask_uri": "",
                                "visual_metrics": res.metrics,
                            },
                            "engine_project_revision": manifest["source_control_revision"],
                            "collector_version": manifest["collector_version"],
                            "reviewer_status": "unresolved",
                            "reviewer_disposition": {
                                "decision": "unresolved",
                                "reviewer_id": "unassigned",
                                "updated_at": manifest["collection_timestamp"],
                                "notes": "",
                            },
                            "first_seen_build": manifest["source_control_revision"],
                            "run_id": run_id,
                        }
                    )

            # 2. Image-only boundary comparison across adjacent shots (without knowing camera cuts or declared transitions)
            if idx > 0:
                prev_shot = shots[idx - 1]
                prev_start = int(prev_shot["start_frame"])
                prev_rgb = prev_shot.get("evidence_capture_config", {}).get("rgb_frames", {}).get(str(prev_start))
                if curr_rgb and prev_rgb and Path(curr_rgb).exists() and Path(prev_rgb).exists():
                    res = self.cv_comparator.compute_naive_image_only_diff(
                        curr_rgb, prev_rgb, raw_l1_threshold=14.0
                    )
                    if not res.passed:
                        first_actor = (
                            shot["actor_bindings"][0]
                            if shot.get("actor_bindings")
                            else {"actor_guid": "unknown", "actor_label": "SceneFrame", "asset_path": "/Game/Scene"}
                        )
                        issue_id = self.rule_engine.make_issue_id(
                            manifest["sequence_id"], shot_id, start_frame, first_actor["actor_guid"], "IF-003"
                        )
                        b2_issues.append(
                            {
                                "issue_id": issue_id,
                                "project_hash": manifest["project_id_hash"],
                                "engine_version": manifest["engine_version"],
                                "sequence_id": manifest["sequence_id"],
                                "sequence_path": manifest["sequence_path"],
                                "shot_id": shot_id,
                                "frame_time": {"frame": start_frame, "seconds": round(start_sec, 4)},
                                "actor_guid": first_actor["actor_guid"],
                                "actor_label": first_actor["actor_label"],
                                "asset_path": first_actor["asset_path"],
                                "rule_id": "IF-003",
                                "issue_type": "Unexpected state change",
                                "rule_version": self.rule_engine.RULE_ENGINE_VERSION,
                                "model_version": "b2-naive-image-diff-1.0",
                                "severity": "Major",
                                "confidence": 0.60,
                                "confidence_band": "Candidate / Needs Review",
                                "status": "needs_review",
                                "observation": res.explanation,
                                "one_sentence_explanation": f"Unmasked shot boundary frame difference between {prev_shot['shot_id']} and {shot_id}.",
                                "expected_state": {"raw_pixel_l1_max": 14.0},
                                "actual_state": {"raw_pixel_l1": res.raw_pixel_l1, "ssim": res.structural_similarity},
                                "evidence_uri": str(curr_rgb),
                                "supporting_evidence": {
                                    "detection_source": "cv_only",
                                    "rgb_frame_uri": str(curr_rgb),
                                    "reference_frame_uri": str(prev_rgb),
                                    "object_id_mask_uri": "",
                                    "visual_metrics": res.metrics,
                                },
                                "engine_project_revision": manifest["source_control_revision"],
                                "collector_version": manifest["collector_version"],
                                "reviewer_status": "unresolved",
                                "reviewer_disposition": {
                                    "decision": "unresolved",
                                    "reviewer_id": "unassigned",
                                    "updated_at": manifest["collection_timestamp"],
                                    "notes": "",
                                },
                                "first_seen_build": manifest["source_control_revision"],
                                "run_id": run_id,
                            }
                        )

        return b2_issues
