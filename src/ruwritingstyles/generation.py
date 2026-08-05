"""LLM-driven generation of new Style Passports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .providers import BaseProvider, ProviderRequest


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
    
    prompt = f"""You are the RuWritingStyles `Style Architect` (2026 Edition). 
Your task is to create a new `Style Passport` and a corresponding `Source Prompt` for a private authorial style.

**Style Name:** {style_name}
**Description:** {description}
"""
    if examples:
        prompt += f"\n**Reference Examples (Expert Texts):**\n{examples}\n"

    prompt += """
## Architectural Requirements

1. **Philological Cluster Assignment**: 
   - Assign this style to one of the 17 clusters (ling_iesh, ling_mss, ling_mts, ling_nss, ling_pfg, ling_tsh, ling_kmsh, ling_dss, lit_opoyaz, lit_structural, lit_textology, lit_mythopoetics, lit_narratology, lit_bakhtin, lit_historico_cultural, lit_reception, lit_poststructural).
   - If unsure, use `ling_nss` for general styles or `ling_mts` for cultural ones.

2. **Source Prompt (Markdown)**: 
   - Write a detailed "System Prompt" in Russian for an LLM.
   - It MUST describe the "Method" (composition, syntax, epistemic modality).
   - **CRITICAL**: Include a rule: "Never simplify or remove epistemic markers (e.g., 'по-видимому', 'вероятно') if they are characteristic of the cluster."

3. **Style Passport (YAML)**:
   - Level: `private`.
   - Cluster: [cluster_id].
   - Role: [one of: systematic_grammar_reviewer, polemical_linguistic_reviewer, source_critical_reviewer, clarity_reviewer, commentary_reviewer, cultural_context_reviewer].
   - Checks: 5-8 specific philological checks.
   - Limits: 3-5 negative constraints.

## Required Output Format

Return a JSON object:
{
  "passport_id": "slug-of-style",
  "cluster_id": "ling_...",
  "passport_yaml": "--- ... full yaml content ...",
  "source_prompt_md": "# ... full markdown content ..."
}
"""

    system_instructions = (
        "You are an expert philologist and prompt engineer specializing in "
        "multi-agent linguistic systems."
    )
    request = ProviderRequest(
        task="generation",
        prompt=f"{system_instructions}\n\n{prompt}",
        schema={},
        metadata={"style_name": style_name},
        model=model,
    )
    result = provider.generate_json(request)

    missing = [
        key
        for key in ("passport_id", "passport_yaml", "source_prompt_md")
        if not result.get(key)
    ]
    if missing:
        raise ValueError(
            f"provider returned an incomplete generation result (missing: {', '.join(missing)})"
        )
    return result


def save_generated_style(repo_root: Path, generation_result: dict[str, str]) -> str:
    """Save the generated files and update the manifest (v0.2 support)."""
    passport_id = generation_result["passport_id"]
    cluster_id = generation_result.get("cluster_id", "ling_nss")
    passport_yaml = generation_result["passport_yaml"]
    source_prompt_md = generation_result["source_prompt_md"]
    
    passport_path = repo_root / "styles" / "passports" / f"{passport_id}.yml"
    source_prompt_rel = f"ClaudeStyles/{passport_id}-style.md"
    source_prompt_path = repo_root / source_prompt_rel
    
    # Save files
    passport_path.write_text(passport_yaml, encoding="utf-8")
    source_prompt_path.write_text(source_prompt_md, encoding="utf-8")
    
    # Update manifest (v0.2)
    manifest_path = repo_root / "styles" / "manifest.yml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    
    if f"id: {passport_id}" not in manifest_text:
        new_entry = f"""  - id: {passport_id}
    path: styles/passports/{passport_id}.yml
    level: private
    cluster: {cluster_id}
    source_prompt: {source_prompt_rel}
"""
        # Append to passports list
        if "\npassports:" in manifest_text:
            # Insert after the last passport entry or at the end of the section
            # For simplicity, we'll append to the end of the passports block
            lines = manifest_text.splitlines()
            last_passport_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith("- id:") and i > 0 and lines[i-1].strip() == "passports:":
                    last_passport_idx = i
                elif line.strip().startswith("- id:") and last_passport_idx != -1:
                    last_passport_idx = i
            
            if last_passport_idx != -1:
                # Find the end of this passport entry
                end_idx = last_passport_idx + 1
                while end_idx < len(lines) and lines[end_idx].startswith("    "):
                    end_idx += 1
                lines.insert(end_idx, new_entry.rstrip())
                manifest_text = "\n".join(lines)
            else:
                manifest_text = manifest_text.replace("\npassports:", f"\npassports:\n{new_entry}")
        
        manifest_path.write_text(manifest_text, encoding="utf-8")
        
    return passport_id
