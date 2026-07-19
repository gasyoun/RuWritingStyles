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
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    cost_estimate: float = 0.0,
    schema_repair: bool = False,
    budget: dict[str, Any] | None = None,
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
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_estimate": cost_estimate,
        "schema_repair": schema_repair,
    }
    if error:
        entry["error"] = error
    if budget is not None:
        entry["budget"] = budget
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


def render_provider_log(entries: list[dict[str, Any]]) -> str:
    """Render provider log entries for CLI inspection."""

    if not entries:
        return "no provider executions"

    total_duration = sum(_number(entry.get("duration_ms")) for entry in entries)
    total_retries = sum(_number(entry.get("retry_count")) for entry in entries)
    total_retry_delay = sum(_number(entry.get("retry_delay_seconds")) for entry in entries)
    lines = [
        f"executions: {len(entries)}",
        f"duration_ms: {round(total_duration)}",
        f"retries: {round(total_retries)}",
        f"retry_delay_seconds: {round(total_retry_delay, 3)}",
    ]

    for entry in entries:
        statuses = ", ".join(str(item) for item in entry.get("retry_statuses") or [])
        if not statuses:
            statuses = "-"
        lines.append(
            " - "
            f"{entry.get('task') or ''} "
            f"{entry.get('provider') or ''}/{entry.get('model') or ''} "
            f"status={entry.get('status') or ''} "
            f"duration_ms={entry.get('duration_ms') or 0} "
            f"retries={entry.get('retry_count') or 0} "
            f"retry_delay_seconds={entry.get('retry_delay_seconds') or 0} "
            f"retry_statuses={statuses} "
            f"artifact={entry.get('artifact') or ''}"
        )
    return "\n".join(lines)


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0
