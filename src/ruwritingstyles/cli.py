"""Command-line interface for RuWritingStyles."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import load_manifest, load_model_policy, load_passport_summaries, repo_root_from
from .review import create_review_bundle
from .runs import create_prepare_run
from .segment import normalize_document, read_document, segment_markdown


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

    show_config = subparsers.add_parser(
        "show-config",
        help="Show the loaded style manifest and default model policy summary.",
    )
    show_config.set_defaults(func=cmd_show_config)

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

    review = subparsers.add_parser(
        "review",
        help="Create an offline review bundle for one style and a prepared run directory.",
    )
    review.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    review.add_argument("--style", required=True, help="Style id from `rws list-styles`.")
    review.set_defaults(func=cmd_review)

    return parser


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


def cmd_review(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    manifest = load_manifest(repo_root)
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    bundle = create_review_bundle(
        repo_root=repo_root,
        run_dir=run_dir,
        style_id=args.style,
        manifest=manifest,
    )
    print(f"created {bundle.review_json.relative_to(repo_root)}")
    print(f"prompt {bundle.prompt_md.relative_to(repo_root)}")
    return 0


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
