"""Adversarial eval cases score a *non*-edit (H1480).

The suite's majority are catch-the-error cases: a document carries one planted
mistake and the reviewer must name it. The ``*-adversarial`` family is the
inverse — the document is *correct as written*, and the pipeline passes only by
leaving it alone. Nothing pinned that inversion mechanically, so a later edit
could quietly relax an adversarial case into an ordinary one and the mock gate
would not notice (it compares pass/fail, not scoring semantics).

Three properties are pinned here:

1. every ``*-adversarial`` case demands ``strict_fidelity``;
2. the three literary refusal cases (very-high pipeline risk per
   ``docs/roadmap_literary_clusters.md``) additionally pin both diff bounds to
   ``0.0``, so any edit at all fails them;
3. their required finding types come from the reviewing cluster's own
   ``checks`` — the rule ``evals/GOLD_PROTOCOL.md`` states and the four older
   adversarial cases silently break (``oversimplification`` appears in no
   passport, so no reviewer can emit it).
"""

import unittest
from pathlib import Path

from ruwritingstyles.config import load_manifest, load_passport_by_id
from ruwritingstyles.evals import load_eval_cases

REPO_ROOT = Path(__file__).resolve().parents[1]

# case id -> reviewing cluster whose `checks` must contain the required types.
LITERARY_REFUSAL_CASES = {
    "bakhtin-adversarial": "lit_bakhtin",
    "poststructural-adversarial": "lit_poststructural",
    "textology-adversarial": "lit_textology",
}


class AdversarialRefusalCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = {case.case_id: case for case in load_eval_cases(REPO_ROOT)}
        cls.manifest = load_manifest(REPO_ROOT)

    def test_every_adversarial_case_requires_strict_fidelity(self) -> None:
        adversarial = [c for c in self.cases.values() if c.case_id.endswith("-adversarial")]
        self.assertGreaterEqual(len(adversarial), 7)
        for case in adversarial:
            with self.subTest(case=case.case_id):
                self.assertTrue(
                    case.strict_fidelity,
                    f"{case.case_id} is an adversarial case but does not demand fidelity",
                )

    def test_literary_refusal_cases_forbid_any_edit(self) -> None:
        for case_id in LITERARY_REFUSAL_CASES:
            with self.subTest(case=case_id):
                case = self.cases[case_id]
                self.assertEqual(case.max_changed_line_ratio, 0.0)
                self.assertEqual(case.max_char_delta_ratio, 0.0)
                self.assertTrue(case.input_path.exists())

    def test_required_finding_types_exist_in_the_reviewing_cluster_checks(self) -> None:
        for case_id, cluster_id in LITERARY_REFUSAL_CASES.items():
            with self.subTest(case=case_id):
                case = self.cases[case_id]
                self.assertEqual(case.default_styles, (cluster_id,))
                passport = load_passport_by_id(REPO_ROOT, cluster_id, self.manifest)
                self.assertIsNotNone(passport, f"unknown cluster {cluster_id!r}")
                checks = set(passport.get("checks") or [])
                for required in case.required_finding_types:
                    self.assertIn(
                        required,
                        checks,
                        f"{case_id} requires {required!r}, which cluster {cluster_id} "
                        f"cannot emit (its checks: {sorted(checks)})",
                    )


if __name__ == "__main__":
    unittest.main()
