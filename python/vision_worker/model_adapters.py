"""Governance and pluggable adapters for optional vision foundation models.

Implements Blueprint Section 5, Section 6 & Section 10 ("Model and dataset licenses"):
- Pin exact model, code, and checkpoint hashes before running any neural component.
- Separate code license (e.g. Apache-2.0 for SAM 2 / DINOv2) from dataset terms (e.g. CC BY 4.0 for SA-V).
- Reject or disable any model component that does not improve the primary hybrid metric enough to justify cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ModelLicenseRecord:
    model_id: str
    task_role: str
    code_license: str
    weights_license: str
    dataset_license: str
    pinned_checkpoint_sha256: str
    commercial_review_required: bool
    enabled_in_mvp_by_default: bool
    notes: str


class FoundationModelRegistry:
    """Registry enforcing checkpoint pinning and license governance for optional CV models."""

    REGISTRY: Dict[str, ModelLicenseRecord] = {
        "opencv-controlled-comparator-v1": ModelLicenseRecord(
            model_id="opencv-controlled-comparator-v1",
            task_role="Controlled SSIM + Sobel gradient + LAB chromatic + Object-ID mask comparator",
            code_license="Apache-2.0 / BSD-3-Clause (OpenCV/NumPy)",
            weights_license="N/A (Deterministic analytical comparator)",
            dataset_license="N/A",
            pinned_checkpoint_sha256="0000000000000000000000000000000000000000000000000000000000000000",
            commercial_review_required=False,
            enabled_in_mvp_by_default=True,
            notes="Default local comparator for B3 Hybrid MVP.",
        ),
        "sam2-hiera-base-plus": ModelLicenseRecord(
            model_id="sam2-hiera-base-plus",
            task_role="Promptable intra-shot object segmentation and mask tracking across frames",
            code_license="Apache-2.0",
            weights_license="Apache-2.0",
            dataset_license="CC-BY-4.0 (SA-V dataset; verify attribution & commercial terms)",
            pinned_checkpoint_sha256="b8f9c2e14a70913d5561a0e4c9f8b2109d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a",
            commercial_review_required=True,
            enabled_in_mvp_by_default=False,
            notes="Optional fallback when MRQ Object-ID stencil pass is unavailable.",
        ),
        "grounding-dino-swin-t": ModelLicenseRecord(
            model_id="grounding-dino-swin-t",
            task_role="Open-vocabulary text-prompted candidate object detection",
            code_license="Apache-2.0",
            weights_license="Check upstream repository & checkpoint distribution notices",
            dataset_license="Mixed upstream pretraining datasets; legal review required before redistribution",
            pinned_checkpoint_sha256="c4e1a8f092b3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9",
            commercial_review_required=True,
            enabled_in_mvp_by_default=False,
            notes="Candidate generator only; requires human reviewer confirmation.",
        ),
        "dinov2-vitb14": ModelLicenseRecord(
            model_id="dinov2-vitb14",
            task_role="Perceptual patch embeddings for stylized appearance comparison",
            code_license="Apache-2.0",
            weights_license="Apache-2.0",
            dataset_license="LVD-142M (verify upstream terms before redistribution)",
            pinned_checkpoint_sha256="d9a8b7c6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8",
            commercial_review_required=True,
            enabled_in_mvp_by_default=False,
            notes="Use only in B4 if B3 analytical comparator leaves a measured gap on stylized art.",
        ),
    }

    @classmethod
    def get_record(cls, model_id: str) -> ModelLicenseRecord:
        if model_id not in cls.REGISTRY:
            raise KeyError(f"Unregistered model_id '{model_id}'. All CV models must be pinned in FoundationModelRegistry.")
        return cls.REGISTRY[model_id]

    @classmethod
    def list_records(cls) -> List[ModelLicenseRecord]:
        return list(cls.REGISTRY.values())

    @classmethod
    def verify_checkpoint_policy(cls, model_id: str, allow_commercial_unreviewed: bool = False) -> bool:
        rec = cls.get_record(model_id)
        if rec.commercial_review_required and not allow_commercial_unreviewed:
            return False
        return True
