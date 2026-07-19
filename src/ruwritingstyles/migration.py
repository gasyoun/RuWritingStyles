"""Linguistic style migration logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .providers import BaseProvider
from .config import load_manifest, StylePassportSummary
from .budget import generate_with_budget


def migrate_document_style(
    *,
    repo_root: Path,
    input_file: Path,
    from_style_id: str,
    to_style_id: str,
    provider: BaseProvider,
    model: str | None,
) -> Path:
    """Migrate a document from one stylistic register to another."""
    
    # Load passports
    from .config import load_passport_summaries
    summaries = load_passport_summaries(repo_root)
    style_map = {s.style_id: s for s in summaries}
    
    from_style = style_map.get(from_style_id)
    to_style = style_map.get(to_style_id)
    
    if not to_style:
        raise ValueError(f"Target style '{to_style_id}' not found.")
        
    source_text = input_file.read_text(encoding="utf-8")
    
    # In migration mode, we skip the multi-stage pipeline and do a direct 'Migration Council' call
    # This is faster for 1-to-1 style ports.
    
    prompt = f"""You are the RuWritingStyles Migration Expert.
Your task is to migrate a document from its current style to a new target style.

**Original Style:** {from_style.name if from_style else 'Unknown/Mixed'}
**Target Style:** {to_style.name}

## Target Style Rules
"""
    # Load target style prompt
    target_prompt_path = repo_root / to_style.source_prompt
    if target_prompt_path.exists():
        prompt += f"\n{target_prompt_path.read_text(encoding='utf-8')[:3000]}\n"

    prompt += f"""
## Instructions

1. **Transform Register**: Rewrite the document to match the target style's syntax, vocabulary, and tone.
2. **Preserve Information**: Every fact, argument, and citation from the original MUST be preserved.
3. **Migration Rationale**: Explain the major changes you made (e.g. 'Simplified complex syntax', 'Replaced academic jargon').

## Source Text
{source_text}

## Required Output Format
Return a JSON object:
{{
  "migration_summary": "Explanation of the transformation.",
  "revised_text": "The full migrated document text."
}}
"""

    from .providers import ProviderRequest, load_schema
    
    schema = load_schema(repo_root, "schemas/migration-summary.schema.json")
    
    result = generate_with_budget(provider,
        ProviderRequest(
            task="migration",
            prompt=prompt,
            schema=schema,
            metadata={
                "from_style_id": from_style_id,
                "to_style_id": to_style_id,
            },
            model=model,
        ),
    )
    
    # Save result
    migration_run_id = f"migration-{from_style_id}-to-{to_style_id}-{input_file.stem}"
    run_dir = repo_root / "runs" / migration_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    migrated_path = run_dir / "revision.md"
    migrated_path.write_text(result["revised_text"], encoding="utf-8")
    
    summary_path = run_dir / "migration-summary.json"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return migrated_path
