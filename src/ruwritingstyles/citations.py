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

def verify_citations_against_knowledge(repo_root: Path, citations: list[str]) -> dict[str, Any]:
    """Check if the extracted citations exist in the knowledge collections."""
    collections_dir = repo_root / "knowledge" / "collections"
    if not collections_dir.exists():
        return {"status": "error", "message": "Knowledge collections not found."}
        
    verification = {
        "status": "completed",
        "verified": [],
        "missing": [],
        "hallucinations": []
    }
    
    for cite in citations:
        found = False
        # Search for Author or Key in filenames and headers
        for p in collections_dir.glob("*.md"):
            content = p.read_text(encoding="utf-8")
            # If the filename (author) or a header contains the cite, consider it grounded
            if cite.lower() in p.stem.lower() or cite.lower() in content.lower():
                found = True
                verification["verified"].append({
                    "citation": cite,
                    "source_file": p.name
                })
                break
        
        if not found:
            verification["missing"].append(cite)
            # If it looks like a real citation but we don't have it, it might be a hallucination
            verification["hallucinations"].append({
                "citation": cite,
                "reason": "Not found in project knowledge collections."
            })
            
    return verification
