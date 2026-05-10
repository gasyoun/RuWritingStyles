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
from .citations import extract_citations, verify_citations_against_knowledge
from .bias import run_bias_audit

def run_full_pipeline(repo_root: Path, run_dir: Path, provider_name: str, model: str | None = None, profile: str = "researcher", on_update: Any = None, injection_queue: Optional[queue.Queue] = None) -> None:
    from .db import Database
    from .profiling import calculate_bloom_stats, calculate_methodological_compass, calculate_tension_heatmap
    
    db = Database(repo_root)
    run_id = run_dir.name
    db.update_run_status(run_id, "executing")
    if on_update: on_update({"type": "run_status", "status": "executing"})
    
    def step(step_id, func):
        steps = db.get_run_steps(run_id)
        done = any(s["step_id"] == step_id and s["status"] == "completed" for s in steps)
        if done:
            print(f"Step '{step_id}' already completed, skipping.")
            return

        db.update_step_status(run_id, step_id, "executing")
        if on_update: on_update({"type": "step_update", "step_id": step_id, "status": "executing"})
        try:
            artifact_path = func()
            db.update_step_status(run_id, step_id, "completed", artifact_path=str(artifact_path) if artifact_path else None)
            if on_update: on_update({"type": "step_update", "step_id": step_id, "status": "completed", "artifact_path": str(artifact_path) if artifact_path else None})
        except Exception as e:
            db.update_step_status(run_id, step_id, "failed", error=str(e))
            if on_update: on_update({"type": "step_update", "step_id": step_id, "status": "failed", "error": str(e)})
            raise

    try:
        manifest = load_manifest(repo_root)
        model_policy = load_model_policy(repo_root)
        provider = provider_from_name(provider_name)
        style_ids = manifest.mvp_style_ids
        
        # 1. Review
        def do_review():
            for style_id in style_ids:
                bundle = create_review_bundle(repo_root=repo_root, run_dir=run_dir, style_id=style_id, manifest=manifest, profile=profile)
                execute_review_artifact(
                    repo_root=repo_root,
                    review_path=bundle.review_json,
                    provider=provider,
                    model=model or model_policy.resolve_model("style_review", provider_name),
                )
            return run_dir / "reviews"
        step("review", do_review)

        # 2. Council
        def do_council():
            council = create_council_bundle(repo_root=repo_root, run_dir=run_dir, manifest=manifest, profile=profile)
            execute_council_artifact(
                repo_root=repo_root,
                council_path=council.council_json,
                provider=provider,
                model=model or model_policy.resolve_model("council", provider_name),
                injection_queue=injection_queue
            )
            # Save Council metrics
            db.save_metric(run_id, "bloom_stats", calculate_bloom_stats(run_dir))
            db.save_metric(run_id, "compass", calculate_methodological_compass(run_dir, manifest))
            return council.council_json
        step("council", do_council)

        # 2.5. Bias Audit
        def do_bias_audit():
            res = run_bias_audit(
                repo_root=repo_root,
                run_dir=run_dir,
                provider=provider,
                model=model or model_policy.resolve_model("council", provider_name),
            )
            db.save_metric(run_id, "bias_score", res.get("bias_score", 0))
            return run_dir / "bias-audit.json"
        step("bias_audit", do_bias_audit)

        # 3. Revision
        def do_revision():
            revision = create_revision_bundle(repo_root=repo_root, run_dir=run_dir)
            execute_revision_artifact(
                repo_root=repo_root,
                revision_path=revision.revision_json,
                provider=provider,
                model=model or model_policy.resolve_model("synthesis", provider_name),
            )
            write_revision_diff(run_dir)
            return revision.revision_json
        step("revision", do_revision)

        # 4. Verification
        def do_verify():
            verification = create_verification_bundle(repo_root=repo_root, run_dir=run_dir)
            execute_verification_artifact(
                repo_root=repo_root,
                verification_path=verification.verification_json,
                provider=provider,
                model=model or model_policy.resolve_model("verification", provider_name),
            )
            return verification.verification_json
        step("verification", do_verify)

        # 4.5. Citations
        def do_citations():
            rev_path = run_dir / "revised.md"
            if not rev_path.exists():
                return
            text = rev_path.read_text(encoding="utf-8")
            citations = extract_citations(text)
            verification = verify_citations_against_knowledge(repo_root, citations)
            
            cite_path = run_dir / "citations.json"
            cite_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
            
            # Save to metrics
            db.save_metric(run_id, "citation_stats", {
                "total": len(citations),
                "verified": len(verification["verified"]),
                "hallucinations": len(verification["hallucinations"])
            })
            return cite_path
        step("citations", do_citations)

        # 5. Impact
        def do_impact():
            impact = create_impact_bundle(repo_root=repo_root, run_dir=run_dir)
            execute_impact_artifact(
                repo_root=repo_root,
                impact_path=impact.impact_json,
                provider=provider,
                model=model or model_policy.resolve_model("verification", provider_name),
            )
            db.save_metric(run_id, "tension", calculate_tension_heatmap(run_dir))
            return impact.impact_json
        step("impact", do_impact)

        # 6. Syntax
        def do_syntax():
            syntax_bundle = create_syntax_bundle(repo_root=repo_root, run_dir=run_dir)
            if syntax_bundle:
                execute_syntax_artifact(
                    repo_root=repo_root,
                    syntax_path=Path(syntax_bundle["syntax_path"]),
                    provider=provider,
                    model=model or model_policy.resolve_model("verification", provider_name),
                )
                return syntax_bundle["syntax_path"]
        step("syntax", do_syntax)

        # 7. Reports
        def do_reports():
            write_run_report(run_dir)
            write_html_report(run_dir)
            from .latex import write_latex_report
            write_latex_report(run_dir, db.get_run(run_id))
            from .bibtex import write_bibtex
            write_bibtex(run_dir)
            return run_dir / "reports"
        step("reports", do_reports)
        
        db.update_run_status(run_id, "completed")
    except Exception as exc:
        db.update_run_status(run_id, "failed", summary=str(exc))
        raise
