"""Project-wide stylistic consistency auditing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .providers import BaseProvider


def audit_project_consistency(
    *,
    repo_root: Path,
    project_dir: Path,
    provider: BaseProvider,
    model: str | None,
) -> dict[str, Any]:
    """Audit all revised documents in a project against the global commitments."""
    
    context_path = project_dir / "project-context.json"
    if not context_path.exists():
        return {"status": "error", "message": "No project-context.json found."}
        
    context = json.loads(context_path.read_text(encoding="utf-8"))
    commitments = context.get("commitments", [])
    if not commitments:
        return {"status": "completed", "message": "No commitments to verify.", "violations": []}
        
    # Collect all revisions
    revisions: dict[str, str] = {}
    for run_dir in project_dir.iterdir():
        if run_dir.is_dir():
            rev_path = run_dir / "revision.md"
            if rev_path.exists():
                revisions[run_dir.name] = rev_path.read_text(encoding="utf-8")
                
    if not revisions:
        return {"status": "error", "message": "No revised documents (revision.md) found."}

    commitments_json = json.dumps(commitments, ensure_ascii=False, indent=2)
    
    prompt = f"""You are the Global Consistency Auditor for RuWritingStyles.
Your task is to verify that all revised documents in this project follow the binding stylistic commitments.

## Stylistic Commitments
```json
{commitments_json}
```

## Revised Documents
"""
    for run_id, text in revisions.items():
        # Truncate if too long for audit prompt, but here we'll try full or samples
        prompt += f"\n--- Document: {run_id} ---\n{text[:5000]}\n"

    prompt += """
## Instructions

1. **Detect Violations**: Check every document against every commitment.
2. **Flag Inconsistencies**: If a document uses a term or style that violates a commitment, record it.
3. **Report Status**: For each commitment, state if it is followed across all documents.

Return a JSON object:
{
  "status": "completed",
  "audit_summary": "Overall assessment of project consistency.",
  "violations": [
    {
      "document_id": "run-001",
      "term": "идиом",
      "issue": "Used 'диалект' instead of 'идиом' as committed.",
      "severity": "critical"
    }
  ],
  "passed_commitments": ["list of commitment terms that were perfectly followed"]
}
"""

    response_text = provider.generate(
        prompt=prompt,
        model=model,
        system_instructions="You are a meticulous philological auditor.",
        json_mode=True
    )
    
    return json.loads(response_text)
