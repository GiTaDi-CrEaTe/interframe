# Contributing to Interframe

Thank you for your interest in contributing to **Interframe**! We welcome contributions to our Unreal Engine Level Sequence continuity QA engine, schemas, computer vision comparator, and evaluation testbeds.

---

## Code of Conduct

Please treat everyone with respect and empathy. We are committed to providing a friendly, safe, and welcoming environment for all contributors.

---

## Development Setup

### Prerequisites
- **Python 3.11+**
- **Unreal Engine 5.8** (optional for standalone Python development; required for Editor Plugin compilation)
- `git`

### Quickstart
1. Clone your fork of the repository:
   ```bash
   git clone https://github.com/GiTaDi-CrEaTe/interframe.git
   cd interframe
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies in editable mode:
   ```bash
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```

---

## Running Verification & Tests

Always run the full verification gate before opening a pull request:
```bash
bash scripts/run_ci_checks.sh
```

Or run test suites independently:
- **Unit and Integration Tests**:
  ```bash
  python3 -m unittest discover -s tests -t . -p "test_*.py" -v
  ```
- **LEAVE_ALIVE Benchmark Evaluation**:
  ```bash
  python3 evaluation/evaluate_baselines.py
  ```

---

## Coding Standards

### Python
- Maintain standard Python typing annotations for public APIs.
- Ensure all file operations explicitly specify `encoding="utf-8"`.
- Use context managers (`with`) for database connections and temporary files to prevent resource leaks.
- Avoid external cloud dependencies for core engine rules; maintain workstation-local execution.

### Unreal Engine C++
- Follow Epic Games C++ coding conventions (PascalCase, `F`/`U`/`A`/`E`/`T` prefixes).
- Ensure all `USTRUCT(BlueprintType)` declarations have `GENERATED_BODY()`.
- Use `#pragma once` for header guards.
- Log via dedicated categorizations.

---

## Submitting Pull Requests

1. Create a feature branch: `git checkout -b feature/my-feature-name`.
2. Commit your changes with clear, descriptive commit messages.
3. Verify all tests and benchmarks pass with zero regressions.
4. Push your branch to GitHub and open a Pull Request against `main`.
