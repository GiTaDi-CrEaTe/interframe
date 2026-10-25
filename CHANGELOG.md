# Changelog

All notable changes to the **Interframe** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-25

### Added
- **Unreal Engine 5.8 Editor Plugin** (`Unreal/InterframePlugin/`):
  - Slate review tab (`SInterframeReviewTab`) for visualizing continuity findings.
  - Sequencer integration bridge (`InterframeSequencerBridge`) to query cuts, bindings, and shot metadata.
  - Data validation asset base integration (`InterframeEditorValidator`).
- **Deterministic Engine Rule Suite** (`IF-001` through `IF-008`):
  - `IF-001`: Missing or broken asset reference detection.
  - `IF-002`: Unbound expected actor verification.
  - `IF-003`: Unexpected state change detection across cut boundaries.
  - `IF-004`: 3D transform discontinuity checks.
  - `IF-005`: Prop camera-space occlusion detection using Object-ID masks.
  - `IF-006`: Controlled appearance regression checks (SSIM & LAB chroma).
  - `IF-007`: Unexpected asset substitution checks.
  - `IF-008`: Config audit and rule contradiction verification.
- **Computer Vision Comparator**:
  - Controlled SSIM, Sobel edge difference, and LAB color space delta calculations within actor stencil masks.
- **Reporting & Persistence**:
  - SQLite database store for finding history and technical artist sign-offs (`true_positive`, `false_positive`, `intentional_change`).
  - Multi-format report exporter: versioned JSON, CSV, and standalone HTML reports.
- **Benchmark Evaluation Suite**:
  - `LEAVE_ALIVE` 25-sequence synthetic benchmark with 105 seeded continuity faults.
  - Automated comparative evaluation across B1 (Rules Only), B2 (Image Only), and B3 (Hybrid Interframe).
