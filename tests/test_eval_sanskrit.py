import json
import shutil
import unittest
from pathlib import Path

from ruwritingstyles.evals import run_eval_case

REPO_ROOT = Path(__file__).resolve().parents[1]

# (case_id, required finding type that must be matched deterministically on mock)
CASES = [
    ("translit-mixed-scheme", "mixed_transliteration_scheme"),
    ("translit-first-mention", "missing_iast_on_first_mention"),
    ("gost-hallucinated-ref", "hallucinated_citation"),
]


class SanskritEvalCaseTests(unittest.TestCase):
    """The W5 cases must pass deterministically under the mock provider so the
    Eval Smoke CI exercises the linter and citation grounding without keys."""

    def _run(self, case_id: str) -> dict:
        run_id = f"unittest-w5-{case_id}"
        run_dir = REPO_ROOT / "runs" / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
        self.addCleanup(lambda: shutil.rmtree(run_dir, ignore_errors=True))
        result = run_eval_case(
            repo_root=REPO_ROOT, case_id=case_id, provider_name="mock", run_id=run_id
        )
        return json.loads(result.result_path.read_text(encoding="utf-8"))

    def test_cases_pass_on_mock(self) -> None:
        for case_id, required_type in CASES:
            with self.subTest(case=case_id):
                data = self._run(case_id)
                self.assertTrue(
                    data["scoring"]["passed"],
                    f"{case_id} should pass on mock: {data['scoring']}",
                )
                self.assertIn(
                    required_type, data["scoring"]["matched_required_finding_types"]
                )
                self.assertEqual(data["provider"], "mock")


if __name__ == "__main__":
    unittest.main()
