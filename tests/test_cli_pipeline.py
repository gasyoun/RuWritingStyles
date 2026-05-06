from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ruwritingstyles.cli import main
from ruwritingstyles.config import load_model_routes
from ruwritingstyles.evals import load_eval_cases
from ruwritingstyles.findings import load_finding_summaries, render_finding_summaries
from ruwritingstyles.providers import _extract_anthropic_text, _extract_gemini_text, _is_retryable_status
from ruwritingstyles.segment import normalize_document, segment_markdown


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


class ModelPolicyTests(unittest.TestCase):
    def test_model_routes_load_from_policy(self) -> None:
        routes = load_model_routes(ROOT)
        route = next(route for route in routes if route.provider == "openai" and route.task == "style_review")
        self.assertEqual(route.model, "gpt-5.5")
        self.assertEqual(route.mode_name, "reasoning")
        self.assertEqual(route.mode_value, "medium")
        self.assertEqual(main(["model-routes", "--provider", "openai", "--task", "style_review"]), 0)


class EvalManifestTests(unittest.TestCase):
    def test_eval_manifest_loads_demo_case(self) -> None:
        cases = load_eval_cases(ROOT)
        self.assertEqual(cases[0].case_id, "pseudo-etymology")
        self.assertTrue(cases[0].input_path.exists())
        self.assertIn("zalizniak-zametki", cases[0].default_styles)
        self.assertEqual(main(["eval-list"]), 0)


class CliPipelineTests(unittest.TestCase):
    run_dir = ROOT / "runs" / "unittest-readme"
    executed_run_dir = ROOT / "runs" / "unittest-readme-executed"
    demo_run_dir = ROOT / "runs" / "unittest-demo"

    def tearDown(self) -> None:
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)
        if self.executed_run_dir.exists():
            shutil.rmtree(self.executed_run_dir)
        if self.demo_run_dir.exists():
            shutil.rmtree(self.demo_run_dir)

    def test_full_offline_run_creates_expected_artifacts(self) -> None:
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

        exit_code = main(["run", "README.md", "--run-id", "unittest-readme"])
        self.assertEqual(exit_code, 0)

        self.assertTrue((self.run_dir / "segments.json").exists())
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
        provider_log_lines = (self.executed_run_dir / "provider.log.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(provider_log_lines), 6)
        provider_log_entry = json.loads(provider_log_lines[0])
        self.assertEqual(provider_log_entry["provider"], "mock")
        self.assertEqual(provider_log_entry["status"], "completed")
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
        self.assertEqual(main(["export", str(self.executed_run_dir)]), 0)
        bundle_path = self.executed_run_dir / "unittest-readme-executed-bundle.zip"
        self.assertTrue(bundle_path.exists())
        with ZipFile(bundle_path) as archive:
            names = set(archive.namelist())
        self.assertIn("unittest-readme-executed/report.md", names)
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


if __name__ == "__main__":
    unittest.main()
