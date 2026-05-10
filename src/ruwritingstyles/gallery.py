"""Philological Style Gallery generation logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .providers import BaseProvider
from .config import load_passport_summaries, load_manifest

def generate_style_gallery(
    *,
    repo_root: Path,
    input_text: str,
    style_ids: list[str],
    provider: BaseProvider,
    model: str | None,
) -> str:
    """Generate a Markdown gallery showcasing different styles on the same text."""
    
    summaries = load_passport_summaries(repo_root)
    style_map = {s.style_id: s for s in summaries}
    
    gallery_md = [
        "# Philological Style Gallery",
        "",
        "This document showcases how the same philological thought is transformed by different RuWritingStyles agents.",
        "",
        "### Source Text",
        f"> {input_text}",
        "",
        "---",
        ""
    ]
    
    for i, style_id in enumerate(style_ids, 1):
        style = style_map.get(style_id)
        if not style:
            print(f"Warning: Style '{style_id}' not found. Skipping.")
            continue
            
        print(f"  -> Generating gallery entry for: {style.name} ({style_id})...")
        
        prompt = f"""You are the RuWritingStyles Gallery Architect.
Your task is to transform a sample text into the target philological style.

**Target Style:** {style.name}

## Style Rules
"""
        # Load style prompt
        prompt_path = repo_root / style.source_prompt
        if prompt_path.exists():
            prompt += f"\n{prompt_path.read_text(encoding='utf-8')[:3000]}\n"
            
        prompt += f"""
## Instructions
1. Rewrite the Source Text below to perfectly match the target style's syntax, vocabulary, and scholarly register.
2. Preserve all facts and nuances.
3. Be concise but faithful to the style's character.

## Source Text
{input_text}

## Required Output Format
Return a JSON object:
{{
  "transformed_text": "The text in the new style.",
  "accent_description": "Briefly describe the philological accent of this transformation (1 sentence)."
}}
"""
        from .providers import ProviderRequest
        
        schema = {
            "type": "object",
            "required": ["transformed_text", "accent_description"],
            "properties": {
                "transformed_text": {"type": "string"},
                "accent_description": {"type": "string"}
            }
        }
        
        try:
            result = provider.generate_json(
                ProviderRequest(
                    task="gallery",
                    prompt=prompt,
                    schema=schema,
                    metadata={"style_id": style_id},
                    model=model,
                )
            )
            
            gallery_md.append(f"## {i}. {style.name} — `{style_id}`")
            gallery_md.append(f"**Accent**: {result.get('accent_description', 'N/A')}")
            gallery_md.append("")
            gallery_md.append(f"> {result.get('transformed_text', 'Error in transformation.')}")
            gallery_md.append("")
            
        except Exception as e:
            gallery_md.append(f"## {i}. {style.name} — `{style_id}`")
            gallery_md.append(f"**Error**: {e}")
            gallery_md.append("")
            
    return "\n".join(gallery_md)
