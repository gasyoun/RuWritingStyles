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

def calculate_tension_heatmap(run_dir: Path) -> dict[str, float]:
    """Identify 'philological hotspots' where multiple styles or agents conflict.
    
    Returns a mapping of span_id to a tension score (0.0 to 1.0).
    """
    reviews_dir = run_dir / "reviews"
    span_tension: dict[str, int] = {}
    
    # 1. Count findings per span across all style reviews
    if reviews_dir.exists():
        for p in reviews_dir.glob("*.review.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for finding in data.get("findings", []):
                    span_id = finding.get("span_id")
                    if span_id:
                        span_tension[span_id] = span_tension.get(span_id, 0) + 1
            except:
                continue
                
    # 2. Factor in Council complexity
    council_path = run_dir / "council.json"
    if council_path.exists():
        try:
            council = json.loads(council_path.read_text(encoding="utf-8"))
            # If a decision was 'accepted' or 'rejected' after deliberation, it adds tension
            for decision in council.get("decisions", []):
                span_id = decision.get("span_id") # We need to ensure decisions have span_id
                # In current schema, decisions have finding_id. We might need to map it back.
                # But findings have span_id.
                pass
        except:
            pass
            
    if not span_tension:
        return {}
        
    # Normalize (max tension becomes 1.0)
    max_val = max(span_tension.values())
    return {span_id: round(val / max_val, 2) for span_id, val in span_tension.items()}
