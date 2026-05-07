"""Council artifact inspection helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_council_summary(run_dir: Path) -> dict[str, Any]:
    """Load council.json from a run directory."""

    path = run_dir / "council.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def render_council_summary(council: dict[str, Any]) -> str:
    """Render a compact council summary for CLI output."""

    if not council:
        return "no council artifact found"
    replies = _dicts(council.get("replies"))
    decisions = _dicts(council.get("decisions"))
    lines = [
        f"run_id: {council.get('run_id') or ''}",
        f"status: {council.get('status') or ''}",
        f"replies: {len(replies)}",
        f"decisions: {len(decisions)}",
    ]
    if replies:
        lines.append("reply positions:")
        for reply in replies:
            lines.append(
                " - "
                + " ".join(
                    [
                        str(reply.get("reply_to") or ""),
                        str(reply.get("style_id") or ""),
                        f"position={reply.get('position') or ''}",
                    ]
                ).strip()
            )
    if decisions:
        lines.append("decisions:")
        for decision in decisions:
            lines.append(
                " - "
                + " ".join(
                    [
                        str(decision.get("finding_id") or ""),
                        f"status={decision.get('status') or ''}",
                        f"reason={_one_line(decision.get('reason'))}",
                    ]
                ).strip()
            )
    return "\n".join(lines)


def _dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _one_line(value: Any) -> str:
    return str(value or "").replace("\n", " ").strip()
