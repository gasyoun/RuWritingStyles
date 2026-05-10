"""Multi-style batch analysis engine."""

from pathlib import Path
import argparse
from .cli import _execute_run_pipeline
from .config import load_manifest, load_model_policy

from .runs import create_prepare_run
from .segment import read_document, normalize_document, segment_markdown

def run_multi_style_batch(repo_root: Path, input_file: Path, clusters: list[str], provider: str):
    print(f"Batch Analysis: {input_file.name} against {len(clusters)} clusters")
    manifest = load_manifest(repo_root)
    model_policy = load_model_policy(repo_root)
    
    # Pre-process text once
    original_text = read_document(input_file)
    normalized_text = normalize_document(original_text)
    segments = segment_markdown(normalized_text)
    
    for cluster_id in clusters:
        print(f"\n>>> Profile: {cluster_id}")
        run_id = f"batch-{input_file.stem}-{cluster_id}"
        run_dir = repo_root / "runs" / run_id
        
        # Initialize run if it doesn't exist
        if not run_dir.exists():
            create_prepare_run(
                repo_root=repo_root,
                input_path=input_file,
                original_text=original_text,
                normalized_text=normalized_text,
                segments=segments,
                manifest=manifest,
                model_policy=model_policy,
                provider=provider,
                profile=cluster_id,
                run_id=run_id
            )
        
        # Mock args
        args = argparse.Namespace(
            input=input_file,
            run_id=run_id,
            provider=provider,
            model=None,
            profile=cluster_id,
            execute=True,
            interactive=False,
            max_iterations=1,
            require_provider_ready=False,
            deliberate=True,
            scrutiny=True
        )
        
        try:
            _execute_run_pipeline(repo_root, run_dir, args, manifest, model_policy)
        except Exception as e:
            print(f"Failed {cluster_id}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--provider", default="mock")
    args = parser.parse_args()
    
    repo_root = Path(__file__).parent.parent.parent
    manifest = load_manifest(repo_root)
    clusters = [p.style_id for p in manifest.passports]
    
    run_multi_style_batch(repo_root, args.input_file, clusters, args.provider)
