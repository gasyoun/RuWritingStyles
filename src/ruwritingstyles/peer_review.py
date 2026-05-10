"""Philological peer review logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .providers import BaseProvider
from .config import load_archetypes


def run_peer_review(
    *,
    repo_root: Path,
    run_dir: Path,
    provider: BaseProvider,
    model: str | None,
    reviewer_archetype_id: str,
) -> dict[str, Any]:
    """Run a peer review of the revision using a specific council archetype."""
    
    rev_path = run_dir / "revision.md"
    council_path = run_dir / "council.json"
    
    if not rev_path.exists() or not council_path.exists():
        return {"status": "error", "message": "Revision or Council file missing."}
        
    revision_text = rev_path.read_text(encoding="utf-8")
    author_council = json.loads(council_path.read_text(encoding="utf-8"))
    
    archetypes = load_archetypes(repo_root)
    reviewer = next((a for a in archetypes if a.id == reviewer_archetype_id), None)
    
    reviewer_persona = reviewer.persona if reviewer else "A rigorous philological peer reviewer."
    
    prompt = f"""You are a Philological Peer Reviewer. 
Your persona: {reviewer_persona}

## Task
Review the "Revised Document" produced based on the "Author Council Decisions". 
Your goal is to evaluate if the revision successfully implemented the stylistic mandates without introducing new errors.

## Author Council Decisions
{json.dumps(author_council.get('decisions', []), indent=2, ensure_ascii=False)}

## Revised Document
{revision_text[:6000]}

## Review Criteria
1. **Mandate Adherence**: Did the revision follow all "accepted" council decisions?
2. **Linguistic Integrity**: Were any new grammar, spelling, or logic errors introduced?
3. **Style Consistency**: Is the resulting style unified, or does it feel "patchy"?
4. **Scholarly Rigor**: Is the tone appropriate for the intended philological tradition?

Return a JSON object:
{{
  "reviewer_archetype": "{reviewer_archetype_id}",
  "overall_score": 0, (1-10)
  "comments": [
    {{ "id": "pr001", "type": "criticism|praise|correction", "text": "..." }}
  ],
  "recommendation": "accept|minor_revision|major_revision"
}}
"""

    from .providers import ProviderRequest
    
    schema = {
        "type": "object",
        "required": ["reviewer_archetype", "overall_score", "comments", "recommendation"],
        "properties": {
            "reviewer_archetype": {"type": "string"},
            "overall_score": {"type": "integer", "minimum": 1, "maximum": 10},
            "comments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "type", "text"],
                    "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string", "enum": ["criticism", "praise", "correction"]},
                        "text": {"type": "string"}
                    }
                }
            },
            "recommendation": {"type": "string", "enum": ["accept", "minor_revision", "major_revision"]}
        }
    }
    
    result = provider.generate_json(
        ProviderRequest(
            task="peer_review",
            prompt=prompt,
            schema=schema,
            metadata={"archetype": reviewer_archetype_id},
            model=model,
        )
    )
    
    # Save to run dir
    peer_review_path = run_dir / "peer-review.json"
    peer_review_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return result
