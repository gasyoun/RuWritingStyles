from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ruwritingstyles.cli import main
from ruwritingstyles.config import load_model_routes
from ruwritingstyles.council_summary import load_council_summary, render_council_summary
from ruwritingstyles.document import DocumentInputError
from ruwritingstyles.evals import load_eval_cases
from ruwritingstyles.findings import load_finding_summaries, render_finding_summaries
from ruwritingstyles.providers import (
    ProviderRetryTelemetry,
    _extract_anthropic_text,
    _extract_gemini_text,
    _is_retryable_status,
    _retry_delay_from_headers,
)
from ruwritingstyles.provider_log import load_provider_log, render_provider_log
from ruwritingstyles.provider_status import provider_statuses, provider_statuses_json, render_provider_statuses
from ruwritingstyles.schema_validation import validate_json_schema
from ruwritingstyles.segment import SegmentOptions, normalize_document, read_document, segment_markdown
from ruwritingstyles.validation import _load_schema_store, validate_provider_status_file


class SegmentTests(unittest.TestCase):
    def test_segment_markdown_headings_paragraphs_and_code(self) -> None:
        text = normalize_document(
            """# Title

First paragraph.

```text
code
```

## Next
Second paragraph.
"""
        )

        segments = segment_markdown(text)
        self.assertEqual([segment.segment_type for segment in segments], ["heading", "paragraph", "code", "heading", "paragraph"])
        self.assertEqual([segment.span_id for segment in segments], ["h001", "p002", "c003", "h004", "p005"])
        self.assertEqual(segments[1].metrics["sentence_count"], 1)

    def test_normalization_preserves_russian_philological_marks(self) -> None:
        text = normalize_document("Ёлка и сло\u0301во ѣсть.\r\n\r\n\r\nСледующая строка.\t \n")
        self.assertIn("Ёлка", text)
        self.assertIn("сло\u0301во", text)
        self.assertIn("ѣсть", text)
        self.assertNotIn("\r", text)
        self.assertNotIn("\t \n", text)

    def test_segment_metrics_count_cyrillic_and_historical_letters(self) -> None:
        text = normalize_document("Сло\u0301во, ёлка и ѣсть. Latin test.")
        segment = segment_markdown(text)[0]
        self.assertEqual(segment.metrics["word_count"], 6)
        self.assertEqual(segment.metrics["cyrillic_word_count"], 4)
        self.assertEqual(segment.metrics["latin_word_count"], 2)
        self.assertEqual(segment.metrics["yo_count"], 1)
        self.assertEqual(segment.metrics["historical_cyrillic_count"], 1)
        self.assertEqual(segment.metrics["accent_mark_count"], 1)

    def test_long_paragraphs_split_on_sentence_boundaries(self) -> None:
        text = normalize_document("Первое предложение достаточно длинное. Второе предложение тоже достаточно длинное.")
        segments = segment_markdown(text, SegmentOptions(max_segment_chars=45))
        self.assertEqual([segment.segment_type for segment in segments], ["paragraph", "paragraph"])
        self.assertEqual([segment.span_id for segment in segments], ["p001", "p002"])
        self.assertTrue(all(len(segment.text) <= 45 for segment in segments))

    def test_read_document_accepts_cp1251_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.txt"
            path.write_bytes("Простой русский текст.".encode("cp1251"))
            self.assertEqual(read_document(path), "Простой русский текст.")

    def test_read_document_rejects_binary_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "binary.txt"
            path.write_bytes(b"\x00\x01\x02\x03" * 16)
            with self.assertRaises(DocumentInputError):
                read_document(path)


