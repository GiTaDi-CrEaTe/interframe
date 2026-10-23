# Interframe Continuity QA — Project Fixes & Remediation Log

This document records the full audit, bug fixes, code corrections, and language humanization performed across the Interframe codebase.

---

## 1. Code Fixes & Technical Corrections

### 1.1 C++ Unreal Engine Plugin Compilation Fix (`InterframeSequencerBridge.cpp`)
- **Problem**: In `Source/InterframePlugin/Private/InterframeSequencerBridge.cpp` (line 116), nested string arguments inside `TEXT(...)` were unescaped: `TEXT(""%s" analyze --manifest "%s" --out "%s"")`. In C++, this resulted in invalid string concatenation and broken compilation.
- **Fix**: Escaped quotes properly: `TEXT("\"%s\" analyze --manifest \"%s\" --out \"%s\"")`.

### 1.2 Implemented Reviewer Disposition in C++ Bridge (`InterframeSequencerBridge.cpp`)
- **Problem**: `FInterframeSequencerBridge::RecordReviewerDisposition` was a dummy placeholder that only checked `!InIssueId.IsEmpty()`, without invoking persistence.
- **Fix**: Implemented complete execution path: resolves the disposition enum (`true_positive`, `false_positive`, `intentional_change`, `unresolved`), builds the CLI command targeting `interframe_local.sqlite`, and executes the process via `FPlatformProcess::ExecProcess`.

### 1.3 Resolved SQLite Database Connection Leaks (`python/interframe_engine/persistence.py`)
- **Problem**: `sqlite3.connect(...)` used as a context manager (`with sqlite3.connect(...) as conn:`) only commits or rolls back transactions on block exit—it does not close the connection handle. This leaked file descriptors and caused `ResourceWarning: unclosed database in <sqlite3.Connection>` warnings during test and evaluation runs.
- **Fix**: Added a dedicated `_connect()` context manager using `try ... finally: conn.close()` to ensure all SQLite database connections close immediately upon completion across `_init_db`, `save_run`, `update_reviewer_disposition`, `get_issues_for_run`, and `get_issue_history`.

### 1.4 Fixed Schema / Config Property Casing (`rules/default_continuity_rules.json`)
- **Problem**: In rule `IF-005` thresholds, `"min_Visible_pixel_count"` had an inconsistent uppercase `V`, diverging from code expectations in `python/vision_worker/comparator.py`.
- **Fix**: Standardized to lowercase `"min_visible_pixel_count"`.

### 1.5 Missing Typing Import and Parameter Alignment (`evaluation/evaluate_baselines.py`)
- **Problem**: `evaluation/evaluate_baselines.py` used `Optional[Path]` in function signatures without importing `Optional` from `typing`. Additionally, the bootstrap resample default (`n_resamples = 400`) did not match the documentation (500).
- **Fix**: Added `Optional` to `from typing import ...` and updated default `n_resamples = 500`.

### 1.6 Environment Auto-Detection in CI/Runner Script (`scripts/run_ci_checks.sh`)
- **Problem**: `scripts/run_ci_checks.sh` hardcoded `python3`, which broke on systems where dependencies were installed inside a project virtualenv (`.venv`).
- **Fix**: Added auto-detection logic to prioritize `.venv/bin/python3` when present, falling back to system `python3`.

### 1.7 Repository Git Hygiene (`.gitignore`)
- **Problem**: `.gitignore` lacked entries for virtual environment directories (`.venv/`, `venv/`) and `.DS_Store`.
- **Fix**: Added `.venv/`, `venv/`, and `.DS_Store` to prevent accidental commit of local environment files.

---

## 2. AI Markers, Buzzwords & Prompt Artifact Elimination

A comprehensive pass was conducted to remove synthetic AI markers, prompt section references, and corporate buzzwords, replacing them with standard engineering terminology.

