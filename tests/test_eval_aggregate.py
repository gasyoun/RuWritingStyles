"""Tests for the N-run eval aggregate harness and the scorer alias policy.

The aggregation math and the alias matching are pure, so they are unit-tested
directly; a small end-to-end aggregate is exercised on the deterministic mock
provider so no API keys are needed.
"""

import json
import shutil
import unittest
from pathlib import Path

from ruwritingstyles.evals import (
    _aggregate_case_stats,
    _stat_summary,
    match_required_finding_types,
    run_eval_repeat,
)
from ruwritingstyles.validation import validate_eval_aggregate_file

REPO_ROOT = Path(__file__).resolve().parents[1]


class StatSummaryTests(unittest.TestCase):
    def test_empty_values(self) -> None:
        self.assertEqual(
            _stat_summary([]),
            {"n": 0, "mean": None, "stdev": None, "min": None, "max": None},
        )

    def test_single_value_zero_stdev(self) -> None:
        summary = _stat_summary([0.5])
        self.assertEqual(summary["n"], 1)
        self.assertEqual(summary["mean"], 0.5)
        self.assertEqual(summary["stdev"], 0.0)

    def test_mean_stdev_min_max(self) -> None:
        summary = _stat_summary([0.0, 0.4, 0.8, None])
        self.assertEqual(summary["n"], 3)
        self.assertEqual(summary["mean"], 0.4)
        self.assertEqual(summary["min"], 0.0)
        self.assertEqual(summary["max"], 0.8)
        # population stdev of [0, 0.4, 0.8]
        self.assertAlmostEqual(summary["stdev"], 0.326599, places=5)


class AggregateCaseStatsTests(unittest.TestCase):
    def _row(self, passed, detected, diff_ok, status, char, line, findings):
        return {
            "run_id": "r",
            "run_dir": "runs/r",
            "result_path": "runs/r/eval-result.json",
            "passed": passed,
            "detected": detected,
            "diff_within_limits": diff_ok,
            "verification_status": status,
            "required_match_count": 1 if detected else 0,
            "finding_count": findings,
            "changed_line_ratio": line,
            "char_delta_ratio": char,
        }

    def test_mixed_pass_fail(self) -> None:
        rows = [
            self._row(True, True, True, "passed", 0.1, 0.2, 3),
            self._row(False, True, False, "passed", 0.9, 0.6, 5),
            self._row(False, False, True, "needs_human_review", 0.0, 0.0, 0),
            self._row(True, True, True, "passed", 0.2, 0.3, 4),
        ]
        stats = _aggregate_case_stats("demo", rows)
        self.assertEqual(stats["repeat"], 4)
        self.assertEqual(stats["pass_count"], 2)
        self.assertEqual(stats["pass_rate"], 0.5)
        self.assertEqual(stats["detection_count"], 3)
        self.assertEqual(stats["detection_rate"], 0.75)
        self.assertEqual(stats["diff_ok_count"], 3)
        self.assertEqual(
            stats["verification_status_distribution"],
            {"passed": 3, "needs_human_review": 1},
        )
        self.assertEqual(stats["metrics"]["char_delta_ratio"]["n"], 4)
        self.assertEqual(stats["metrics"]["char_delta_ratio"]["max"], 0.9)


class AliasPolicyTests(unittest.TestCase):
    def test_canonical_direct_match(self) -> None:
        self.assertEqual(
            match_required_finding_types(("wrong_samasa_type",), {}, {"wrong_samasa_type"}),
            ["wrong_samasa_type"],
        )

    def test_alias_matches_canonical(self) -> None:
        matched = match_required_finding_types(
            ("unsupported_sanskrit_etymology",),
            {"unsupported_sanskrit_etymology": ("unsupported_etymology",)},
            {"unsupported_etymology", "accidental_similarity"},
        )
        self.assertEqual(matched, ["unsupported_sanskrit_etymology"])

    def test_no_match(self) -> None:
        self.assertEqual(
            match_required_finding_types(
                ("wrong_samasa_type",),
                {"wrong_samasa_type": ("misclassified_compound",)},
                {"unrelated_finding"},
            ),
            [],
        )


class MockAggregateEndToEndTests(unittest.TestCase):
    """A deterministic case must aggregate cleanly on the mock provider."""

    def test_repeat_aggregate_on_mock(self) -> None:
        agg_id = "unittest-agg-translit"
        agg_dir = REPO_ROOT / "runs" / agg_id
        if agg_dir.exists():
            shutil.rmtree(agg_dir)
        self.addCleanup(lambda: shutil.rmtree(agg_dir, ignore_errors=True))
        for i in range(1, 4):
            self.addCleanup(
                lambda i=i: shutil.rmtree(
                    REPO_ROOT / "runs" / f"{agg_id}-r{i:02d}", ignore_errors=True
                )
            )

        result = run_eval_repeat(
            repo_root=REPO_ROOT,
            case_id="translit-mixed-scheme",
            provider_name="mock",
            repeat=3,
            aggregate_id=agg_id,
        )
        data = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertEqual(data["kind"], "eval-aggregate")
        self.assertEqual(data["scope"], "case")
        self.assertEqual(data["repeat"], 3)
        case = data["cases"][0]
        self.assertEqual(case["pass_count"], 3)
        self.assertEqual(case["pass_rate"], 1.0)
        self.assertEqual(case["detection_count"], 3)
        # Deterministic mock: no spread in char delta.
        self.assertEqual(case["metrics"]["char_delta_ratio"]["stdev"], 0.0)

        validation = validate_eval_aggregate_file(result.result_path)
        self.assertTrue(validation.ok, validation.messages)


if __name__ == "__main__":
    unittest.main()