class ProviderParsingTests(unittest.TestCase):
    def test_provider_text_extractors(self) -> None:
        gemini = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": '{"ok": '},
                            {"text": "true}"},
                        ]
                    }
                }
            ]
        }
        anthropic = {
            "content": [
                {"type": "text", "text": '{"ok": '},
                {"type": "text", "text": "true}"},
            ]
        }
        self.assertEqual(_extract_gemini_text(gemini), '{"ok": true}')
        self.assertEqual(_extract_anthropic_text(anthropic), '{"ok": true}')
        self.assertTrue(_is_retryable_status(429))
        self.assertFalse(_is_retryable_status(400))

    def test_provider_retry_telemetry_records_attempts(self) -> None:
        telemetry = ProviderRetryTelemetry()
        telemetry.record("429", 1.25)
        telemetry.record("503", 2.0)
        self.assertEqual(
            telemetry.to_json(),
            {
                "retry_count": 2,
                "retry_delay_seconds": 3.25,
                "retry_statuses": ["429", "503"],
            },
        )

    def test_provider_retry_delay_uses_rate_limit_headers(self) -> None:
        now = datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(_retry_delay_from_headers({"Retry-After": "2.5"}, 1.0, now=now), 2.5)
        self.assertEqual(
            _retry_delay_from_headers(
                {
                    "x-ratelimit-remaining-requests": "0",
                    "x-ratelimit-reset-requests": "1s",
                    "x-ratelimit-remaining-tokens": "100",
                    "x-ratelimit-reset-tokens": "6m0s",
                },
                1.0,
                now=now,
            ),
            1.0,
        )
        self.assertEqual(
            _retry_delay_from_headers(
                {
                    "anthropic-ratelimit-tokens-remaining": "0",
                    "anthropic-ratelimit-tokens-reset": "2026-05-07T10:00:05Z",
                },
                1.0,
                now=now,
            ),
            5.0,
        )


class ModelPolicyTests(unittest.TestCase):
    def test_model_routes_load_from_policy(self) -> None:
        routes = load_model_routes(ROOT)
        route = next(route for route in routes if route.provider == "openai" and route.task == "style_review")
        self.assertEqual(route.model, "gpt-5.5")
        self.assertEqual(route.mode_name, "reasoning")
        self.assertEqual(route.mode_value, "medium")
        self.assertEqual(main(["model-routes", "--provider", "openai", "--task", "style_review"]), 0)

    def test_provider_statuses_do_not_expose_keys(self) -> None:
        statuses = provider_statuses(
            {
                "OPENAI_API_KEY": "sk-secret",
                "RWS_OPENAI_MODEL": "gpt-test",
            }
        )
        openai = next(status for status in statuses if status.provider == "openai")
        google = next(status for status in statuses if status.provider == "google")
        self.assertTrue(openai.ready)
        self.assertEqual(openai.configured_env, "OPENAI_API_KEY")
        self.assertEqual(openai.model, "gpt-test")
        self.assertFalse(google.ready)
        rendered = render_provider_statuses(statuses, provider="openai")
        self.assertIn("ready: yes", rendered)
        self.assertIn("configured_env: OPENAI_API_KEY", rendered)
        self.assertNotIn("sk-secret", rendered)
        rendered_json = provider_statuses_json(statuses, provider="openai")
        self.assertEqual(rendered_json[0]["configured_env"], "OPENAI_API_KEY")
        self.assertNotIn("sk-secret", json.dumps(rendered_json))
        schema_store = _load_schema_store(ROOT, [])
        self.assertEqual(
            validate_json_schema(
                rendered_json,
                schema_store["provider-status.schema.json"],
                schema_store=schema_store,
            ),
            (),
        )
        status_path = ROOT / "runs" / "unittest-provider-status.json"
        status_path.parent.mkdir(exist_ok=True)
        status_path.write_text(json.dumps(rendered_json), encoding="utf-8")
        self.assertTrue(validate_provider_status_file(status_path).ok)
        self.assertEqual(main(["validate-provider-status", str(status_path)]), 0)
        status_path.unlink()
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(main(["provider-status", "--provider", "mock", "--strict"]), 0)
            self.assertEqual(main(["provider-status", "--provider", "mock", "--json"]), 0)
            self.assertEqual(main(["provider-status", "--provider", "openai", "--strict"]), 1)


