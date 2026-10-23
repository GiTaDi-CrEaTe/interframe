"""Movie Render Queue (MRQ) sampling and pass orchestrator.

Orchestration rules:
- Run deterministic rules first; only request renders for shots requiring visual verification.
- Sample boundary and anchor frames deterministically (`[start_frame, mid_frame, end_frame]`).
- Cache rendered frames by `(project_id_hash, source_control_revision, sequence_id, shot_id, render_profile_id)`.
- Support optional Object-ID / stencil masks without failing if experimental passes are disabled.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MRQRenderProfile:
    profile_id: str = "MRQ_Controlled_Linear_sRGB_v1"
    resolution: tuple[int, int] = (640, 360)
    anti_aliasing_spatial_samples: int = 1
    anti_aliasing_temporal_samples: int = 4
    lock_exposure_ev100: float = 1.0
    disable_motion_blur_for_diff: bool = True
    enable_object_id_pass: bool = True
    enable_depth_pass: bool = False


@dataclass
class MRQJobSpec:
    job_id: str
    sequence_path: str
    shot_id: str
    sampled_frames: List[int]
    profile: MRQRenderProfile
    cache_key: str
    output_dir: str
    extra_passes: List[str] = field(default_factory=list)


class MRQRenderOrchestrator:
    """Builds command-line / Python MRQ render jobs and manages content-addressed frame caching."""

    def __init__(self, cache_root: Path) -> None:
        self.cache_root = Path(cache_root)
        self.cache_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_shot_cache_key(
        project_id_hash: str,
        source_control_revision: str,
        sequence_id: str,
        shot_id: str,
        profile_id: str,
        sampled_frames: List[int],
    ) -> str:
        payload = json.dumps(
            {
                "project_id_hash": project_id_hash,
                "revision": source_control_revision,
                "sequence_id": sequence_id,
                "shot_id": shot_id,
                "profile_id": profile_id,
                "sampled_frames": sorted(sampled_frames),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def select_deterministic_sample_frames(start_frame: int, end_frame: int) -> List[int]:
        """Selects boundary and midpoint frames for continuity inspection."""
        if end_frame <= start_frame:
            return [start_frame]
        mid_frame = (start_frame + end_frame) // 2
        frames = sorted({start_frame, mid_frame, end_frame})
        return frames

    def plan_render_jobs_for_manifest(
        self,
        manifest: Dict[str, Any],
        profile: Optional[MRQRenderProfile] = None,
        only_shots_with_visual_rules: bool = True,
    ) -> List[MRQJobSpec]:
        """Creates MRQ job specifications only for shots that require visual evidence."""
        if profile is None:
            profile = MRQRenderProfile(profile_id=manifest.get("render_profile_id", "MRQ_Default"))

        rules_by_id = {
            r["rule_instance_id"]: r for r in manifest.get("expected_state_rules", [])
        }
        visual_rule_ids = {"IF-005", "IF-006"}

        jobs: List[MRQJobSpec] = []
        for shot in manifest.get("shot_list", []):
            shot_rule_instances = shot.get("expected_state_rule_ids", [])
            needs_visual = not only_shots_with_visual_rules
            for r_inst_id in shot_rule_instances:
                rule_obj = rules_by_id.get(r_inst_id, {})
                if rule_obj.get("rule_id") in visual_rule_ids or rule_obj.get("must_be_visible_in_camera"):
                    needs_visual = True
                    break
            # Also render if reference_rgb_frames or object_id_masks are configured
            ev_cfg = shot.get("evidence_capture_config", {})
            if ev_cfg.get("reference_rgb_frames") or ev_cfg.get("object_id_masks"):
                needs_visual = True

            if not needs_visual:
                continue

            sampled = ev_cfg.get("sampled_frames") or self.select_deterministic_sample_frames(
                shot["start_frame"], shot["end_frame"]
            )
            cache_key = self.compute_shot_cache_key(
                manifest["project_id_hash"],
                manifest["source_control_revision"],
                manifest["sequence_id"],
                shot["shot_id"],
                profile.profile_id,
                sampled,
            )
            extra_passes = ["DeferredRendering"]
            if profile.enable_object_id_pass:
                extra_passes.append("ObjectIdPass_Limited")
            if profile.enable_depth_pass:
                extra_passes.append("SceneDepth")

            jobs.append(
                MRQJobSpec(
                    job_id=f"mrq_{manifest['sequence_id']}_{shot['shot_id']}_{cache_key[:8]}",
                    sequence_path=manifest["sequence_path"],
                    shot_id=shot["shot_id"],
                    sampled_frames=sampled,
                    profile=profile,
                    cache_key=cache_key,
                    output_dir=str(self.cache_root / cache_key),
                    extra_passes=extra_passes,
                )
            )
        return jobs

    @staticmethod
    def build_unreal_cli_command(uproject_path: str, job: MRQJobSpec) -> List[str]:
        """Generates the exact UnrealEditor-Cmd MoviePipeline command line for CI/Horde execution."""
        return [
            "UnrealEditor-Cmd",
            uproject_path,
            job.sequence_path,
            "-game",
            f"-MoviePipelineConfig={job.profile.profile_id}",
            f"-Shot={job.shot_id}",
            f"-ResX={job.profile.resolution[0]}",
            f"-ResY={job.profile.resolution[1]}",
            "-NoLoadingScreen",
            "-StdOut",
            "-FullStdOutLogOutput",
            "-unattended",
        ]
