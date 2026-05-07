"""Philological sentiment and tone analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .providers import BaseProvider


def analyze_philological_sentiment(
    *,
    repo_root: Path,
    run_dir: Path,
    provider: BaseProvider,
    model: str | None,
) -> dict[str, Any]:
    """Analyze the tone and scholarly distance of the original and revised text."""
    
    orig_path = run_dir / "original.md"
    rev_path = run_dir / "revision.md"
    
    if not orig_path.exists() or not rev_path.exists():
        return {"status": "error", "message": "Original or revision file missing."}
        
    orig_text = orig_path.read_text(encoding="utf-8")
    rev_text = rev_path.read_text(encoding="utf-8")
    
    prompt = f"""You are a Philological Tone Auditor.
Analyze the original and revised text across four linguistic dimensions (Score 1-10).

## Metrics
1. **Academic Distance**: (1: Personal/Casual, 10: Detached/Scholarly)
2. **Certainty (Epistemic Modality)**: (1: Speculative/Humble, 10: Assertive/Definitive)
3. **Vocabulary Complexity**: (1: Basic, 10: Highly Technical/Archaic)
4. **Register Politeness**: (1: Blunt/Direct, 10: Elaborate/Deferential)

## Original Text
{orig_text[:4000]}

## Revised Text
{rev_text[:4000]}

## Instructions
1. Provide scores for BOTH versions.
2. Calculate the delta for each dimension.
3. Provide a brief qualitative justification for the shifts.

Return a JSON object:
{{
  "original": {{ "distance": 0, "certainty": 0, "complexity": 0, "politeness": 0 }},
  "revised": {{ "distance": 0, "certainty": 0, "complexity": 0, "politeness": 0 }},
  "deltas": {{ "distance": 0, "certainty": 0, "complexity": 0, "politeness": 0 }},
  "justification": "Brief explanation."
}}
"""

    response_text = provider.generate(
        prompt=prompt,
        model=model,
        system_instructions="You are a meticulous linguistic auditor.",
        json_mode=True
    )
    
    result = json.loads(response_text)
    
    # Save to run dir
    sentiment_path = run_dir / "sentiment.json"
    sentiment_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return result