### 2.1 Removed Prompt Blueprint Section Artifacts
The original codebase contained references to prompt instructions and assignment blueprints:
- Removed `"Blueprint Section 5 & Section 6"`, `"Blueprint Pages 8–9"`, and `"Blueprint Section 9"` from Python docstrings in:
  - `python/interframe_engine/hybrid_pipeline.py`
  - `python/interframe_engine/rule_engine.py`
  - `python/interframe_engine/persistence.py`
  - `python/vision_worker/comparator.py`
  - `python/vision_worker/model_adapters.py`
  - `python/collector/mrq_orchestrator.py`
  - `evaluation/evaluate_baselines.py`
  - `evaluation/benchmark_generator.py`
  - `evaluation/__init__.py`
- Removed `"Blueprint Section 4 & Section 5"` from `Source/InterframePlugin/Public/InterframeEditorValidator.h`.
- Removed `"Blueprint Section 5 & Section 9"` from schema descriptions in:
  - `schemas/issue.v1.json`
  - `schemas/manifest.v1.json`
- Removed `"Appendix A"` label in user-facing headings (`README.md`, `rules/default_continuity_rules.json`).

### 2.2 Replaced AI Buzzwords & Hyperbole
- **Buzzwords removed or replaced**:
  - `falsifiable scientific evaluation` -> `measurable evaluation`
  - `hybrid verification architecture` -> `engine-aware continuity verification`
  - `Human-in-the-Loop Artist Governance` -> `Artist Review & Sign-off`
  - `Targeted Controlled Render Verification` -> `Selective Render Checks`
  - `bridges both worlds` -> `connects both data sources`
  - `light up on anti-aliasing` -> `fire on anti-aliasing`
  - `studio-ready artifacts` -> `JSON, CSV, and HTML reports`
  - `rigorous systems engineering paired with falsifiable scientific evaluation` -> `real systems engineering and measurable evaluation`
- **Studio Deployment & Production Focus (`docs/STUDIO_DEPLOYMENT_GUIDE.md`)**:
  - Completely removed the academic portfolio guide (`docs/MIT_PORTFOLIO_AND_STUDIO_GUIDE.md`) and replaced it with a production-focused studio pipeline guide (`docs/STUDIO_DEPLOYMENT_GUIDE.md`).
  - Added operational studio instructions: Editor plugin setup, automated pre-submit validation hooks, interactive Slate tab review, headless build farm execution, and Perforce/Git artist sign-off workflows.

---

## 3. Verification & Test Results

All verification suites were run against the updated codebase:

1. **Unit Test Suite** (`tests/unit/test_core.py`):
   - `test_clean_manifest_produces_zero_issues`: **PASS**
   - `test_if001_missing_asset_reference`: **PASS**
   - `test_if002_unbound_expected_actor`: **PASS**
   - `test_if003_unexpected_state_change_and_declared_transition_override`: **PASS**
   - `test_if004_transform_discontinuity`: **PASS**
   - `test_if005_and_if006_visual_worker`: **PASS**
   - `test_mrq_orchestrator_and_model_registry`: **PASS**
   - `test_persistence_versioning_and_reviewer_disposition`: **PASS**

2. **Integration Test Suite** (`tests/integration/test_end_to_end.py`):
   - `test_cli_analyze_and_review_workflow`: **PASS**
   - `test_full_evaluation_protocol_and_hypotheses`: **PASS**

3. **Evaluation Benchmark** (`evaluation/evaluate_baselines.py`):
   - **B1 (Engine Rules Only)**: Precision = 1.0000, Recall = 0.7143, F1 = 0.8333, FP/100 boundaries = 0.00
   - **B2 (Image Only Diff)**: Precision = 0.2308, Recall = 0.2857, F1 = 0.2553, FP/100 boundaries = 100.00
   - **B3 (Hybrid Interframe)**: Precision = 1.0000, Recall = 1.0000, F1 = 1.0000, FP/100 boundaries = 0.00
   - All hypothesis gates: **PASSED**
   - Warnings & leaks: **0 ResourceWarnings, 0 unclosed connections**
