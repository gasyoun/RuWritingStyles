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


def is_verified(profile: dict[str, Any] | None) -> bool:
    """D10 gate predicate: absent verified is treated as false."""
    return bool(isinstance(profile, dict) and profile.get("verified") is True)


def derive_profile(slug: str) -> dict[str, Any]:
    """Derive a submission profile draft from the journal's live pages.

    Everything mechanically derivable comes from the platform (OAI Identify,
    citation_* metadata on a fresh article); the judgment fields a real
    submission needs (max_chars, citation_format, first_mention_rule, ...) are
    NOT guessable and stay absent — an auto-derived draft never pretends to
    know them. The result carries ``verified: false``; the D10 gate in
    ``project.set_journal_profile`` refuses it until someone checks the
    guidelines page and confirms.

    Existing hand-written profiles are never overwritten in place by callers;
    ``rws journal-add`` emits a proposed diff instead.
    """
    from datetime import datetime

    from . import rcsi
    from .config import repo_root_from

    root = Path(repo_root_from())
    info = rcsi.identify(slug)
    name = info.get("repository_name") or slug
    profile: dict[str, Any] = {
        "id": slug,
        "name": name,
        "verified": False,
        "checked_on": datetime.now().strftime("%d-%m-%Y"),
        "platform": "rcsi",
        "slug": slug,
        "url": f"{rcsi.BASE}/{slug}",
        "guidelines_url": f"{rcsi.BASE}/{slug}/about/submissions",
        "oai_endpoint": f"{rcsi.BASE}/{slug}/oai",
        "derived_by": f"rws journal-add ({_tool_version(root)})",
    }
    return profile


def _tool_version(repo_root: Path) -> str:
    try:
        text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    except OSError:
        return "dev"
    import re as _re

    match = _re.search(r'^version\s*=\s*"([^"]+)"', text, _re.MULTILINE)
    return match.group(1) if match else "dev"


def proposed_profile_diff(existing: dict[str, Any], draft: dict[str, Any]) -> list[str]:
    """Human-readable key-level diff for the journal-add refusal message."""
    lines: list[str] = []
    for key in sorted(set(existing) | set(draft)):
        left = existing.get(key)
        right = draft.get(key)
        if left != right:
            lines.append(f"  {key}: {left!r} -> {right!r}")
    return lines
