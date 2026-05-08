from pathlib import Path
from .config import load_manifest, load_model_policy
from .providers import provider_from_name
from .review import create_review_bundle
from .council import create_council_bundle
from .revision import create_revision_bundle
from .diff import write_revision_diff
from .verification import create_verification_bundle
from .assess import create_impact_bundle
from .syntax import create_syntax_bundle
from .execution import (
    execute_review_artifact,
    execute_council_artifact,
    execute_revision_artifact,
    execute_verification_artifact,
    execute_impact_artifact,
    execute_syntax_artifact
)
from .report import write_run_report
from .html_summary import write_html_report

def run_full_pipeline(repo_root: Path, run_dir: Path, provider_name: str, model: str | None = None, profile: str = "researcher") -> None:
    from .db import Database
    from .profiling import calculate_bloom_stats, calculate_methodological_compass, calculate_tension_heatmap
    
    db = Database(repo_root)
    run_id = run_dir.name
    db.update_run_status(run_id, "executing")
    
    try:
        manifest = load_manifest(repo_root)
        model_policy = load_model_policy(repo_root)
        provider = provider_from_name(provider_name)
        
        style_ids = manifest.mvp_style_ids
        
        # 1. Review
        for style_id in style_ids:
            bundle = create_review_bundle(repo_root=repo_root, run_dir=run_dir, style_id=style_id, manifest=manifest, profile=profile)
            execute_review_artifact(
                repo_root=repo_root,
                review_path=bundle.review_json,
                provider=provider,
                model=model or model_policy.resolve_model("style_review", provider_name),
            )

        # 2. Council
        council = create_council_bundle(repo_root=repo_root, run_dir=run_dir, manifest=manifest, profile=profile)
        execute_council_artifact(
            repo_root=repo_root,
            council_path=council.council_json,
            provider=provider,
            model=model or model_policy.resolve_model("council", provider_name),
        )
        # Save Council metrics
        db.save_metric(run_id, "bloom_stats", calculate_bloom_stats(run_dir))
        db.save_metric(run_id, "profile", calculate_methodological_compass(run_dir, manifest))

        # 3. Revision
        revision = create_revision_bundle(repo_root=repo_root, run_dir=run_dir)
        execute_revision_artifact(
            repo_root=repo_root,
            revision_path=revision.revision_json,
            provider=provider,
            model=model or model_policy.resolve_model("synthesis", provider_name),
        )
        write_revision_diff(run_dir)

        # 4. Verification
        verification = create_verification_bundle(repo_root=repo_root, run_dir=run_dir)
        execute_verification_artifact(
            repo_root=repo_root,
            verification_path=verification.verification_json,
            provider=provider,
            model=model or model_policy.resolve_model("verification", provider_name),
        )

        # 5. Impact
        impact = create_impact_bundle(repo_root=repo_root, run_dir=run_dir)
        execute_impact_artifact(
            repo_root=repo_root,
            impact_path=impact.impact_json,
            provider=provider,
            model=model or model_policy.resolve_model("verification", provider_name),
        )
        db.save_metric(run_id, "tension", calculate_tension_heatmap(run_dir))

        # 6. Syntax
        syntax_bundle = create_syntax_bundle(repo_root=repo_root, run_dir=run_dir)
        if syntax_bundle:
            execute_syntax_artifact(
                repo_root=repo_root,
                syntax_path=Path(syntax_bundle["syntax_path"]),
                provider=provider,
                model=model or model_policy.resolve_model("verification", provider_name),
            )

        # 7. Reports
        write_run_report(run_dir)
        write_html_report(run_dir)
        
        from .latex import write_latex_report
        write_latex_report(run_dir, db.get_run(run_id))
        
        from .bibtex import write_bibtex
        write_bibtex(run_dir)
        
        db.update_run_status(run_id, "completed")
    except Exception as exc:
        db.update_run_status(run_id, "failed", summary=str(exc))
        raise
