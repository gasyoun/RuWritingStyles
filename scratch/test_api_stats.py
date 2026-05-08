from pathlib import Path
from ruwritingstyles.api import calculate_methodological_compass, calculate_bloom_stats
from ruwritingstyles.config import load_manifest, repo_root_from
import json

repo_root = repo_root_from()
manifest = load_manifest(repo_root)

run_dir = Path("runs/20260508-161756-iesh-vs-nss-conflict")

compass = calculate_methodological_compass(run_dir, manifest)
bloom = calculate_bloom_stats(run_dir)

print("Compass:", json.dumps(compass, indent=2, ensure_ascii=False))
print("Bloom:", json.dumps(bloom, indent=2))
