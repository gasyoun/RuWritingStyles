"""Tests for the F4-second-half verifier injection (H588 N3):
THIS run's council commitments + reviewing passports' limits reach the
verification prompt, with the RWS_VERIFY_STYLE_COMMITMENTS=0 kill switch."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ruwritingstyles.verification import _render_run_style_commitments  # noqa: E402


def _make_run_dir(tmp: Path) -> Path:
    run_dir = tmp / "run"
    (run_dir / "reviews").mkdir(parents=True)
    (run_dir / "council.json").write_text(json.dumps({
        "stylistic_commitments": [
            {"term": "kāraka", "decision": "никогда не переводить как 'падеж'"},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    (run_dir / "reviews" / "panini-traditional.review.json").write_text(json.dumps({
        "style_id": "panini-traditional",
        "findings": [],
    }), encoding="utf-8")
    return run_dir


class RunStyleCommitmentsTests(unittest.TestCase):
    def test_council_commitments_and_passport_limits_injected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _make_run_dir(Path(tmp))
            original_import = __import__

            def reject_pyyaml(name, *args, **kwargs):
                if name == "yaml":
                    raise AssertionError("verification must not import PyYAML")
                return original_import(name, *args, **kwargs)

            with mock.patch("builtins.__import__", side_effect=reject_pyyaml):
                section = _render_run_style_commitments(REPO_ROOT, run_dir)
        self.assertIn("Run Style Commitments", section)
        self.assertIn("kāraka", section)
        # a real limit from styles/passports/panini-traditional.yml
        self.assertIn("[panini-traditional]", section)
        self.assertIn("отождествлять караку с падежом", section)

    def test_kill_switch_restores_pre_h588_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _make_run_dir(Path(tmp))
            with mock.patch.dict(os.environ, {"RWS_VERIFY_STYLE_COMMITMENTS": "0"}):
                section = _render_run_style_commitments(REPO_ROOT, run_dir)
        self.assertEqual(section, "")

    def test_empty_run_renders_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty-run"
            empty.mkdir()
            section = _render_run_style_commitments(REPO_ROOT, empty)
        self.assertEqual(section, "")

    def test_missing_optional_fixture_passport_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            reviews = run_dir / "reviews"
            reviews.mkdir(parents=True)
            (reviews / "fixture.review.json").write_text(
                json.dumps({"style_id": "optional-fixture", "findings": []}),
                encoding="utf-8",
            )
            section = _render_run_style_commitments(root, run_dir)
        self.assertEqual(section, "")


if __name__ == "__main__":
    unittest.main()
