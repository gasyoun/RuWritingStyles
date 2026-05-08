"""Context builder to assemble prompts with unified style and knowledge data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

def build_unified_context(
    *,
    manifest: dict[str, Any],
    style_id: str | None = None,
    knowledge_results: str = "",
    long_artifact_preview: str = "",
    source_passage_id: str | None = None,
) -> str:
    """
    Builds a unified context block for prompt templates.
    Avoids using Vector DBs by formatting exact-matched knowledge passages.
    """
    context_lines = []
    
    if style_id:
        style_info = manifest.get("styles", {}).get(style_id, {})
        context_lines.append(f"### Style Passport: {style_info.get('name', style_id)}")
        context_lines.append(f"Description: {style_info.get('description', '')}")
        context_lines.append("")
        
    if knowledge_results:
        context_lines.append("### Selected Philological Knowledge Passages")
        context_lines.append(knowledge_results.strip())
        context_lines.append("")
        
    if long_artifact_preview:
        context_lines.append("### Relevant Artifact Preview")
        context_lines.append(long_artifact_preview.strip())
        context_lines.append("")
        
    if source_passage_id:
        context_lines.append(f"### Target Passage ID: {source_passage_id}")
        context_lines.append("")
        
    return "\n".join(context_lines)

def build_long_artifact_preview(artifact_path: Path, max_lines: int = 100) -> str:
    """Creates a truncated preview for long artifacts to conserve context."""
    if not artifact_path.exists():
        return ""
        
    try:
        content = artifact_path.read_text(encoding="utf-8")
        if artifact_path.suffix == ".json":
            # For JSON, we might want to truncate lists, but for now simple line truncation
            data = json.loads(content)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            lines = formatted.split("\n")
        else:
            lines = content.split("\n")
            
        if len(lines) <= max_lines:
            return "\n".join(lines)
        
        preview = "\n".join(lines[:max_lines])
        return f"{preview}\n\n... [TRUNCATED: original length {len(lines)} lines] ..."
    except Exception:
        return ""
