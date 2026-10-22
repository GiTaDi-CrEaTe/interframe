"""Controlled render comparison, Object-ID mask visibility, and anti-diff-trap filters.

Implements Blueprint Section 5, Section 6 & Section 9 ("Avoid visual-diff traps"):
- Naive pixel differences light up on anti-aliasing, Lumen noise, exposure shifts, or TAA jitter.
- ControlledRenderComparator normalizes global exposure, computes structural similarity (SSIM)
  and gradient-structure cosine similarity, and restricts appearance regression checks to the
  actor's semantic / Object-ID mask where available.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np


@dataclass
class VisualEvidenceResult:
    passed: bool
    confidence: float
    structural_similarity: float
    gradient_similarity: float
    chromatic_delta: float
    raw_pixel_l1: float
    mask_pixel_count: int
    mask_coverage_ratio: float
    explanation: str
    metrics: Dict[str, Any]


class ControlledRenderComparator:
    """Evaluates rendered shot frames and Object-ID masks for continuity defects."""

    MODEL_VERSION = "interframe-cv-comparator-1.0.0-opencv4"

    def __init__(
        self,
        min_structural_similarity: float = 0.82,
        max_chromatic_shift: float = 18.0,
        min_mask_pixel_ratio: float = 0.0015,
        min_visible_pixel_count: int = 35,
    ) -> None:
        self.min_structural_similarity = min_structural_similarity
        self.max_chromatic_shift = max_chromatic_shift
        self.min_mask_pixel_ratio = min_mask_pixel_ratio
        self.min_visible_pixel_count = min_visible_pixel_count

    @staticmethod
    def load_image(path: str | Path) -> np.ndarray:
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"Could not read render image at {path}")
        return img

    @staticmethod
    def load_mask(path: str | Path) -> np.ndarray:
        mask = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if mask is None:
            raise FileNotFoundError(f"Could not read object-ID mask at {path}")
        if mask.ndim == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        return mask

    @staticmethod
    def compute_ssim(gray_a: np.ndarray, gray_b: np.ndarray, roi_mask: Optional[np.ndarray] = None) -> float:
        """Computes windowed Structural Similarity Index (Wang et al., 2004) in pure NumPy/OpenCV."""
        a = gray_a.astype(np.float64)
        b = gray_b.astype(np.float64)

        # Normalize global luminance drift (e.g. minor exposure/tonemap shift) before structural check
        if roi_mask is not None and np.any(roi_mask > 0):
            valid = roi_mask > 0
            mean_diff = float(np.mean(a[valid]) - np.mean(b[valid]))
        else:
            mean_diff = float(np.mean(a) - np.mean(b))
        if abs(mean_diff) <= 15.0:
            b = np.clip(b + mean_diff, 0.0, 255.0)

        c1 = (0.01 * 255.0) ** 2
        c2 = (0.03 * 255.0) ** 2

        mu1 = cv2.GaussianBlur(a, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(b, (11, 11), 1.5)

        mu1_sq = mu1 * mu1
        mu2_sq = mu2 * mu2
        mu1_mu2 = mu1 * mu2

        sigma1_sq = cv2.GaussianBlur(a * a, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(b * b, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(a * b, (11, 11), 1.5) - mu1_mu2

        ssim_map = ((2.0 * mu1_mu2 + c1) * (2.0 * sigma12 + c2)) / (
            (mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2) + 1e-12
        )

        if roi_mask is not None and np.any(roi_mask > 0):
            return float(np.clip(np.mean(ssim_map[roi_mask > 0]), 0.0, 1.0))
        return float(np.clip(np.mean(ssim_map), 0.0, 1.0))

    @staticmethod
    def compute_gradient_similarity(
        gray_a: np.ndarray, gray_b: np.ndarray, roi_mask: Optional[np.ndarray] = None
    ) -> float:
        """Computes gradient-magnitude structural correlation resilient to high-frequency Lumen/TAA noise."""
        blur_a = cv2.GaussianBlur(gray_a.astype(np.float32), (5, 5), 1.0)
        blur_b = cv2.GaussianBlur(gray_b.astype(np.float32), (5, 5), 1.0)

        gx_a = cv2.Sobel(blur_a, cv2.CV_32F, 1, 0, ksize=3)
        gy_a = cv2.Sobel(blur_a, cv2.CV_32F, 0, 1, ksize=3)
        mag_a = np.sqrt(gx_a * gx_a + gy_a * gy_a)

        gx_b = cv2.Sobel(blur_b, cv2.CV_32F, 1, 0, ksize=3)
        gy_b = cv2.Sobel(blur_b, cv2.CV_32F, 0, 1, ksize=3)
        mag_b = np.sqrt(gx_b * gx_b + gy_b * gy_b)

        if roi_mask is not None and np.any(roi_mask > 0):
            va = mag_a[roi_mask > 0].ravel()
            vb = mag_b[roi_mask > 0].ravel()
        else:
            va = mag_a.ravel()
            vb = mag_b.ravel()

        norm_a = float(np.linalg.norm(va))
        norm_b = float(np.linalg.norm(vb))
        if norm_a < 1e-6 and norm_b < 1e-6:
            return 1.0
        if norm_a < 1e-6 or norm_b < 1e-6:
            return 0.0
        return float(np.clip(np.dot(va, vb) / (norm_a * norm_b), 0.0, 1.0))

    def check_actor_visibility_in_mask(
        self,
        mask_path: str | Path,
        stencil_object_id: int,
    ) -> VisualEvidenceResult:
        """Checks IF-005: Whether an actor that exists in scene metadata is actually visible in camera."""
        mask = self.load_mask(mask_path)
        total_pixels = int(mask.shape[0] * mask.shape[1])
        actor_pixels = int(np.sum(mask == stencil_object_id))
        coverage_ratio = float(actor_pixels) / float(max(total_pixels, 1))

        is_visible = (
            actor_pixels >= self.min_visible_pixel_count
            and coverage_ratio >= self.min_mask_pixel_ratio
        )
        confidence = 0.89 if not is_visible else 0.95
        explanation = (
            f"Object-ID stencil {stencil_object_id} occupies {actor_pixels} pixels "
            f"({coverage_ratio * 100:.3f}% of frame), confirming camera visibility."
            if is_visible
            else f"Actor exists in Sequencer with visibility=True, but Object-ID stencil {stencil_object_id} "
            f"has only {actor_pixels} visible pixels ({coverage_ratio * 100:.4f}% < {self.min_mask_pixel_ratio * 100:.2f}% threshold) "
            f"due to full camera occlusion or frustum clipping."
        )
        return VisualEvidenceResult(
            passed=is_visible,
            confidence=confidence,
            structural_similarity=1.0 if is_visible else 0.0,
            gradient_similarity=1.0 if is_visible else 0.0,
            chromatic_delta=0.0,
            raw_pixel_l1=0.0,
            mask_pixel_count=actor_pixels,
            mask_coverage_ratio=round(coverage_ratio, 6),
            explanation=explanation,
            metrics={
                "stencil_object_id": stencil_object_id,
                "actor_pixels": actor_pixels,
                "total_pixels": total_pixels,
                "coverage_ratio": round(coverage_ratio, 6),
            },
        )

    def compare_controlled_renders(
        self,
        current_rgb_path: str | Path,
        reference_rgb_path: str | Path,
        mask_path: Optional[str | Path] = None,
        stencil_object_id: Optional[int] = None,
    ) -> VisualEvidenceResult:
        """Checks IF-006: Controlled reference vs current render comparison resilient to TAA/Lumen grain."""
        curr_bgr = self.load_image(current_rgb_path)
        ref_bgr = self.load_image(reference_rgb_path)
        if curr_bgr.shape != ref_bgr.shape:
            ref_bgr = cv2.resize(ref_bgr, (curr_bgr.shape[1], curr_bgr.shape[0]))

        roi_mask: Optional[np.ndarray] = None
        mask_pixels = int(curr_bgr.shape[0] * curr_bgr.shape[1])
        if mask_path is not None and Path(mask_path).exists() and stencil_object_id is not None:
            raw_mask = self.load_mask(mask_path)
            if raw_mask.shape[:2] != curr_bgr.shape[:2]:
                raw_mask = cv2.resize(
                    raw_mask, (curr_bgr.shape[1], curr_bgr.shape[0]), interpolation=cv2.INTER_NEAREST
                )
            binary_roi = (raw_mask == stencil_object_id).astype(np.uint8)
            if int(np.sum(binary_roi)) >= 20:
                roi_mask = binary_roi
                mask_pixels = int(np.sum(binary_roi))

        # Gently denoise sub-pixel TAA/Lumen grain before structural and chromatic comparison
        curr_denoised = cv2.GaussianBlur(curr_bgr, (3, 3), 0.7)
        ref_denoised = cv2.GaussianBlur(ref_bgr, (3, 3), 0.7)

        curr_gray = cv2.cvtColor(curr_denoised, cv2.COLOR_BGR2GRAY)
        ref_gray = cv2.cvtColor(ref_denoised, cv2.COLOR_BGR2GRAY)

        ssim_val = self.compute_ssim(curr_gray, ref_gray, roi_mask=roi_mask)
        grad_sim = self.compute_gradient_similarity(curr_gray, ref_gray, roi_mask=roi_mask)

        # Compute LAB chromatic AB delta (ignoring L luminance channel to avoid exposure false positives)
        curr_lab = cv2.cvtColor(curr_denoised, cv2.COLOR_BGR2LAB).astype(np.float32)
        ref_lab = cv2.cvtColor(ref_denoised, cv2.COLOR_BGR2LAB).astype(np.float32)
        ab_diff = np.sqrt(
            (curr_lab[:, :, 1] - ref_lab[:, :, 1]) ** 2
            + (curr_lab[:, :, 2] - ref_lab[:, :, 2]) ** 2
        )
        raw_l1_map = np.mean(np.abs(curr_bgr.astype(np.float32) - ref_bgr.astype(np.float32)), axis=2)

        if roi_mask is not None:
            chromatic_delta = float(np.mean(ab_diff[roi_mask > 0]))
            raw_l1 = float(np.mean(raw_l1_map[roi_mask > 0]))
        else:
            chromatic_delta = float(np.mean(ab_diff))
            raw_l1 = float(np.mean(raw_l1_map))

        total_pixels = int(curr_bgr.shape[0] * curr_bgr.shape[1])
        coverage_ratio = float(mask_pixels) / float(max(total_pixels, 1))

        # Appearance regression occurs if either structural similarity drops significantly
        # OR chromatic shift inside the actor region exceeds threshold
        passed = (
            ssim_val >= self.min_structural_similarity
            and chromatic_delta <= self.max_chromatic_shift
        )
        deficit = max(
            (self.min_structural_similarity - ssim_val) * 1.5,
            (chromatic_delta - self.max_chromatic_shift) / 40.0,
            0.0,
        )
        confidence = float(np.clip(0.75 + deficit, 0.72, 0.96)) if not passed else 0.92

        explanation = (
            f"Controlled render comparison passed (SSIM={ssim_val:.3f}, ChromaticDelta={chromatic_delta:.2f})."
            if passed
            else f"Controlled render appearance regression detected within actor region "
            f"(SSIM={ssim_val:.3f} vs min {self.min_structural_similarity:.2f}, "
            f"ChromaticDelta={chromatic_delta:.2f} vs max {self.max_chromatic_shift:.1f})."
        )
        return VisualEvidenceResult(
            passed=passed,
            confidence=round(confidence, 3),
            structural_similarity=round(ssim_val, 4),
            gradient_similarity=round(grad_sim, 4),
            chromatic_delta=round(chromatic_delta, 3),
            raw_pixel_l1=round(raw_l1, 3),
            mask_pixel_count=mask_pixels,
            mask_coverage_ratio=round(coverage_ratio, 6),
            explanation=explanation,
            metrics={
                "ssim": round(ssim_val, 4),
                "gradient_similarity": round(grad_sim, 4),
                "chromatic_delta": round(chromatic_delta, 3),
                "raw_pixel_l1": round(raw_l1, 3),
                "roi_masked": roi_mask is not None,
            },
        )

    def compute_naive_image_only_diff(
        self,
        frame_a_path: str | Path,
        frame_b_path: str | Path,
        raw_l1_threshold: float = 8.5,
    ) -> VisualEvidenceResult:
        """Baseline B2 comparator: Image-only diff without engine metadata or semantic masks.

        Used in the scientific evaluation protocol (Blueprint Section 6) to quantify false positives
        caused by camera cuts, Lumen lighting grain, TAA jitter, and intentional state changes.
        """
        img_a = self.load_image(frame_a_path)
        img_b = self.load_image(frame_b_path)
        if img_a.shape != img_b.shape:
            img_b = cv2.resize(img_b, (img_a.shape[1], img_a.shape[0]))

        raw_l1 = float(np.mean(np.abs(img_a.astype(np.float32) - img_b.astype(np.float32))))
        gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
        gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)
        ssim_val = self.compute_ssim(gray_a, gray_b, roi_mask=None)

        passed = raw_l1 <= raw_l1_threshold and ssim_val >= 0.88
        return VisualEvidenceResult(
            passed=passed,
            confidence=0.65,
            structural_similarity=round(ssim_val, 4),
            gradient_similarity=0.0,
            chromatic_delta=0.0,
            raw_pixel_l1=round(raw_l1, 3),
            mask_pixel_count=int(img_a.shape[0] * img_a.shape[1]),
            mask_coverage_ratio=1.0,
            explanation=f"Image-only unmasked comparison (RawL1={raw_l1:.2f}, SSIM={ssim_val:.3f}).",
            metrics={"raw_pixel_l1": round(raw_l1, 3), "ssim": round(ssim_val, 4)},
        )
