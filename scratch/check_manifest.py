import sys
from pathlib import Path
sys.path.append(str(Path.cwd() / "src"))
from ruwritingstyles.config import load_manifest, repo_root_from

try:
    repo_root = repo_root_from()
    manifest = load_manifest(repo_root)
    print(f"Loaded {len(manifest.passports)} passports")
    for p in manifest.passports[:5]:
        print(f"ID: {p.style_id}, Path: {p.path}, Source: {p.source_prompt}")
except Exception as e:
    print(f"Error: {e}")
