# Interframe Technical Architecture & Data Path

## 1. Core Idea: Engine Data + Controlled Pixel Checks

Game cinematics inside Unreal Engine 5.8 are authored in **Sequencer** (`ULevelSequence` / `UMovieScene`), where every camera cut, actor binding (`FMovieSceneBinding`), skeletal/static mesh assignment, visibility track, and 3D transform curve is explicitly represented in engine memory.

Pixel-only QA tools ignore this structured data and try to spot continuity errors from raw video alone — which means they fire off false positives whenever a camera cuts to a reverse angle, Lumen global illumination denoises differently, Temporal Super Resolution (TSR) jitters sub-pixel edges, or an artist deliberately toggles a state at a plot beat.

On the other hand, static asset validators (`UEditorValidatorBase`) can't tell whether a key narrative prop marked `bVisible = true` in Sequencer is actually blocked behind a wall from the active camera's point of view (`IF-005`), or whether a custom material parameter broke the look of a hero asset (`IF-006`).

Interframe connects both sides in an 8-stage local pipeline:

1. **Sequence Selection & Profile Binding**: The technical artist selects one or more `ULevelSequence` assets and a validation profile in the Unreal Editor dockable tab (`SInterframeReviewTab`) or CI commandlet (`UInterframeEditorValidator`).
2. **Manifest Extraction (`schemas/manifest.v1.json`)**: `FInterframeSequencerBridge` (C++) and `SequencerManifestCollector` (Python) read the `UMovieSceneCameraCutTrack`, actor bindings, transform samples at shot boundaries, and Asset Registry status, then write out a content-addressed manifest.
3. **Stage-1 Deterministic Rule Engine (`IF-001`..`IF-004`, `IF-007`, `IF-008`)**: Runs in milliseconds with zero GPU render cost. Flags missing assets, unbound actors, undeclared cross-cut state toggles, and continuous-cut transform jumps.
4. **Selective Movie Render Queue (MRQ) Orchestration**: `MRQRenderOrchestrator` filters for shots with visual rules (`IF-005`, `IF-006`) and computes a deterministic SHA-256 cache key over `(project_id_hash, source_control_revision, sequence_id, shot_id, profile_id, sampled_frames)` to skip redundant renders.
5. **Controlled Visual Comparator (`python/vision_worker/comparator.py`)**:
   - **Object-ID Stencil Check (`IF-005`)**: Counts unoccluded pixels for the target actor's stencil ID in the rendered mask pass.
   - **ROI-Masked Structural & Color Comparison (`IF-006`)**: Normalizes global luminance drift (`<= 15.0` L1), applies a `3x3` Gaussian pre-filter against TSR/Lumen grain, and runs windowed Structural Similarity (SSIM), Sobel gradient cosine similarity, and CIE LAB color delta strictly inside the actor's semantic mask.
6. **Combined Decision Layer**: Merges deterministic rule outputs and visual evidence, tagging high-certainty structural violations as `failed` and visual/threshold-based candidates as `needs_review`.
7. **Evidence-Linked Reporting**: Generates JSON (`schemas/issue.v1.json`), CSV, and interactive HTML reports with exact sequence/shot/frame/actor pointers.
8. **Versioned Persistence & Feedback Loop**: Saves runs in local SQLite (`InterframeStore`) and append-only JSONL audit logs, keeping `first_seen_build` across revisions and carrying forward artist dispositions (`true_positive`, `false_positive`, `intentional_change`).
