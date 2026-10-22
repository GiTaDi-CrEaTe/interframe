#!/usr/bin/env python3
"""Command-line interface for the Interframe Continuity QA Engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure sibling packages are importable
PYTHON_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from interframe_engine.hybrid_pipeline import InterframeHybridPipeline
from interframe_engine.persistence import InterframeStore
from interframe_engine.reporting import InterframeReportExporter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="interframe",
        description="Interframe: Engine-aware hybrid continuity QA for Unreal Engine Level Sequences.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze_p = sub.add_parser("analyze", help="Run continuity diagnostics on a shot manifest JSON.")
    analyze_p.add_argument("--manifest", required=True, help="Path to manifest.v1.json")
    analyze_p.add_argument("--out", required=True, help="Output JSON report path")
    analyze_p.add_argument("--csv", help="Optional CSV output path")
    analyze_p.add_argument("--html", help="Optional HTML output path")
    analyze_p.add_argument("--db", help="Optional SQLite persistence path")
    analyze_p.add_argument(
        r"--mode",
        choices=["B1_RULES_ONLY", "B2_IMAGE_ONLY", "B3_HYBRID"],
        default="B3_HYBRID",
        help="Execution baseline mode",
    )
    analyze_p.add_argument("--run-id", default="run-cli-001", help="Unique run identifier")

    review_p = sub.add_parser("review", help="Update reviewer disposition for a finding in SQLite.")
    review_p.add_argument("--db", required=True, help="SQLite DB path")
    review_p.add_argument("--issue-id", required=True, help="Issue ID")
    review_p.add_argument(
        r"--decision",
        required=True,
        choices=["true_positive", "false_positive", "intentional_change", "unresolved"],
    )
    review_p.add_argument("--reviewer", default="cinematic_lead")
    review_p.add_argument("--notes", default="")

    args = parser.parse_args(argv)

    if args.command == "analyze":
        with open(args.manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        pipeline = InterframeHybridPipeline()
        issues = pipeline.run(manifest, mode=args.mode, run_id=args.run_id)
        if args.db:
            store = InterframeStore(args.db)
            store.save_run(args.run_id, manifest, issues, execution_mode=args.mode)
            issues = store.get_issues_for_run(args.run_id)
        InterframeReportExporter.export_json(
            issues,
            args.out,
            metadata={"sequence_id": manifest["sequence_id"], "mode": args.mode, "run_id": args.run_id},
        )
        if args.csv:
            InterframeReportExporter.export_csv(issues, args.csv)
        if args.html:
            InterframeReportExporter.export_html(issues, args.html)
        print(f"Analyzed {manifest['sequence_id']} ({args.mode}): {len(issues)} findings written to {args.out}")
        return 0

    if args.command == "review":
        store = InterframeStore(args.db)
        rec = store.update_reviewer_disposition(
            issue_id=args.issue_id,
            decision=args.decision,
            reviewer_id=args.reviewer,
            notes=args.notes,
        )
        print(f"Updated {rec['issue_id']} -> {rec['decision']}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
