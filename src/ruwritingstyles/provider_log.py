"""Provider execution log helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def append_provider_log(
    *,
    run_dir: Path,
    task: str,
    provider: str,
    model: str,
    artifact_path: str,
    status: str,
    duration_ms: int,
    retry_count: int = 0,
    retry_delay_seconds: float = 0.0,
    retry_statuses: list[str] | None = None,
    error: str | None = None,
) -> Path:
    """Append one JSONL entry to provider.log.jsonl."""

    log_path = run_dir.resolve() / "provider.log.jsonl"
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": task,
        "provider": provider,
        "model": model,
        "artifact": artifact_path,
        "status": status,
        "duration_ms": duration_ms,
        "retry_count": retry_count,
        "retry_delay_seconds": retry_delay_seconds,
        "retry_statuses": retry_statuses or [],
    }
    if error:
        entry["error"] = error
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return log_path


def load_provider_log(run_dir: Path) -> list[dict[str, Any]]:
    """Load provider.log.jsonl if present."""

    log_path = run_dir.resolve() / "provider.log.jsonl"
    if not log_path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            data = json.loads(line)
            if isinstance(data, dict):
                entries.append(data)
    return entries
