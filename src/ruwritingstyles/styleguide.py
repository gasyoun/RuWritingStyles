"""Automated generation of the project Stylebook."""

from __future__ import annotations

import json
from pathlib import Path
from .config import load_manifest, load_passport_summaries, load_archetypes, StylePassportSummary, CouncilArchetype

def generate_stylebook_markdown(repo_root: Path) -> str:
    manifest = load_manifest(repo_root)
    summaries = load_passport_summaries(repo_root, manifest)
    archetypes = load_archetypes(repo_root)
    
    md = [
        "# RuWritingStyles Project Stylebook",
        "",
        "This document is automatically generated from the project's Style Passports and Council Archetypes. It represents the binding stylistic and philological rules enforced by the multi-agent pipeline.",
        "",
        "## 1. Style Agents (Passports)",
        "",
        "Each agent represents a specific philological tradition or stylistic register.",
        ""
    ]
    
    for s in summaries:
        md.append(f"### {s.name} (`{s.style_id}`)")
        md.append(f"- **Role**: {s.role}")
        md.append(f"- **Passport Path**: [`{s.passport_path.relative_to(repo_root)}`](file:///{s.passport_path.resolve()})")
        md.append(f"- **Source Prompt**: [`{s.source_prompt}`](file:///{ (repo_root / s.source_prompt).resolve() })")
        
        # Load extra details from the YAML
        import yaml
        try:
            with open(s.passport_path, 'r', encoding='utf-8') as f:
                passport_data = yaml.safe_load(f)
                
            if "best_for" in passport_data:
                md.append("\n**Best For:**")
                for item in passport_data["best_for"]:
                    md.append(f"- {item}")
            
            if "checks" in passport_data:
                md.append("\n**Key Checks:**")
                for item in passport_data["checks"]:
                    md.append(f"- `{item}`")
                    
            if "limits" in passport_data:
                md.append("\n**Constraints (Limits):**")
                for item in passport_data["limits"]:
                    md.append(f"- {item}")
        except:
            pass
            
        md.append("")
        
    md.append("## 2. Council Archetypes")
    md.append("")
    md.append("Archetypes define the 'personality' of the deliberation process when style agents disagree.")
    md.append("")
    
    for a in archetypes:
        md.append(f"### {a.name}")
        md.append(f"**{a.description}**")
        md.append("\n**Instructions:**")
        md.append("```")
        md.append(a.instructions.strip())
        md.append("```")
        if a.weights:
            md.append("\n**Authority Weights:**")
            for agent, weight in a.weights.items():
                md.append(f"- `{agent}`: {weight}x")
        md.append("")
        
    md.append("---")
    md.append(f"*Generated on: {Path.cwd().name}*")
    
    return "\n".join(md)

def save_stylebook(repo_root: Path, content: str, filename: str = "STYLEBOOK.md") -> Path:
    path = repo_root / filename
    path.write_text(content, encoding="utf-8")
    return path
