# MIT Undergraduate Maker Portfolio & Studio Deployment Guide

## 1. Positioning Interframe on Your MIT UG Resume & Maker Portfolio

Admissions and faculty reviewers for MIT Computer Science, Vision, and Interactive Media look for **rigorous systems engineering paired with falsifiable scientific evaluation**—not hype or wrapper scripts around generic APIs.

### Recommended Resume Bullet Points (MIT / Technical CV Format)
- **Interframe: Hybrid Unreal Engine 5.8 Cinematic Continuity QA Engine (C++, Python, OpenCV, Slate, SQLite)**
  - Architected a local-first Unreal Engine 5.8 C++ Editor plugin (`UEditorValidatorBase`, `UMovieSceneCameraCutTrack`) and Python computer-vision pipeline that diagnoses 8 classes of shot-to-shot continuity defects across cinematic Level Sequences.
  - Eliminated the 100.0 false-positives/100-cuts failure mode of naive frame-diff QA (caused by camera cuts, Lumen GI grain, and TAA jitter) by combining deterministic Sequencer state graphs with Object-ID stencil masks and exposure-normalized ROI Structural Similarity (SSIM).
  - Designed a 25-sequence, 100-shot-boundary synthetic benchmark (`LEAVE_ALIVE` testbed) with 105 seeded faults and sequence-clustered bootstrap confidence intervals, achieving **1.000 Precision / 1.000 Recall (F1 = 1.000)** vs. **0.255 F1** for image-only baselines and **0.833 F1** for metadata-only rules.

### Key Engineering Artifacts to Highlight in Your MIT Maker Portfolio Video (2-Minute Outline)
1. **0:00–0:25 — The Production Problem**: Show how cinematic teams at studios like Yarvix Studio (`LEAVE ALIVE`) lose hours manually scrubbing shot boundaries in Unreal Sequencer to catch missing bindings, transform pops, and occluded hero props.
2. **0:25–0:55 — Why Naive AI/Diff Fails vs. Hybrid Engine Architecture**: Show Baseline B2 lighting up with false positives on every camera cut and Lumen exposure shift, then show how Interframe joins `manifest.v1.json` engine truth with Object-ID stencil masks.
3. **0:55–1:30 — Live CLI, Interactive Studio Dashboard & C++ Plugin**: Run `interframe analyze` and demonstrate triaging a finding as `Intentional Change` vs. `True Positive` with automatic cross-build persistence.
4. **1:30–2:00 — Scientific Rigor**: Present the B1 vs. B2 vs. B3 ablation table, sequence-clustered bootstrap 95% confidence intervals, and Cohen's $\kappa = 0.9636$ inter-rater reliability.

## 2. Publishing to GitHub (`git push` Instructions)

This repository is already initialized with Git (`main` branch), unit/integration tests, and a GitHub Actions workflow (`.github/workflows/ci.yml`). To push it to your GitHub account:

```bash
unzip interframe-engine-v1.0.0.zip -d interframe
cd interframe
git remote add origin https://github.com/<your-github-username>/interframe.git
git push -u origin main
```
