"""Methodological and ideological bias detection for philological workflows."""

from __future__ import annotations

import json
from pathlib import Path
from .io_utils import atomic_write_json
from typing import Any
from .providers import BaseProvider, ProviderRequest, load_schema

def run_bias_audit(
    *,
    repo_root: Path,
    run_dir: Path,
    provider: BaseProvider,
    model: str | None,
) -> dict[str, Any]:
    """Analyze the council decisions and methodological compass for potential biases."""
    
    council_path = run_dir / "council.json"
    if not council_path.exists():
        return {"status": "error", "message": "Council file missing."}
        
    council_data = json.loads(council_path.read_text(encoding="utf-8"))
    
    # Load compass data from metrics if available, or calculate it
    # For now we'll pass the compass logic result directly or just let the LLM audit the council JSON
    
    prompt = f"""You are a Philological Meta-Auditor. 
Your task is to analyze the "Council Decisions" for potential methodological bias.

## Council Decisions
{json.dumps(council_data.get('decisions', []), indent=2, ensure_ascii=False)}

## Audit Criteria
1. **Impartiality**: Does the council favor one philological school (e.g. Moscow School) consistently over others without clear justification?
2. **Epistemic Modesty**: Does the council make overly assertive claims where the source material is ambiguous?
3. **Tradition Alignment**: Does the selected style match the methodological commitments expressed in the justifications?
4. **Silence Audit**: Are there critical findings that were ignored or "swept under the rug" by the council?

Return a JSON object:
{{
  "status": "completed",
  "bias_score": 0, (0-10, where 10 is highly biased)
  "primary_bias_detected": "none|methodological|ideological|terminological",
  "findings": [
    {{ "id": "bias-001", "severity": "warning|critical|note", "issue": "...", "recommendation": "..." }}
  ],
  "methodological_critique": "Overall assessment of the council's impartiality."
}}
"""

    schema = {
        "type": "object",
        "required": ["status", "bias_score", "primary_bias_detected", "findings", "methodological_critique"],
        "properties": {
            "status": {"type": "string"},
            "bias_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "primary_bias_detected": {"type": "string", "enum": ["none", "methodological", "ideological", "terminological"]},
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "severity", "issue", "recommendation"],
                    "properties": {
                        "id": {"type": "string"},
                        "severity": {"type": "string", "enum": ["warning", "critical", "note"]},
                        "issue": {"type": "string"},
                        "recommendation": {"type": "string"}
                    }
                }
            },
            "methodological_critique": {"type": "string"}
        }
    }

    result = provider.generate_json(
        ProviderRequest(
            task="bias_audit",
            prompt=prompt,
            schema=schema,
            metadata={"run_id": run_dir.name},
            model=model,
        )
    )
    
    bias_path = run_dir / "bias-audit.json"
    atomic_write_json(bias_path, result)
    
    return result
