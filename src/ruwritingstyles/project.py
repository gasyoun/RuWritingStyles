"""Project-level orchestration for multi-document stylistic consistency."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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

    existing_terms = {c["term"]: c for c in context["stylistic_commitments"]}
    
    for commitment in new_commitments:
        term = commitment.get("term")
        if term:
            # Overwrite or add new commitment
            existing_terms[term] = commitment

    context["stylistic_commitments"] = list(existing_terms.values())
    
    context_path.write_text(
        json.dumps(context, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
