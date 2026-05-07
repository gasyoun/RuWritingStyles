"""LLM-driven generation of new Style Passports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .providers import BaseProvider


def generate_style_passport(
    *,
    repo_root: Path,
    provider: BaseProvider,
    model: str | None,
    style_name: str,
    description: str,
    examples: str | None = None,
) -> dict[str, str]:
    """Generate a new Style Passport and Source Prompt using an LLM."""
    
    # We want the LLM to return TWO files: the YAML passport and the MD source prompt.
    # We'll ask for a JSON response containing both.
    
    prompt = f"""You are a Style Architect for RuWritingStyles. 
Your task is to create a new Style Passport and a corresponding Source Prompt for a specific writing style.

**Style Name:** {style_name}
**Description:** {description}
"""
    if examples:
        prompt += f"\n**Reference Examples:**\n{examples}\n"

    prompt += """
## Instructions

1. **Source Prompt (Markdown)**: 
   - Write a detailed "System Prompt" in Russian for an LLM (like Claude).
   - It must describe the "Method" of this style, not just mimic phrases.
   - Include: Purpose, Core Rules, Composition, Syntax/Rhythm, Vocabulary, Recommended Formulas, and Modality.
   - Look at the existing `ClaudeStyles/zaliznyak-novgorod-style.md` for the level of depth required.

2. **Style Passport (YAML)**:
   - Create a YAML file that mirrors the structure of `styles/passports/zaliznyak-novgorod.yml`.
   - Fields: id, name, source_prompt, role, language, best_for, checks, limits, review_mode, council.
   - `id` should be a slug like `dostoevsky-style`.
   - `source_prompt` should be the relative path to the generated markdown file.
   - `checks` should be a list of 5-8 specific things this style agent looks for during a review.
   - `limits` should be 3-5 things the agent MUST NOT do.

## Required Output Format

Return a JSON object:
{
  "passport_id": "slug-of-style",
  "passport_yaml": "--- ... full yaml content ...",
  "source_prompt_md": "# ... full markdown content ..."
}
"""

    # We use the provider directly
    response_text = provider.generate(
        prompt=prompt,
        model=model,
        system_instructions="You are an expert philologist and prompt engineer.",
        json_mode=True
    )
    
    try:
        result = json.loads(response_text)
        return result
    except json.JSONDecodeError:
        # Fallback if the LLM didn't return pure JSON
        import re
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"LLM failed to return valid JSON: {response_text}")


def save_generated_style(repo_root: Path, generation_result: dict[str, str]) -> str:
    """Save the generated files and update the manifest."""
    passport_id = generation_result["passport_id"]
    passport_yaml = generation_result["passport_yaml"]
    source_prompt_md = generation_result["source_prompt_md"]
    
    passport_path = repo_root / "styles" / "passports" / f"{passport_id}.yml"
    source_prompt_rel = f"ClaudeStyles/{passport_id}-style.md"
    source_prompt_path = repo_root / source_prompt_rel
    
    # Save files
    passport_path.write_text(passport_yaml, encoding="utf-8")
    source_prompt_path.write_text(source_prompt_md, encoding="utf-8")
    
    # Update manifest
    manifest_path = repo_root / "styles" / "manifest.yml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    
    # Simple append for now
    if f"id: {passport_id}" not in manifest_text:
        new_entry = f"""
  - id: {passport_id}
    path: styles/passports/{passport_id}.yml
    source_prompt: {source_prompt_rel}
    weight: 1.0
"""
        # Find the end of the passports list
        # This is a bit brittle, but works for the current manifest structure
        if "\ncouncil:" in manifest_text:
            manifest_text = manifest_text.replace("\ncouncil:", f"{new_entry}\ncouncil:")
        else:
            manifest_text += new_entry
            
        manifest_path.write_text(manifest_text, encoding="utf-8")
        
    return passport_id
