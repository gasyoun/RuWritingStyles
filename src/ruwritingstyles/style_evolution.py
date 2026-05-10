"""Automated Style Evolution based on Bias Audits."""

import json
from pathlib import Path
from .config import load_manifest

def evolve_styles(repo_root: Path):
    """Analyze batch runs and update style passports with new constraints."""
    manifest = load_manifest(repo_root)
    runs_dir = repo_root / "runs"
    
    updates_made = {}
    
    for passport in manifest.passports:
        # Find batch runs for this style
        style_runs = list(runs_dir.glob(f"batch-*-{passport.style_id}"))
        if not style_runs:
            continue
            
        common_critiques = []
        for run_dir in style_runs:
            # Check db or run metadata. For simplicity here we check db.
            from .db import Database
            db = Database(repo_root)
            with db._connection() as conn:
                metrics_rows = conn.execute(
                    "SELECT data_json FROM run_metrics WHERE run_id = ? AND metric_type = 'bias_audit'", 
                    (run_dir.name,)
                ).fetchall()
            
            for row in metrics_rows:
                try:
                    audit = json.loads(row['data_json'])
                    if audit.get("bias_score", 0) > 4: # High bias detected
                        common_critiques.append(audit.get("methodological_critique", ""))
                except Exception:
                    pass
                    
        if common_critiques:
            # If we found significant bias, we append a constraint to the passport
            # Note: In a real "automated" system, an LLM would synthesize the critiques.
            # Here we apply a generic programmatic constraint based on the presence of bias.
            constraint = f"\n- PHILOLOGICAL CONSTRAINT: Address historical bias. Recent audits noted: {common_critiques[0][:100]}...\n"
            
            content = passport.path.read_text(encoding="utf-8")
            if "PHILOLOGICAL CONSTRAINT" not in content:
                # Add to instructions section
                new_content = content.replace("instructions: |", f"instructions: |{constraint}")
                passport.path.write_text(new_content, encoding="utf-8")
                updates_made[passport.style_id] = True
                
    return updates_made

if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent.parent
    updates = evolve_styles(repo_root)
    print(f"Evolved styles: {list(updates.keys())}")
