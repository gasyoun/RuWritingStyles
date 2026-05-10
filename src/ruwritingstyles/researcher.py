"""Web Researcher agent for finding academic precedents (Phase III)."""

import json
import logging
import urllib.request
import urllib.parse
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class WebResearcher:
    """
    Academic search agent that uses free scholarly APIs (like OpenAlex)
    to verify citations and find bibliographic precedents.
    """
    
    OPENALEX_API_URL = "https://api.openalex.org/works"

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Perform a heuristic search for a citation.
        1. Clean query
        2. Query OpenAlex API
        3. Parse and rank results
        """
        logger.info(f"WebResearcher: Searching for '{query}'...")
        
        try:
            # OpenAlex search parameters
            params = {
                "search": query,
                "mailto": "researcher@ruwritingstyles.ai", # Good practice for OpenAlex
                "per_page": 5
            }
            url = f"{self.OPENALEX_API_URL}?{urllib.parse.urlencode(params)}"
            
            req = urllib.request.Request(
                url, 
                headers={"User-Agent": "RuWritingStyles/1.0 (https://github.com/gasyoun/RuWritingStyles)"}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                
            return self._parse_openalex_results(data)
            
        except Exception as e:
            logger.error(f"WebResearcher: Search failed for '{query}': {e}")
            # Fallback to internal heuristic or empty result
            return []

    def _parse_openalex_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        for work in data.get("results", []):
            # Extract author
            authors = work.get("authorships", [])
            primary_author = "Unknown"
            if authors:
                primary_author = authors[0].get("author", {}).get("display_name", "Unknown")
            
            # Extract year
            year = work.get("publication_year", 0)
            
            # Extract title
            title = work.get("display_name") or work.get("title") or "Untitled"
            
            # Extract DOI
            doi = work.get("doi") or ""
            
            results.append({
                "id": f"{primary_author.split()[-1]} {year}" if primary_author != "Unknown" else "Work",
                "author": primary_author,
                "year": year,
                "title": title,
                "doi": doi,
                "source": "OpenAlex (Web Search)"
            })
            
        return results