class SchemaValidationTests(unittest.TestCase):
    def test_schema_validator_reports_required_and_nested_errors(self) -> None:
        schema = {
            "type": "object",
            "required": ["name", "items"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["score"],
                        "properties": {"score": {"type": "number", "minimum": 0, "maximum": 1}},
                    },
                },
            },
        }
        messages = validate_json_schema({"name": "", "items": [{"score": 2}], "extra": True}, schema)
        self.assertIn("$.extra: additional property is not allowed", messages)
        self.assertIn("$.name: length must be at least 1", messages)
        self.assertIn("$.items[0].score: must be <= 1", messages)


class EvalManifestTests(unittest.TestCase):
    def test_eval_manifest_loads_demo_case(self) -> None:
        cases = load_eval_cases(ROOT)
        self.assertEqual({case.case_id for case in cases}, {"pseudo-etymology", "source-claim", "register-shift"})
        self.assertEqual(cases[0].case_id, "pseudo-etymology")
        self.assertTrue(cases[0].input_path.exists())
        self.assertIn("zalizniak-zametki", cases[0].default_styles)
        self.assertEqual(cases[0].min_required_matches, 1)
        self.assertIn("unsupported_etymology", cases[0].required_finding_types)
        self.assertEqual(cases[0].max_changed_line_ratio, 0.75)
        self.assertEqual(cases[0].max_char_delta_ratio, 0.5)
        self.assertEqual(main(["eval-list"]), 0)


