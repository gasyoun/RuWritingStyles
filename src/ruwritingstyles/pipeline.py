"""Single pipeline orchestrator shared by the CLI (`rws run`) and the
FastAPI surface.

`core_pipeline` is the one place the stage sequence lives. Both call sites pass
flags/callbacks instead of reimplementing it:

- CLI: emit=print, configurable style_ids, max_iterations, deliberate/scrutiny,
  an interactive_hook, optional prompt-only mode (execute=False).
- API: on_update + injection_queue callbacks, mvp styles, single iteration.

The CLI flow is the superset; the API flow is the
execute=True / single-iteration / no-optional-stages / +callbacks case.
"""

import json
import queue
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from .config import load_manifest, load_model_policy
from .providers import provider_from_name
from .review import create_review_bundle, create_deliberation_bundle
from .council import create_council_bundle
from .revision import create_revision_bundle
from .diff import write_revision_diff
from .verification import create_verification_bundle
from .assess import create_impact_bundle
from .syntax import create_syntax_bundle
from .scrutiny import create_scrutiny_bundle
from .execution import (
    execute_review_artifact,
    execute_deliberation_artifact,
    execute_council_artifact,
    execute_revision_artifact,
    execute_verification_artifact,
    execute_impact_artifact,
    execute_syntax_artifact,
    execute_scrutiny_artifact,
)
from .report import write_run_report
from .html_summary import write_html_report
from .citations import citation_stats, extract_citations, verify_citations_against_knowledge
from .bias import run_bias_audit
from .io_utils import atomic_write_json


class ExecutionMode(str, Enum):
    PREPARE = "prepare"
    PROMPT = "prompt"
    EXECUTE = "execute"


@dataclass(frozen=True)
class PipelineOptions:
    """Normalized, durable contract shared by CLI, API and resume."""

    mode: ExecutionMode = ExecutionMode.EXECUTE
    max_iterations: int = 1
    deliberate: bool = False
    scrutiny: bool = False
    lint_translit: bool = True
    style_ids: tuple[str, ...] = ()
    archetype: str | None = None
    budget_mode: str = "standard"
    expensive_opt_in: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", ExecutionMode(self.mode))
        object.__setattr__(self, "style_ids", tuple(self.style_ids))
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

    def to_json(self) -> dict[str, Any]:
        value = asdict(self)
        value["mode"] = self.mode.value
        value["style_ids"] = list(self.style_ids)
        return value

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> "PipelineOptions":
        return cls(**value)


def build_step_plan(options: PipelineOptions) -> list[dict[str, Any]]:
    """Return the deterministic stage plan persisted before execution."""

    if options.mode is ExecutionMode.PREPARE:
        return []
    steps: list[dict[str, Any]] = [{"step_id": "review", "provider_backed": options.mode is ExecutionMode.EXECUTE}]
    if options.deliberate:
        steps.append({"step_id": "deliberation", "provider_backed": options.mode is ExecutionMode.EXECUTE})
    if options.scrutiny:
        steps.append({"step_id": "scrutiny", "provider_backed": options.mode is ExecutionMode.EXECUTE})
    for iteration in range(1, options.max_iterations + 1):
        suffix = f"_iter{iteration}" if options.max_iterations > 1 else ""
        steps.append({"step_id": f"council{suffix}", "provider_backed": options.mode is ExecutionMode.EXECUTE})
        if options.mode is ExecutionMode.EXECUTE:
            steps.append({"step_id": f"bias_audit{suffix}", "provider_backed": True})
        steps.extend([
            {"step_id": f"revision{suffix}", "provider_backed": options.mode is ExecutionMode.EXECUTE},
            {"step_id": f"verification{suffix}", "provider_backed": options.mode is ExecutionMode.EXECUTE},
        ])
        if options.lint_translit:
            steps.append({"step_id": f"translit_lint{suffix}", "provider_backed": False})
        if options.mode is ExecutionMode.EXECUTE:
            steps.extend([
                {"step_id": f"citations{suffix}", "provider_backed": False},
                {"step_id": f"impact{suffix}", "provider_backed": True},
                {"step_id": f"syntax{suffix}", "provider_backed": True},
            ])
    steps.append({"step_id": "reports", "provider_backed": False})
    return steps


