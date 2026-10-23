# Deployment, Privacy, Threat Model & Licensing

## 1. Local-First Studio Security Model

Game studios keep unreleased cinematic sequences, narrative spoilers, and proprietary 3D assets under strict NDAs. Interframe v1 runs in a **local-only deployment model**:
- **Zero Cloud Upload**: All `ULevelSequence` manifests, rendered Movie Render Queue frames, Object-ID masks, and SQLite databases stay on the developer workstation or studio on-prem build agent.
- **No Raw Asset Telemetry**: Telemetry is strictly opt-in and never sends asset paths, actor names, or rendered images.
- **Read-Only Scene Inspection**: Neither the C++ plugin nor the Python collector modifies `.uasset` or `.umap` files during inspection. Reports and manifests go under `Saved/Interframe/`.

## 2. Foundation Model & Dataset License Tracking (`FoundationModelRegistry`)

When studios opt into neural CV components beyond Interframe's default analytical OpenCV comparator, `python/vision_worker/model_adapters.py` pins exact checkpoint SHA-256 hashes and tracks code licenses separately from dataset obligations:
- **OpenCV Analytical Comparator (`opencv-controlled-comparator-v1`)**: Apache-2.0 / BSD-3-Clause; zero external weights; on by default.
- **SAM 2 (`sam2-hiera-base-plus`)**: Model & code under Apache-2.0; SA-V dataset under CC BY 4.0. Off by default until commercial attribution/redistribution sign-off is toggled.
- **Grounding DINO (`grounding-dino-swin-t`) & DINOv2 (`dinov2-vitb14`)**: Code under Apache-2.0; needs explicit legal review of checkpoint and upstream dataset notices before commercial redistribution.
