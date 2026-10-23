"""Deterministic continuity rule engine for rules IF-001..IF-004, IF-007, IF-008.

Rule coverage:
- IF-001: Invalid/missing asset reference (Asset Registry check, High confidence, Critical)
- IF-002: Expected actor unbound in shot (Explicit expected rule references unbound actor, High confidence, Critical)
- IF-003: Unexpected state change across shot boundary (Mesh/material/visibility changes outside declared transitions)
- IF-004: Transform discontinuity across continuous_action shot boundary (Position/rotation jump exceeds threshold)
- IF-007: Unexpected asset substitution (Asset/mesh/material ID differs from declared expected asset invariant)
- IF-008: Rule/data-quality problem (Missing expected-state rule target or contradictory rule definitions)
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional


class DeterministicRuleEngine:
    """Evaluates deterministic engine-truth continuity rules over a LevelSequence shot manifest."""

    RULE_ENGINE_VERSION = "1.0.0"

    def __init__(self, rules_config_path: Optional[Path] = None) -> None:
        if rules_config_path is None:
            rules_config_path = (
                Path(__file__).resolve().parents[2] / "rules" / "default_continuity_rules.json"
            )
        with open(rules_config_path, "r", encoding="utf-8") as f:
            self.rules_pack = json.load(f)
        self.rules_by_id: Dict[str, Dict[str, Any]] = {
            r["rule_id"]: r for r in self.rules_pack["rules"]
        }

    @staticmethod
    def make_issue_id(
        sequence_id: str,
        shot_id: str,
        frame: int,
        actor_guid: str,
        rule_id: str,
    ) -> str:
        raw = f"{sequence_id}:{shot_id}:{frame}:{actor_guid}:{rule_id}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        return f"ISS-{rule_id.replace('-', '')}-{digest.upper()}"

    @staticmethod
    def euclidean_distance_cm(loc_a: List[float], loc_b: List[float]) -> float:
        return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(loc_a, loc_b)))

    @staticmethod
    def angular_distance_deg(rot_a: List[float], rot_b: List[float]) -> float:
        diffs = []
        for a, b in zip(rot_a, rot_b):
            d = abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)
            diffs.append(d)
        return max(diffs) if diffs else 0.0

    def _build_issue(
        self,
        manifest: Dict[str, Any],
        shot_id: str,
        frame: int,
        seconds: float,
        actor_guid: str,
        actor_label: str,
        asset_path: str,
        rule_id: str,
        severity: str,
        confidence: float,
        status: str,
        observation: str,
        explanation: str,
        expected_state: Dict[str, Any],
        actual_state: Dict[str, Any],
        evidence_uri: str,
        run_id: str,
        supporting_evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        issue_id = self.make_issue_id(manifest["sequence_id"], shot_id, frame, actor_guid, rule_id)
        rule_meta = self.rules_by_id[rule_id]
        conf_band = (
            "High"
            if confidence >= 0.90
            else ("Medium" if confidence >= 0.80 else "Candidate / Needs Review")
        )
        return {
            "issue_id": issue_id,
            "project_hash": manifest["project_id_hash"],
            "engine_version": manifest["engine_version"],
            "sequence_id": manifest["sequence_id"],
            "sequence_path": manifest["sequence_path"],
            "shot_id": shot_id,
            "frame_time": {"frame": int(frame), "seconds": round(float(seconds), 4)},
            "actor_guid": actor_guid,
            "actor_label": actor_label,
            "asset_path": asset_path,
            "rule_id": rule_id,
            "issue_type": rule_meta["defect_type"],
            "rule_version": self.RULE_ENGINE_VERSION,
            "model_version": "none (deterministic_rule)",
            "severity": severity,
            "confidence": round(float(confidence), 3),
            "confidence_band": conf_band,
            "status": status,
            "observation": observation,
            "one_sentence_explanation": explanation,
            "expected_state": expected_state,
            "actual_state": actual_state,
            "evidence_uri": evidence_uri,
            "supporting_evidence": supporting_evidence
            or {
                "detection_source": "deterministic_engine_rule",
                "rgb_frame_uri": evidence_uri,
                "reference_frame_uri": "",
                "object_id_mask_uri": "",
                "visual_metrics": {},
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

    def evaluate(self, manifest: Dict[str, Any], run_id: str = "run-default") -> List[Dict[str, Any]]:
        """Runs all deterministic checks (IF-001, IF-002, IF-003, IF-004, IF-007, IF-008)."""
        issues: List[Dict[str, Any]] = []
        shots = manifest.get("shot_list", [])
        expected_rules = manifest.get("expected_state_rules", [])
        rules_by_instance = {r["rule_instance_id"]: r for r in expected_rules}

        # 1. Check IF-008: Rule/data-quality problem (contradictory or malformed rules)
        seen_visibility_expectations: Dict[tuple[str, str], bool] = {}
        for rule in expected_rules:
            r_id = rule.get("rule_id")
            r_inst = rule.get("rule_instance_id", "unknown_rule")
            target_guid = rule.get("target_actor_guid", "")

            if r_id == "IF-008" or rule.get("contradictory_flag") is True:
                first_shot = shots[0] if shots else {"shot_id": "SH_001", "start_frame": 0}
                issues.append(
                    self._build_issue(
                        manifest=manifest,
                        shot_id=first_shot["shot_id"],
                        frame=first_shot.get("start_frame", 0),
                        seconds=0.0,
                        actor_guid=target_guid or "rule_config",
                        actor_label=rule.get("target_actor_label", "RuleConfig"),
                        asset_path=rule.get("expected_asset_path", "/Game/Config/Rules"),
                        rule_id="IF-008",
                        severity="Informational",
                        confidence=1.0,
                        status="configuration_warning",
                        observation=f"Rule instance '{r_inst}' contains contradictory or incomplete expected-state constraints.",
                        explanation=f"Rule configuration '{r_inst}' defines contradictory expected state parameters; fix rule definition instead of flagging a scene defect.",
                        expected_state={"valid_rule_schema": True},
                        actual_state={"rule_instance_id": r_inst, "contradictory_flag": True},
                        evidence_uri=f"manifest://{manifest['sequence_id']}/rules/{r_inst}",
                        run_id=run_id,
                    )
                )
                continue

            if target_guid and "expected_visible" in rule:
                key = (target_guid, "visibility")
                if key in seen_visibility_expectations and seen_visibility_expectations[key] != rule["expected_visible"]:
                    first_shot = shots[0] if shots else {"shot_id": "SH_001", "start_frame": 0}
                    issues.append(
                        self._build_issue(
                            manifest=manifest,
                            shot_id=first_shot["shot_id"],
                            frame=first_shot.get("start_frame", 0),
                            seconds=0.0,
                            actor_guid=target_guid,
                            actor_label=rule.get("target_actor_label", target_guid),
                            asset_path=rule.get("expected_asset_path", "/Game/Config/Rules"),
                            rule_id="IF-008",
                            severity="Informational",
                            confidence=1.0,
                            status="configuration_warning",
                            observation=f"Contradictory visibility expectations declared for actor {target_guid}.",
                            explanation=f"Conflicting expected_visible rules found for actor '{rule.get('target_actor_label', target_guid)}'; resolve contradictory rule definitions.",
                            expected_state={"expected_visible": seen_visibility_expectations[key]},
                            actual_state={"expected_visible": rule["expected_visible"]},
                            evidence_uri=f"manifest://{manifest['sequence_id']}/rules/{r_inst}",
                            run_id=run_id,
                        )
                    )
                seen_visibility_expectations[key] = rule["expected_visible"]

        # 2. Per-shot deterministic checks: IF-001, IF-002, IF-007
        for shot in shots:
            shot_id = shot["shot_id"]
            start_frame = int(shot["start_frame"])
            fps = float(shot.get("frame_rate", 24.0))
            start_sec = start_frame / max(fps, 1.0)
            ev_cfg = shot.get("evidence_capture_config", {})
            rgb_map = ev_cfg.get("rgb_frames", {})
            default_ev_uri = (
                rgb_map.get(str(start_frame))
                or f"manifest://{manifest['sequence_id']}/{shot_id}/frame_{start_frame}"
            )

            actors_by_guid: Dict[str, Dict[str, Any]] = {
                a["actor_guid"]: a for a in shot.get("actor_bindings", [])
            }

            # IF-001: Invalid/missing asset reference in shot actor bindings
            for actor in shot.get("actor_bindings", []):
                if not actor.get("asset_exists_in_registry", True) or not actor.get("asset_path", "").startswith("/Game/"):
                    issues.append(
                        self._build_issue(
                            manifest=manifest,
                            shot_id=shot_id,
                            frame=start_frame,
                            seconds=start_sec,
                            actor_guid=actor["actor_guid"],
                            actor_label=actor["actor_label"],
                            asset_path=actor.get("asset_path", "<missing>"),
                            rule_id="IF-001",
                            severity="Critical",
                            confidence=0.99,
                            status="failed",
                            observation=f"Asset Registry returned missing/unresolvable reference for '{actor.get('asset_path')}' bound to actor '{actor['actor_label']}'.",
                            explanation=f"Actor '{actor['actor_label']}' in {shot_id} references missing or unresolvable asset '{actor.get('asset_path')}'.",
                            expected_state={"asset_exists_in_registry": True, "valid_package_prefix": "/Game/"},
                            actual_state={
                                "asset_exists_in_registry": actor.get("asset_exists_in_registry", False),
                                "asset_path": actor.get("asset_path", ""),
                            },
                            evidence_uri=default_ev_uri,
                            run_id=run_id,
                        )
                    )

            # Evaluate explicit shot rules for IF-002 (unbound actor) and IF-007 (asset substitution)
            for r_inst_id in shot.get("expected_state_rule_ids", []):
                rule = rules_by_instance.get(r_inst_id)
                if not rule:
                    continue
                r_id = rule["rule_id"]
                target_guid = rule.get("target_actor_guid", "")
                target_label = rule.get("target_actor_label", target_guid)
                actor_obj = actors_by_guid.get(target_guid)

                if r_id == "IF-002":
                    if actor_obj is None or not actor_obj.get("bound_in_sequencer", True):
                        issues.append(
                            self._build_issue(
                                manifest=manifest,
                                shot_id=shot_id,
                                frame=start_frame,
                                seconds=start_sec,
                                actor_guid=target_guid,
                                actor_label=target_label,
                                asset_path=rule.get("expected_asset_path", "/Game/Cinematics/Unbound"),
                                rule_id="IF-002",
                                severity="Critical",
                                confidence=0.98,
                                status="failed",
                                observation=f"Expected actor '{target_label}' ({target_guid}) required by rule '{r_inst_id}' is unbound in {shot_id}.",
                                explanation=f"Required actor '{target_label}' is missing or unbound in Level Sequence shot {shot_id}.",
                                expected_state={"bound_in_sequencer": True, "actor_guid": target_guid},
                                actual_state={
                                    "bound_in_sequencer": False if actor_obj is None else actor_obj.get("bound_in_sequencer", False)
                                },
                                evidence_uri=default_ev_uri,
                                run_id=run_id,
                            )
                        )

                elif r_id == "IF-007" and actor_obj is not None:
                    exp_mesh = rule.get("expected_mesh_id")
                    exp_mats = rule.get("expected_material_ids")
                    exp_asset = rule.get("expected_asset_path")

                    mesh_mismatch = exp_mesh is not None and actor_obj.get("mesh_id") != exp_mesh
                    mat_mismatch = exp_mats is not None and actor_obj.get("material_ids") != exp_mats
                    asset_mismatch = exp_asset is not None and actor_obj.get("asset_path") != exp_asset

                    if mesh_mismatch or mat_mismatch or asset_mismatch:
                        issues.append(
                            self._build_issue(
                                manifest=manifest,
                                shot_id=shot_id,
                                frame=start_frame,
                                seconds=start_sec,
                                actor_guid=target_guid,
                                actor_label=actor_obj["actor_label"],
                                asset_path=actor_obj["asset_path"],
                                rule_id="IF-007",
                                severity="Major",
                                confidence=0.95,
                                status="failed",
                                observation=f"Actor '{actor_obj['actor_label']}' in {shot_id} uses substituted mesh/material/asset compared to declared invariant '{r_inst_id}'.",
                                explanation=f"Actor '{actor_obj['actor_label']}' in {shot_id} substituted '{actor_obj.get('mesh_id')}' / '{actor_obj.get('material_ids')}' instead of declared asset invariant.",
                                expected_state={
                                    "mesh_id": exp_mesh or actor_obj.get("mesh_id"),
                                    "material_ids": exp_mats or actor_obj.get("material_ids"),
                                    "asset_path": exp_asset or actor_obj.get("asset_path"),
                                },
                                actual_state={
                                    "mesh_id": actor_obj.get("mesh_id"),
                                    "material_ids": actor_obj.get("material_ids"),
                                    "asset_path": actor_obj.get("asset_path"),
                                },
                                evidence_uri=default_ev_uri,
                                run_id=run_id,
                            )
                        )

        # 3. Cross-shot temporal boundary checks: IF-003 (Unexpected state change) & IF-004 (Transform discontinuity)
        allowed_transitions_by_actor: Dict[str, set[str]] = {}
        custom_jump_thresholds: Dict[str, tuple[float, float]] = {}
        for rule in expected_rules:
            t_guid = rule.get("target_actor_guid")
            if t_guid:
                if rule.get("allowed_transition_shots"):
                    allowed_transitions_by_actor.setdefault(t_guid, set()).update(
                        rule["allowed_transition_shots"]
                    )
                if "max_position_jump_cm" in rule or "max_rotation_jump_deg" in rule:
                    custom_jump_thresholds[t_guid] = (
                        float(rule.get("max_position_jump_cm", 45.0)),
                        float(rule.get("max_rotation_jump_deg", 30.0)),
                    )

        default_pos_thresh = float(
            self.rules_by_id["IF-004"]["thresholds"].get("max_position_jump_cm", 45.0)
        )
        default_rot_thresh = float(
            self.rules_by_id["IF-004"]["thresholds"].get("max_rotation_jump_deg", 30.0)
        )

        for idx in range(len(shots) - 1):
            prev_shot = shots[idx]
            curr_shot = shots[idx + 1]
            curr_shot_id = curr_shot["shot_id"]
            curr_start_frame = int(curr_shot["start_frame"])
            fps = float(curr_shot.get("frame_rate", 24.0))
            curr_start_sec = curr_start_frame / max(fps, 1.0)
            anchor = curr_shot.get("continuity_anchor", "continuous_action")

            ev_cfg = curr_shot.get("evidence_capture_config", {})
            rgb_map = ev_cfg.get("rgb_frames", {})
            ev_uri = (
                rgb_map.get(str(curr_start_frame))
                or f"manifest://{manifest['sequence_id']}/{curr_shot_id}/frame_{curr_start_frame}"
            )

            prev_actors = {a["actor_guid"]: a for a in prev_shot.get("actor_bindings", [])}
            curr_actors = {a["actor_guid"]: a for a in curr_shot.get("actor_bindings", [])}

            for guid, curr_a in curr_actors.items():
                if guid not in prev_actors:
                    continue
                prev_a = prev_actors[guid]
                if not prev_a.get("bound_in_sequencer", True) or not curr_a.get("bound_in_sequencer", True):
                    continue

                is_allowed_transition = curr_shot_id in allowed_transitions_by_actor.get(guid, set())

                # IF-003: Unexpected visibility, mesh, or material state toggle across shot boundary
                vis_changed = prev_a.get("visibility_state", True) != curr_a.get("visibility_state", True)
                mesh_changed = prev_a.get("mesh_id") != curr_a.get("mesh_id")
                mat_changed = prev_a.get("material_ids") != curr_a.get("material_ids")

                # Check if already flagged as explicit IF-007 in curr_shot
                already_if007 = any(
                    iss["shot_id"] == curr_shot_id
                    and iss["actor_guid"] == guid
                    and iss["rule_id"] == "IF-007"
                    for iss in issues
                )

                if (vis_changed or mesh_changed or mat_changed) and not is_allowed_transition and not already_if007:
                    change_desc = []
                    if vis_changed:
                        change_desc.append(
                            f"visibility toggled {prev_a.get('visibility_state')} -> {curr_a.get('visibility_state')}"
                        )
                    if mesh_changed:
                        change_desc.append(
                            f"mesh changed '{prev_a.get('mesh_id')}' -> '{curr_a.get('mesh_id')}'"
                        )
                    if mat_changed:
                        change_desc.append(
                            f"materials changed {prev_a.get('material_ids')} -> {curr_a.get('material_ids')}"
                        )
                    joined_desc = "; ".join(change_desc)
                    issues.append(
                        self._build_issue(
                            manifest=manifest,
                            shot_id=curr_shot_id,
                            frame=curr_start_frame,
                            seconds=curr_start_sec,
                            actor_guid=guid,
                            actor_label=curr_a["actor_label"],
                            asset_path=curr_a["asset_path"],
                            rule_id="IF-003",
                            severity="Major",
                            confidence=0.86,
                            status="failed",
                            observation=f"Unexpected state change between {prev_shot['shot_id']} and {curr_shot_id} for '{curr_a['actor_label']}': {joined_desc}.",
                            explanation=f"Actor '{curr_a['actor_label']}' had an undeclared state change across cut {prev_shot['shot_id']} -> {curr_shot_id} ({joined_desc}).",
                            expected_state={
                                "visibility_state": prev_a.get("visibility_state"),
                                "mesh_id": prev_a.get("mesh_id"),
                                "material_ids": prev_a.get("material_ids"),
                            },
                            actual_state={
                                "visibility_state": curr_a.get("visibility_state"),
                                "mesh_id": curr_a.get("mesh_id"),
                                "material_ids": curr_a.get("material_ids"),
                            },
                            evidence_uri=ev_uri,
                            run_id=run_id,
                        )
                    )

                # IF-004: Transform discontinuity across continuous_action cut boundary
                if anchor == "continuous_action" and not is_allowed_transition:
                    prev_samples = prev_a.get("transform_samples", [])
                    curr_samples = curr_a.get("transform_samples", [])
                    if prev_samples and curr_samples:
                        last_sample = sorted(prev_samples, key=lambda s: s["frame"])[-1]
                        first_sample = sorted(curr_samples, key=lambda s: s["frame"])[0]

                        pos_jump = self.euclidean_distance_cm(
                            last_sample["location_cm"], first_sample["location_cm"]
                        )
                        rot_jump = self.angular_distance_deg(
                            last_sample["rotation_deg"], first_sample["rotation_deg"]
                        )
                        pos_thresh, rot_thresh = custom_jump_thresholds.get(
                            guid, (default_pos_thresh, default_rot_thresh)
                        )
                        if pos_jump > pos_thresh or rot_jump > rot_thresh:
                            issues.append(
                                self._build_issue(
                                    manifest=manifest,
                                    shot_id=curr_shot_id,
                                    frame=curr_start_frame,
                                    seconds=curr_start_sec,
                                    actor_guid=guid,
                                    actor_label=curr_a["actor_label"],
                                    asset_path=curr_a["asset_path"],
                                    rule_id="IF-004",
                                    severity="Major",
                                    confidence=0.81,
                                    status="needs_review",
                                    observation=(
                                        f"Transform jump across continuous cut {prev_shot['shot_id']} -> {curr_shot_id}: "
                                        f"delta_pos={pos_jump:.1f}cm (max {pos_thresh:.1f}cm), "
                                        f"delta_rot={rot_jump:.1f}deg (max {rot_thresh:.1f}deg)."
                                    ),
                                    explanation=(
                                        f"Actor '{curr_a['actor_label']}' jumped {pos_jump:.1f} cm / {rot_jump:.1f} deg "
                                        f"at continuous shot boundary {prev_shot['shot_id']} -> {curr_shot_id}."
                                    ),
                                    expected_state={
                                        "location_cm": last_sample["location_cm"],
                                        "rotation_deg": last_sample["rotation_deg"],
                                        "max_position_jump_cm": pos_thresh,
                                        "max_rotation_jump_deg": rot_thresh,
                                    },
                                    actual_state={
                                        "location_cm": first_sample["location_cm"],
                                        "rotation_deg": first_sample["rotation_deg"],
                                        "measured_position_jump_cm": round(pos_jump, 2),
                                        "measured_rotation_jump_deg": round(rot_jump, 2),
                                    },
                                    evidence_uri=ev_uri,
                                    run_id=run_id,
                                )
                            )

        return issues
