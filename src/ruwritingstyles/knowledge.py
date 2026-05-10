"""Philological knowledge base management."""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any

class KnowledgeManager:
    """Centralized hub for philological knowledge (Stage II)."""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.knowledge_dir = repo_root / "knowledge"
        self.bib_path = self.knowledge_dir / "bibliography.json"
        self.collections_dir = self.knowledge_dir / "collections"
        
    def _load_bibliography(self) -> list[dict[str, Any]]:
        if not self.bib_path.exists():
            return []
        try:
            return json.loads(self.bib_path.read_text(encoding="utf-8"))
        except:
            return []

    def verify_citation(self, citation_id: str) -> dict[str, Any] | None:
        """Verify a citation against the structured bibliography."""
        bib = self._load_bibliography()
        # Exact match on ID or fuzzy match on Author + Year
        for entry in bib:
            if entry["id"].lower() == citation_id.lower():
                return entry
            # Fuzzy match: "Zaliznyak 2004" in "Зализняк А. А. 2004"
            author_year = f"{entry['author']} {entry['year']}"
            if citation_id.lower() in author_year.lower() or author_year.lower() in citation_id.lower():
                return entry
        return None

    def search(self, query_terms: list[str]) -> str:
        """Search both structured and unstructured knowledge."""
        results = []
        
        # 1. Search Bibliography
        bib = self._load_bibliography()
        for entry in bib:
            for term in query_terms:
                if term.lower() in str(entry).lower():
                    results.append(f"BibRef: {entry['id']} - {entry['title']} ({entry['year']})")
                    break
                    
        # 2. Search Collections (JSON and Markdown)
        if self.collections_dir.exists():
            # JSON Collections
            for p in self.collections_dir.glob("*.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    for entry in data:
                        for term in query_terms:
                            if term.lower() in str(entry).lower():
                                results.append(f"Collection: {p.name} - {entry.get('id', 'item')}\n{entry.get('text_normalized', '')}")
                                break
                except: pass

            # Markdown Collections
            for p in self.collections_dir.glob("*.md"):
                content = p.read_text(encoding="utf-8")
                for term in query_terms:
                    if not term or len(term) < 3: continue
                    matches = re.finditer(f"## .*?{re.escape(term)}.*?\n(.*?)(?=\n##|$)", content, re.IGNORECASE | re.DOTALL)
                    for match in matches:
                        results.append(f"Source: {p.name}\n{match.group(0).strip()}")
                        
        return "\n\n---\n\n".join(results[:10]) # Limit results

def search_knowledge_base(repo_root: Path, query_terms: list[str]) -> str:
    """Legacy wrapper for KnowledgeManager.search."""
    return KnowledgeManager(repo_root).search(query_terms)

def extract_keywords_from_reviews(run_dir: Path) -> list[str]:
    """Extract key philological terms from existing style reviews."""
    reviews_dir = run_dir / "reviews"
    keywords = set()
    if not reviews_dir.exists(): return []
        
    for p in reviews_dir.glob("*.review.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            for f in data.get("findings", []):
                if f.get("term"): keywords.add(f["term"])
                comment = f.get("comment", "")
                terms = re.findall(r"\b[A-ZА-Я][a-zа-я]{3,}\b", comment)
                for t in terms: keywords.add(t)
        except: pass
    return sorted(list(keywords))

import json
