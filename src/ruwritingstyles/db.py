"""SQLite database layer for RuWritingStyles (Phase G)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
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

    @contextmanager
    def _connection(self):
        conn = self._get_connection()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initialize the database schema."""
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    input_path TEXT,
                    provider TEXT,
                    model TEXT,
                    archetype TEXT,
                    profile TEXT,
                    status TEXT DEFAULT 'prepared',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    duration_seconds REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    summary TEXT,
                    config_json TEXT
                )
            """)
            
            # Migration for existing DBs
            try:
                conn.execute("ALTER TABLE runs ADD COLUMN started_at TIMESTAMP")
            except sqlite3.OperationalError: pass
            try:
                conn.execute("ALTER TABLE runs ADD COLUMN finished_at TIMESTAMP")
            except sqlite3.OperationalError: pass
            try:
                conn.execute("ALTER TABLE runs ADD COLUMN duration_seconds REAL")
            except sqlite3.OperationalError: pass
            try:
                conn.execute("ALTER TABLE runs ADD COLUMN profile TEXT")
            except sqlite3.OperationalError: pass
            try:
                conn.execute("ALTER TABLE runs ADD COLUMN config_json TEXT")
            except sqlite3.OperationalError: pass
            
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
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS run_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    step_id TEXT,
                    status TEXT DEFAULT 'pending',
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    artifact_path TEXT,
                    error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                    UNIQUE(run_id, step_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS run_tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    task TEXT,
                    tool_name TEXT,
                    arguments_json TEXT,
                    response_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS corpus_metadata (
                    file_path TEXT PRIMARY KEY,
                    title TEXT,
                    author TEXT,
                    year INTEGER,
                    last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # FTS5 Virtual Table for Deep Document Retrieval (Phase VI)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS corpus_segments USING fts5(
                    file_path,
                    segment_index,
                    content,
                    tokenize="unicode61"
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tool_calls_run_id ON run_tool_calls(run_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_steps_run_id ON run_steps(run_id)
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

    def register_run(self, run_id: str, input_path: str, provider: str, model: str | None = None, archetype: str | None = None, profile: str | None = None, config: dict | None = None):
        """Create a new run entry."""
        with self._connection() as conn:
            conn.execute("DELETE FROM run_steps WHERE run_id = ?", (run_id,))
            conn.execute("DELETE FROM run_metrics WHERE run_id = ?", (run_id,))
            conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
            conn.execute(
                "INSERT INTO runs (run_id, input_path, provider, model, archetype, profile, config_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, input_path, provider, model, archetype, profile, json.dumps(config) if config else None)
            )

    def update_step_status(self, run_id: str, step_id: str, status: str, artifact_path: str | None = None, error: str | None = None):
        """Update the status of a specific step in a run."""
        with self._connection() as conn:
            now = datetime.now(timezone.utc).isoformat()
            
            row = conn.execute("SELECT id FROM run_steps WHERE run_id = ? AND step_id = ?", (run_id, step_id)).fetchone()
            
            if not row:
                conn.execute(
                    "INSERT INTO run_steps (run_id, step_id, status, started_at) VALUES (?, ?, ?, ?)",
                    (run_id, step_id, status, now if status == "executing" else None)
                )
            else:
                if status == "executing":
                    conn.execute(
                        "UPDATE run_steps SET status = ?, started_at = ?, error = NULL WHERE id = ?",
                        (status, now, row["id"])
                    )
                elif status in ("completed", "failed"):
                    conn.execute(
                        "UPDATE run_steps SET status = ?, finished_at = ?, artifact_path = ?, error = ? WHERE id = ?",
                        (status, now, artifact_path, error, row["id"])
                    )
                else:
                    conn.execute(
                        "UPDATE run_steps SET status = ? WHERE id = ?",
                        (status, row["id"])
                    )

    def get_run_steps(self, run_id: str) -> list[dict[str, Any]]:
        """Retrieve all steps for a run."""
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM run_steps WHERE run_id = ? ORDER BY id ASC", (run_id,)).fetchall()
            return [dict(row) for row in rows]

    def update_run_status(self, run_id: str, status: str, summary: str | None = None):
        """Update the status of an existing run and track timestamps."""
        with self._connection() as conn:
            now = datetime.now(timezone.utc).isoformat()
            
            if status == "executing":
                conn.execute(
                    "UPDATE runs SET status = ?, started_at = ? WHERE run_id = ?",
                    (status, now, run_id)
                )
            elif status in ("completed", "failed"):
                # Fetch started_at to calculate duration
                row = conn.execute("SELECT started_at FROM runs WHERE run_id = ?", (run_id,)).fetchone()
                duration = None
                if row and row["started_at"]:
                    try:
                        start_time = datetime.fromisoformat(row["started_at"])
                        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                    except ValueError:
                        pass
                
                if summary:
                    conn.execute(
                        "UPDATE runs SET status = ?, finished_at = ?, duration_seconds = ?, summary = ? WHERE run_id = ?",
                        (status, now, duration, summary, run_id)
                    )
                else:
                    conn.execute(
                        "UPDATE runs SET status = ?, finished_at = ?, duration_seconds = ? WHERE run_id = ?",
                        (status, now, duration, run_id)
                    )
            else:
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
        with self._connection() as conn:
            # Upsert logic for metrics of same type for same run
            conn.execute(
                "DELETE FROM run_metrics WHERE run_id = ? AND metric_type = ?",
                (run_id, metric_type)
            )
            conn.execute(
                "INSERT INTO run_metrics (run_id, metric_type, data_json) VALUES (?, ?, ?)",
                (run_id, metric_type, json.dumps(data, ensure_ascii=False))
            )

    def save_tool_call(self, run_id: str, task: str, tool_name: str, arguments: dict, response: Any):
        """Record an agentic tool call and its response."""
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO run_tool_calls (run_id, task, tool_name, arguments_json, response_json) VALUES (?, ?, ?, ?, ?)",
                (
                    run_id,
                    task,
                    tool_name,
                    json.dumps(arguments, ensure_ascii=False),
                    json.dumps(response, ensure_ascii=False) if response is not None else None,
                )
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve full run details including metrics."""
        with self._connection() as conn:
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
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def delete_run(self, run_id: str):
        """Delete a run and its associated metrics."""
        with self._connection() as conn:
            conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
