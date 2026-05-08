"""Business logic for applying human resolutions to council decisions.

This module is the single source of truth for resolution logic, used by both
the CLI (`cmd_apply_resolution` in cli.py) and the API (`/runs/{run_id}/resolve`).
The API and CLI are consumers — neither calls the other.
"""

from __future__ import annotations

import json
from pathlib import Path


def apply_resolution(run_dir: Path, overrides: list[dict]) -> int:
    """
    Apply a list of human-review overrides to `council.json`.

    Args:
        run_dir: Path to the specific run directory.
        overrides: List of dicts with keys ``finding_id``, ``status``,
                   and optionally ``human_comment``.

    Returns:
        Number of decisions actually updated.

    Raises:
        FileNotFoundError: If council.json is missing.
        ValueError: If overrides list is empty.
    """
    council_path = run_dir / "council.json"
    if not council_path.exists():
        raise FileNotFoundError(f"council.json not found in {run_dir}")

    if not overrides:
        raise ValueError("overrides list must not be empty")

    council = json.loads(council_path.read_text(encoding="utf-8"))
    override_map = {o["finding_id"]: o for o in overrides}
    decisions = council.get("decisions", [])

    updated_count = 0
    for decision in decisions:
        fid = decision.get("finding_id")
        if fid in override_map:
            override = override_map[fid]
            decision["status"] = override["status"]
            if "human_comment" in override and override["human_comment"]:
                decision["human_resolution"] = override["human_comment"]
            updated_count += 1

    council["decisions"] = decisions
    council_path.write_text(
        json.dumps(council, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return updated_count


def write_final_manuscript(run_dir: Path) -> Path:
    """
    Extract the revised document from revision.json and write it as final.md.

    Args:
        run_dir: Path to the specific run directory.

    Returns:
        Path to the written final.md file.

    Raises:
        FileNotFoundError: If revision.json is missing.
        ValueError: If revision is not in 'completed' status or has no content.
    """
    revision_path = run_dir / "revision.json"
    if not revision_path.exists():
        raise FileNotFoundError(
            f"revision.json not found in {run_dir}. Run the revision step first."
        )

    rev_data = json.loads(revision_path.read_text(encoding="utf-8"))
    if rev_data.get("status") != "completed":
        raise ValueError(
            f"Revision status is '{rev_data.get('status')}', expected 'completed'."
        )

    revised_text = rev_data.get("revised_document", "")
    if not revised_text:
        raise ValueError("No revised_document content found in revision.json.")

    final_path = run_dir / "final.md"
    final_path.write_text(revised_text, encoding="utf-8")
    return final_path
