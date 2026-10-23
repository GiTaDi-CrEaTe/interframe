# Studio Deployment & Production Pipeline Guide

This guide describes how to deploy, configure, and integrate Interframe into Unreal Engine 5.8 cinematic production pipelines.

---

## 1. Plugin Installation

Interframe provides an Unreal Engine 5.8 Editor plugin located in `Unreal/InterframePlugin/`.

### 1.1 Project-Level Installation
1. Copy the plugin directory into your project's `Plugins/` folder:
   ```bash
   cp -r Unreal/InterframePlugin <YourProject>/Plugins/InterframePlugin
   ```
2. Enable the required prerequisite plugins in your `<YourProject>.uproject`:
   - `LevelSequenceEditor`
   - `SequencerScripting`
   - `MovieRenderPipeline`
   - `DataValidation`
   - `PythonScriptPlugin`
3. Regenerate project files and build your project editor target.

---

## 2. Unreal Editor Workflow

### 2.1 Automated Pre-Submit Asset Validation
Interframe includes `UInterframeEditorValidator`, which extends Unreal Engine's `UEditorValidatorBase`:
- Automatically triggers when a `ULevelSequence` is saved or submitted via Perforce / Git source control.
- Deterministically evaluates rules `IF-001` through `IF-004`, `IF-007`, and `IF-008` directly from engine memory.
- Blocks submission if critical defects exist (e.g. broken asset references or unbound required actors).
- Emits warnings for transform jumps or undeclared state changes that require artist review.

### 2.2 Interactive Slate Review Tab (`SInterframeReviewTab`)
Artists and technical directors can review continuity findings inside the Unreal Editor:
1. Open the review tool via **Window -> Cinematics -> Interframe Continuity QA**.
2. Select target Level Sequences and validation profile.
3. Scrub flagged shot boundaries to inspect actor bindings, transform deltas, and rendered mask evidence.
4. Mark findings directly as `True Positive`, `False Positive`, or `Intentional Change`.

---

## 3. Headless CI & Build Farm Integration

For nightly builds or automated review pipelines, Interframe runs standalone via command line or headless engine commandlet.

### 3.1 Python CLI Diagnostic Analysis
Run continuity diagnostics against any generated Level Sequence manifest:
```bash
python3 python/interframe_engine/cli.py analyze \
  --manifest Saved/Interframe/Manifests/LS_Cinematic_Scn01.manifest.v1.json \
  --out Saved/Interframe/Reports/LS_Cinematic_Scn01_report.json \
  --csv Saved/Interframe/Reports/LS_Cinematic_Scn01_report.csv \
  --html Saved/Interframe/Reports/LS_Cinematic_Scn01_report.html \
  --db Saved/Interframe/interframe_local.sqlite \
  --mode B3_HYBRID
```

### 3.2 Automated Unreal Editor Commandlet
To extract manifests and run checks headlessly on build agents:
```bash
UnrealEditor-Cmd "<ProjectPath>" -run=InterframeValidate \
  -Sequence="/Game/Cinematics/Sequences/LS_Scn01" \
  -Profile="MRQ_Controlled_Linear_sRGB_v1" \
  -unattended -nopause -StdOut
```

---

## 4. Reviewer Feedback & Disposition Workflow

Interframe maintains an append-only audit trail and local SQLite persistence (`InterframeStore`):
- Findings are tracked with stable identifiers (`issue_id`) and content hashes.
- Dispositions (`true_positive`, `false_positive`, `intentional_change`, `unresolved`) persist across builds and source revisions.
- Technical artists can record dispositions via the Editor tab or CLI:
  ```bash
  python3 python/interframe_engine/cli.py review \
    --db Saved/Interframe/interframe_local.sqlite \
    --issue-id ISS-IF001-7D98A42E1B90 \
    --decision true_positive \
    --reviewer lead_tech_artist \
    --notes "Broken CaveLantern asset reference fixed in CL 10492"
  ```
- Findings marked `intentional_change` are carried forward so approved narrative changes do not repeatedly block CI gates.

---

## 5. Security & Asset Privacy

- **Local-First Execution**: All manifest files, rendered Movie Render Queue frames, Object-ID masks, and SQLite databases remain strictly on local developer workstations or on-premise studio infrastructure.
- **Zero Asset Upload**: No textures, geometry, animation curves, or rendered pixels are transmitted to external services.
- **Read-Only Operations**: Diagnostic checks inspect scene and asset registry states without modifying `.uasset` or `.umap` files.
