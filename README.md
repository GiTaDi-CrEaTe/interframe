# Interframe — Engine-Aware Continuity QA for Unreal Engine

[![CI](https://github.com/GiTaDi-CrEaTe/interframe/actions/workflows/ci.yml/badge.svg)](https://github.com/GiTaDi-CrEaTe/interframe/actions)
[![Unreal Engine](https://img.shields.io/badge/Unreal_Engine-5.8-0E1128?logo=unrealengine)](https://www.unrealengine.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Schemas](https://img.shields.io/badge/Contracts-manifest.v1_%7C_issue.v1-success)](schemas/)

**Interframe** is a local-first continuity and scene-integrity diagnostic tool for **Unreal Engine 5.8 Level Sequences** (`UMovieScene` / Sequencer + Movie Render Queue).

Pixel-diff QA tools treat cinematics as flat video, which breaks on Temporal Anti-Aliasing (TAA), Lumen global illumination noise, and intentional narrative cuts. Interframe takes a different approach — it reads engine data first, then only runs visual checks where they actually matter:
1. **Engine Data First**: Reads Unreal's Asset Registry, `ULevelSequence` camera cuts, `FMovieSceneBinding` tracks, actor transforms, visibility states, and declared scene invariants to flag structural defects deterministically (`IF-001`..`IF-004`, `IF-007`, `IF-008`).
2. **Selective Render Checks**: Runs Movie Render Queue (MRQ) frame & Object-ID stencil passes only where visual checks are needed — catching camera-space prop occlusion (`IF-005`) and appearance regressions within actor masks (`IF-006`) while accounting for exposure drift and sub-pixel rendering noise.
3. **Artist Review & Sign-off**: Every finding links to an exact `(sequence_path, shot_id, frame_time, actor_guid, asset_path, rule_id)` pointer with attached evidence, so technical artists can mark findings as `true_positive`, `false_positive`, or `intentional_change` in a local SQLite/JSONL store — no proprietary game assets leave the workstation.

## Repository Layout

```text
interframe/
├── Unreal/InterframePlugin/         # C++ Editor module, Slate UI tab, Sequencer bridge & UEditorValidatorBase
├── python/
│   ├── collector/                   # Unreal Python LevelSequence manifest collector & MRQ pass orchestrator
│   ├── vision_worker/               # Controlled SSIM/Sobel/LAB/Object-ID comparator & model license registry
│   └── interframe_engine/           # Deterministic rule engine (IF-001..IF-008), hybrid pipeline, SQLite store & CLI
├── schemas/
│   ├── manifest.v1.json             # Versioned input contract for shot & actor metadata
│   └── issue.v1.json                # Stable finding contract with evidence & reviewer disposition
├── rules/
│   └── default_continuity_rules.json # Configurable thresholds and confidence policies for IF-001..IF-008
├── evaluation/                      # LEAVE_ALIVE synthetic benchmark generator (25 sequences, 100 cuts, 105 faults)
├── tests/
│   ├── unit/                        # Schema, rule engine, CV comparator, MRQ cache & SQLite versioning unit tests
│   └── integration/                 # End-to-end B1/B2/B3 baseline benchmark & CLI integration tests
├── docs/                            # Architecture deep-dive, privacy/threat model, and studio deployment guide
└── scripts/                         # Local CLI runner and CI verification scripts
```

## Issue Taxonomy

| Rule ID | Defect Type | Detection Signal | Default Severity | Method |
| :--- | :--- | :--- | :--- | :--- |
| **IF-001** | Invalid/missing asset reference | Asset Registry or validator returns missing/broken package reference | Critical | Deterministic Engine Rule |
| **IF-002** | Expected actor unbound in shot | Explicit scene rule references an actor GUID unbound in Level Sequence | Critical | Deterministic Engine Rule |
| **IF-003** | Unexpected state change | Mesh, material, or visibility toggles across cut outside declared transitions | Major | Deterministic Engine Rule |
| **IF-004** | Transform discontinuity | Position (>45 cm) or rotation (>30 deg) jump at a `continuous_action` boundary | Major | Deterministic Engine Rule |
| **IF-005** | Expected prop not visible | Actor has `visibility_state=True` in Sequencer but 0% unoccluded pixels in Object-ID mask | Major | Hybrid Metadata + Object-ID CV |
| **IF-006** | Appearance regression in shot | Controlled reference vs current render diverges in SSIM (<0.82) or LAB chroma (>18.0) inside actor ROI | Minor | Hybrid Metadata + Controlled CV |
| **IF-007** | Unexpected asset substitution | Bound mesh/material ID differs from declared expected asset invariant | Major | Deterministic Engine Rule |
| **IF-008** | Rule/data-quality problem | Contradictory or incomplete expected-state rule configuration | Informational | Deterministic Config Audit |

## Benchmark Evaluation (`LEAVE_ALIVE` Testbed)

Three baselines are tested on a 25-sequence benchmark (**125 shots**, **100 shot boundaries**, **105 seeded faults** across `IF-001`..`IF-008`, with simulated Lumen GI grain, exposure shifts, camera cuts, and declared intentional narrative state changes):

| Baseline | Precision (95% CI) | Recall (95% CI) | F1 Score (95% CI) | False Positives / 100 Cuts | Runtime (25 Seqs) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **B1 — Engine Rules Only** | 1.0000 (1.0, 1.0) | 0.7143 (0.697, 0.7317) | 0.8333 (0.8214, 0.8451) | 0.00 | 3.365s |
| **B2 — Image-Only Diff** | 0.2308 (0.1803, 0.2857) | 0.2857 (0.2683, 0.303) | 0.2553 (0.2136, 0.2888) | 100.00 | 5.852s |
| **B3 — Hybrid Interframe** | **1.0000** (1.0, 1.0) | **1.0000** (1.0, 1.0) | **1.0000** (1.0, 1.0) | **0.00** | 6.109s |

- **Detection Accuracy**: Combining Unreal Engine metadata with Object-ID masked render checks gets rid of the 100.0 FP/100-cuts camera-cut & exposure false-positive problem seen in image-only diffs (`B2`) while bringing recall from `0.7143` (`B1`) up to `1.0000` (`B3`) by catching camera-space prop occlusions (`IF-005`) and shader regressions (`IF-006`).
- **Review Efficiency**: In the 25-sequence crossover review simulation, median sequence review time drops from **15.00 min** (manual) to **6.20 min** (Interframe-assisted), a **58.67% reduction**.
- **Inter-Rater Agreement**: Adjudicated 40-item subset hits Cohen's $\kappa = 0.9636$ (97.5% observed agreement).

## Quickstart

### Prerequisites
- **Python 3.11+**
- **Unreal Engine 5.8** (optional, for Editor plugin compilation)

### Installation
Clone the repository and set up a local Python virtual environment:
```bash
git clone https://github.com/GiTaDi-CrEaTe/interframe.git
cd interframe
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

### 1. Run Unit & Integration Tests
```bash
python3 -m unittest discover -s tests -t . -p "test_*.py" -v
```

### 2. Run the Scientific Evaluation Benchmark (B1 vs. B2 vs. B3)
```bash
python3 evaluation/evaluate_baselines.py
```

### 3. Analyze a Single Level Sequence Manifest via CLI
```bash
python3 python/interframe_engine/cli.py analyze \
  --manifest evaluation/artifacts/dataset/manifests/LS_LeaveAlive_Scn01.manifest.v1.json \
  --out /tmp/scn01_report.json \
  --csv /tmp/scn01_report.csv \
  --html /tmp/scn01_report.html \
  --db /tmp/interframe_local.sqlite \
  --mode B3_HYBRID
```

### 4. Record an Artist/QA Reviewer Disposition
```bash
python3 python/interframe_engine/cli.py review \
  --db /tmp/interframe_local.sqlite \
  --issue-id ISS-IF001-7D98A42E1B90 \
  --decision true_positive \
  --reviewer lead_tech_artist \
  --notes "Broken CaveLantern asset path fixed in CL 10492"
```

## Contributors

- **Adityajyoti Kar** ([@GiTaDi-CrEaTe](https://github.com/GiTaDi-CrEaTe)) — Creator & Lead Developer

## License & Notice

Released under the Apache License 2.0. Copyright 2026 Adityajyoti Kar. Independent research and engineering project; not affiliated with or endorsed by Epic Games, InterPositive, or Netflix.
