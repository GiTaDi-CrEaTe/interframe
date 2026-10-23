"""Local-first SQLite and JSONL persistence with build versioning & reviewer feedback.

Storage behaviors:
- Uses local SQLite + append-only JSONL with content hashes.
- Never silently overwrites historical findings; versions them by `run_id` / `first_seen_build`.
- Persists artist/QA reviewer dispositions (`true_positive`, `false_positive`, `intentional_change`, `unresolved`)
  and exports reviewer decisions for auditability.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


class InterframeStore:
    """SQLite + JSONL local storage for manifests, versioned findings, and reviewer feedback."""

    VALID_DISPOSITIONS = {"true_positive", "false_positive", "intentional_change", "unresolved"}

    def __init__(self, db_path: str | Path, jsonl_audit_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_audit_path = (
            Path(jsonl_audit_path)
            if jsonl_audit_path is not None
            else self.db_path.with_suffix(".audit.jsonl")
        )
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Provides a managed SQLite connection that closes properly upon exit."""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS diagnostic_runs (
                    run_id TEXT PRIMARY KEY,
                    project_hash TEXT NOT NULL,
                    sequence_id TEXT NOT NULL,
                    source_control_revision TEXT NOT NULL,
                    execution_mode TEXT NOT NULL,
                    manifest_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS findings_history (
                    record_pk INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    issue_id TEXT NOT NULL,
                    sequence_id TEXT NOT NULL,
                    shot_id TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL,
                    reviewer_status TEXT NOT NULL,
                    first_seen_build TEXT NOT NULL,
                    issue_json TEXT NOT NULL,
                    UNIQUE(run_id, issue_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reviewer_dispositions (
                    issue_id TEXT PRIMARY KEY,
                    decision TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_run(
        self,
        run_id: str,
        manifest: Dict[str, Any],
        issues: List[Dict[str, Any]],
        execution_mode: str = "B3_HYBRID",
    ) -> str:
        """Persists a diagnostic run and its findings without overwriting prior runs."""
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO diagnostic_runs
                (run_id, project_hash, sequence_id, source_control_revision, execution_mode, manifest_sha256, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    manifest["project_id_hash"],
                    manifest["sequence_id"],
                    manifest["source_control_revision"],
                    execution_mode,
                    manifest_sha256,
                    now_iso,
                ),
            )

            for issue in issues:
                # Check if an earlier build already recorded this issue_id
                row = conn.execute(
                    "SELECT first_seen_build FROM findings_history WHERE issue_id = ? ORDER BY record_pk ASC LIMIT 1",
                    (issue["issue_id"],),
                ).fetchone()
                if row:
                    issue["first_seen_build"] = row[0]

                # Apply existing reviewer disposition if already reviewed
                disp = conn.execute(
                    "SELECT decision, reviewer_id, notes, updated_at FROM reviewer_dispositions WHERE issue_id = ?",
                    (issue["issue_id"],),
                ).fetchone()
                if disp:
                    issue["reviewer_status"] = disp[0]
                    issue["reviewer_disposition"] = {
                        "decision": disp[0],
                        "reviewer_id": disp[1],
                        "notes": disp[2],
                        "updated_at": disp[3],
                    }

                conn.execute(
                    """
                    INSERT OR REPLACE INTO findings_history
                    (run_id, issue_id, sequence_id, shot_id, rule_id, severity, confidence, status, reviewer_status, first_seen_build, issue_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        issue["issue_id"],
                        issue["sequence_id"],
                        issue["shot_id"],
                        issue["rule_id"],
                        issue["severity"],
                        issue["confidence"],
                        issue["status"],
                        issue["reviewer_status"],
                        issue["first_seen_build"],
                        json.dumps(issue, sort_keys=True),
                    ),
                )
            conn.commit()

        with open(self.jsonl_audit_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "event": "run_saved",
                        "run_id": run_id,
                        "sequence_id": manifest["sequence_id"],
                        "manifest_sha256": manifest_sha256,
                        "issue_count": len(issues),
                        "timestamp": now_iso,
                    }
                )
                + "\n"
            )
        return manifest_sha256

    def update_reviewer_disposition(
        self,
        issue_id: str,
        decision: str,
        reviewer_id: str = "tech_artist_lead",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Updates reviewer disposition and logs to the append-only audit trail."""
        if decision not in self.VALID_DISPOSITIONS:
            raise ValueError(f"Invalid decision '{decision}'. Must be one of {sorted(self.VALID_DISPOSITIONS)}")

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reviewer_dispositions
                (issue_id, decision, reviewer_id, notes, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (issue_id, decision, reviewer_id, notes, now_iso),
            )
            rows = conn.execute(
                "SELECT record_pk, issue_json FROM findings_history WHERE issue_id = ?",
                (issue_id,),
            ).fetchall()
            for pk, raw_json in rows:
                issue_obj = json.loads(raw_json)
                issue_obj["reviewer_status"] = decision
                issue_obj["reviewer_disposition"] = {
                    "decision": decision,
                    "reviewer_id": reviewer_id,
                    "notes": notes,
                    "updated_at": now_iso,
                }
                conn.execute(
                    "UPDATE findings_history SET reviewer_status = ?, issue_json = ? WHERE record_pk = ?",
                    (decision, json.dumps(issue_obj, sort_keys=True), pk),
                )
            conn.commit()

        record = {
            "event": "reviewer_disposition_updated",
            "issue_id": issue_id,
            "decision": decision,
            "reviewer_id": reviewer_id,
            "notes": notes,
            "updated_at": now_iso,
        }
        with open(self.jsonl_audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record

    def get_issues_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT issue_json FROM findings_history WHERE run_id = ? ORDER BY record_pk ASC",
                (run_id,),
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def get_issue_history(self, issue_id: str) -> List[Dict[str, Any]]:
        """Returns all historical versions of an issue across builds/runs."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT run_id, first_seen_build, reviewer_status, issue_json FROM findings_history WHERE issue_id = ? ORDER BY record_pk ASC",
                (issue_id,),
            ).fetchall()
        return [
            {
                "run_id": r[0],
                "first_seen_build": r[1],
                "reviewer_status": r[2],
                "issue": json.loads(r[3]),
            }
            for r in rows
        ]