class CliPipelineTests(unittest.TestCase):
    run_dir = ROOT / "runs" / "unittest-readme"
    executed_run_dir = ROOT / "runs" / "unittest-readme-executed"
    demo_run_dir = ROOT / "runs" / "unittest-demo"
    eval_run_dir = ROOT / "runs" / "unittest-eval-pseudo"
    eval_suite_dir = ROOT / "runs" / "unittest-suite"
    eval_suite_candidate_dir = ROOT / "runs" / "unittest-suite-candidate"
    eval_suite_case_run_dir = ROOT / "runs" / "unittest-suite-pseudo-etymology"
    eval_suite_source_run_dir = ROOT / "runs" / "unittest-suite-source-claim"
    eval_suite_register_run_dir = ROOT / "runs" / "unittest-suite-register-shift"
    eval_suite_candidate_case_run_dir = ROOT / "runs" / "unittest-suite-candidate-pseudo-etymology"
    eval_suite_candidate_source_run_dir = ROOT / "runs" / "unittest-suite-candidate-source-claim"
    eval_suite_candidate_register_run_dir = ROOT / "runs" / "unittest-suite-candidate-register-shift"
    openai_missing_dir = ROOT / "runs" / "unittest-openai-missing"

    def tearDown(self) -> None:
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)
        if self.executed_run_dir.exists():
            shutil.rmtree(self.executed_run_dir)
        if self.demo_run_dir.exists():
            shutil.rmtree(self.demo_run_dir)
        if self.eval_run_dir.exists():
            shutil.rmtree(self.eval_run_dir)
        if self.eval_suite_dir.exists():
            shutil.rmtree(self.eval_suite_dir)
        if self.eval_suite_candidate_dir.exists():
            shutil.rmtree(self.eval_suite_candidate_dir)
        if self.eval_suite_case_run_dir.exists():
            shutil.rmtree(self.eval_suite_case_run_dir)
        if self.eval_suite_source_run_dir.exists():
            shutil.rmtree(self.eval_suite_source_run_dir)
        if self.eval_suite_register_run_dir.exists():
            shutil.rmtree(self.eval_suite_register_run_dir)
        if self.eval_suite_candidate_case_run_dir.exists():
            shutil.rmtree(self.eval_suite_candidate_case_run_dir)
        if self.eval_suite_candidate_source_run_dir.exists():
            shutil.rmtree(self.eval_suite_candidate_source_run_dir)
        if self.eval_suite_candidate_register_run_dir.exists():
            shutil.rmtree(self.eval_suite_candidate_register_run_dir)
        if self.openai_missing_dir.exists():
            shutil.rmtree(self.openai_missing_dir)

    def test_full_offline_run_creates_expected_artifacts(self) -> None:
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

        exit_code = main(["run", "README.md", "--run-id", "unittest-readme"])
        self.assertEqual(exit_code, 0)

        self.assertTrue((self.run_dir / "segments.json").exists())
        self.assertTrue((self.run_dir / "summary.html").exists())
        self.assertTrue((self.run_dir / "council.json").exists())
        self.assertTrue((self.run_dir / "revision.json").exists())
        self.assertTrue((self.run_dir / "verification.json").exists())

        reviews = sorted((self.run_dir / "reviews").glob("*.review.json"))
        prompts = sorted((self.run_dir / "reviews").glob("*.prompt.md"))
        self.assertEqual(len(reviews), 3)
        self.assertEqual(len(prompts), 3)

        segments = json.loads((self.run_dir / "segments.json").read_text(encoding="utf-8"))
        self.assertEqual(segments["segment_count"], len(segments["segments"]))
        self.assertEqual(segments["segments"][0]["span_id"], "h001")

        verification = json.loads((self.run_dir / "verification.json").read_text(encoding="utf-8"))
        self.assertEqual(verification["status"], "prompt_ready")

        self.assertEqual(main(["validate-run", str(self.run_dir)]), 0)

    def test_provider_preflight_stops_before_run_creation(self) -> None:
        if self.openai_missing_dir.exists():
            shutil.rmtree(self.openai_missing_dir)

        with patch.dict("os.environ", {}, clear=True):
            exit_code = main(
                [
                    "run",
                    "README.md",
                    "--run-id",
                    "unittest-openai-missing",
                    "--execute",
                    "--provider",
                    "openai",
                    "--require-provider-ready",
                ]
            )
        self.assertEqual(exit_code, 1)
        self.assertFalse(self.openai_missing_dir.exists())

    def test_full_mock_executed_run_updates_artifacts(self) -> None:
        if self.executed_run_dir.exists():
            shutil.rmtree(self.executed_run_dir)

        exit_code = main(
            [
                "run",
                "README.md",
                "--run-id",
                "unittest-readme-executed",
                "--execute",
                "--provider",
                "mock",
            ]
        )
        self.assertEqual(exit_code, 0)

        reviews = sorted((self.executed_run_dir / "reviews").glob("*.review.json"))
        self.assertEqual(len(reviews), 3)
        for path in reviews:
            review = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(review["status"], "completed")
            self.assertEqual(len(review["findings"]), 1)
            self.assertEqual(review["findings"][0]["span_id"], "p002")

        council = json.loads((self.executed_run_dir / "council.json").read_text(encoding="utf-8"))
        self.assertEqual(council["status"], "completed")
        self.assertEqual(len(council["decisions"]), 3)
        council_summary = render_council_summary(load_council_summary(self.executed_run_dir))
        self.assertIn("decisions: 3", council_summary)
        self.assertIn("status=informational", council_summary)
        self.assertEqual(main(["council-summary", str(self.executed_run_dir)]), 0)
        provider_log_lines = (self.executed_run_dir / "provider.log.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(provider_log_lines), 6)
        provider_log_entry = json.loads(provider_log_lines[0])
        self.assertEqual(provider_log_entry["provider"], "mock")
        self.assertEqual(provider_log_entry["status"], "completed")
        self.assertEqual(provider_log_entry["retry_count"], 0)
        self.assertEqual(provider_log_entry["retry_delay_seconds"], 0.0)
        self.assertEqual(provider_log_entry["retry_statuses"], [])
        provider_log_summary = render_provider_log(load_provider_log(self.executed_run_dir))
        self.assertIn("executions: 6", provider_log_summary)
        self.assertIn("retries: 0", provider_log_summary)
        self.assertEqual(main(["provider-log", str(self.executed_run_dir)]), 0)
        summaries = load_finding_summaries(self.executed_run_dir, span_id="p002")
        self.assertEqual(len(summaries), 3)
        self.assertIn("Mock provider placeholder finding", render_finding_summaries(summaries))
        self.assertEqual(main(["findings", str(self.executed_run_dir), "--span", "p002"]), 0)

        revision = json.loads((self.executed_run_dir / "revision.json").read_text(encoding="utf-8"))
        self.assertEqual(revision["status"], "completed")
        self.assertTrue((self.executed_run_dir / "revised.md").exists())
        self.assertTrue((self.executed_run_dir / "revision.diff").exists())
        self.assertEqual(main(["diff", str(self.executed_run_dir)]), 0)

        verification = json.loads((self.executed_run_dir / "verification.json").read_text(encoding="utf-8"))
        self.assertEqual(verification["status"], "needs_human_review")

        report = (self.executed_run_dir / "report.md").read_text(encoding="utf-8")
        self.assertIn("## Findings", report)
        self.assertIn("Mock provider placeholder finding", report)
        self.assertIn("## Provider Log", report)
        self.assertEqual(main(["report", str(self.executed_run_dir)]), 0)
        html_report = (self.executed_run_dir / "summary.html").read_text(encoding="utf-8")
        self.assertIn("Run Summary", html_report)
        self.assertIn("Findings By Span", html_report)
        self.assertIn("Mock provider placeholder finding", html_report)
        self.assertIn("Provider Log", html_report)
        self.assertEqual(main(["html-report", str(self.executed_run_dir)]), 0)
        self.assertEqual(main(["export", str(self.executed_run_dir)]), 0)
        bundle_path = self.executed_run_dir / "unittest-readme-executed-bundle.zip"
        self.assertTrue(bundle_path.exists())
        with ZipFile(bundle_path) as archive:
            names = set(archive.namelist())
        self.assertIn("unittest-readme-executed/report.md", names)
        self.assertIn("unittest-readme-executed/summary.html", names)
        self.assertIn("unittest-readme-executed/provider.log.jsonl", names)
        self.assertIn("unittest-readme-executed/revised.md", names)
        self.assertIn("unittest-readme-executed/revision.diff", names)
        self.assertIn("unittest-readme-executed/bundle-manifest.json", names)

        self.assertEqual(main(["validate-run", str(self.executed_run_dir)]), 0)

    def test_demo_document_runs_with_mock_provider(self) -> None:
        if self.demo_run_dir.exists():
            shutil.rmtree(self.demo_run_dir)

        exit_code = main(
            [
                "run",
                "examples/input/pseudo-etymology.md",
                "--run-id",
                "unittest-demo",
                "--execute",
                "--provider",
                "mock",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue((self.demo_run_dir / "revised.md").exists())
        self.assertEqual(main(["validate-run", str(self.demo_run_dir)]), 0)

    def test_eval_run_creates_eval_result(self) -> None:
        if self.eval_run_dir.exists():
            shutil.rmtree(self.eval_run_dir)

        exit_code = main(
            [
                "eval-run",
                "--case",
                "pseudo-etymology",
                "--provider",
                "mock",
                "--run-id",
                "unittest-eval-pseudo",
            ]
        )
        self.assertEqual(exit_code, 0)
        result = json.loads((self.eval_run_dir / "eval-result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["case_id"], "pseudo-etymology")
        self.assertEqual(result["provider"], "mock")
        self.assertEqual(result["finding_count"], 3)
        self.assertFalse(result["scoring"]["passed"])
        self.assertEqual(result["scoring"]["required_match_count"], 0)
        self.assertTrue(result["scoring"]["diff_within_limits"])
        self.assertEqual(result["diff_metrics"]["changed_line_ratio"], 0)
        self.assertEqual(result["diff_metrics"]["char_delta_ratio"], 0)
        self.assertTrue((self.eval_run_dir / "provider.log.jsonl").exists())
        self.assertEqual(main(["validate-run", str(self.eval_run_dir)]), 0)

    def test_eval_suite_runs_manifest_cases(self) -> None:
        if self.eval_suite_dir.exists():
            shutil.rmtree(self.eval_suite_dir)
        if self.eval_suite_case_run_dir.exists():
            shutil.rmtree(self.eval_suite_case_run_dir)

        exit_code = main(
            [
                "eval-suite",
                "--provider",
                "mock",
                "--suite-id",
                "unittest-suite",
            ]
        )
        self.assertEqual(exit_code, 0)
        result = json.loads((self.eval_suite_dir / "eval-suite-result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["suite_id"], "unittest-suite")
        self.assertEqual(result["case_count"], 3)
        self.assertEqual(result["failed_count"], 3)
        self.assertEqual({row["case_id"] for row in result["results"]}, {"pseudo-etymology", "source-claim", "register-shift"})
        report = (self.eval_suite_dir / "eval-suite-report.md").read_text(encoding="utf-8")
        self.assertIn("# Eval Suite: unittest-suite", report)
        self.assertIn("| pseudo-etymology | no |", report)
        self.assertIn("| source-claim | no |", report)
        self.assertIn("| register-shift | no |", report)
        self.assertTrue((self.eval_suite_case_run_dir / "eval-result.json").exists())
        self.assertTrue((self.eval_suite_source_run_dir / "eval-result.json").exists())
        self.assertTrue((self.eval_suite_register_run_dir / "eval-result.json").exists())
        self.assertEqual(main(["eval-status", str(self.eval_suite_dir)]), 0)
        self.assertEqual(main(["validate-eval-suite", str(self.eval_suite_dir)]), 0)
        comparison_path = self.eval_suite_dir / "comparison.md"
        comparison_json_path = self.eval_suite_dir / "comparison.json"
        self.assertEqual(
            main(
                [
                    "eval-compare",
                    str(self.eval_suite_dir),
                    str(self.eval_suite_dir),
                    "--output",
                    str(comparison_path),
                    "--json-output",
                    str(comparison_json_path),
                ]
            ),
            0,
        )
        self.assertIn("# Eval Suite Comparison", comparison_path.read_text(encoding="utf-8"))
        comparison = json.loads(comparison_json_path.read_text(encoding="utf-8"))
        self.assertEqual(comparison["case_count"], 3)
        self.assertEqual(comparison["pass_rate_delta"], 0.0)
        self.assertEqual(main(["eval-status", str(comparison_json_path)]), 0)
        schema_store = _load_schema_store(ROOT, [])
        self.assertEqual(
            validate_json_schema(
                comparison,
                schema_store["eval-suite-comparison.schema.json"],
                schema_store=schema_store,
            ),
            (),
        )
        self.assertEqual(main(["validate-eval-comparison", str(comparison_json_path)]), 0)
        self.assertEqual(main(["export-eval-suite", str(self.eval_suite_dir)]), 0)
        bundle_path = self.eval_suite_dir / "unittest-suite-bundle.zip"
        self.assertTrue(bundle_path.exists())
        with ZipFile(bundle_path) as archive:
            names = set(archive.namelist())
        self.assertIn("unittest-suite/bundle-manifest.json", names)
        self.assertIn("unittest-suite/eval-suite-result.json", names)
        self.assertIn("unittest-suite/eval-suite-report.md", names)
        self.assertIn("unittest-suite/comparison.md", names)
        self.assertIn("unittest-suite/comparison.json", names)
        self.assertIn("unittest-suite/cases/unittest-suite-pseudo-etymology/eval-result.json", names)
        self.assertIn("unittest-suite/cases/unittest-suite-pseudo-etymology/provider.log.jsonl", names)
        self.assertIn("unittest-suite/cases/unittest-suite-source-claim/eval-result.json", names)
        self.assertIn("unittest-suite/cases/unittest-suite-register-shift/eval-result.json", names)

    def test_eval_suite_can_compare_to_baseline(self) -> None:
        for path in [
            self.eval_suite_dir,
            self.eval_suite_candidate_dir,
            self.eval_suite_case_run_dir,
            self.eval_suite_source_run_dir,
            self.eval_suite_register_run_dir,
            self.eval_suite_candidate_case_run_dir,
            self.eval_suite_candidate_source_run_dir,
            self.eval_suite_candidate_register_run_dir,
        ]:
            if path.exists():
                shutil.rmtree(path)

        self.assertEqual(
            main(["eval-suite", "--provider", "mock", "--suite-id", "unittest-suite"]),
            0,
        )
        self.assertEqual(
            main(
                [
                    "eval-suite",
                    "--provider",
                    "mock",
                    "--suite-id",
                    "unittest-suite-candidate",
                    "--compare-to",
                    str(self.eval_suite_dir),
                ]
            ),
            0,
        )
        comparison_json = self.eval_suite_candidate_dir / "comparison.json"
        comparison_md = self.eval_suite_candidate_dir / "comparison.md"
        self.assertTrue(comparison_json.exists())
        self.assertTrue(comparison_md.exists())
        comparison = json.loads(comparison_json.read_text(encoding="utf-8"))
        self.assertEqual(comparison["pass_rate_delta"], 0.0)
        self.assertEqual(comparison["regressed"], [])
        self.assertEqual(main(["validate-eval-comparison", str(comparison_json)]), 0)

    def test_eval_compare_strict_returns_failure_on_regression(self) -> None:
        baseline_dir = ROOT / "runs" / "unittest-compare-baseline"
        candidate_dir = ROOT / "runs" / "unittest-compare-candidate"
        for path in [baseline_dir, candidate_dir]:
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True)
        baseline = {
            "suite_id": "unittest-compare-baseline",
            "provider": "mock",
            "model": "mock",
            "case_count": 1,
            "passed_count": 1,
            "failed_count": 0,
            "pass_rate": 1.0,
            "results": [
                {
                    "case_id": "pseudo-etymology",
                    "run_dir": "runs/unittest-suite-pseudo-etymology",
                    "result_path": "runs/unittest-suite-pseudo-etymology/eval-result.json",
                    "passed": True,
                    "finding_count": 3,
                    "verification_status": "needs_human_review",
                    "changed_line_ratio": 0.0,
                    "char_delta_ratio": 0.0,
                }
            ],
        }
        candidate = dict(baseline)
        candidate["suite_id"] = "unittest-compare-candidate"
        candidate["passed_count"] = 0
        candidate["failed_count"] = 1
        candidate["pass_rate"] = 0.0
        candidate["results"] = [dict(baseline["results"][0], passed=False)]
        (baseline_dir / "eval-suite-result.json").write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        (candidate_dir / "eval-suite-result.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        try:
            self.assertEqual(main(["eval-compare", str(baseline_dir), str(candidate_dir), "--strict"]), 1)
        finally:
            shutil.rmtree(baseline_dir)
            shutil.rmtree(candidate_dir)

    def test_eval_suite_strict_returns_failure_on_failed_cases(self) -> None:
        if self.eval_suite_dir.exists():
            shutil.rmtree(self.eval_suite_dir)
        if self.eval_suite_case_run_dir.exists():
            shutil.rmtree(self.eval_suite_case_run_dir)
        if self.eval_suite_source_run_dir.exists():
            shutil.rmtree(self.eval_suite_source_run_dir)
        if self.eval_suite_register_run_dir.exists():
            shutil.rmtree(self.eval_suite_register_run_dir)

        exit_code = main(
            [
                "eval-suite",
                "--provider",
                "mock",
                "--suite-id",
                "unittest-suite",
                "--strict",
            ]
        )
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
