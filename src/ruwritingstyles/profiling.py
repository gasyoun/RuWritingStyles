"""Profiling and Methodological Compass calculation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from .config import Manifest

def calculate_methodological_compass(run_dir: Path, manifest: Manifest) -> dict[str, float]:
    """Calculate alignment scores with different philological schools (Moscow, Leningrad, etc.)"""
    council_path = run_dir / "council.json"
    if not council_path.exists():
        return {}
        
    try:
        council = json.loads(council_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
        
    decisions = council.get("decisions", [])
    if not decisions:
        return {}
        
    # Map clusters to locations
    cluster_locations = {c.id: c.location for c in manifest.clusters}
    
    # Aggregate influence
    location_scores: dict[str, float] = {}
    total_influence = 0.0
    
    for decision in decisions:
        influence = decision.get("influence", {})
        if not influence:
            # Fallback to primary_school if influence is missing
            primary = decision.get("primary_school")
            if primary:
                influence = {primary: 1.0}
        
        for cluster_id, weight in influence.items():
            location = cluster_locations.get(cluster_id, "Other")
            location_scores[location] = location_scores.get(location, 0.0) + weight
            total_influence += weight
            
    if total_influence == 0:
        return {}
        
    # Normalize scores
    normalized = {loc: round(score / total_influence, 2) for loc, score in location_scores.items()}
    return normalized

def calculate_bloom_stats(run_dir: Path) -> dict[str, int]:
    """Calculate frequency of Bloom levels in council deliberation."""
    council_path = run_dir / "council.json"
    if not council_path.exists():
        return {}
        
    try:
        council = json.loads(council_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
        
    stats: dict[str, int] = {}
    
    # Count levels in replies and decisions
    items = council.get("replies", []) + council.get("decisions", [])
    for item in items:
        level = item.get("bloom_level")
        if level:
            stats[level] = stats.get(level, 0) + 1
            
    return stats
