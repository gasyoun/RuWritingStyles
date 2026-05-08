"""SQLite database layer for RuWritingStyles (Phase G)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, repo_root: Path):
        self.db_path = repo_root / "rws.db"
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    input_path TEXT,
                    provider TEXT,
                    model TEXT,
                    archetype TEXT,
                    status TEXT DEFAULT 'prepared',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    summary TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS run_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    metric_type TEXT,
                    data_json TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_run_id ON run_metrics(run_id)
            """)
            
            # Add updated_at trigger logic
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_run_timestamp 
                AFTER UPDATE ON runs
                FOR EACH ROW
                BEGIN
                    UPDATE runs SET updated_at = CURRENT_TIMESTAMP WHERE run_id = old.run_id;
                END
            """)

    def register_run(self, run_id: str, input_path: str, provider: str, model: str | None = None, archetype: str | None = None):
        """Create a new run entry."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO runs (run_id, input_path, provider, model, archetype) VALUES (?, ?, ?, ?, ?)",
                (run_id, input_path, provider, model, archetype)
            )

    def update_run_status(self, run_id: str, status: str, summary: str | None = None):
        """Update the status of an existing run."""
        with self._get_connection() as conn:
            if summary:
                conn.execute(
                    "UPDATE runs SET status = ?, summary = ? WHERE run_id = ?",
                    (status, summary, run_id)
                )
            else:
                conn.execute(
                    "UPDATE runs SET status = ? WHERE run_id = ?",
                    (status, run_id)
                )

    def save_metric(self, run_id: str, metric_type: str, data: Any):
        """Save a metric (e.g., bloom_stats, compass) as JSON."""
        with self._get_connection() as conn:
            # Upsert logic for metrics of same type for same run
            conn.execute(
                "DELETE FROM run_metrics WHERE run_id = ? AND metric_type = ?",
                (run_id, metric_type)
            )
            conn.execute(
                "INSERT INTO run_metrics (run_id, metric_type, data_json) VALUES (?, ?, ?)",
                (run_id, metric_type, json.dumps(data, ensure_ascii=False))
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve full run details including metrics."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if not row:
                return None
            
            run_data = dict(row)
            
            # Fetch metrics
            metrics_rows = conn.execute("SELECT metric_type, data_json FROM run_metrics WHERE run_id = ?", (run_id,)).fetchall()
            for m_row in metrics_rows:
                run_data[m_row['metric_type']] = json.loads(m_row['data_json'])
                
            return run_data

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        """List recent runs."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def delete_run(self, run_id: str):
        """Delete a run and its associated metrics."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
