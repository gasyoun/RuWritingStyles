"""Command-line interface for RuWritingStyles."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import load_manifest, load_model_policy, load_model_routes, load_passport_summaries, repo_root_from
from .council import create_council_bundle
from .diff import write_revision_diff
from .evals import load_eval_cases, run_eval_case
from .execution import (
    execute_council_artifact,
    execute_review_artifact,
    execute_revision_artifact,
    execute_verification_artifact,
)
from .export import export_run_bundle
from .findings import load_finding_summaries, render_finding_summaries
from .providers import provider_from_name
from .report import write_run_report
from .review import create_review_bundle
from .revision import create_revision_bundle
from .runs import create_prepare_run
from .segment import normalize_document, read_document, segment_markdown
from .validation import validate_run_dir
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

    diff = subparsers.add_parser(
        "diff",
        help="Write a unified diff between normalized.md and revised.md for a run.",
    )
    diff.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    diff.set_defaults(func=cmd_diff)

    report = subparsers.add_parser(
        "report",
        help="Render or refresh the Markdown report for a run directory.",
    )
    report.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    report.set_defaults(func=cmd_report)

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

    validate_run = subparsers.add_parser(
        "validate-run",
        help="Validate run artifacts and completed style findings.",
    )
    validate_run.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    validate_run.set_defaults(func=cmd_validate_run)

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
    report_path = write_run_report(run_dir)
    print(f"updated {report_path.relative_to(repo_root)}")
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


def cmd_review(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    manifest = load_manifest(repo_root)
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    style_ids = _selected_style_ids(args, manifest)

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
    report_path = write_run_report(run_dir)
    print(f"updated {report_path.relative_to(repo_root)}")
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


def cmd_council(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
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
    report_path = write_run_report(run_dir)
    print(f"updated {report_path.relative_to(repo_root)}")
    return 0


def cmd_revise(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
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
    report_path = write_run_report(run_dir)
    print(f"updated {report_path.relative_to(repo_root)}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
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
    report_path = write_run_report(run_dir)
    print(f"updated {report_path.relative_to(repo_root)}")
    return 0


def cmd_findings(args: argparse.Namespace) -> int:
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    summaries = load_finding_summaries(run_dir, span_id=args.span)
    print(render_finding_summaries(summaries))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    report_path = write_run_report(run_dir)
    print(f"updated {report_path.relative_to(repo_root)}")
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


def cmd_validate_run(args: argparse.Namespace) -> int:
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    result = validate_run_dir(run_dir)
    if result.ok:
        print("OK run artifacts valid")
        return 0
    for message in result.messages:
        print(f"FAIL {message}", file=sys.stderr)
    return 1


def _display_path(repo_root: Path, path: Path) -> Path | str:
    try:
        return path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return str(path)


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
