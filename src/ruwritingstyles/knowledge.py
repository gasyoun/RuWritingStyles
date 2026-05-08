"""Philological knowledge base management."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def search_knowledge_base(repo_root: Path, query_terms: list[str]) -> str:
    """Search the knowledge/ directory for relevant philological data."""
    knowledge_dir = repo_root / "knowledge"
    if not knowledge_dir.exists():
        return ""
        
    results = []
    # Simple keyword search through all markdown files
    for p in knowledge_dir.glob("*.md"):
        content = p.read_text(encoding="utf-8")
        # Check if any query term is in the content
        # We look for terms in headers or bold text for higher relevance
        for term in query_terms:
            if not term or len(term) < 3:
                continue
            # Regex to find sections containing the term
            # Find the header (##) and the text until the next header
            matches = re.finditer(f"## .*?{re.escape(term)}.*?\n(.*?)(?=\n##|$)", content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                section_text = match.group(0).strip()
                if section_text not in results:
                    results.append(f"Source: {p.name}\n{section_text}")
                    
    if not results:
        return ""
        
    return "\n\n---\n\n".join(results)


def extract_keywords_from_reviews(run_dir: Path) -> list[str]:
    """Extract key philological terms from existing style reviews to drive knowledge search."""
    reviews_dir = run_dir / "reviews"
    keywords = set()
    
    if not reviews_dir.exists():
        return []
        
    for p in reviews_dir.glob("*.review.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            findings = data.get("findings", [])
            for f in findings:
                # Look at 'term' or 'issue' fields
                if f.get("term"):
                    keywords.add(f["term"])
                # Also try to extract capitalized words from comments (potential terms)
                comment = f.get("comment", "")
                terms = re.findall(r"\b[A-ZА-Я][a-zа-я]{3,}\b", comment)
                for t in terms:
                    keywords.add(t)
        except:
            pass
            
    return sorted(list(keywords))

import json # Needed for extract_keywords_from_reviews
