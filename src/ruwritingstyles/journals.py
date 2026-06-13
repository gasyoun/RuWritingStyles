"""Journal submission profiles (Phase 1, W3).

Presets live in knowledge/journals/<id>.json and are copied into a
project's project-context.json under the `journal_profile` key by
`rws project set-journal`. Downstream consumers (verification prompt,
transliteration linter, report) read the resolved profile from the run's
project context.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _presets_dir(repo_root: Path) -> Path:
    return repo_root / "knowledge" / "journals"


def list_journal_presets(repo_root: Path) -> list[str]:
    directory = _presets_dir(repo_root)
    if not directory.exists():
        return []
    return sorted(p.stem for p in directory.glob("*.json"))


def load_journal_preset(repo_root: Path, journal_id: str) -> dict[str, Any] | None:
    path = _presets_dir(repo_root) / f"{journal_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
