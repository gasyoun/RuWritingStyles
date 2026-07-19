from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ruwritingstyles.cli import _eval_comparison_has_regression
from ruwritingstyles.evals import compare_eval_suites


def _suite(path: Path, results: list[dict]) -> Path:
    passed_count = sum(1 for row in results if row["passed"])
    payload = {
        "suite_id": path.parent.name,
        "provider": "mock",
        "model": "mock",
        "case_count": len(results),
        "passed_count": passed_count,
        "failed_count": len(results) - passed_count,
        "pass_rate": round(passed_count / max(1, len(results)), 6),
        "results": results,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _row(case_id: str, passed: bool) -> dict:
    return {
        "case_id": case_id,
        "passed": passed,
        "finding_count": 0,
        "verification_status": "passed" if passed else "failed",
        "changed_line_ratio": 0.0,
        "char_delta_ratio": 0.0,
    }


class EvalComparisonGateTests(unittest.TestCase):
    def test_previously_passing_case_regresses(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = _suite(root / "baseline.json", [_row("protected", True)])
            candidate = _suite(root / "candidate.json", [_row("protected", False)])
            data = compare_eval_suites(baseline, candidate).data
        self.assertEqual(data["regressed"], ["protected"])
        self.assertTrue(_eval_comparison_has_regression(data))

    def test_missing_candidate_case_is_fatal(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = _suite(root / "baseline.json", [_row("kept", False)])
            candidate = _suite(root / "candidate.json", [])
            data = compare_eval_suites(baseline, candidate).data
        self.assertEqual(data["missing_candidate"], ["kept"])
        self.assertTrue(_eval_comparison_has_regression(data))

    def test_new_case_requires_baseline_refresh(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = _suite(root / "baseline.json", [_row("existing", True)])
            candidate = _suite(
                root / "candidate.json",
                [_row("existing", True), _row("new-case", True)],
            )
            data = compare_eval_suites(baseline, candidate).data
        self.assertEqual(data["missing_baseline"], ["new-case"])
        self.assertTrue(_eval_comparison_has_regression(data))


if __name__ == "__main__":
    unittest.main()
