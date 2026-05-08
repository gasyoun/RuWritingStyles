"""Unit tests for resolution.py, hooks.py, and context_builder.py (Sprint D)."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ruwritingstyles import hooks
from ruwritingstyles.resolution import apply_resolution, write_final_manuscript
from ruwritingstyles.context_builder import build_unified_context, build_long_artifact_preview


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_dir(tmp: Path) -> Path:
    run_dir = tmp / "test-run"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_council(run_dir: Path, decisions: list[dict]) -> None:
    (run_dir / "council.json").write_text(
        json.dumps({"run_id": "test-run", "decisions": decisions}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_revision(run_dir: Path, status: str = "completed", content: str = "Final text.") -> None:
    (run_dir / "revision.json").write_text(
        json.dumps(
            {"run_id": "test-run", "status": status, "revised_document": content},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# resolution.py tests
# ---------------------------------------------------------------------------

class ApplyResolutionTests(unittest.TestCase):

    def test_applies_override_status_and_comment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _make_run_dir(Path(tmp))
            _write_council(run_dir, [
                {"finding_id": "f-001", "status": "pending"},
                {"finding_id": "f-002", "status": "pending"},
            ])
            overrides = [
                {"finding_id": "f-001", "status": "accepted", "human_comment": "Good change."},
            ]
            updated = apply_resolution(run_dir, overrides)

            self.assertEqual(updated, 1)
            council = json.loads((run_dir / "council.json").read_text(encoding="utf-8"))
            d001 = next(d for d in council["decisions"] if d["finding_id"] == "f-001")
            self.assertEqual(d001["status"], "accepted")
            self.assertEqual(d001["human_resolution"], "Good change.")
            # f-002 untouched
            d002 = next(d for d in council["decisions"] if d["finding_id"] == "f-002")
            self.assertEqual(d002["status"], "pending")

    def test_empty_overrides_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _make_run_dir(Path(tmp))
            _write_council(run_dir, [{"finding_id": "f-001", "status": "pending"}])
            with self.assertRaises(ValueError):
                apply_resolution(run_dir, [])

    def test_missing_council_json_raises_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _make_run_dir(Path(tmp))
            with self.assertRaises(FileNotFoundError):
                apply_resolution(run_dir, [{"finding_id": "f-001", "status": "accepted"}])

    def test_override_without_comment_does_not_write_human_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _make_run_dir(Path(tmp))
            _write_council(run_dir, [{"finding_id": "f-001", "status": "pending"}])
            apply_resolution(run_dir, [{"finding_id": "f-001", "status": "rejected"}])
            council = json.loads((run_dir / "council.json").read_text(encoding="utf-8"))
            d = council["decisions"][0]
            self.assertEqual(d["status"], "rejected")
            self.assertNotIn("human_resolution", d)


class WriteFinalManuscriptTests(unittest.TestCase):

    def test_writes_final_md_from_completed_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _make_run_dir(Path(tmp))
            _write_revision(run_dir, status="completed", content="The final text.\n")
            final_path = write_final_manuscript(run_dir)
            self.assertTrue(final_path.exists())
            self.assertEqual(final_path.read_text(encoding="utf-8"), "The final text.\n")

    def test_missing_revision_raises_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _make_run_dir(Path(tmp))
            with self.assertRaises(FileNotFoundError):
                write_final_manuscript(run_dir)

    def test_incomplete_revision_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _make_run_dir(Path(tmp))
            _write_revision(run_dir, status="executing", content="Draft.")
            with self.assertRaises(ValueError):
                write_final_manuscript(run_dir)

    def test_empty_revised_document_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _make_run_dir(Path(tmp))
            _write_revision(run_dir, status="completed", content="")
            with self.assertRaises(ValueError):
                write_final_manuscript(run_dir)


# ---------------------------------------------------------------------------
# hooks.py tests
# ---------------------------------------------------------------------------

class HooksCredentialDetectionTests(unittest.TestCase):

    def _make_request(self, prompt: str):
        from ruwritingstyles.providers import ProviderRequest
        return ProviderRequest(task="review", prompt=prompt, schema={}, metadata={})

    def test_safe_slavic_sk_prefix_not_blocked(self) -> None:
        """'sk-' as a Slavic morpheme prefix must NOT trigger the guardrail."""
        req = self._make_request("Рассмотрим слова с префиксом -ск- в русском языке.")
        # Must not raise
        result = hooks.pre_provider_call(req)
        self.assertIsNotNone(result)

    def test_openai_key_pattern_blocked(self) -> None:
        """A real OpenAI-style key (sk- + 48 alphanum chars) MUST be blocked."""
        fake_key = "sk-" + "A" * 48
        req = self._make_request(f"Use this key: {fake_key}")
        with self.assertRaises(RuntimeError):
            hooks.pre_provider_call(req)

    def test_aws_key_pattern_blocked(self) -> None:
        """An AWS AKIA key must be blocked."""
        req = self._make_request("AKIAIOSFODNN7EXAMPLE is the key.")
        with self.assertRaises(RuntimeError):
            hooks.pre_provider_call(req)

    def test_path_traversal_sanitised(self) -> None:
        """Directory traversal sequences must be replaced, not blocked."""
        req = self._make_request("Load ../../../etc/passwd")
        result = hooks.pre_provider_call(req)
        self.assertNotIn("../", result.prompt)
        self.assertIn("[[PATH_REDACTED]]", result.prompt)

    def test_prompt_over_limit_blocked(self) -> None:
        """Prompts exceeding the character limit must be blocked."""
        req = self._make_request("a" * 200_001)
        with self.assertRaises(RuntimeError):
            hooks.pre_provider_call(req)

    def test_prompt_at_limit_allowed(self) -> None:
        """Prompts exactly at the limit must pass."""
        req = self._make_request("a" * 200_000)
        result = hooks.pre_provider_call(req)
        self.assertIsNotNone(result)


class HooksArtifactRedactionTests(unittest.TestCase):

    def test_no_credential_passes_through_unchanged(self) -> None:
        artifact = {"key": "value", "findings": [{"id": "f-001"}]}
        result = hooks.pre_write_artifact(artifact)
        self.assertEqual(result, artifact)

    def test_openai_key_in_leaf_value_is_redacted(self) -> None:
        fake_key = "sk-" + "B" * 48
        artifact = {"leaked": fake_key, "safe": "normal text"}
        result = hooks.pre_write_artifact(artifact)
        self.assertNotIn(fake_key, result["leaked"])
        self.assertIn("[REDACTED]", result["leaked"])
        self.assertEqual(result["safe"], "normal text")

    def test_nested_structure_is_traversed(self) -> None:
        fake_key = "sk-" + "C" * 48
        artifact = {"meta": {"deep": {"value": fake_key}}}
        result = hooks.pre_write_artifact(artifact)
        self.assertIn("[REDACTED]", result["meta"]["deep"]["value"])

    def test_null_values_are_preserved(self) -> None:
        """post_schema_validate must NOT prune null values."""
        output = {"status": "pending", "human_resolution": None, "comment": "ok"}
        result = hooks.post_schema_validate(output, {})
        self.assertIn("human_resolution", result)
        self.assertIsNone(result["human_resolution"])


# ---------------------------------------------------------------------------
# context_builder.py tests
# ---------------------------------------------------------------------------

class BuildUnifiedContextTests(unittest.TestCase):

    def test_empty_inputs_returns_empty_string(self) -> None:
        result = build_unified_context(manifest={})
        self.assertEqual(result.strip(), "")

    def test_style_id_renders_passport_block(self) -> None:
        manifest = {"styles": {"akadem": {"name": "Academic", "description": "Formal prose."}}}
        result = build_unified_context(manifest=manifest, style_id="akadem")
        self.assertIn("Academic", result)
        self.assertIn("Formal prose.", result)

    def test_knowledge_results_rendered(self) -> None:
        result = build_unified_context(manifest={}, knowledge_results="Gasparov passage here.")
        self.assertIn("Gasparov passage here.", result)
        self.assertIn("Knowledge Passages", result)

    def test_source_passage_id_rendered(self) -> None:
        result = build_unified_context(manifest={}, source_passage_id="p042")
        self.assertIn("p042", result)

    def test_artifact_preview_rendered(self) -> None:
        result = build_unified_context(manifest={}, long_artifact_preview="Preview line 1\nLine 2")
        self.assertIn("Preview line 1", result)


class BuildLongArtifactPreviewTests(unittest.TestCase):

    def test_missing_file_returns_empty_string(self) -> None:
        result = build_long_artifact_preview(Path("/nonexistent/path.json"))
        self.assertEqual(result, "")

    def test_short_file_returned_in_full(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.md"
            p.write_text("line1\nline2\nline3", encoding="utf-8")
            result = build_long_artifact_preview(p, max_lines=100)
            self.assertIn("line1", result)
            self.assertIn("line3", result)
            self.assertNotIn("TRUNCATED", result)

    def test_long_file_truncated_with_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "long.md"
            p.write_text("\n".join(f"line{i}" for i in range(200)), encoding="utf-8")
            result = build_long_artifact_preview(p, max_lines=50)
            self.assertIn("TRUNCATED", result)
            self.assertIn("line49", result)
            self.assertNotIn("line50", result)

    def test_json_file_parsed_and_previewed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "data.json"
            p.write_text(json.dumps({"key": "value", "list": list(range(200))}), encoding="utf-8")
            result = build_long_artifact_preview(p, max_lines=10)
            self.assertIn("key", result)


if __name__ == "__main__":
    unittest.main()
