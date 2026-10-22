# Deployment, Privacy, Threat Model & Licensing Governance

## 1. Local-First Studio Security Model

Game studios guard unreleased cinematic sequences, narrative spoilers, and proprietary 3D assets under strict NDAs. Interframe v1 enforces a **local-only deployment model**:
- **Zero Cloud Upload**: All `ULevelSequence` manifests, rendered Movie Render Queue frames, Object-ID masks, and SQLite databases remain on the developer workstation or studio on-prem build agent.
- **No Raw Asset Telemetry**: Telemetry is strictly opt-in and never transmits asset paths, actor names, or rendered images.
- **Read-Only Scene Inspection**: Neither the C++ plugin nor the Python collector mutates `.uasset` or `.umap` files during inspection. Reports and manifests are staged under `Saved/Interframe/`.

## 2. Foundation Model & Dataset License Governance (`FoundationModelRegistry`)

When studios opt into neural CV components beyond Interframe's default analytical OpenCV comparator, `python/vision_worker/model_adapters.py` enforces strict checkpoint SHA-256 pinning and separates code licenses from dataset obligations:
- **OpenCV Analytical Comparator (`opencv-controlled-comparator-v1`)**: Apache-2.0 / BSD-3-Clause; zero external weights; enabled by default.
- **SAM 2 (`sam2-hiera-base-plus`)**: Model & code under Apache-2.0; SA-V dataset under CC BY 4.0. Disabled by default until commercial attribution/redistribution sign-off is toggled.
- **Grounding DINO (`grounding-dino-swin-t`) & DINOv2 (`dinov2-vitb14`)**: Code under Apache-2.0; requires explicit legal review of checkpoint and upstream dataset notices before commercial redistribution.
