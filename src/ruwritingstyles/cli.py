"""Command-line interface for RuWritingStyles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from datetime import datetime
from typing import Any
from dotenv import load_dotenv

# Load API keys from .env file if it exists
load_dotenv()

from .config import load_manifest, load_model_policy, load_model_routes, load_passport_summaries, repo_root_from
from .assess import create_impact_bundle
from .scrutiny import create_scrutiny_bundle
from .project import update_project_context
from .audit import audit_project_consistency
from .repl import run_council_repl
from .migration import migrate_document_style
from .sentiment import analyze_philological_sentiment
from .peer_review import run_peer_review
from .dashboard import generate_project_dashboard
from .db import Database
from .api import app as web_app
from .generation import generate_style_passport, save_generated_style
from .styleguide import generate_stylebook_markdown, save_stylebook
from .profiling import calculate_bloom_stats, calculate_methodological_compass
from .council import create_council_bundle
from .council_summary import load_council_summary, render_council_summary
from .diff import write_revision_diff
from .evals import (
    compare_eval_suites,
    load_eval_cases,
    render_eval_suite_comparison,
    run_eval_case,
    run_eval_repeat,
    run_eval_suite,
    run_eval_suite_repeat,
)
from .execution import (
    execute_council_artifact,
    execute_review_artifact,
    execute_deliberation_artifact,
    execute_revision_artifact,
    execute_verification_artifact,
    execute_impact_artifact,
    execute_scrutiny_artifact,
)
from .export import export_eval_suite_bundle, export_run_bundle
from .findings import load_finding_summaries, render_finding_summaries
from .html_summary import write_html_report
from .provider_log import load_provider_log, render_provider_log
from .provider_status import provider_statuses, provider_statuses_json, render_provider_statuses
from .providers import provider_from_name
from .report import write_run_report
from .review import create_review_bundle, create_deliberation_bundle
from .revision import create_revision_bundle
from .citations import citation_stats, extract_citations, verify_citations_against_knowledge
from .bias import run_bias_audit
from .runs import create_prepare_run
from .segment import normalize_document, read_document, segment_markdown
from .validation import (
    validate_eval_aggregate_file,
    validate_eval_comparison_file,
    validate_eval_suite_dir,
    validate_provider_status_file,
    validate_run_dir,
)
from .verification import create_verification_bundle
from .gallery import generate_style_gallery
from .db import Database

PROVIDER_CHOICES = ["mock", "openai", "google", "anthropic", "openrouter", "deepseek", "local", "ollama"]
REAL_PROVIDER_CHOICES = ["openai", "google", "anthropic", "openrouter", "deepseek", "local", "ollama"]


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rws",
        description="RuWritingStyles document preparation and agentic review tooling.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    web = subparsers.add_parser(
        "web",
        help="Launch the modern web frontend (RuWritingStyles Web Studio).",
    )
    web.set_defaults(func=cmd_web)

    prepare = subparsers.add_parser(
        "prepare",
        help="Normalize and segment a Markdown/TXT document into run artifacts.",
    )
    prepare.add_argument("input", type=Path, help="Input .md or .txt document.")
    prepare.add_argument(
        "--run-id",
        help="Optional deterministic run id. The target runs/<run-id> must not already exist.",
    )
    _add_provider_args(prepare)
    prepare.add_argument(
        "--profile",
        default="researcher",
        help="Researcher profile name (e.g., 'Editor', 'Student'). Default: 'researcher'.",
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
    _add_style_selection_group(
        run, required=False,
        mvp_help="Use the MVP styles from styles/manifest.yml. This is the default.",
    )
    run.add_argument(
        "--max-iterations",
        type=int,
        default=1,
        help="Maximum number of fact-checking iterations if verification fails.",
    )
    run.add_argument(
        "--deliberate",
        action="store_true",
        help="Enable multi-turn deliberation (style agents debate each other).",
    )
    run.add_argument(
        "--scrutiny",
        action="store_true",
        help="Enable deep linguistic scrutiny (expert philological audit).",
    )
    run.add_argument(
        "--project-dir",
        type=Path,
        help="Optional project directory to store shared stylistic context.",
    )
    run.add_argument(
        "--journal",
        help="Apply a journal profile by id (see `rws journals`), e.g. vestnik-spbu — "
             "checks length/citation/transliteration/abstract against that journal.",
    )
    run.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactively review and override Council decisions before revision.",
    )
    run.add_argument("--archetype", help="Council archetype ID")
    run.add_argument(
        "--no-lint-translit",
        action="store_true",
        help="Disable the deterministic Sanskrit transliteration linter (on by default).",
    )
    _add_execute_args(run)
    run.set_defaults(func=cmd_run)

    lint_translit = subparsers.add_parser(
        "lint-translit",
        help="Deterministically lint a Markdown file for Sanskrit transliteration issues (IAST vs русская передача, Harvard-Kyoto, Devanagari NFC).",
    )
    lint_translit.add_argument("input", type=Path, help="Input .md or .txt document.")
    lint_translit.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 when any finding is reported.",
    )
    lint_translit.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print the full lint artifact as JSON instead of a human-readable list.",
    )
    lint_translit.add_argument(
        "--journal",
        help="Apply a journal profile's rules (preset id from `rws journals`).",
    )
    lint_translit.set_defaults(func=cmd_lint_translit)
 

    ab_test = subparsers.add_parser(
        "ab-test",
        help="Compare multiple Council archetypes on the same document.",
    )
    ab_test.add_argument("input_file", type=Path, help="Markdown file to test.")
    ab_test.add_argument(
        "--archetypes",
        "-a",
        nargs="+",
        help="List of archetype IDs to compare (e.g., 'The Radical' 'The Minimalist').",
    )
    ab_test.add_argument(
        "--styles",
        "-s",
        nargs="+",
        help="Optional styles to use (overrides manifest MVP).",
    )
    _add_execute_args(ab_test)
    ab_test.set_defaults(func=cmd_ab_test)

    style_gallery = subparsers.add_parser(
        "style-gallery",
        help="Generate a Markdown gallery showcasing multiple styles on a sample text.",
    )
    style_gallery.add_argument("input_text", help="The sample text to transform.")
    style_gallery.add_argument(
        "--styles",
        "-s",
        nargs="+",
        help="List of style IDs. Defaults to MVP set.",
    )
    style_gallery.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output Markdown path (e.g. docs/my-gallery.md).",
    )
    _add_provider_args(style_gallery)
    style_gallery.set_defaults(func=cmd_style_gallery)

    project_run = subparsers.add_parser(
        "project-run",
        help="Run the pipeline on a directory of documents with shared consistency.",
    )
    project_run.add_argument("input_dir", type=Path, help="Directory containing .md files.")
    project_run.add_argument(
        "--deliberate",
        action="store_true",
        help="Enable multi-turn deliberation.",
    )
    project_run.add_argument(
        "--scrutiny",
        action="store_true",
        help="Enable deep linguistic scrutiny.",
    )
    project_run.add_argument(
        "--max-iterations",
        type=int,
        default=1,
        help="Max fact-checking iterations.",
    )
    project_run.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactively review and override Council decisions.",
    )
    _add_execute_args(project_run)
    project_run.set_defaults(func=cmd_project_run)

    journals = subparsers.add_parser(
        "journals",
        help="List available journal submission profiles from knowledge/journals/.",
    )
    journals.set_defaults(func=cmd_journals)

    project_set_journal = subparsers.add_parser(
        "project-set-journal",
        help="Write a journal profile into a project's project-context.json.",
    )
    project_set_journal.add_argument(
        "journal_id", help="Journal preset id from `rws journals` (e.g. vya, ppv, vestnik-spbu)."
    )
    project_set_journal.add_argument(
        "--project-dir",
        type=Path,
        default=Path(".rws-project"),
        help="Project directory holding project-context.json (default: .rws-project).",
    )
    project_set_journal.set_defaults(func=cmd_project_set_journal)

    corpus_status = subparsers.add_parser(
        "corpus-status",
        help="Show the corpus directory and FTS5 index status (Deep Retrieval).",
    )
    corpus_status.set_defaults(func=cmd_corpus_status)

    corpus_ingest = subparsers.add_parser(
        "corpus-ingest",
        help="Index the corpus .txt files into the local FTS5 store (rws.db).",
    )
    corpus_ingest.add_argument(
        "--force", action="store_true", help="Re-index files even if already indexed."
    )
    corpus_ingest.set_defaults(func=cmd_corpus_ingest)

    corpus_search = subparsers.add_parser(
        "corpus-search",
        help="Full-text search the indexed corpus (FTS5) and print snippets.",
    )
    corpus_search.add_argument("query", help="FTS5 query, e.g. \"samasa OR vigraha\".")
    corpus_search.add_argument("--limit", type=int, default=5, help="Max results (default 5).")
    corpus_search.add_argument(
        "--json", action="store_true", dest="as_json", help="Print results as JSON."
    )
    corpus_search.set_defaults(func=cmd_corpus_search)

    audit = subparsers.add_parser(
        "audit",
        help="Perform a final project-wide consistency audit against all stylistic commitments.",
    )
    audit.add_argument("project_dir", type=Path, help="The project directory containing run subfolders.")
    _add_provider_args(audit)
    audit.set_defaults(func=cmd_audit)

    repl = subparsers.add_parser(
        "repl",
        help="Enter an interactive REPL session to chat with the Council.",
    )
    repl.add_argument("run_dir", type=Path, help="The run directory containing the council.json.")
    _add_provider_args(repl)
    repl.set_defaults(func=cmd_repl)

    migrate_corpus = subparsers.add_parser(
        "migrate-corpus",
        help="Migrate an entire directory of documents to a new philological style.",
    )
    migrate_corpus.add_argument("input_dir", type=Path, help="Directory containing .md files.")
    migrate_corpus.add_argument("--from-style", help="The original style (optional context).")
    migrate_corpus.add_argument("--to-style", required=True, help="The target style ID.")
    _add_provider_args(migrate_corpus)
    migrate_corpus.set_defaults(func=cmd_migrate_corpus)

    sentiment = subparsers.add_parser(
        "sentiment",
        help="Analyze the tone, distance, and scholarly register shift of a revision.",
    )
    sentiment.add_argument("run_dir", type=Path, help="The run directory to analyze.")
    _add_provider_args(sentiment)
    sentiment.set_defaults(func=cmd_sentiment)

    peer_review = subparsers.add_parser(
        "peer-review",
        help="Use a second Council archetype to critique the revision and council decisions.",
    )
    peer_review.add_argument("run_dir", type=Path, help="The run directory to review.")
    peer_review.add_argument("--archetype", required=True, help="Archetype ID to act as reviewer.")
    _add_provider_args(peer_review)
    peer_review.set_defaults(func=cmd_peer_review)

    style_regression = subparsers.add_parser(
        "style-regression",
        help="Verify a style passport against its anchor test cases to detect linguistic drift.",
    )
    style_regression.add_argument("--style", required=True, help="Style ID to test.")
    _add_provider_args(style_regression)
    style_regression.set_defaults(func=cmd_style_regression)

    peer_review_ab = subparsers.add_parser(
        "peer-review-ab",
        help="Compare multiple peer reviewers (archetypes) on the same revision.",
    )
    peer_review_ab.add_argument("run_dir", type=Path, help="The run directory to review.")
    peer_review_ab.add_argument("--archetypes", nargs="+", required=True, help="List of archetype IDs.")
    _add_provider_args(peer_review_ab)
    peer_review_ab.set_defaults(func=cmd_peer_review_ab)

    dashboard = subparsers.add_parser(
        "dashboard",
        help="Generate a project-wide interactive HTML dashboard of all runs and metrics.",
    )
    dashboard.add_argument("--output", "-o", type=Path, help="Output HTML path.")
    dashboard.set_defaults(func=cmd_dashboard)

    migrate = subparsers.add_parser(
        "migrate",
        help="Port a document from one philological style to another.",
    )
    migrate.add_argument("input_file", type=Path, help="The document to migrate.")
    migrate.add_argument("--from-style", help="The original style (optional context).")
    migrate.add_argument("--to-style", required=True, help="The target style ID.")
    _add_provider_args(migrate)
    migrate.set_defaults(func=cmd_migrate)

    generate_passport = subparsers.add_parser(
        "generate-passport",
        help="Use an LLM to generate a new Style Passport and Source Prompt.",
    )
    generate_passport.add_argument("name", help="Human-friendly name of the style.")
    generate_passport.add_argument(
        "--description",
        "-d",
        required=True,
        help="Detailed description of the style goals and tone.",
    )
    generate_passport.add_argument(
        "--examples",
        "-e",
        help="Optional reference text to extract the style from.",
    )
    _add_execute_args(generate_passport)
    generate_passport.set_defaults(func=cmd_generate_passport)

    generate_styleguide = subparsers.add_parser(
        "generate-styleguide",
        help="Generate a human-readable Stylebook from passports and archetypes.",
    )
    generate_styleguide.add_argument(
        "--output",
        "-o",
        default="STYLEBOOK.md",
        help="Output filename (default: STYLEBOOK.md).",
    )
    generate_styleguide.set_defaults(func=cmd_generate_styleguide)

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
        choices=REAL_PROVIDER_CHOICES,
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
        choices=PROVIDER_CHOICES,
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

    councils = subparsers.add_parser(
        "councils",
        help="List the named councils defined in styles/manifest.yml.",
    )
    councils.set_defaults(func=cmd_councils)

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
    eval_run.add_argument(
        "--deliberate",
        action="store_true",
        help="Enable multi-turn deliberation (style agents debate each other).",
    )
    eval_run.add_argument(
        "--routes",
        action="store_true",
        help="Resolve per-stage models from model_policy.yml task_routes (review/council/revision/verification) instead of one provider default; an explicit --model still wins.",
    )
    eval_run.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Run the case N independent times and write an aggregate (pass-rate, "
             "detection-rate, mean/σ of diff metrics) to runs/<agg-id>/eval-aggregate.json.",
    )
    eval_run.add_argument(
        "--aggregate-id",
        help="Optional deterministic aggregate id (directory name) when --repeat > 1.",
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
    eval_suite.add_argument(
        "--deliberate",
        action="store_true",
        help="Enable multi-turn deliberation (style agents debate each other).",
    )
    eval_suite.add_argument(
        "--routes",
        action="store_true",
        help="Resolve per-stage models from model_policy.yml task_routes; an explicit --model still wins.",
    )
    eval_suite.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Run every case N independent times and write a suite-level aggregate "
             "to runs/<agg-id>/eval-aggregate.json (statistically meaningful pass-rate).",
    )
    eval_suite.add_argument(
        "--aggregate-id",
        help="Optional deterministic aggregate id (directory name) when --repeat > 1.",
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
        help="Optional path to write the full comparison JSON result.",
    )
    eval_compare.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when the candidate suite regresses against the baseline.",
    )
    eval_compare.set_defaults(func=cmd_eval_compare)

    eval_benchmark = subparsers.add_parser(
        "eval-benchmark",
        help="Run the evaluation suite on multiple models and generate a leaderboard.",
    )
    eval_benchmark.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="List of model names to benchmark (e.g. 'gpt-5.5' 'gemini-3.1-pro-preview').",
    )
    eval_benchmark.add_argument(
        "--provider",
        choices=REAL_PROVIDER_CHOICES,
        required=True,
        help="Provider to use for all models in this benchmark.",
    )
    eval_benchmark.set_defaults(func=cmd_eval_benchmark)

    eval_promote = subparsers.add_parser(
        "eval-promote",
        help="Promote a suite result to be the new baseline (Gold Standard).",
    )
    eval_promote.add_argument("suite_result", type=Path, help="Path to an eval-suite-result.json file.")
    eval_promote.add_argument(
        "--tag",
        default="gold",
        help="Baseline tag (default: 'gold'). Saves to evals/baselines/<tag>.json",
    )
    eval_promote.set_defaults(func=cmd_eval_promote)

    eval_regression = subparsers.add_parser(
        "eval-regression",
        help="Run all evals and compare against the 'gold' baseline. Fails on regression.",
    )
    eval_regression.add_argument(
        "--baseline",
        type=Path,
        help="Optional baseline path override. Defaults to evals/baselines/gold.json.",
    )
    _add_provider_args(eval_regression)
    eval_regression.set_defaults(func=cmd_eval_regression)

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
    _add_style_selection_group(
        review, required=True,
        mvp_help="Create review bundles for the MVP styles from styles/manifest.yml.",
    )
    _add_execute_args(review)
    review.set_defaults(func=cmd_review)

    council = subparsers.add_parser(
        "council",
        help="Create an offline council bundle from prepared style reviews.",
    )
    council.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    council.add_argument("--feedback", type=Path, help="Optional verification.json to use as feedback.")
    _add_execute_args(council)
    council.set_defaults(func=cmd_council)

    deliberate = subparsers.add_parser(
        "deliberate",
        help="Perform cross-style deliberation/debate from prepared style reviews.",
    )
    deliberate.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    _add_style_selection_group(
        deliberate, required=True,
        mvp_help="Create deliberation bundles for the MVP styles.",
    )
    _add_execute_args(deliberate)
    deliberate.set_defaults(func=cmd_deliberate)

    revise = subparsers.add_parser(
        "revise",
        help="Create an offline revision bundle from a council artifact.",
    )
    revise.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    _add_execute_args(revise)
    revise.set_defaults(func=cmd_revise)

    assess = subparsers.add_parser(
        "assess",
        help="Perform impact assessment on a revised document (rhyme/meter check).",
    )
    assess.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    _add_execute_args(assess)
    assess.set_defaults(func=cmd_assess)

    scrutiny = subparsers.add_parser(
        "scrutiny",
        help="Perform deep philological scrutiny (etymology/anachronism check).",
    )
    scrutiny.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    _add_execute_args(scrutiny)
    scrutiny.set_defaults(func=cmd_scrutiny)

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

    council_summary = subparsers.add_parser(
        "council-summary",
        help="Show council replies and decisions for a run.",
    )
    council_summary.add_argument("run_dir", type=Path, help="Prepared run directory, for example runs/<run-id>.")
    council_summary.set_defaults(func=cmd_council_summary)

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

    apply_res = subparsers.add_parser(
        "apply-resolution",
        help="Apply human stylistic overrides from resolution.json to council decisions.",
    )
    apply_res.add_argument("run_dir", type=Path, help="Prepared run directory.")
    apply_res.add_argument("--resolution", type=Path, help="Path to resolution.json (defaults to <run_dir>/resolution.json).")
    apply_res.set_defaults(func=cmd_apply_resolution)

    finalize = subparsers.add_parser(
        "finalize",
        help="Produce the final philological manuscript by merging revisions and resolutions.",
    )
    finalize.add_argument("run_dir", type=Path, help="Prepared run directory.")
    finalize.set_defaults(func=cmd_finalize)

    resume = subparsers.add_parser(
        "resume",
        help="Resume a failed or interrupted run from the last completed step.",
    )
    resume.add_argument("run_dir", type=Path, help="Run directory to resume.")
    _add_execute_args(resume)
    resume.set_defaults(func=cmd_resume)

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

    validate_eval_aggregate = subparsers.add_parser(
        "validate-eval-aggregate",
        help="Validate an eval-aggregate.json artifact (from eval-run/eval-suite --repeat N).",
    )
    validate_eval_aggregate.add_argument(
        "aggregate",
        type=Path,
        help="Aggregate directory or eval-aggregate.json, for example runs/<agg-id>.",
    )
    validate_eval_aggregate.set_defaults(func=cmd_validate_eval_aggregate)

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


def _add_style_selection_group(
    parser: argparse.ArgumentParser, *, required: bool, mvp_help: str
) -> None:
    """The shared --style/--styles/--council/--mvp mutually-exclusive group used
    by run/review/deliberate (they differ only in `required` and the --mvp help)."""
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--style", help="One style id from `rws list-styles`.")
    group.add_argument("--styles", help="Comma-separated style ids from `rws list-styles`.")
    group.add_argument(
        "--council",
        help="A named council from styles/manifest.yml (see `rws councils`), e.g. sanskrit.",
    )
    group.add_argument("--mvp", action="store_true", help=mvp_help)


def _add_execute_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute generated prompts with a provider and update artifacts.",
    )
    parser.add_argument(
        "--provider",
        default="mock",
        choices=PROVIDER_CHOICES,
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
    parser.add_argument(
        "--profile",
        default="researcher",
        help="Researcher profile name (e.g., 'Editor', 'Student'). Default: 'researcher'.",
    )


def _add_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        default="mock",
        choices=PROVIDER_CHOICES,
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
        provider=args.provider,
        profile=args.profile,
    )

    print(f"created {run_dir.relative_to(repo_root)}")
    print(f"segments: {len(segments)}")
    return 0


def cmd_style_gallery(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    manifest = load_manifest(repo_root)
    
    style_ids = args.styles
    if not style_ids:
        style_ids = manifest.mvp_style_ids
        
    if not style_ids:
        print("error: no styles specified and no MVP styles found in manifest.")
        return 1
        
    print(f"Generating Style Gallery for {len(style_ids)} styles...")
    
    gallery_md = generate_style_gallery(
        repo_root=repo_root,
        input_text=args.input_text,
        style_ids=style_ids,
        provider=provider_from_name(args.provider),
        model=args.model,
    )
    
    output_path = args.output
    if not output_path:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = repo_root / "docs" / f"style-gallery-{timestamp}.md"
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(gallery_md, encoding="utf-8")
    
    print(f"\nGallery generated! Saved to: {output_path.relative_to(repo_root)}")
    return 0


def cmd_ab_test(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    manifest = load_manifest(repo_root)
    archetypes_list = args.archetypes
    if not archetypes_list:
        # Load all from archetypes.yml
        from .config import load_archetypes
        archetypes_list = [a.id for a in load_archetypes(repo_root)]
    
    if not archetypes_list:
        print("error: no archetypes found to test.")
        return 1
        
    print(f"Starting A/B test for {len(archetypes_list)} archetypes...")
    
    test_run_id = f"ab-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    test_dir = repo_root / "runs" / test_run_id
    test_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for archetype_id in archetypes_list:
        print(f"\n>>> Testing Archetype: {archetype_id}")
        # Create a run for this archetype
        run_id = f"{test_run_id}-{archetype_id.replace(' ', '-').lower()}"
        
        # We need a custom manifest for this run
        from dataclasses import replace
        from .config import CouncilConfig
        custom_manifest = replace(manifest, council=CouncilConfig(archetype=archetype_id, conflict_resolution_strategy=manifest.council.conflict_resolution_strategy if manifest.council else "balanced"))
        
        # Build command args for a standard run
        run_args = argparse.Namespace(
            input_file=args.input_file,
            styles=args.styles,
            run_id=run_id,
            deliberate=True,
            scrutiny=True,
            interactive=False,
            execute=args.execute,
            provider=args.provider,
            model=args.model,
            require_provider_ready=args.require_provider_ready,
        )
        
        # We can't easily call cmd_run directly because it re-loads the manifest
        # So we'll run a modified version of its logic
        status = _execute_ab_run(repo_root, run_args, custom_manifest)
        if status == 0:
            results.append({
                "archetype": archetype_id,
                "run_dir": repo_root / "runs" / run_id
            })
            
    if results:
        report_path = _write_ab_comparison_report(repo_root, test_dir, results)
        print(f"\nA/B Test Complete! Comparison report: {report_path.relative_to(repo_root)}")
        return 0
    return 1


def _execute_ab_run(repo_root: Path, args: argparse.Namespace, manifest: Any) -> int:
    # Minimal version of cmd_run that takes a pre-loaded manifest
    from .runs import create_prepare_run
    from .execution import execute_review_artifact, execute_council_artifact, execute_revision_artifact
    from .review import create_review_bundle
    from .council import create_council_bundle
    from .revision import create_revision_bundle
    from .config import load_model_policy, provider_from_name
    
    from .document import read_document, normalize_document, segment_markdown
    original_text = read_document(args.input_file)
    normalized_text = normalize_document(original_text)
    segments = segment_markdown(normalized_text)
    model_policy = load_model_policy(repo_root)

    run_dir = create_prepare_run(
        repo_root=repo_root,
        input_path=args.input_file,
        original_text=original_text,
        normalized_text=normalized_text,
        segments=segments,
        manifest=manifest,
        model_policy=model_policy,
        run_id=args.run_id,
        provider=args.provider,
        archetype=manifest.council.archetype if manifest.council else None,
        profile="ab-tester",
    )

    style_ids = args.styles or manifest.mvp_style_ids
    
    if args.execute:
        # 1. Review
        for style_id in style_ids:
            bundle = create_review_bundle(repo_root=repo_root, run_dir=run_dir, style_id=style_id, manifest=manifest)
            execute_review_artifact(repo_root=repo_root, review_path=bundle.review_json, provider=provider_from_name(args.provider), model=args.model or model_policy.resolve_model("style_review", args.provider))
        
        # 2. Council
        council = create_council_bundle(repo_root=repo_root, run_dir=run_dir, manifest=manifest)
        execute_council_artifact(repo_root=repo_root, council_path=council.council_json, provider=provider_from_name(args.provider), model=args.model or model_policy.resolve_model("council", args.provider))
        
        # 3. Revision
        revision = create_revision_bundle(repo_root=repo_root, run_dir=run_dir, manifest=manifest)
        execute_revision_artifact(repo_root=repo_root, revision_path=revision.revision_json, provider=provider_from_name(args.provider), model=args.model or model_policy.resolve_model("synthesis", args.provider))
        
    return 0


def _write_ab_comparison_report(repo_root: Path, test_dir: Path, results: list[dict[str, Any]]) -> Path:
    # Generate a simple side-by-side HTML comparison
    html = [
        "<html><head><title>Archetype A/B Comparison</title>",
        "<style>",
        "  body { font-family: system-ui; padding: 2rem; background: #f8f9fa; }",
        "  .comparison-grid { display: flex; gap: 1rem; overflow-x: auto; }",
        "  .column { min-width: 400px; flex: 1; background: #fff; padding: 1rem; border-radius: 8px; border: 1px solid #ddd; }",
        "  h2 { border-bottom: 2px solid #007bff; padding-bottom: 0.5rem; }",
        "  pre { white-space: pre-wrap; font-size: 14px; line-height: 1.5; }",
        "</style></head><body>",
        f"<h1>Council Archetype A/B Test</h1>",
        f"<p class='muted'>Test ID: {test_dir.name}</p>",
        "<div class='comparison-grid'>"
    ]
    
    for res in results:
        rev_path = res["run_dir"] / "revision.md"
        content = rev_path.read_text(encoding="utf-8") if rev_path.exists() else "No revision generated."
        html.append(f"<div class='column'>")
        html.append(f"<h2>{res['archetype']}</h2>")
        html.append(f"<pre>{content}</pre>")
        html.append("</div>")
        
    html.append("</div></body></html>")
    
    report_path = test_dir / "ab-comparison.html"
    report_path.write_text("\n".join(html), encoding="utf-8")
    return report_path


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

    run_id = args.run_id
    project_dir = getattr(args, "project_dir", None)
    if project_dir:
        project_dir = project_dir if project_dir.is_absolute() else (Path.cwd() / project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)

    run_dir = create_prepare_run(
        repo_root=repo_root,
        input_path=input_path,
        original_text=original_text,
        normalized_text=normalized_text,
        segments=segments,
        manifest=manifest,
        model_policy=model_policy,
        run_id=run_id,
        provider=args.provider,
        archetype=getattr(args, "archetype", None),
        profile=args.profile,
        config={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items() if k != "func"},
    )

    if project_dir:
        # Copy project context into the run directory for the Council to see
        context_path = project_dir / "project-context.json"
        if context_path.exists():
            (run_dir / "project-context.json").write_text(context_path.read_text(encoding="utf-8"), encoding="utf-8")

    journal_id = getattr(args, "journal", None)
    if journal_id:
        # Inject a journal profile directly (no project dir needed): verification,
        # the transliteration linter, and the report read it from the run context.
        from .journals import load_journal_preset, list_journal_presets
        preset = load_journal_preset(repo_root, journal_id)
        if preset is None:
            available = ", ".join(list_journal_presets(repo_root)) or "(none)"
            raise SystemExit(f"unknown journal '{journal_id}'. Available: {available}")
        ctx_path = run_dir / "project-context.json"
        ctx: dict[str, Any] = {}
        if ctx_path.exists():
            try:
                ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                ctx = {}
        ctx["journal_profile"] = preset
        ctx_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return _execute_run_pipeline(repo_root, run_dir, args, manifest, model_policy)


def _execute_run_pipeline(repo_root: Path, run_dir: Path, args: argparse.Namespace, manifest: Any, model_policy: Any) -> int:
    """Thin CLI wrapper over the shared `core_pipeline` (see pipeline.py)."""
    from .pipeline import core_pipeline

    style_ids = _selected_style_ids(args, manifest)
    project_dir = getattr(args, "project_dir", None)
    if project_dir:
        project_dir = project_dir if project_dir.is_absolute() else (Path.cwd() / project_dir)

    interactive_hook = (
        _interactive_council_review if getattr(args, "interactive", False) else None
    )

    post_run = None
    if project_dir and args.execute:
        def post_run() -> None:
            update_project_context(project_dir, run_dir)

    core_pipeline(
        repo_root=repo_root,
        run_dir=run_dir,
        provider_name=args.provider,
        model=args.model,
        profile=args.profile,
        manifest=manifest,
        model_policy=model_policy,
        style_ids=style_ids,
        execute=args.execute,
        max_iterations=getattr(args, "max_iterations", 1),
        deliberate=getattr(args, "deliberate", False),
        scrutiny=getattr(args, "scrutiny", False),
        lint_translit=not getattr(args, "no_lint_translit", False),
        archetype=getattr(args, "archetype", None),
        interactive_hook=interactive_hook,
        emit=print,
        post_run=post_run,
    )
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


def cmd_project_run(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    input_dir = args.input_dir if args.input_dir.is_absolute() else (Path.cwd() / args.input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"error: {input_dir} is not a directory")
        return 1

    md_files = sorted(input_dir.glob("*.md"))
    if not md_files:
        print(f"no .md files found in {input_dir}")
        return 0

    print(f"Project Run: {len(md_files)} files in {input_dir.name}")
    
    # We use the input_dir as the project_dir
    project_dir = input_dir / ".rws-project"
    project_dir.mkdir(parents=True, exist_ok=True)

    for md_file in md_files:
        print(f"\n>>> Processing {md_file.name}...")
        # Create a clean args object for cmd_run
        run_args = argparse.Namespace(
            input=md_file,
            run_id=None,
            execute=args.execute,
            provider=args.provider,
            model=args.model,
            require_provider_ready=args.require_provider_ready,
            style=None,
            styles=None,
            mvp=True,
            deliberate=args.deliberate,
            scrutiny=args.scrutiny,
            max_iterations=args.max_iterations,
            interactive=args.interactive,
            project_dir=project_dir,
            profile=args.profile,
        )
        cmd_run(run_args)
    
    print(f"\nProject run complete. Context saved to {project_dir / 'project-context.json'}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    project_dir = args.project_dir if args.project_dir.is_absolute() else (Path.cwd() / args.project_dir)
    provider = provider_from_name(args.provider)
    
    print(f"Auditing project consistency for: {project_dir.name}...")
    try:
        report = audit_project_consistency(
            repo_root=repo_root,
            project_dir=project_dir,
            provider=provider,
            model=args.model,
        )
        
        audit_path = project_dir / "audit-report.json"
        audit_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        
        print(f"\nAudit Summary: {report.get('audit_summary', 'No summary available.')}")
        violations = report.get("violations", [])
        if violations:
            print(f"\nWARNING: Found {len(violations)} consistency violations!")
            for v in violations:
                print(f"- [{v.get('document_id')}] {v.get('term')}: {v.get('issue')}")
        else:
            print("\nSUCCESS: All documents are consistent with project commitments.")
            
        print(f"\nFull audit report saved to: {audit_path.relative_to(repo_root)}")
        return 0 if not violations else 1
    except Exception as e:
        print(f"error: audit failed: {e}")
        return 1


def cmd_repl(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    provider = provider_from_name(args.provider)
    manifest = load_manifest(repo_root)
    
    run_council_repl(
        repo_root=repo_root,
        run_dir=run_dir,
        manifest=manifest,
        provider=provider,
        model=args.model,
    )
    return 0


def cmd_migrate_corpus(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    input_dir = args.input_dir if args.input_dir.is_absolute() else (Path.cwd() / args.input_dir)
    provider = provider_from_name(args.provider)
    
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"error: {input_dir} is not a directory")
        return 1
        
    md_files = sorted(input_dir.glob("*.md"))
    if not md_files:
        print(f"no .md files found in {input_dir}")
        return 0
        
    output_dir = input_dir / "migrated"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Migrating corpus ({len(md_files)} files) to style: {args.to_style}...")
    
    success_count = 0
    for md_file in md_files:
        print(f"  -> {md_file.name}")
        try:
            migrated_path = migrate_document_style(
                repo_root=repo_root,
                input_file=md_file,
                from_style_id=args.from_style,
                to_style_id=args.to_style,
                provider=provider,
                model=args.model,
            )
            # Copy to corpus output dir with original name
            target = output_dir / md_file.name
            target.write_text(migrated_path.read_text(encoding="utf-8"), encoding="utf-8")
            success_count += 1
        except Exception as e:
            print(f"    error: {e}")
            
    print(f"\nMigration Complete! {success_count}/{len(md_files)} files saved to {output_dir.relative_to(repo_root)}")
    return 0 if success_count == len(md_files) else 1


def cmd_sentiment(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    provider = provider_from_name(args.provider)
    
    print(f"Analyzing philological sentiment for: {run_dir.name}...")
    try:
        result = analyze_philological_sentiment(
            repo_root=repo_root,
            run_dir=run_dir,
            provider=provider,
            model=args.model,
        )
        print(f"\nSentiment Shift Analysis:")
        print(f"- Academic Distance: {result['original']['distance']} -> {result['revised']['distance']} (Delta: {result['deltas']['distance']})")
        print(f"- Certainty:         {result['original']['certainty']} -> {result['revised']['certainty']} (Delta: {result['deltas']['certainty']})")
        print(f"- Complexity:        {result['original']['complexity']} -> {result['revised']['complexity']} (Delta: {result['deltas']['complexity']})")
        print(f"\nJustification: {result['justification']}")
        
        # Trigger report refresh
        _write_reports(repo_root, run_dir)
        return 0
    except Exception as e:
        print(f"error: sentiment analysis failed: {e}")
        return 1


def cmd_peer_review(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    provider = provider_from_name(args.provider)
    
    print(f"Running Philological Peer Review for: {run_dir.name}...")
    print(f"Reviewer Archetype: {args.archetype}")
    
    try:
        result = run_peer_review(
            repo_root=repo_root,
            run_dir=run_dir,
            provider=provider,
            model=args.model,
            reviewer_archetype_id=args.archetype,
        )
        
        print(f"\nPeer Review Summary (Score: {result['overall_score']}/10)")
        print(f"Recommendation: {result['recommendation'].upper()}")
        print("\nComments:")
        for comment in result['comments']:
            print(f"- [{comment['type']}] {comment['text']}")
            
        # Trigger report refresh
        _write_reports(repo_root, run_dir)
        return 0
    except Exception as e:
        print(f"error: peer review failed: {e}")
        return 1


def cmd_style_regression(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    style_id = args.style
    provider = provider_from_name(args.provider)
    
    print(f"Running Style Regression Test for: {style_id}...")
    
    try:
        from .evals import run_style_regression_test
        result = run_style_regression_test(
            repo_root=repo_root,
            style_id=style_id,
            provider_name=args.provider,
            model=args.model,
            execute=True,
        )
        
        print(f"\nStyle Regression Result: {result['status'].upper()}")
        print(f"Total Anchors: {result['total_anchors']}")
        print(f"Passed:        {result['passed_anchors']}")
        print(f"Regressions:   {len(result['regressions'])}")
        
        if result['regressions']:
            print("\nREGRESSIONS DETECTED:")
            for reg in result['regressions']:
                print(f"- [Case: {reg['case_id']}] {reg['issue']}")
                
        return 0 if not result['regressions'] else 1
    except Exception as e:
        print(f"error: style regression failed: {e}")
        return 1


def cmd_peer_review_ab(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    provider = provider_from_name(args.provider)
    archetypes = args.archetypes
    
    print(f"Running Peer Review A/B Test for: {run_dir.name}...")
    print(f"Comparing Archetypes: {', '.join(archetypes)}")
    
    results = []
    for arch_id in archetypes:
        print(f"  -> Reviewing as: {arch_id}")
        try:
            res = run_peer_review(
                repo_root=repo_root,
                run_dir=run_dir,
                provider=provider,
                model=args.model,
                reviewer_archetype_id=arch_id,
            )
            # Rename the file to avoid overwrite
            p = run_dir / "peer-review.json"
            new_p = run_dir / f"peer-review-{arch_id.replace(' ', '-').lower()}.json"
            if p.exists():
                new_p.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
            
            results.append(res)
        except Exception as e:
            print(f"    error for {arch_id}: {e}")
            
    if results:
        report_path = _write_peer_review_ab_report(repo_root, run_dir, results)
        print(f"\nPeer Review A/B Test Complete! Report: {report_path.relative_to(repo_root)}")
        return 0
    return 1


def _write_peer_review_ab_report(repo_root: Path, run_dir: Path, results: list[dict[str, Any]]) -> Path:
    html = [
        "<html><head><title>Peer Review A/B Comparison</title>",
        "<style>",
        "  body { font-family: system-ui; padding: 2rem; }",
        "  table { width: 100%; border-collapse: collapse; }",
        "  th, td { border: 1px solid #ddd; padding: 1rem; text-align: left; vertical-align: top; }",
        "  th { background: #f4f4f4; }",
        "  .recommendation { font-weight: bold; }",
        "  .ACCEPT { color: green; }",
        "  .MAJOR_REVISION { color: red; }",
        "</style></head><body>",
        f"<h1>Peer Review A/B Comparison: {run_dir.name}</h1>",
        "<table><tr>"
    ]
    
    for res in results:
        html.append(f"<th>{res['reviewer_archetype']}</th>")
    html.append("</tr><tr>")
    
    for res in results:
        html.append(f"<td>")
        html.append(f"<div class='recommendation {res['recommendation']}'>Recommendation: {res['recommendation'].upper()}</div>")
        html.append(f"<div>Score: {res['overall_score']}/10</div>")
        html.append("<ul>")
        for c in res.get('comments', []):
            html.append(f"<li><b>{c['type']}</b>: {c['text']}</li>")
        html.append("</ul></td>")
        
    html.append("</tr></table></body></html>")
    
    report_path = run_dir / "peer-review-ab.html"
    report_path.write_text("\n".join(html), encoding="utf-8")
    return report_path


def cmd_dashboard(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    print("Generating Interactive Project Dashboard...")
    try:
        from .dashboard import generate_project_dashboard
        output_path = args.output if args.output else repo_root / "DASHBOARD.html"
        path = generate_project_dashboard(repo_root, output_path)
        print(f"Success! Dashboard saved to: {path.relative_to(repo_root)}")
        return 0
    except Exception as e:
        print(f"error: dashboard generation failed: {e}")
        return 1


def _warn_if_port_busy(port: int) -> None:
    import subprocess
    import re
    try:
        output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
        pids = set(re.findall(r"LISTENING\s+(\d+)", output))
        for pid in pids:
            print(f"warning: port {port} is already busy (PID: {pid})")
    except subprocess.CalledProcessError:
        pass

def cmd_web(args: argparse.Namespace) -> int:
    import subprocess
    import time
    import webbrowser
    
    repo_root = repo_root_from()
    
    print("Pre-flight check: inspecting ports 8000 and 5173...")
    _warn_if_port_busy(8000)
    _warn_if_port_busy(5173)
    
    print("Launching RuWritingStyles Web Studio...")
    
    # 1. Start API Backend
    api_process = subprocess.Popen(
        ["python", "-m", "ruwritingstyles.api"],
        cwd=repo_root
    )
    
    # 2. Start Vite Frontend (if in dev mode)
    web_dir = repo_root / "web"
    frontend_process = None
    if web_dir.exists():
        print("Starting Vite development server...")
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=web_dir,
            shell=True
        )
        time.sleep(2)
        webbrowser.open("http://localhost:5173")
    else:
        print("Frontend directory not found. Please run 'npm install' in 'web/'.")
        return 1
        
    try:
        api_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        api_process.terminate()
        if frontend_process:
            frontend_process.terminate()
            
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    input_file = args.input_file if args.input_file.is_absolute() else (Path.cwd() / args.input_file)
    provider = provider_from_name(args.provider)
    
    print(f"Migrating {input_file.name} to style: {args.to_style}...")
    try:
        migrated_path = migrate_document_style(
            repo_root=repo_root,
            input_file=input_file,
            from_style_id=args.from_style,
            to_style_id=args.to_style,
            provider=provider,
            model=args.model,
        )
        print(f"Success! Migrated document saved to: {migrated_path.relative_to(repo_root)}")
        return 0
    except Exception as e:
        print(f"error: migration failed: {e}")
        return 1


def cmd_eval_promote(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    suite_path = args.suite_result if args.suite_result.is_absolute() else (Path.cwd() / args.suite_result)
    if not suite_path.exists():
        print(f"error: suite result not found at {suite_path}")
        return 1
        
    baseline_dir = repo_root / "evals" / "baselines"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    
    target = baseline_dir / f"{args.tag}.json"
    target.write_text(suite_path.read_text(encoding="utf-8"), encoding="utf-8")
    
    print(f"Promoted {suite_path.name} to baseline: {target.relative_to(repo_root)}")
    return 0


def cmd_eval_regression(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    baseline_path = args.baseline
    if not baseline_path:
        baseline_path = repo_root / "evals" / "baselines" / "gold.json"
    
    if not baseline_path.exists():
        print(f"error: baseline not found at {baseline_path}. Run `rws eval-suite --execute` then `rws eval-promote` first.")
        return 1
        
    print(f"Running regression test against baseline: {baseline_path.name}")
    
    # Run a temporary suite
    suite_args = argparse.Namespace(
        suite_id=None,
        execute=True,
        provider=args.provider,
        model=args.model,
        require_provider_ready=args.require_provider_ready,
        strict=True,
        compare_to=baseline_path,
        deliberate=True,
        scrutiny=True,
    )
    
    try:
        status = cmd_eval_suite(suite_args)
        if status == 0:
            print("\nSUCCESS: No regressions detected.")
        else:
            print("\nFAILURE: Regressions or failures detected. See comparison report.")
        return status
    except Exception as e:
        print(f"error: regression test failed: {e}")
        return 1


def cmd_generate_passport(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    provider = provider_from_name(args.provider)
    
    print(f"Generating style passport for: {args.name}...")
    try:
        result = generate_style_passport(
            repo_root=repo_root,
            provider=provider,
            model=args.model,
            style_name=args.name,
            description=args.description,
            examples=args.examples,
        )
        passport_id = save_generated_style(repo_root, result)
        print(f"Success! Generated style '{passport_id}'.")
        print(f"- Passport: styles/passports/{passport_id}.yml")
        print(f"- Prompt:   ClaudeStyles/{passport_id}-style.md")
        print(f"- Manifest updated.")
        return 0
    except Exception as e:
        print(f"error: failed to generate style: {e}")
        return 1


def cmd_apply_resolution(args: argparse.Namespace) -> int:
    """Apply human review overrides from resolution.json to council decisions."""
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    res_path = getattr(args, "resolution", None) or (run_dir / "resolution.json")

    if not res_path.exists():
        print(f"error: resolution.json not found at {res_path}")
        return 1

    resolution = json.loads(res_path.read_text(encoding="utf-8"))
    overrides = resolution.get("overrides", [])

    from .resolution import apply_resolution
    try:
        updated_count = apply_resolution(run_dir, overrides)
        print(f"Success: Applied {updated_count} human resolution(s) to council decisions.")
        return 0
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}")
        return 1


def cmd_finalize(args: argparse.Namespace) -> int:
    """Produce the final philological manuscript by merging revisions and resolutions."""
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    repo_root = repo_root_from()

    from .resolution import write_final_manuscript
    try:
        final_path = write_final_manuscript(run_dir)
        print(f"Success: Final manuscript written to {final_path.relative_to(repo_root)}")
        return 0
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}")
        return 1


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume a failed or interrupted run from the last completed step."""
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    
    if not run_dir.exists():
        print(f"error: run directory {run_dir} not found")
        return 1
        
    db = Database(repo_root)
    run_id = run_dir.name
    run_data = db.get_run(run_id)
    
    if not run_data:
        print(f"error: run {run_id} not found in database. Cannot resume.")
        return 1
        
    print(f"Resuming run {run_id}...")
    
    # Reconstruct args from config_json
    config = json.loads(run_data.get("config_json", "{}"))
    if not config:
        print("warning: no config_json found in database. Reconstructing minimal args.")
        config = {
            "provider": run_data["provider"],
            "model": run_data.get("model"),
            "profile": run_data.get("profile", "researcher"),
            "execute": True, # Resuming usually implies execution
        }
    
    # Override with CLI args if provided (though resume has few args)
    if getattr(args, "execute", False):
        config["execute"] = True
    
    resumed_args = argparse.Namespace(**config)
    
    manifest = load_manifest(repo_root)
    model_policy = load_model_policy(repo_root)
    
    return _execute_run_pipeline(repo_root, run_dir, resumed_args, manifest, model_policy)


