"""Synthetic LEAVE_ALIVE continuity benchmark generator.

Generates a deterministic benchmark dataset with:
- 25 Level Sequences containing 5 shots each (125 shots, 100 shot boundaries).
- Rendered RGB frames, reference RGB frames, and Object-ID segmentation masks (160x90 PNGs)
  including simulated Lumen lighting noise, Temporal AA jitter, camera cuts, and intentional state changes.
- 105 seeded continuity faults across defect types IF-001 through IF-008 with exact ground truth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np


class LeaveAliveBenchmarkGenerator:
    """Builds the reproducible 25-sequence, 100-shot-boundary continuity benchmark."""

    def __init__(self, output_dir: str | Path, seed: int = 20261022) -> None:
        self.output_dir = Path(output_dir)
        self.renders_dir = self.output_dir / "renders"
        self.manifests_dir = self.output_dir / "manifests"
        self.renders_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.rng = np.random.default_rng(seed)

    def _render_synthetic_shot(
        self,
        seq_idx: int,
        shot_idx: int,
        frame_num: int,
        camera_cut_shift: int,
        prop_visible_in_camera: bool,
        appearance_regressed: bool,
        exposure_shift: float,
    ) -> Tuple[str, str, str]:
        """Renders synthetic Reference RGB, Current RGB, and 8-bit Object-ID Stencil Mask PNGs."""
        h, w = 90, 160
        ref_img = np.zeros((h, w, 3), dtype=np.uint8)

        # Background gradient + architectural pillars (shifted by camera_cut_shift on hard cuts)
        for y in range(h):
            ref_img[y, :, 0] = int(35 + (y / h) * 40)
            ref_img[y, :, 1] = int(42 + (y / h) * 35)
            ref_img[y, :, 2] = int(50 + (y / h) * 30)

        pillar_x = (25 + camera_cut_shift) % (w - 30)
        cv2.rectangle(ref_img, (pillar_x, 10), (pillar_x + 18, h - 10), (75, 82, 95), -1)

        # Actor 1 (Protagonist, Stencil ID = 1)
        hero_x = 55 + (shot_idx * 3)
        cv2.rectangle(ref_img, (hero_x, 28), (hero_x + 24, 78), (180, 140, 90), -1)

        # Actor 2 (Key Prop Relic, Stencil ID = 2)
        prop_x, prop_y = 105, 48
        cv2.circle(ref_img, (prop_x, prop_y), 14, (60, 195, 235), -1)
        cv2.circle(ref_img, (prop_x, prop_y), 8, (90, 225, 250), -1)

        # Build Current RGB starting from Reference RGB + realistic Lumen/TAA noise + minor exposure shift
        noise = self.rng.normal(0.0, 2.2, size=ref_img.shape)
        curr_float = np.clip(ref_img.astype(np.float32) + exposure_shift + noise, 0, 255)
        curr_img = curr_float.astype(np.uint8)

        # Build Object-ID Stencil Mask (0=background, 1=hero, 2=key_prop)
        mask_img = np.zeros((h, w), dtype=np.uint8)
        cv2.rectangle(mask_img, (hero_x, 28), (hero_x + 24, 78), 1, -1)

        if prop_visible_in_camera:
            cv2.circle(mask_img, (prop_x, prop_y), 14, 2, -1)
        else:
            # Prop is occluded in camera by a foreground blocker even though metadata says visibility=True
            cv2.rectangle(curr_img, (prop_x - 16, prop_y - 16), (prop_x + 16, prop_y + 16), (48, 52, 60), -1)
            # Stencil ID 2 is 0 pixels in mask_img!

        if appearance_regressed:
            # Corrupt shader/material appearance inside Key Prop (Stencil ID = 2) region
            cv2.circle(curr_img, (prop_x, prop_y), 14, (210, 40, 200), -1)
            cv2.line(curr_img, (prop_x - 12, prop_y - 12), (prop_x + 12, prop_y + 12), (15, 15, 15), 3)

        prefix = f"seq{seq_idx:02d}_sh{shot_idx:02d}_f{frame_num:04d}"
        curr_path = self.renders_dir / f"{prefix}_curr_rgb.png"
        ref_path = self.renders_dir / f"{prefix}_ref_rgb.png"
        mask_path = self.renders_dir / f"{prefix}_obj_mask.png"

        cv2.imwrite(str(curr_path), curr_img)
        cv2.imwrite(str(ref_path), ref_img)
        cv2.imwrite(str(mask_path), mask_img)

        return str(curr_path), str(ref_path), str(mask_path)

    def generate_benchmark(self) -> Dict[str, Any]:
        """Generates 25 sequences (125 shots, 100 shot boundaries) and 105 seeded ground-truth faults."""
        manifests: List[Dict[str, Any]] = []
        ground_truth_faults: List[Dict[str, Any]] = []

        # Plan exact deterministic fault injection schedule across the 25 sequences:
        # Total faults = 105 across IF-001 (15), IF-002 (15), IF-003 (15), IF-004 (15),
        # IF-005 (15), IF-006 (15), IF-007 (10), IF-008 (5).
        fault_quotas = {
            "IF-001": 15,
            "IF-002": 15,
            "IF-003": 15,
            "IF-004": 15,
            "IF-005": 15,
            "IF-006": 15,
            "IF-007": 10,
            "IF-008": 5,
        }
        remaining = dict(fault_quotas)

        for seq_idx in range(1, 26):
            seq_id = f"LS_LeaveAlive_Scn{seq_idx:02d}"
            seq_path = f"/Game/LeaveAlive/Cinematics/{seq_id}"
            expected_rules: List[Dict[str, Any]] = [
                {
                    "rule_instance_id": f"rule_{seq_id}_hero_bound",
                    "rule_id": "IF-002",
                    "target_actor_guid": f"guid-hero-{seq_idx:02d}",
                    "target_actor_label": "BP_Protagonist_Kael",
                    "expected_asset_path": "/Game/LeaveAlive/Characters/Kael/BP_Protagonist_Kael",
                },
                {
                    "rule_instance_id": f"rule_{seq_id}_relic_vis",
                    "rule_id": "IF-005",
                    "target_actor_guid": f"guid-relic-{seq_idx:02d}",
                    "target_actor_label": "BP_SignalRelic_Prop",
                    "must_be_visible_in_camera": True,
                },
                {
                    "rule_instance_id": f"rule_{seq_id}_relic_appearance",
                    "rule_id": "IF-006",
                    "target_actor_guid": f"guid-relic-{seq_idx:02d}",
                    "target_actor_label": "BP_SignalRelic_Prop",
                },
                {
                    "rule_instance_id": f"rule_{seq_id}_relic_asset_inv",
                    "rule_id": "IF-007",
                    "target_actor_guid": f"guid-relic-{seq_idx:02d}",
                    "target_actor_label": "BP_SignalRelic_Prop",
                    "expected_mesh_id": "SM_SignalRelic_Hero",
                    "expected_material_ids": ["MI_SignalRelic_Gold"],
                    "expected_asset_path": "/Game/LeaveAlive/Props/SM_SignalRelic_Hero",
                },
            ]

            # Declare an intentional state transition on Shot 5 for odd sequences so we test that
            # Interframe respects declared artist intent without raising a false positive!
            if seq_idx % 2 == 1:
                expected_rules.append(
                    {
                        "rule_instance_id": f"rule_{seq_id}_declared_transition",
                        "rule_id": "IF-003",
                        "target_actor_guid": f"guid-lantern-{seq_idx:02d}",
                        "target_actor_label": "BP_CaveLantern",
                        "allowed_transition_shots": ["SH_005"],
                    }
                )

            # Inject IF-008 in sequences 21..25 (5 total)
            if remaining["IF-008"] > 0 and seq_idx >= 21:
                remaining["IF-008"] -= 1
                expected_rules.append(
                    {
                        "rule_instance_id": f"rule_{seq_id}_bad_cfg",
                        "rule_id": "IF-008",
                        "target_actor_guid": f"guid-lantern-{seq_idx:02d}",
                        "target_actor_label": "BP_CaveLantern",
                        "contradictory_flag": True,
                    }
                )
                ground_truth_faults.append(
                    {
                        "sequence_id": seq_id,
                        "shot_id": "SH_001",
                        "actor_guid": f"guid-lantern-{seq_idx:02d}",
                        "rule_id": "IF-008",
                        "severity": "Informational",
                    }
                )

            shot_list: List[Dict[str, Any]] = []
            for shot_idx in range(1, 6):
                shot_id = f"SH_{shot_idx:03d}"
                start_frame = (shot_idx - 1) * 48
                end_frame = shot_idx * 48 - 1

                # Inject specific faults per shot index so they don't collide on the same actor/shot
                inject_if001 = (shot_idx == 1 and remaining["IF-001"] > 0)
                inject_if002 = (shot_idx == 2 and remaining["IF-002"] > 0)
                inject_if003 = (shot_idx == 3 and remaining["IF-003"] > 0)
                inject_if004 = (shot_idx == 4 and remaining["IF-004"] > 0)
                inject_if005 = (shot_idx == 3 and remaining["IF-005"] > 0)
                inject_if006 = (shot_idx == 4 and remaining["IF-006"] > 0)
                inject_if007 = (shot_idx == 5 and remaining["IF-007"] > 0)

                if inject_if001:
                    remaining["IF-001"] -= 1
                if inject_if002:
                    remaining["IF-002"] -= 1
                if inject_if003:
                    remaining["IF-003"] -= 1
                if inject_if004:
                    remaining["IF-004"] -= 1
                if inject_if005:
                    remaining["IF-005"] -= 1
                if inject_if006:
                    remaining["IF-006"] -= 1
                if inject_if007:
                    remaining["IF-007"] -= 1

                # Simulate camera cut shift & minor exposure shift across shots (causes B2 false positives!)
                camera_cut_shift = (shot_idx * 27 + seq_idx * 7) % 85
                exposure_shift = 4.5 if (shot_idx % 2 == 0) else -3.5

                curr_rgb, ref_rgb, mask_png = self._render_synthetic_shot(
                    seq_idx=seq_idx,
                    shot_idx=shot_idx,
                    frame_num=start_frame,
                    camera_cut_shift=camera_cut_shift,
                    prop_visible_in_camera=not inject_if005,
                    appearance_regressed=inject_if006,
                    exposure_shift=exposure_shift,
                )

                hero_loc = [100.0, 20.0, 0.0]
                if inject_if004:
                    # 125 cm sudden jump across continuous cut boundary
                    hero_loc = [225.0, 20.0, 0.0]

                lantern_vis = True
                if inject_if003:
                    # Unexplained state toggle on Shot 3
                    lantern_vis = False
                elif shot_idx == 5 and seq_idx % 2 == 1:
                    # Declared intentional state transition on Shot 5 (should NOT trigger IF-003)
                    lantern_vis = False

                relic_mesh = "SM_SignalRelic_ProxyLow" if inject_if007 else "SM_SignalRelic_Hero"
                relic_mat = ["MI_SignalRelic_Greybox"] if inject_if007 else ["MI_SignalRelic_Gold"]

                lantern_asset = (
                    "/InvalidMount/Missing/SM_BrokenLantern"
                    if inject_if001
                    else "/Game/LeaveAlive/Props/SM_CaveLantern"
                )

                actor_bindings = [
                    {
                        "actor_guid": f"guid-hero-{seq_idx:02d}",
                        "actor_label": "BP_Protagonist_Kael",
                        "actor_role": "lead_character",
                        "asset_path": "/Game/LeaveAlive/Characters/Kael/BP_Protagonist_Kael",
                        "asset_exists_in_registry": True,
                        "bound_in_sequencer": not inject_if002,
                        "visibility_state": True,
                        "mesh_id": "SK_Kael_Cine",
                        "material_ids": ["MI_Kael_Suit"],
                        "stencil_object_id": 1,
                        "transform_samples": [
                            {
                                "frame": start_frame,
                                "time_seconds": round(start_frame / 24.0, 4),
                                "location_cm": hero_loc,
                                "rotation_deg": [0.0, 15.0, 0.0],
                                "scale": [1.0, 1.0, 1.0],
                            },
                            {
                                "frame": end_frame,
                                "time_seconds": round(end_frame / 24.0, 4),
                                "location_cm": [100.0, 20.0, 0.0],
                                "rotation_deg": [0.0, 15.0, 0.0],
                                "scale": [1.0, 1.0, 1.0],
                            },
                        ],
                    },
                    {
                        "actor_guid": f"guid-relic-{seq_idx:02d}",
                        "actor_label": "BP_SignalRelic_Prop",
                        "actor_role": "hero_prop",
                        "asset_path": "/Game/LeaveAlive/Props/SM_SignalRelic_Hero",
                        "asset_exists_in_registry": True,
                        "bound_in_sequencer": True,
                        "visibility_state": True,
                        "mesh_id": relic_mesh,
                        "material_ids": relic_mat,
                        "stencil_object_id": 2,
                        "transform_samples": [
                            {
                                "frame": start_frame,
                                "time_seconds": round(start_frame / 24.0, 4),
                                "location_cm": [140.0, -10.0, 85.0],
                                "rotation_deg": [0.0, 0.0, 0.0],
                                "scale": [1.0, 1.0, 1.0],
                            },
                            {
                                "frame": end_frame,
                                "time_seconds": round(end_frame / 24.0, 4),
                                "location_cm": [140.0, -10.0, 85.0],
                                "rotation_deg": [0.0, 0.0, 0.0],
                                "scale": [1.0, 1.0, 1.0],
                            },
                        ],
                    },
                    {
                        "actor_guid": f"guid-lantern-{seq_idx:02d}",
                        "actor_label": "BP_CaveLantern",
                        "actor_role": "environment_prop",
                        "asset_path": lantern_asset,
                        "asset_exists_in_registry": not inject_if001,
                        "bound_in_sequencer": True,
                        "visibility_state": lantern_vis,
                        "mesh_id": "SM_CaveLantern",
                        "material_ids": ["MI_Lantern_Glass"],
                        "stencil_object_id": 3,
                        "transform_samples": [
                            {
                                "frame": start_frame,
                                "time_seconds": round(start_frame / 24.0, 4),
                                "location_cm": [80.0, -45.0, 120.0],
                                "rotation_deg": [0.0, 0.0, 0.0],
                                "scale": [1.0, 1.0, 1.0],
                            },
                            {
                                "frame": end_frame,
                                "time_seconds": round(end_frame / 24.0, 4),
                                "location_cm": [80.0, -45.0, 120.0],
                                "rotation_deg": [0.0, 0.0, 0.0],
                                "scale": [1.0, 1.0, 1.0],
                            },
                        ],
                    },
                ]

                # Record ground truth faults for this shot
                if inject_if001:
                    ground_truth_faults.append(
                        {
                            "sequence_id": seq_id,
                            "shot_id": shot_id,
                            "actor_guid": f"guid-lantern-{seq_idx:02d}",
                            "rule_id": "IF-001",
                            "severity": "Critical",
                        }
                    )
                if inject_if002:
                    ground_truth_faults.append(
                        {
                            "sequence_id": seq_id,
                            "shot_id": shot_id,
                            "actor_guid": f"guid-hero-{seq_idx:02d}",
                            "rule_id": "IF-002",
                            "severity": "Critical",
                        }
                    )
                if inject_if003:
                    ground_truth_faults.append(
                        {
                            "sequence_id": seq_id,
                            "shot_id": shot_id,
                            "actor_guid": f"guid-lantern-{seq_idx:02d}",
                            "rule_id": "IF-003",
                            "severity": "Major",
                        }
                    )
                    # Reset lantern visibility on Shot 4 if we don't want a second transition fault on Shot 4,
                    # OR keep it consistent by setting Shot 4/5 lantern_vis to match Shot 3 when inject_if003 is active:
                if inject_if004:
                    ground_truth_faults.append(
                        {
                            "sequence_id": seq_id,
                            "shot_id": shot_id,
                            "actor_guid": f"guid-hero-{seq_idx:02d}",
                            "rule_id": "IF-004",
                            "severity": "Major",
                        }
                    )
                if inject_if005:
                    ground_truth_faults.append(
                        {
                            "sequence_id": seq_id,
                            "shot_id": shot_id,
                            "actor_guid": f"guid-relic-{seq_idx:02d}",
                            "rule_id": "IF-005",
                            "severity": "Major",
                        }
                    )
                if inject_if006:
                    ground_truth_faults.append(
                        {
                            "sequence_id": seq_id,
                            "shot_id": shot_id,
                            "actor_guid": f"guid-relic-{seq_idx:02d}",
                            "rule_id": "IF-006",
                            "severity": "Minor",
                        }
                    )
                if inject_if007:
                    ground_truth_faults.append(
                        {
                            "sequence_id": seq_id,
                            "shot_id": shot_id,
                            "actor_guid": f"guid-relic-{seq_idx:02d}",
                            "rule_id": "IF-007",
                            "severity": "Major",
                        }
                    )

                shot_rule_ids = [
                    f"rule_{seq_id}_hero_bound",
                    f"rule_{seq_id}_relic_vis",
                    f"rule_{seq_id}_relic_appearance",
                    f"rule_{seq_id}_relic_asset_inv",
                ]
                shot_list.append(
                    {
                        "shot_id": shot_id,
                        "start_frame": start_frame,
                        "end_frame": end_frame,
                        "frame_rate": 24.0,
                        "continuity_anchor": "continuous_action",
                        "camera_binding": {
                            "camera_guid": f"cam-{seq_idx:02d}-{shot_idx:02d}",
                            "camera_name": f"CineCam_{shot_idx:02d}",
                            "focal_length_mm": 35.0 if shot_idx % 2 == 1 else 50.0,
                            "aperture_fstop": 2.8,
                            "transform": {
                                "location_cm": [-240.0 + shot_idx * 15.0, 0.0, 145.0],
                                "rotation_deg": [0.0, 0.0, 0.0],
                            },
                        },
                        "actor_bindings": actor_bindings,
                        "expected_state_rule_ids": shot_rule_ids,
                        "evidence_capture_config": {
                            "sampled_frames": [start_frame, end_frame],
                            "rgb_frames": {str(start_frame): curr_rgb},
                            "reference_rgb_frames": {str(start_frame): ref_rgb},
                            "object_id_masks": {str(start_frame): mask_png},
                            "resolution": [160, 90],
                        },
                    }
                )

            # Note: If Shot 3 toggled lantern_vis to False (for IF-003), keep Shot 4 & Shot 5 at False
            # so Shot 3 -> Shot 4 doesn't trigger a second unintended toggle.
            if seq_idx <= 15:
                for s_follow in shot_list[3:]:
                    for a_bind in s_follow["actor_bindings"]:
                        if a_bind["actor_guid"] == f"guid-lantern-{seq_idx:02d}":
                            a_bind["visibility_state"] = False

            manifest = {
                "schema_version": "1.0.0",
                "project_id_hash": "leavealive98a7b6c5",
                "project_name": "LEAVE_ALIVE_Testbed",
                "engine_version": "5.8.0",
                "source_control_revision": "git-20261022-r104",
                "sequence_id": seq_id,
                "sequence_path": seq_path,
                "render_profile_id": "MRQ_Controlled_Linear_sRGB_v1",
                "collection_timestamp": "2026-10-22T14:30:00+00:00",
                "collector_version": "1.0.0",
                "nondeterministic_effects": {
                    "dynamic_lighting_lumen": True,
                    "niagara_particles_active": False,
                    "chaos_physics_sim": False,
                    "temporal_upscaler": "TSR_Deterministic_Seed",
                },
                "expected_state_rules": expected_rules,
                "shot_list": shot_list,
            }

            manifest_path = self.manifests_dir / f"{seq_id}.manifest.v1.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
            manifests.append(manifest)

        gt_path = self.output_dir / "ground_truth_labels.json"
        summary = {
            "benchmark_name": "LEAVE_ALIVE_Controlled_Continuity_Benchmark_v1",
            "total_sequences": len(manifests),
            "total_shots": sum(len(m["shot_list"]) for m in manifests),
            "total_shot_boundaries": sum(len(m["shot_list"]) - 1 for m in manifests),
            "total_seeded_faults": len(ground_truth_faults),
            "fault_counts_by_rule": fault_quotas,
            "ground_truth_faults": ground_truth_faults,
        }
        with open(gt_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return {"manifests": manifests, "ground_truth": summary}
