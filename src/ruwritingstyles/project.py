"""Project-level orchestration for multi-document stylistic consistency."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_project_context(run_dir: Path) -> dict[str, Any]:
    """Read the project context that applies to a run.

    Prefers the copy placed inside the run directory by `cmd_run`, then
    falls back to a sibling `project-context.json` (legacy layout)."""
    for candidate in (
        run_dir / "project-context.json",
        run_dir.parent / "project-context.json",
    ):
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
            return data if isinstance(data, dict) else {}
    return {}


def resolve_journal_profile(run_dir: Path) -> dict[str, Any] | None:
    """Return the journal_profile block for a run, if any."""
    profile = load_project_context(run_dir).get("journal_profile")
    return profile if isinstance(profile, dict) else None


def set_journal_profile(project_dir: Path, profile: dict[str, Any]) -> Path:
    """Write a journal profile into the project's project-context.json,
    preserving existing commitments."""
    project_dir.mkdir(parents=True, exist_ok=True)
    context_path = project_dir / "project-context.json"
    if context_path.exists():
        try:
            context = json.loads(context_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            context = {}
    else:
        context = {}
    if not isinstance(context, dict):
        context = {}
    context.setdefault("stylistic_commitments", [])
    context["journal_profile"] = profile
    context_path.write_text(
        json.dumps(context, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return context_path


def update_project_context(project_dir: Path, run_dir: Path) -> None:
    """Extract commitments from a run and update the project context."""
    council_path = run_dir / "council.json"
    if not council_path.exists():
        return

    council_doc = json.loads(council_path.read_text(encoding="utf-8"))
    new_commitments = council_doc.get("stylistic_commitments", [])
    if not new_commitments:
        return

    context_path = project_dir / "project-context.json"
    if context_path.exists():
        context = json.loads(context_path.read_text(encoding="utf-8"))
    else:
        context = {"stylistic_commitments": []}
    context.setdefault("stylistic_commitments", [])

    existing_terms = {c["term"]: c for c in context["stylistic_commitments"]}

    for commitment in new_commitments:
        term = commitment.get("term")
        if term:
            # Overwrite or add new commitment
            existing_terms[term] = commitment

    context["stylistic_commitments"] = list(existing_terms.values())
    # `journal_profile` and any other top-level keys are preserved because we
    # mutate the loaded context in place rather than rebuilding it.

    context_path.write_text(
        json.dumps(context, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
