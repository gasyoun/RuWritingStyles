"""Philological citation extraction and verification logic."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

def extract_citations(text: str) -> list[str]:
    """Extract citations from text. 
    Matches: (Author Year), [Author Year], or @AuthorYear.
    """
    # Pattern for (Author Year) or [Author Year]
    bracketed = re.findall(r"[\(\[](?:[А-ЯA-Z][а-яa-z]+|[\w-]+)\s+\d{4}[\)\]]", text)
    # Pattern for @Key
    at_style = re.findall(r"@[\w-]+", text)
    
    # Clean up
    results = []
    for c in bracketed:
        results.append(c[1:-1].strip())
    for c in at_style:
        results.append(c[1:].strip())
        
    return sorted(list(set(results)))

from .knowledge import KnowledgeManager

def verify_citations_against_knowledge(repo_root: Path, citations: list[str]) -> dict[str, Any]:
    """Check if the extracted citations exist in the knowledge collections."""
    km = KnowledgeManager(repo_root)
    
    verification = {
        "status": "completed",
        "verified": [],
        "missing": [],
        "hallucinations": []
    }
    
    for cite in citations:
        entry = km.verify_citation(cite)
        if entry:
            verification["verified"].append({
                "citation": cite,
                "entry": entry
            })
        else:
            verification["missing"].append(cite)
            # Verification logic for hallucinations
            verification["hallucinations"].append({
                "citation": cite,
                "reason": "Not found in structured bibliography."
            })
            
    return verification
