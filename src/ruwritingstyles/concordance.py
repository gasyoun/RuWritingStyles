"""Interactive Concordance for specific academic collections (Phase F)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def search_concordance(repo_root: Path, query: str) -> list[dict[str, str]]:
    """Search specific academic collections for examples of usage.
    
    Returns a list of matches with source and snippet.
    """
    collections_dir = repo_root / "knowledge" / "collections"
    if not collections_dir.exists():
        return []
        
    results = []
    # Query can be a phrase or a single word
    # We use a simple regex search for now
    for p in collections_dir.glob("*.md"):
        content = p.read_text(encoding="utf-8")
        # Split into paragraphs or sections
        sections = re.split(r"\n(?=## )", content)
        for section in sections:
            if re.search(re.escape(query), section, re.IGNORECASE):
                # Extract the snippet (the text after the header)
                header_match = re.match(r"(## .*?)\n(.*)", section, re.DOTALL)
                if header_match:
                    source = f"{p.stem.capitalize()}: {header_match.group(1).replace('## ', '')}"
                    snippet = header_match.group(2).strip()
                    results.append({
                        "source": source,
                        "text": snippet
                    })
                else:
                    results.append({
                        "source": p.stem.capitalize(),
                        "text": section.strip()
                    })
                    
    return results[:10] # Limit results


def get_concordance_data(repo_root: Path, terms: list[str]) -> dict[str, list[dict[str, str]]]:
    """Retrieve concordance matches for multiple terms."""
    concordance_map = {}
    for term in terms:
        if not term or len(term) < 3:
            continue
        matches = search_concordance(repo_root, term)
        if matches:
            concordance_map[term] = matches
    return concordance_map