def _artifact_valid(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_dir():
        return any(path.iterdir())
    if path.stat().st_size == 0:
        return False
    if path.suffix == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return False
    return True


def _noop(_msg: str) -> None:
    pass


def core_pipeline(
    repo_root: Path,
    run_dir: Path,
    *,
    provider_name: str,
    model: str | None = None,
    profile: str = "researcher",
    manifest: Any = None,
    model_policy: Any = None,
    style_ids: list[str] | tuple[str, ...] | None = None,
    execute: bool | None = True,
    max_iterations: int = 1,
    deliberate: bool = False,
    scrutiny: bool = False,
    lint_translit: bool = True,
    archetype: str | None = None,
    interactive_hook: Optional[Callable[[Path, Path], None]] = None,
    on_update: Any = None,
    injection_queue: Optional[queue.Queue] = None,
    emit: Optional[Callable[[str], None]] = None,
    post_run: Optional[Callable[[], None]] = None,
    options: PipelineOptions | None = None,
) -> None:
    """Run the full review pipeline over a prepared run directory.

    Stages: review -> [deliberation] -> [scrutiny] -> (council -> bias ->
    revision -> verify -> [translit_lint] -> citations -> [impact -> syntax])
    x iterations -> reports. Bundles are always created; provider calls happen
    only when ``execute`` is True. The translit linter, citation grounding and
    bias audit are deterministic/standalone and run regardless, preserving prior
    behavior of both call sites.
    """
    from .db import Database
    from .profiling import (
        calculate_bloom_stats,
        calculate_methodological_compass,
        calculate_tension_heatmap,
    )

    emit = emit or _noop
    db = Database(repo_root)
    run_id = run_dir.name

    if manifest is None:
        manifest = load_manifest(repo_root)
    if model_policy is None:
        model_policy = load_model_policy(repo_root)
    if style_ids is None:
        style_ids = manifest.mvp_style_ids
    if options is None:
        options = PipelineOptions(
            mode=ExecutionMode.EXECUTE if execute is not False else ExecutionMode.PROMPT,
            max_iterations=max_iterations,
            deliberate=deliberate,
            scrutiny=scrutiny,
            lint_translit=lint_translit,
            style_ids=tuple(style_ids),
            archetype=archetype,
        )
    style_ids = list(options.style_ids or style_ids)
    execute_mode = options.mode is ExecutionMode.EXECUTE
    max_iterations = options.max_iterations
    deliberate = options.deliberate
    scrutiny = options.scrutiny
    lint_translit = options.lint_translit
    archetype = options.archetype
    step_plan = build_step_plan(options)
    provider = provider_from_name(provider_name) if execute_mode else None

    def resolve(task: str) -> str:
        return model or model_policy.resolve_model(task, provider_name)

    def rel(path: Path) -> str:
        try:
            return str(path.relative_to(repo_root))
        except ValueError:
            return str(path)

    from .runs import record_step_state, write_run_manifest

    db.update_run_status(run_id, "executing")
    write_run_manifest(
        repo_root, run_dir,
        pipeline_options=options.to_json(), step_plan=step_plan,
    )
    if on_update:
        on_update({"type": "run_status", "status": "executing"})

    def step(
        step_id: str,
        func: Callable[[], Any],
        expected_outputs: tuple[Path, ...] = (),
    ) -> None:
        steps = db.get_run_steps(run_id)
        existing = next((s for s in steps if s["step_id"] == step_id), None)
        if existing and existing["status"] == "completed":
            recorded = Path(existing["artifact_path"]) if existing.get("artifact_path") else None
            candidates = expected_outputs or ((recorded,) if recorded else ())
            if candidates and all(_artifact_valid(path) for path in candidates):
                emit(f"skipping completed step: {step_id}")
                return
            emit(f"completed step is stale; rerunning: {step_id}")
            record_step_state(repo_root, run_dir, step_id, "stale")
        event = record_step_state(repo_root, run_dir, step_id, "executing")
        if on_update:
            on_update(event)
        try:
            artifact_path = func()
            path_str = str(artifact_path) if artifact_path else None
            event = record_step_state(
                repo_root, run_dir, step_id, "completed", artifact_path=path_str,
            )
            if on_update:
                on_update(event)
        except Exception as exc:
            event = record_step_state(
                repo_root, run_dir, step_id, "failed", error=str(exc),
            )
            if on_update:
                on_update(event)
            raise

    try:
        # 1. Review
        def do_review():
            for style_id in style_ids:
                bundle = create_review_bundle(
                    repo_root=repo_root, run_dir=run_dir, style_id=style_id,
                    manifest=manifest, profile=profile,
                )
                emit(f"created {rel(bundle.review_json)}")
                if execute_mode:
                    execute_review_artifact(
                        repo_root=repo_root, review_path=bundle.review_json,
                        provider=provider, model=resolve("style_review"),
                    )
                    emit(f"completed {rel(bundle.review_json)}")
            return run_dir / "reviews"
        step("review", do_review, (run_dir / "reviews",))

        # 2. Deliberation (optional)
        if deliberate:
            def do_deliberation():
                emit("\n--- Cross-Style Deliberation (Debate) ---")
                for style_id in style_ids:
                    bundle = create_deliberation_bundle(
                        repo_root=repo_root, run_dir=run_dir, style_id=style_id,
                        manifest=manifest, profile=profile,
                    )
                    emit(f"created {rel(bundle.deliberation_json)}")
                    if execute_mode:
                        execute_deliberation_artifact(
                            repo_root=repo_root, delib_path=bundle.deliberation_json,
                            provider=provider, model=resolve("style_review"),
                        )
                        emit(f"completed {rel(bundle.deliberation_json)}")
                return run_dir / "deliberations"
            step("deliberation", do_deliberation, (run_dir / "deliberations",))

        # 3. Scrutiny (optional)
        if scrutiny:
            def do_scrutiny():
                emit("\n--- Linguistic Scrutiny (Expert Audit) ---")
                bundle = create_scrutiny_bundle(repo_root=repo_root, run_dir=run_dir)
                emit(f"created {rel(bundle.scrutiny_json)}")
                if execute_mode:
                    execute_scrutiny_artifact(
                        repo_root=repo_root, scrutiny_path=bundle.scrutiny_json,
                        provider=provider, model=resolve("verification"),
                    )
                    emit(f"completed {rel(bundle.scrutiny_json)}")
                return bundle.scrutiny_json
            step("scrutiny", do_scrutiny, (run_dir / "scrutiny" / "scrutiny.json",))

        # 4. Iterations
        for iteration in range(1, max_iterations + 1):
            suffix = f"_iter{iteration}" if max_iterations > 1 else ""
            if iteration > 1:
                emit(f"\n--- Fact-Checking Iteration {iteration} ---")

            def do_council(iteration=iteration):
                verification_feedback = None
                if iteration > 1:
                    prev = run_dir / "verification.json"
                    if prev.exists():
                        verification_feedback = json.loads(prev.read_text(encoding="utf-8"))
                council = create_council_bundle(
                    repo_root=repo_root, run_dir=run_dir, manifest=manifest,
                    verification_feedback=verification_feedback,
                    archetype_id=archetype, profile=profile,
                )
                emit(f"created {rel(council.council_json)}")
                if execute_mode:
                    execute_council_artifact(
                        repo_root=repo_root, council_path=council.council_json,
                        provider=provider, model=resolve("council"),
                        injection_queue=injection_queue,
                    )
                    emit(f"completed {rel(council.council_json)}")
                    if interactive_hook is not None:
                        interactive_hook(repo_root, council.council_json)
                    db.save_metric(run_id, "bloom_stats", calculate_bloom_stats(run_dir))
                    db.save_metric(run_id, "compass", calculate_methodological_compass(run_dir, manifest))
                return council.council_json
            step(f"council{suffix}", do_council, (run_dir / "council.json",))

            if execute_mode:
                def do_bias_audit():
                    emit("\n--- Methodological Bias Audit ---")
                    res = run_bias_audit(
                        repo_root=repo_root, run_dir=run_dir,
                        provider=provider, model=resolve("council"),
                    )
                    db.save_metric(run_id, "bias_score", res.get("bias_score", 0))
                    emit(f"completed bias audit, score: {res.get('bias_score', 0)}/10")
                    return run_dir / "bias-audit.json"
                step(f"bias_audit{suffix}", do_bias_audit, (run_dir / "bias-audit.json",))

            def do_revision():
                revision = create_revision_bundle(repo_root=repo_root, run_dir=run_dir)
                emit(f"created {rel(revision.revision_json)}")
                if execute_mode:
                    execute_revision_artifact(
                        repo_root=repo_root, revision_path=revision.revision_json,
                        provider=provider, model=resolve("synthesis"),
                    )
                    emit(f"completed {rel(revision.revision_json)}")
                    diff_path = write_revision_diff(run_dir)
                    emit(f"updated {rel(diff_path)}")
                return revision.revision_json
            step(f"revision{suffix}", do_revision, (run_dir / "revision.json",))

            def do_verify():
                verification = create_verification_bundle(repo_root=repo_root, run_dir=run_dir)
                emit(f"created {rel(verification.verification_json)}")
                if execute_mode:
                    execute_verification_artifact(
                        repo_root=repo_root, verification_path=verification.verification_json,
                        provider=provider, model=resolve("verification"),
                    )
                    emit(f"completed {rel(verification.verification_json)}")
                return verification.verification_json
            step(f"verification{suffix}", do_verify, (run_dir / "verification.json",))

            if lint_translit:
                def do_translit_lint():
                    from .translit_lint import run_translit_lint
                    artifact = run_translit_lint(repo_root, run_dir)
                    doc = json.loads(artifact.read_text(encoding="utf-8"))
                    emit(f"completed transliteration lint: {len(doc.get('findings', []))} finding(s) in {doc.get('source_file')}")
                    return artifact
                step(f"translit_lint{suffix}", do_translit_lint, (run_dir / "translit-lint.json",))

            if execute_mode:
                def do_citations():
                    emit("\n--- Scholarly Grounding (Citations) ---")
                    rev_path = run_dir / "revised.md"
                    text = rev_path.read_text(encoding="utf-8")
                    citations = extract_citations(text)
                    result = verify_citations_against_knowledge(repo_root, citations)
                    cite_path = run_dir / "citations.json"
                    atomic_write_json(cite_path, result)
                    db.save_metric(run_id, "citation_stats", citation_stats(citations, result))
                    emit(f"completed citation verification: {len(result['verified'])} verified, {len(result['not_in_bibliography'])} not in bibliography")
                    return cite_path
                step(f"citations{suffix}", do_citations, (run_dir / "citations.json",))

            if execute_mode:
                def do_impact():
                    impact = create_impact_bundle(repo_root=repo_root, run_dir=run_dir)
                    emit(f"created {rel(impact.impact_json)}")
                    execute_impact_artifact(
                        repo_root=repo_root, impact_path=impact.impact_json,
                        provider=provider, model=resolve("verification"),
                    )
                    db.save_metric(run_id, "tension", calculate_tension_heatmap(run_dir))
                    emit(f"completed {rel(impact.impact_json)}")
                    return impact.impact_json
                step(f"impact{suffix}", do_impact, (run_dir / "impact.json",))

                def do_syntax():
                    syntax_bundle = create_syntax_bundle(repo_root=repo_root, run_dir=run_dir)
                    if syntax_bundle:
                        s_path = Path(syntax_bundle["syntax_path"])
                        emit(f"created {rel(s_path)}")
                        execute_syntax_artifact(
                            repo_root=repo_root, syntax_path=s_path,
                            provider=provider, model=resolve("verification"),
                        )
                        emit(f"completed {rel(s_path)}")
                        return s_path
                    return None
                step(f"syntax{suffix}", do_syntax)

                # Fact-checking feedback loop control.
                verification_json = run_dir / "verification.json"
                impact_json = run_dir / "impact.json"
                if verification_json.exists() and impact_json.exists():
                    v_doc = json.loads(verification_json.read_text(encoding="utf-8"))
                    i_doc = json.loads(impact_json.read_text(encoding="utf-8"))
                    v_warnings = v_doc.get("warnings", [])
                    i_warnings = [
                        f"Impact failure in {a['span_id']} ({a['tag']}): {a['comment']}"
                        for a in i_doc.get("assessments", []) if not a.get("passed")
                    ]
                    combined_warnings = v_warnings + i_warnings
                    if not combined_warnings or iteration == max_iterations:
                        break
                    atomic_write_json(verification_json, {"warnings": combined_warnings})
                    emit(f"Verification/Impact failed with {len(combined_warnings)} warnings. Retrying...")
                else:
                    break
            else:
                break

        # 5. Reports
        def do_reports():
            write_run_report(run_dir)
            emit(f"updated {rel(run_dir / 'report.md')}")
            write_html_report(run_dir)
            emit(f"updated {rel(run_dir / 'summary.html')}")
            from .latex import write_latex_report
            write_latex_report(run_dir, db.get_run(run_id))
            from .bibtex import write_bibtex
            write_bibtex(run_dir, repo_root)
            return run_dir / "report.md"
        step("reports", do_reports, (run_dir / "report.md", run_dir / "summary.html"))

        if post_run is not None:
            post_run()

        db.update_run_status(run_id, "completed")
        write_run_manifest(repo_root, run_dir)
        if on_update:
            on_update({"type": "run_status", "status": "completed"})
    except Exception as exc:
        db.update_run_status(run_id, "failed", summary=str(exc))
        write_run_manifest(repo_root, run_dir)
        if on_update:
            on_update({"type": "run_status", "status": "failed", "error": str(exc)})
        raise


def run_full_pipeline(
    repo_root: Path,
    run_dir: Path,
    provider_name: str,
    model: str | None = None,
    profile: str = "researcher",
    on_update: Any = None,
    injection_queue: Optional[queue.Queue] = None,
    options: PipelineOptions | None = None,
) -> None:
    """API entry point: single-iteration, mvp styles, streamed via on_update."""
    core_pipeline(
        repo_root=repo_root,
        run_dir=run_dir,
        provider_name=provider_name,
        model=model,
        profile=profile,
        execute=True,
        max_iterations=1,
        on_update=on_update,
        injection_queue=injection_queue,
        options=options,
    )
