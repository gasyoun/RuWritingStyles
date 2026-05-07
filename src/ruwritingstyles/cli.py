"""Command-line interface for RuWritingStyles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .config import load_manifest, load_model_policy, load_model_routes, load_passport_summaries, repo_root_from
from .council import create_council_bundle
from .diff import write_revision_diff
from .evals import compare_eval_suites, load_eval_cases, render_eval_suite_comparison, run_eval_case, run_eval_suite
from .execution import (
    execute_council_artifact,
    execute_review_artifact,
    execute_revision_artifact,
    execute_verification_artifact,
)
from .export import export_eval_suite_bundle, export_run_bundle
from .findings import load_finding_summaries, render_finding_summaries
from .html_summary import write_html_report
from .provider_log import load_provider_log, render_provider_log
from .provider_status import provider_statuses, provider_statuses_json, render_provider_statuses
from .providers import provider_from_name
from .report import write_run_report
from .review import create_review_bundle
from .revision import create_revision_bundle
from .runs import create_prepare_run
from .segment import normalize_document, read_document, segment_markdown
from .validation import (
    validate_eval_comparison_file,
    validate_eval_suite_dir,
    validate_provider_status_file,
    validate_run_dir,
)
from .verification import create_verification_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rws",
        description="RuWritingStyles document preparation and agentic review tooling.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare",
        help="Normalize and segment a Markdown/TXT document into run artifacts.",
    )
    prepare.add_argument("input", type=Path, help="Input .md or .txt document.")
    prepare.add_argument(
        "--run-id",
        help="Optional deterministic run id. The target runs/<run-id> must not already exist.",
    )
    prepare.set_defaults(func=cmd_prepare)

    run = subparsers.add_parser(
        "run",
        help="Run the full offline pipeline: prepare, review, council, revise, verify.",
    )
    run.add_argument("input", type=Path, help="Input .md or .txt document.")
    run.add_argument(
        "--run-id",
        help="Optional deterministic run id. The target runs/<run-id> must not already exist.",
    )
    run_styles = run.add_mutually_exclusive_group()
    run_styles.add_argument("--style", help="One style id from `rws list-styles`.")
    run_styles.add_argument("--styles", help="Comma-separated style ids from `rws list-styles`.")
    run_styles.add_argument(
        "--mvp",
        action="store_true",
        help="Use the MVP styles from styles/manifest.yml. This is the default.",
    )
    _add_execute_args(run)
    run.set_defaults(func=cmd_run)

    show_config = subparsers.add_parser(
        "show-config",
        help="Show the loaded style manifest and default model policy summary.",
    )
    show_config.set_defaults(func=cmd_show_config)

    model_routes = subparsers.add_parser(
        "model-routes",
        help="Show task-to-model routes from model_policy.yml.",
    )
    model_routes.add_argument(
        "--provider",
        choices=["openai", "google", "anthropic"],
        help="Filter routes to one provider.",
    )
    model_routes.add_argument("--task", help="Filter routes to one task, for example style_review.")
    model_routes.set_defaults(func=cmd_model_routes)

    provider_status = subparsers.add_parser(
        "provider-status",
        help="Show provider readiness for real API execution without exposing keys.",
    )
    provider_status.add_argument(
        "--provider",
        choices=["mock", "openai", "google", "anthropic"],
        help="Filter readiness to one provider.",
    )
    provider_status.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when any selected provider is not ready.",
    )
    provider_status.add_argument(
        "--json",
        action="store_true",
        help="Print secret-free JSON readiness data.",
    )
    provider_status.set_defaults(func=cmd_provider_status)

    list_styles = subparsers.add_parser(
        "list-styles",
        help="List style passports known to styles/manifest.yml.",
    )
    list_styles.add_argument(
        "--mvp",
        action="store_true",
        help="Show only the MVP styles used by the first review prototype.",
    )
    list_styles.set_defaults(func=cmd_list_styles)

    eval_list = subparsers.add_parser(
        "eval-list",
        help="List evaluation cases from evals/manifest.json.",
    )
    eval_list.set_defaults(func=cmd_eval_list)

    eval_run = subparsers.add_parser(
        "eval-run",
        help="Run one evaluation case through the executable pipeline.",
    )
    eval_run.add_argument("--case", required=True, help="Eval case id from `rws eval-list`.")
    eval_run.add_argument(
        "--run-id",
        help="Optional deterministic run id. The target runs/<run-id> must not already exist.",
    )
    _add_provider_args(eval_run)
    eval_run.set_defaults(func=cmd_eval_run)

    eval_suite = subparsers.add_parser(
        "eval-suite",
        help="Run all evaluation cases from evals/manifest.json.",
    )
    eval_suite.add_argument(
        "--suite-id",
        help="Optional deterministic suite id. Creates runs/<suite-id>/eval-suite-result.json.",
    )
    eval_suite.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when any eval case fails or --compare-to detects a regression.",
    )
    eval_suite.add_argument(
        "--compare-to",
        type=Path,
        help="Optional baseline suite directory or eval-suite-result.json to compare after the run.",
    )
    _add_provider_args(eval_suite)
    eval_suite.set_defaults(func=cmd_eval_suite)

    eval_compare = subparsers.add_parser(
        "eval-compare",
        help="Compare two eval-suite results and show pass-rate/case deltas.",
    )
    eval_compare.add_argument(
        "baseline",
        type=Path,
        help="Baseline suite directory or eval-suite-result.json.",
    )
    eval_compare.add_argument(
        "candidate",
        type=Path,
        help="Candidate suite directory or eval-suite-result.json.",
    )
    eval_compare.add_argument(
        "--output",
        type=Path,
        help="Optional Markdown report path.",
    )
    eval_compare.add_argument(
        "--json-output",
        type=Path,
        help="Optional machine-readable JSON comparison path.",
    )
    eval_compare.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when candidate pass rate drops or any case regresses.",
    )
    eval_compare.set_defaults(func=cmd_eval_compare)

    eval_status = subparsers.add_parser(
        "eval-status",
        help="Show a compact status summary for an eval suite or comparison JSON.",
    )
    eval_status.add_argument(
        "artifact",
        type=Path,
        help="Suite directory, eval-suite-result.json, or eval comparison JSON.",
    )
    eval_status.set_defaults(func=cmd_eval_status)

    review = subparsers.add_parser(
        "review",
        help="Create an offline review bundle for one style and a prepared run directory.",
    )
    review.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    review_styles = review.add_mutually_exclusive_group(required=True)
    review_styles.add_argument("--style", help="One style id from `rws list-styles`.")
    review_styles.add_argument("--styles", help="Comma-separated style ids from `rws list-styles`.")
    review_styles.add_argument(
        "--mvp",
        action="store_true",
        help="Create review bundles for the MVP styles from styles/manifest.yml.",
    )
    _add_execute_args(review)
    review.set_defaults(func=cmd_review)

    council = subparsers.add_parser(
        "council",
        help="Create an offline council bundle from prepared style reviews.",
    )
    council.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    _add_execute_args(council)
    council.set_defaults(func=cmd_council)

    revise = subparsers.add_parser(
        "revise",
        help="Create an offline revision bundle from a council artifact.",
    )
    revise.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    _add_execute_args(revise)
    revise.set_defaults(func=cmd_revise)

    verify = subparsers.add_parser(
        "verify",
        help="Create an offline verification bundle from a revision artifact.",
    )
    verify.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    _add_execute_args(verify)
    verify.set_defaults(func=cmd_verify)

    findings = subparsers.add_parser(
        "findings",
        help="Show completed style findings grouped by span_id.",
    )
    findings.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    findings.add_argument("--span", help="Optional span_id filter, for example p002.")
    findings.set_defaults(func=cmd_findings)

    provider_log = subparsers.add_parser(
        "provider-log",
        help="Show provider execution log and retry telemetry for a run.",
    )
    provider_log.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    provider_log.set_defaults(func=cmd_provider_log)

    diff = subparsers.add_parser(
        "diff",
        help="Write a unified diff between normalized.md and revised.md for a run.",
    )
    diff.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    diff.set_defaults(func=cmd_diff)

    report = subparsers.add_parser(
        "report",
        help="Render or refresh Markdown and HTML reports for a run directory.",
    )
    report.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    report.set_defaults(func=cmd_report)

    html_report = subparsers.add_parser(
        "html-report",
        help="Render or refresh the static HTML summary for a run directory.",
    )
    html_report.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    html_report.set_defaults(func=cmd_html_report)

    export = subparsers.add_parser(
        "export",
        help="Create a portable ZIP bundle from a run directory.",
    )
    export.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    export.add_argument(
        "--output",
        type=Path,
        help="Optional output ZIP path. Defaults to runs/<run-id>/<run-id>-bundle.zip.",
    )
    export.set_defaults(func=cmd_export)

    export_eval_suite = subparsers.add_parser(
        "export-eval-suite",
        help="Create a portable ZIP bundle from an eval suite and its case runs.",
    )
    export_eval_suite.add_argument(
        "suite_dir",
        type=Path,
        help="Eval suite directory, for example runs/<suite-id>.",
    )
    export_eval_suite.add_argument(
        "--output",
        type=Path,
        help="Optional output ZIP path. Defaults to runs/<suite-id>/<suite-id>-bundle.zip.",
    )
    export_eval_suite.set_defaults(func=cmd_export_eval_suite)

    validate_run = subparsers.add_parser(
        "validate-run",
        help="Validate run artifacts and completed style findings.",
    )
    validate_run.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    validate_run.set_defaults(func=cmd_validate_run)

    validate_eval_suite = subparsers.add_parser(
        "validate-eval-suite",
        help="Validate eval-suite result artifacts and referenced case runs.",
    )
    validate_eval_suite.add_argument(
        "suite_dir",
        type=Path,
        help="Eval suite directory, for example runs/<suite-id>.",
    )
    validate_eval_suite.set_defaults(func=cmd_validate_eval_suite)

    validate_eval_comparison = subparsers.add_parser(
        "validate-eval-comparison",
        help="Validate an eval-compare --json-output artifact.",
    )
    validate_eval_comparison.add_argument(
        "comparison",
        type=Path,
        help="Comparison JSON path, for example runs/<suite>/comparison.json.",
    )
    validate_eval_comparison.set_defaults(func=cmd_validate_eval_comparison)

    validate_provider_status = subparsers.add_parser(
        "validate-provider-status",
        help="Validate a provider-status --json artifact.",
    )
    validate_provider_status.add_argument(
        "status",
        type=Path,
        help="Provider status JSON path created from `rws provider-status --json`.",
    )
    validate_provider_status.set_defaults(func=cmd_validate_provider_status)

    return parser


def _add_execute_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute generated prompts with a provider and update artifacts.",
    )
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai", "google", "anthropic"],
        help="Provider used with --execute. Defaults to deterministic mock.",
    )
    parser.add_argument(
        "--model",
        help="Optional provider-specific model override.",
    )
    parser.add_argument(
        "--require-provider-ready",
        action="store_true",
        help="With --execute, fail before writing artifacts if the selected provider is not configured.",
    )


def _add_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai", "google", "anthropic"],
        help="Provider used for execution. Defaults to deterministic mock.",
    )
    parser.add_argument(
        "--model",
        help="Optional provider-specific model override.",
    )
    parser.add_argument(
        "--require-provider-ready",
        action="store_true",
        help="Fail before execution if the selected provider is not configured.",
    )


def cmd_prepare(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    input_path = args.input if args.input.is_absolute() else (Path.cwd() / args.input)
    input_path = input_path.resolve()

    manifest = load_manifest(repo_root)
    model_policy = load_model_policy(repo_root)
    original_text = read_document(input_path)
    normalized_text = normalize_document(original_text)
    segments = segment_markdown(normalized_text)

    run_dir = create_prepare_run(
        repo_root=repo_root,
        input_path=input_path,
        original_text=original_text,
        normalized_text=normalized_text,
        segments=segments,
        manifest=manifest,
        model_policy=model_policy,
        run_id=args.run_id,
    )

    print(f"created {run_dir.relative_to(repo_root)}")
    print(f"segments: {len(segments)}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    input_path = args.input if args.input.is_absolute() else (Path.cwd() / args.input)
    input_path = input_path.resolve()
    if args.execute and args.require_provider_ready:
        _require_provider_ready(args.provider)

    manifest = load_manifest(repo_root)
    model_policy = load_model_policy(repo_root)
    original_text = read_document(input_path)
    normalized_text = normalize_document(original_text)
    segments = segment_markdown(normalized_text)

    run_dir = create_prepare_run(
        repo_root=repo_root,
        input_path=input_path,
        original_text=original_text,
        normalized_text=normalized_text,
        segments=segments,
        manifest=manifest,
        model_policy=model_policy,
        run_id=args.run_id,
    )

    style_ids = _selected_style_ids(args, manifest)
    print(f"created {run_dir.relative_to(repo_root)}")
    print(f"segments: {len(segments)}")

    for style_id in style_ids:
        bundle = create_review_bundle(
            repo_root=repo_root,
            run_dir=run_dir,
            style_id=style_id,
            manifest=manifest,
        )
        print(f"created {bundle.review_json.relative_to(repo_root)}")
        if args.execute:
            execute_review_artifact(
                repo_root=repo_root,
                review_path=bundle.review_json,
                provider=provider_from_name(args.provider),
                model=args.model,
            )
            print(f"completed {bundle.review_json.relative_to(repo_root)}")

    council = create_council_bundle(repo_root=repo_root, run_dir=run_dir)
    print(f"created {council.council_json.relative_to(repo_root)}")
    if args.execute:
        execute_council_artifact(
            repo_root=repo_root,
            council_path=council.council_json,
            provider=provider_from_name(args.provider),
            model=args.model,
        )
        print(f"completed {council.council_json.relative_to(repo_root)}")
    revision = create_revision_bundle(repo_root=repo_root, run_dir=run_dir)
    print(f"created {revision.revision_json.relative_to(repo_root)}")
    if args.execute:
        execute_revision_artifact(
            repo_root=repo_root,
            revision_path=revision.revision_json,
            provider=provider_from_name(args.provider),
            model=args.model,
        )
        print(f"completed {revision.revision_json.relative_to(repo_root)}")
        diff_path = write_revision_diff(run_dir)
        print(f"updated {diff_path.relative_to(repo_root)}")
    verification = create_verification_bundle(repo_root=repo_root, run_dir=run_dir)
    print(f"created {verification.verification_json.relative_to(repo_root)}")
    if args.execute:
        execute_verification_artifact(
            repo_root=repo_root,
            verification_path=verification.verification_json,
            provider=provider_from_name(args.provider),
            model=args.model,
        )
        print(f"completed {verification.verification_json.relative_to(repo_root)}")
    _write_reports(repo_root, run_dir)
    return 0


def cmd_show_config(_: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    manifest = load_manifest(repo_root)
    model_policy = load_model_policy(repo_root)

    print(f"manifest: {manifest.path.relative_to(repo_root)}")
    print("mvp styles:")
    for style_id in manifest.mvp_style_ids:
        print(f"- {style_id}")
    print("passports:")
    for passport in manifest.passports:
        print(f"- {passport.style_id}: {passport.path.relative_to(repo_root)}")
    print("default model:")
    print(f"- provider: {model_policy.default_provider}")
    print(f"- model: {model_policy.default_model}")
    print(f"- reasoning: {model_policy.default_reasoning}")
    print(f"- speed: {model_policy.default_speed}")
    return 0


def cmd_model_routes(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    routes = load_model_routes(repo_root)
    if args.provider:
        routes = tuple(route for route in routes if route.provider == args.provider)
    if args.task:
        routes = tuple(route for route in routes if route.task == args.task)
    if not routes:
        print("no model routes matched")
        return 1

    for route in routes:
        print(f"{route.provider}.{route.task}")
        print(f"  model: {route.model}")
        print(f"  {route.mode_name}: {route.mode_value}")
    return 0


def cmd_provider_status(args: argparse.Namespace) -> int:
    statuses = provider_statuses()
    if args.json:
        print(json.dumps(provider_statuses_json(statuses, provider=args.provider), ensure_ascii=False, indent=2))
    else:
        print(render_provider_statuses(statuses, provider=args.provider))
    if args.strict:
        selected = tuple(status for status in statuses if args.provider is None or status.provider == args.provider)
        if any(not status.ready for status in selected):
            return 1
    return 0


def cmd_list_styles(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    manifest = load_manifest(repo_root)
    summaries = load_passport_summaries(repo_root, manifest)
    if args.mvp:
        summaries = tuple(summary for summary in summaries if summary.is_mvp)

    for summary in summaries:
        marker = " *" if summary.is_mvp else ""
        print(f"{summary.style_id}{marker}")
        print(f"  name: {summary.name}")
        print(f"  role: {summary.role}")
        print(f"  prompt: {summary.source_prompt.relative_to(repo_root)}")
        print(f"  passport: {summary.passport_path.relative_to(repo_root)}")
    return 0


def cmd_eval_list(_: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    for case in load_eval_cases(repo_root):
        print(case.case_id)
        print(f"  input: {case.input_path.relative_to(repo_root)}")
        print(f"  purpose: {case.purpose}")
        print(f"  styles: {', '.join(case.default_styles)}")
        print(f"  risks: {', '.join(case.expected_risks)}")
    return 0


def cmd_eval_run(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    if args.require_provider_ready:
        _require_provider_ready(args.provider)
    result = run_eval_case(
        repo_root=repo_root,
        case_id=args.case,
        provider_name=args.provider,
        model=args.model,
        run_id=args.run_id,
    )
    print(f"created {result.run_dir.relative_to(repo_root)}")
    print(f"eval result {result.result_path.relative_to(repo_root)}")
    return 0


def cmd_eval_suite(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    if args.require_provider_ready:
        _require_provider_ready(args.provider)
    result = run_eval_suite(
        repo_root=repo_root,
        provider_name=args.provider,
        model=args.model,
        suite_id=args.suite_id,
    )
    data = _load_json(result.result_path)
    print(f"created {result.suite_dir.relative_to(repo_root)}")
    print(f"eval suite result {result.result_path.relative_to(repo_root)}")
    print(f"eval suite report {result.report_path.relative_to(repo_root)}")
    print(f"cases: {data.get('case_count', 0)}")
    print(f"passed: {data.get('passed_count', 0)}")
    print(f"failed: {data.get('failed_count', 0)}")
    comparison_data = None
    if args.compare_to:
        baseline = args.compare_to if args.compare_to.is_absolute() else (Path.cwd() / args.compare_to)
        comparison = compare_eval_suites(baseline, result.suite_dir)
        comparison_data = comparison.data
        comparison_md = result.suite_dir / "comparison.md"
        comparison_json = result.suite_dir / "comparison.json"
        comparison_md.write_text(render_eval_suite_comparison(comparison), encoding="utf-8")
        comparison_json.write_text(json.dumps(comparison.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"comparison report {comparison_md.relative_to(repo_root)}")
        print(f"comparison json {comparison_json.relative_to(repo_root)}")
        print(f"pass_rate_delta: {comparison.data.get('pass_rate_delta', 0)}")
        print(f"regressed: {len(comparison.data.get('regressed', []))}")
    if args.strict and int(data.get("failed_count", 0)) > 0:
        return 1
    if args.strict and comparison_data is not None and _eval_comparison_has_regression(comparison_data):
        return 1
    return 0


def cmd_eval_compare(args: argparse.Namespace) -> int:
    baseline = args.baseline if args.baseline.is_absolute() else (Path.cwd() / args.baseline)
    candidate = args.candidate if args.candidate.is_absolute() else (Path.cwd() / args.candidate)
    comparison = compare_eval_suites(baseline, candidate)
    rendered = render_eval_suite_comparison(comparison)
    print(rendered, end="")
    if args.output:
        output = args.output if args.output.is_absolute() else (Path.cwd() / args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"wrote {output}")
    if args.json_output:
        json_output = args.json_output if args.json_output.is_absolute() else (Path.cwd() / args.json_output)
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(comparison.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {json_output}")
    if args.strict and _eval_comparison_has_regression(comparison.data):
        return 1
    return 0


def cmd_eval_status(args: argparse.Namespace) -> int:
    artifact = args.artifact if args.artifact.is_absolute() else (Path.cwd() / args.artifact)
    data = _load_json(_eval_status_json_path(artifact))
    if "baseline" in data and "candidate" in data:
        print("eval comparison")
        print(f"  baseline: {data.get('baseline', {}).get('suite_id', '')}")
        print(f"  candidate: {data.get('candidate', {}).get('suite_id', '')}")
        print(f"  cases: {data.get('case_count', 0)}")
        print(f"  pass_rate_delta: {data.get('pass_rate_delta', 0)}")
        print(f"  newly_passed: {len(data.get('newly_passed', []))}")
        print(f"  regressed: {len(data.get('regressed', []))}")
        return 0
    if "suite_id" in data and "results" in data:
        print("eval suite")
        print(f"  suite_id: {data.get('suite_id', '')}")
        print(f"  provider: {data.get('provider', '')}")
        print(f"  model: {data.get('model', '')}")
        print(f"  cases: {data.get('case_count', 0)}")
        print(f"  passed: {data.get('passed_count', 0)}")
        print(f"  failed: {data.get('failed_count', 0)}")
        print(f"  pass_rate: {data.get('pass_rate', 0)}")
        return 0
    raise ValueError(f"unknown eval artifact shape: {artifact}")


def _eval_status_json_path(artifact: Path) -> Path:
    artifact = artifact.resolve()
    if artifact.is_dir():
        return artifact / "eval-suite-result.json"
    return artifact


def _eval_comparison_has_regression(data: dict) -> bool:
    regressed = data.get("regressed")
    pass_rate_delta = data.get("pass_rate_delta")
    return bool(regressed) or (isinstance(pass_rate_delta, (int, float)) and pass_rate_delta < 0)


def cmd_review(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    manifest = load_manifest(repo_root)
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    style_ids = _selected_style_ids(args, manifest)
    if args.execute and args.require_provider_ready:
        _require_provider_ready(args.provider)

    for style_id in style_ids:
        bundle = create_review_bundle(
            repo_root=repo_root,
            run_dir=run_dir,
            style_id=style_id,
            manifest=manifest,
        )
        print(f"created {bundle.review_json.relative_to(repo_root)}")
        print(f"prompt {bundle.prompt_md.relative_to(repo_root)}")
        if args.execute:
            execute_review_artifact(
                repo_root=repo_root,
                review_path=bundle.review_json,
                provider=provider_from_name(args.provider),
                model=args.model,
            )
            print(f"completed {bundle.review_json.relative_to(repo_root)}")
    _write_reports(repo_root, run_dir)
    return 0


def _selected_style_ids(args: argparse.Namespace, manifest) -> list[str]:
    if getattr(args, "mvp", False):
        style_ids = list(manifest.mvp_style_ids)
    elif getattr(args, "styles", None):
        style_ids = [style_id.strip() for style_id in args.styles.split(",") if style_id.strip()]
    elif getattr(args, "style", None):
        style_ids = [args.style]
    else:
        style_ids = list(manifest.mvp_style_ids)

    if not style_ids:
        raise ValueError("no style ids selected")
    return style_ids


def _require_provider_ready(provider: str) -> None:
    status = next((item for item in provider_statuses() if item.provider == provider), None)
    if status is None:
        raise ValueError(f"unknown provider {provider!r}")
    if not status.ready:
        missing = ", ".join(status.missing_env)
        raise RuntimeError(f"provider {provider!r} is not ready; missing environment: {missing}")


def cmd_council(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    if args.execute and args.require_provider_ready:
        _require_provider_ready(args.provider)
    bundle = create_council_bundle(repo_root=repo_root, run_dir=run_dir)
    print(f"created {bundle.council_json.relative_to(repo_root)}")
    print(f"prompt {bundle.prompt_md.relative_to(repo_root)}")
    if args.execute:
        execute_council_artifact(
            repo_root=repo_root,
            council_path=bundle.council_json,
            provider=provider_from_name(args.provider),
            model=args.model,
        )
        print(f"completed {bundle.council_json.relative_to(repo_root)}")
    _write_reports(repo_root, run_dir)
    return 0


def cmd_revise(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    if args.execute and args.require_provider_ready:
        _require_provider_ready(args.provider)
    bundle = create_revision_bundle(repo_root=repo_root, run_dir=run_dir)
    print(f"created {bundle.revision_json.relative_to(repo_root)}")
    print(f"prompt {bundle.prompt_md.relative_to(repo_root)}")
    if args.execute:
        execute_revision_artifact(
            repo_root=repo_root,
            revision_path=bundle.revision_json,
            provider=provider_from_name(args.provider),
            model=args.model,
        )
        print(f"completed {bundle.revision_json.relative_to(repo_root)}")
        diff_path = write_revision_diff(run_dir)
        print(f"updated {diff_path.relative_to(repo_root)}")
    _write_reports(repo_root, run_dir)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    if args.execute and args.require_provider_ready:
        _require_provider_ready(args.provider)
    bundle = create_verification_bundle(repo_root=repo_root, run_dir=run_dir)
    print(f"created {bundle.verification_json.relative_to(repo_root)}")
    print(f"prompt {bundle.prompt_md.relative_to(repo_root)}")
    if args.execute:
        execute_verification_artifact(
            repo_root=repo_root,
            verification_path=bundle.verification_json,
            provider=provider_from_name(args.provider),
            model=args.model,
        )
        print(f"completed {bundle.verification_json.relative_to(repo_root)}")
    _write_reports(repo_root, run_dir)
    return 0


def cmd_findings(args: argparse.Namespace) -> int:
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    summaries = load_finding_summaries(run_dir, span_id=args.span)
    print(render_finding_summaries(summaries))
    return 0


def cmd_provider_log(args: argparse.Namespace) -> int:
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    print(render_provider_log(load_provider_log(run_dir)))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    _write_reports(repo_root, run_dir)
    return 0


def cmd_html_report(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    html_path = write_html_report(run_dir)
    print(f"updated {html_path.relative_to(repo_root)}")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    diff_path = write_revision_diff(run_dir)
    print(f"updated {diff_path.relative_to(repo_root)}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    output_path = None
    if args.output:
        output_path = args.output if args.output.is_absolute() else (Path.cwd() / args.output)
    bundle_path = export_run_bundle(run_dir, output_path)
    print(f"created {_display_path(repo_root, bundle_path)}")
    return 0


def cmd_export_eval_suite(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    suite_dir = args.suite_dir if args.suite_dir.is_absolute() else (Path.cwd() / args.suite_dir)
    output_path = None
    if args.output:
        output_path = args.output if args.output.is_absolute() else (Path.cwd() / args.output)
    bundle_path = export_eval_suite_bundle(suite_dir, output_path)
    print(f"created {_display_path(repo_root, bundle_path)}")
    return 0


def cmd_validate_run(args: argparse.Namespace) -> int:
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    result = validate_run_dir(run_dir)
    if result.ok:
        print("OK run artifacts valid")
        return 0
    for message in result.messages:
        print(f"FAIL {message}", file=sys.stderr)
    return 1


def cmd_validate_eval_suite(args: argparse.Namespace) -> int:
    suite_dir = args.suite_dir if args.suite_dir.is_absolute() else (Path.cwd() / args.suite_dir)
    result = validate_eval_suite_dir(suite_dir)
    if result.ok:
        print("OK eval suite artifacts valid")
        return 0
    for message in result.messages:
        print(f"FAIL {message}", file=sys.stderr)
    return 1


def cmd_validate_eval_comparison(args: argparse.Namespace) -> int:
    comparison = args.comparison if args.comparison.is_absolute() else (Path.cwd() / args.comparison)
    result = validate_eval_comparison_file(comparison)
    if result.ok:
        print("OK eval comparison artifact valid")
        return 0
    for message in result.messages:
        print(f"FAIL {message}", file=sys.stderr)
    return 1


def cmd_validate_provider_status(args: argparse.Namespace) -> int:
    status = args.status if args.status.is_absolute() else (Path.cwd() / args.status)
    result = validate_provider_status_file(status)
    if result.ok:
        print("OK provider status artifact valid")
        return 0
    for message in result.messages:
        print(f"FAIL {message}", file=sys.stderr)
    return 1


def _display_path(repo_root: Path, path: Path) -> Path | str:
    try:
        return path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_reports(repo_root: Path, run_dir: Path) -> None:
    report_path = write_run_report(run_dir)
    html_path = write_html_report(run_dir)
    print(f"updated {report_path.relative_to(repo_root)}")
    print(f"updated {html_path.relative_to(repo_root)}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
