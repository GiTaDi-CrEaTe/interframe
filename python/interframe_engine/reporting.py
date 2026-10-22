"""Exports Interframe Continuity QA findings to JSON, CSV, and local HTML reports."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any, Dict, List


class InterframeReportExporter:
    """Exports structured continuity findings into studio-ready JSON, CSV, and HTML artifacts."""

    @staticmethod
    def export_json(issues: List[Dict[str, Any]], out_path: str | Path, metadata: Dict[str, Any] | None = None) -> Path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "report_schema": "interframe.report.v1",
            "metadata": metadata or {},
            "total_issues": len(issues),
            "issues": issues,
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        return out

    @staticmethod
    def export_csv(issues: List[Dict[str, Any]], out_path: str | Path) -> Path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "issue_id",
            "rule_id",
            "issue_type",
            "severity",
            "confidence",
            "status",
            "sequence_id",
            "shot_id",
            "frame",
            "seconds",
            "actor_label",
            "actor_guid",
            "asset_path",
            "one_sentence_explanation",
            "reviewer_status",
            "first_seen_build",
            "run_id",
        ]
        with open(out, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for iss in issues:
                writer.writerow(
                    {
                        "issue_id": iss["issue_id"],
                        "rule_id": iss["rule_id"],
                        "issue_type": iss["issue_type"],
                        "severity": iss["severity"],
                        "confidence": iss["confidence"],
                        "status": iss["status"],
                        "sequence_id": iss["sequence_id"],
                        "shot_id": iss["shot_id"],
                        "frame": iss["frame_time"]["frame"],
                        "seconds": iss["frame_time"]["seconds"],
                        "actor_label": iss.get("actor_label", ""),
                        "actor_guid": iss["actor_guid"],
                        "asset_path": iss["asset_path"],
                        "one_sentence_explanation": iss["one_sentence_explanation"],
                        "reviewer_status": iss["reviewer_status"],
                        "first_seen_build": iss["first_seen_build"],
                        "run_id": iss["run_id"],
                    }
                )
        return out

    @staticmethod
    def export_html(issues: List[Dict[str, Any]], out_path: str | Path, title: str = "Interframe Continuity QA Report") -> Path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        rows_html = []
        for iss in issues:
            rows_html.append(
                f"<tr>"
                f"<td><code>{html.escape(iss['issue_id'])}</code></td>"
                f"<td><strong>{html.escape(iss['rule_id'])}</strong><br><small>{html.escape(iss['issue_type'])}</small></td>"
                f"<td>{html.escape(iss['severity'])}</td>"
                f"<td>{iss['confidence']:.2f}</td>"
                f"<td><code>{html.escape(iss['sequence_id'])} / {html.escape(iss['shot_id'])} @ f{iss['frame_time']['frame']}</code></td>"
                f"<td>{html.escape(iss.get('actor_label', iss['actor_guid']))}</td>"
                f"<td>{html.escape(iss['one_sentence_explanation'])}</td>"
                f"<td>{html.escape(iss['reviewer_status'])}</td>"
                f"</tr>"
            )
        doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; margin: 24px; color: #0f172a; background: #f8fafc; }}
h1 {{ margin-bottom: 8px; }}
table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; }}
th, td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-align: left; font-size: 13px; }}
th {{ background: #0f172a; color: #f8fafc; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p>Total findings: <strong>{len(issues)}</strong></p>
<table>
<thead>
<tr>
<th>Issue ID</th><th>Rule</th><th>Severity</th><th>Confidence</th><th>Sequence / Shot / Frame</th><th>Actor</th><th>Explanation</th><th>Disposition</th>
</tr>
</thead>
<tbody>
{"".join(rows_html)}
</tbody>
</table>
</body>
</html>
"""
        with open(out, "w", encoding="utf-8") as f:
            f.write(doc)
        return out