def cmd_generate_styleguide(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    print("Generating Stylebook...")
    try:
        content = generate_stylebook_markdown(repo_root)
        path = save_stylebook(repo_root, content, args.output)
        print(f"Success! Stylebook saved to: {path.relative_to(repo_root)}")
        return 0
    except Exception as e:
        print(f"error: failed to generate styleguide: {e}")
        return 1


def _interactive_council_review(repo_root: Path, council_path: Path) -> None:
    """Interactively review council decisions in the console."""
    council = json.loads(council_path.read_text(encoding="utf-8"))
    decisions = council.get("decisions", [])
    if not decisions:
        return

    # Load findings for context
    findings_map = {}
    for review_rel in council.get("review_files", []):
        review = json.loads((repo_root / str(review_rel)).read_text(encoding="utf-8"))
        for f in review.get("findings", []):
            findings_map[f["id"]] = f

    print("\n--- Interactive Council Review ---")
    print("Commands: [y]es/accept, [n]o/reject, [i]nformational, [s]kip/keep original, [a]ccept all, [q]uit")
    
    accept_all = False
    new_decisions = []
    
    for decision in decisions:
        fid = decision["finding_id"]
        finding = findings_map.get(fid, {})
        
        if accept_all:
            new_decisions.append(decision)
            continue
            
        print(f"\nFinding: {fid}")
        print(f"Style:   {finding.get('style_id', 'unknown')}")
        print(f"Type:    {finding.get('type', 'unknown')}")
        print(f"Comment: {finding.get('finding', '')}")
        print(f"Suggest: {finding.get('suggestion', '')}")
        print(f"Council Decision: {decision['status']} (Reason: {decision['reason']})")
        
        while True:
            choice = input("Your decision? [y/n/i/s/a/q]: ").lower().strip()
            if choice == 'y':
                decision['status'] = 'accepted'
                break
            elif choice == 'n':
                decision['status'] = 'rejected'
                break
            elif choice == 'i':
                decision['status'] = 'informational'
                break
            elif choice == 's':
                # Keep what council decided
                break
            elif choice == 'a':
                accept_all = True
                break
            elif choice == 'q':
                print("Aborting interactive review. Keeping previous decisions.")
                return
            else:
                print("Invalid choice.")
        
        new_decisions.append(decision)

    council["decisions"] = new_decisions
    council_path.write_text(json.dumps(council, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nCouncil decisions updated.")


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


def cmd_councils(_: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    manifest = load_manifest(repo_root)
    if not manifest.councils:
        print("No councils defined in styles/manifest.yml.")
        return 0
    mvp = tuple(manifest.mvp_style_ids)
    for name, style_ids in manifest.councils:
        default_marker = "  (= default / --mvp)" if style_ids == mvp else ""
        print(f"{name}{default_marker}")
        for style_id in style_ids:
            print(f"  - {style_id}")
    print("\nUse: rws run <doc> --council <name>")
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
    repeat = getattr(args, "repeat", 1) or 1
    if repeat > 1:
        aggregate = run_eval_repeat(
            repo_root=repo_root,
            case_id=args.case,
            provider_name=args.provider,
            model=args.model,
            repeat=repeat,
            aggregate_id=getattr(args, "aggregate_id", None),
            deliberate=args.deliberate,
            use_routes=getattr(args, "routes", False),
        )
        case = aggregate.data["cases"][0]
        print(f"created {aggregate.aggregate_dir.relative_to(repo_root)}")
        print(f"eval aggregate {aggregate.result_path.relative_to(repo_root)}")
        print(f"eval aggregate report {aggregate.report_path.relative_to(repo_root)}")
        print(f"repeat: {aggregate.data['repeat']}")
        print(f"pass-rate: {case['pass_count']}/{case['repeat']} ({case['pass_rate']})")
        print(f"detection-rate: {case['detection_count']}/{case['repeat']} ({case['detection_rate']})")
        return 0
    result = run_eval_case(
        repo_root=repo_root,
        case_id=args.case,
        provider_name=args.provider,
        model=args.model,
        run_id=args.run_id,
        deliberate=args.deliberate,
        use_routes=getattr(args, "routes", False),
    )
    print(f"created {result.run_dir.relative_to(repo_root)}")
    print(f"eval result {result.result_path.relative_to(repo_root)}")
    return 0


def cmd_eval_suite(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    if args.require_provider_ready:
        _require_provider_ready(args.provider)
    repeat = getattr(args, "repeat", 1) or 1
    if repeat > 1:
        aggregate = run_eval_suite_repeat(
            repo_root=repo_root,
            provider_name=args.provider,
            model=args.model,
            repeat=repeat,
            aggregate_id=getattr(args, "aggregate_id", None),
            deliberate=args.deliberate,
            use_routes=getattr(args, "routes", False),
        )
        print(f"created {aggregate.aggregate_dir.relative_to(repo_root)}")
        print(f"eval aggregate {aggregate.result_path.relative_to(repo_root)}")
        print(f"eval aggregate report {aggregate.report_path.relative_to(repo_root)}")
        print(f"repeat: {aggregate.data['repeat']}")
        print(f"cases: {aggregate.data['case_count']}")
        print(f"mean pass-rate: {aggregate.data['mean_pass_rate']}")
        print(f"mean detection-rate: {aggregate.data['mean_detection_rate']}")
        return 0
    result = run_eval_suite(
        repo_root=repo_root,
        provider_name=args.provider,
        model=args.model,
        suite_id=args.suite_id,
        deliberate=args.deliberate,
        use_routes=getattr(args, "routes", False),
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
    if args.strict:
        if args.compare_to:
            if comparison_data is not None and _eval_comparison_has_regression(comparison_data):
                return 1
        elif int(data.get("failed_count", 0)) > 0:
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
            profile=args.profile,
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
    council = getattr(args, "council", None)
    if council:
        if council not in manifest.council_names():
            available = ", ".join(manifest.council_names()) or "(none defined)"
            raise ValueError(f"unknown council {council!r}; available: {available}")
        style_ids = list(manifest.resolve_council(council))
        if not style_ids:
            raise ValueError(f"council {council!r} is defined but empty")
    elif getattr(args, "mvp", False):
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
    manifest = load_manifest(repo_root)
    feedback = None
    if args.feedback:
        feedback_path = args.feedback if args.feedback.is_absolute() else (Path.cwd() / args.feedback)
        if feedback_path.exists():
            feedback = json.loads(feedback_path.read_text(encoding="utf-8"))

    bundle = create_council_bundle(
        repo_root=repo_root,
        run_dir=run_dir,
        manifest=manifest,
        verification_feedback=feedback,
        profile=args.profile,
    )
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


def cmd_deliberate(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    manifest = load_manifest(repo_root)
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    style_ids = _selected_style_ids(args, manifest)
    if args.execute and args.require_provider_ready:
        _require_provider_ready(args.provider)

    for style_id in style_ids:
        bundle = create_deliberation_bundle(
            repo_root=repo_root,
            run_dir=run_dir,
            style_id=style_id,
            manifest=manifest,
            profile=args.profile,
        )
        print(f"created {bundle.deliberation_json.relative_to(repo_root)}")
        if args.execute:
            execute_deliberation_artifact(
                repo_root=repo_root,
                delib_path=bundle.deliberation_json,
                provider=provider_from_name(args.provider),
                model=args.model,
            )
            print(f"completed {bundle.deliberation_json.relative_to(repo_root)}")
    return 0


def cmd_scrutiny(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    if args.execute and args.require_provider_ready:
        _require_provider_ready(args.provider)
    bundle = create_scrutiny_bundle(repo_root=repo_root, run_dir=run_dir)
    print(f"created {bundle.scrutiny_json.relative_to(repo_root)}")
    if args.execute:
        execute_scrutiny_artifact(
            repo_root=repo_root,
            scrutiny_path=bundle.scrutiny_json,
            provider=provider_from_name(args.provider),
            model=args.model,
        )
        print(f"completed {bundle.scrutiny_json.relative_to(repo_root)}")
    return 0


def cmd_assess(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    if args.execute and args.require_provider_ready:
        _require_provider_ready(args.provider)
    bundle = create_impact_bundle(repo_root=repo_root, run_dir=run_dir)
    print(f"created {bundle.impact_json.relative_to(repo_root)}")
    if args.execute:
        execute_impact_artifact(
            repo_root=repo_root,
            impact_path=bundle.impact_json,
            provider=provider_from_name(args.provider),
            model=args.model,
        )
        print(f"completed {bundle.impact_json.relative_to(repo_root)}")
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


def cmd_council_summary(args: argparse.Namespace) -> int:
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    print(render_council_summary(load_council_summary(run_dir)))
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


def cmd_journals(_: argparse.Namespace) -> int:
    from .journals import list_journal_presets, load_journal_preset

    repo_root = repo_root_from()
    ids = list_journal_presets(repo_root)
    if not ids:
        print("no journal presets found in knowledge/journals/")
        return 0
    for journal_id in ids:
        preset = load_journal_preset(repo_root, journal_id) or {}
        name = preset.get("name", "")
        limit = preset.get("max_chars")
        limit_str = f", ≤{limit} знаков" if limit else ""
        print(f"{journal_id:14} {name}{limit_str}")
    return 0


def cmd_project_set_journal(args: argparse.Namespace) -> int:
    from .journals import list_journal_presets, load_journal_preset
    from .project import set_journal_profile

    repo_root = repo_root_from()
    preset = load_journal_preset(repo_root, args.journal_id)
    if preset is None:
        available = ", ".join(list_journal_presets(repo_root)) or "(none)"
        print(f"error: unknown journal '{args.journal_id}'. Available: {available}")
        return 1

    project_dir = args.project_dir if args.project_dir.is_absolute() else (Path.cwd() / args.project_dir)
    context_path = set_journal_profile(project_dir, preset)
    print(f"set journal profile '{preset.get('name', args.journal_id)}' in {context_path}")
    return 0


def cmd_corpus_status(_: argparse.Namespace) -> int:
    from .corpus import CorpusManager

    stats = CorpusManager(repo_root_from()).stats()
    print(f"corpus dir: {stats['corpus_dir']}")
    if not stats["corpus_dir_exists"]:
        print("  (not found — set RWS_OFFLINE/RWS_CORPUS_DIR or add the private corpus repo)")
    print(f"available .txt files: {len(stats['available_txt'])}")
    for name in stats["available_txt"]:
        print(f"  - {name}")
    print(f"indexed files: {stats['indexed_files']}")
    print(f"indexed segments: {stats['indexed_segments']}")
    if stats["available_txt"] and stats["indexed_files"] < len(stats["available_txt"]):
        print("run `rws corpus-ingest` to index the corpus.")
    return 0


def cmd_corpus_ingest(args: argparse.Namespace) -> int:
    from .corpus import CorpusManager
    from .db import Database

    repo_root = repo_root_from()
    Database(repo_root)  # ensure FTS5 tables exist
    cm = CorpusManager(repo_root)
    if not cm.corpus_dir.exists():
        print(f"error: corpus directory not found: {cm.corpus_dir}")
        print("set RWS_CORPUS_DIR or clone the private RuWritingStyles-corpus repo alongside this one.")
        return 1
    cm.ingest_all(force=args.force)
    stats = cm.stats()
    print(f"indexed {stats['indexed_files']} file(s), {stats['indexed_segments']} segment(s) from {cm.corpus_dir}")
    return 0


def cmd_corpus_search(args: argparse.Namespace) -> int:
    from .corpus import CorpusManager

    results = CorpusManager(repo_root_from()).search(args.query, limit=args.limit)
    if getattr(args, "as_json", False):
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    if not results:
        print("no matches (is the corpus indexed? run `rws corpus-ingest`)")
        return 0
    for r in results:
        head = f"{r.get('author') or '?'} {r.get('year') or ''}".strip()
        print(f"[{head}] {r['file']}")
        print(f"  {r.get('snippet') or ''}")
    return 0


def cmd_lint_translit(args: argparse.Namespace) -> int:
    from .journals import load_journal_preset
    from .translit_lint import lint_text, load_sanskrit_terms

    repo_root = repo_root_from()
    input_path = args.input if args.input.is_absolute() else (Path.cwd() / args.input)
    text = read_document(input_path.resolve())
    profile = None
    journal_id = getattr(args, "journal", None)
    if journal_id:
        profile = load_journal_preset(repo_root, journal_id)
        if profile is None:
            print(f"error: unknown journal '{journal_id}'")
            return 1
    result = lint_text(text, load_sanskrit_terms(repo_root), profile)

    if getattr(args, "as_json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        findings = result["findings"]
        summary = result["summary"]
        print(f"segments checked: {summary['segments_checked']}")
        print(f"schemes detected: {', '.join(summary['schemes_detected']) or 'none'}")
        if not findings:
            print("no transliteration findings")
        for f in findings:
            fragment = f" [{f['fragment']}]" if f.get("fragment") else ""
            print(f"{f['severity']:8} {f['span_id']:6} {f['type']}: {f['message']}{fragment}")

    if getattr(args, "strict", False) and result["findings"]:
        return 1
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


def cmd_validate_eval_aggregate(args: argparse.Namespace) -> int:
    aggregate = args.aggregate if args.aggregate.is_absolute() else (Path.cwd() / args.aggregate)
    result = validate_eval_aggregate_file(aggregate)
    if result.ok:
        print("OK eval aggregate artifact valid")
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
    try:
        db = Database(repo_root)
        run_id = run_dir.name
        report_path = write_run_report(run_dir)
        html_path = write_html_report(run_dir)
        from .latex import write_latex_report
        write_latex_report(run_dir, db.get_run(run_id))
        from .bibtex import write_bibtex
        write_bibtex(run_dir, repo_root)
        print(f"updated {report_path.relative_to(repo_root)}")
        print(f"updated {html_path.relative_to(repo_root)}")
    except Exception as e:
        print(f"error generating reports: {e}")
        import traceback
        traceback.print_exc()
        raise


def cmd_eval_benchmark(args: argparse.Namespace) -> int:
    repo_root = repo_root_from()
    models = args.models
    provider = args.provider
    
    print(f"Starting benchmark for {len(models)} models on {provider}...")
    
    suite_paths = []
    
    for model in models:
        print(f"\n>>> Benchmarking Model: {model}")
        suite_id = f"benchmark-{model.replace('.', '-').lower()}"
        
        suite_args = argparse.Namespace(
            suite_id=suite_id,
            execute=True,
            provider=provider,
            model=model,
            require_provider_ready=False,
            strict=False,
            compare_to=None,
            deliberate=True,
            scrutiny=True,
        )
        
        try:
            status = cmd_eval_suite(suite_args)
            if status == 0:
                suite_paths.append(repo_root / "runs" / suite_id / "eval-suite-result.json")
        except Exception as e:
            print(f"error: failed to benchmark {model}: {e}")
            
    if suite_paths:
        from .evals import generate_leaderboard_report
        report_path = generate_leaderboard_report(repo_root, suite_paths)
        print(f"\nBenchmark Complete! Leaderboard report: {report_path.relative_to(repo_root)}")
        return 0
        
    return 1


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
