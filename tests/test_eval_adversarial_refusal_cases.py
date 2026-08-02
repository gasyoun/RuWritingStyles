"""Adversarial eval cases score a *non*-edit (H1480, extended to all seven by H1987).

The suite's majority are catch-the-error cases: a document carries one planted
mistake and the reviewer must name it. The ``*-adversarial`` family is the
inverse — the document is *correct as written*, and the pipeline passes only by
leaving it alone. Nothing pinned that inversion mechanically, so a later edit
could quietly relax an adversarial case into an ordinary one and the mock gate
would not notice (it compares pass/fail, not scoring semantics).

Four properties are pinned here:

1. the registry below covers every ``*-adversarial`` case in the manifest, so a
   new one cannot skip the contract by simply not being listed;
2. every such case demands ``strict_fidelity`` *and* pins both diff bounds to
   ``0.0`` — fidelity alone only asserts that verification raised no warnings,
   so a revision could rewrite the paragraph and still score;
3. every required finding type is declared under ``checks`` by at least one of
   the case's own reviewing styles — the rule ``evals/GOLD_PROTOCOL.md`` states
   and four legacy cases broke for months (``oversimplification``,
   ``missing_epistemic_markers`` and ``loss_of_philological_depth`` appear in no
   passport, so no reviewer could emit them and those cases were unpassable on
   every provider);
4. each ``accepted_finding_aliases`` key is itself a required type, so a stale
   alias map cannot sit in the manifest doing nothing.

Aliases are deliberately *not* required to be grounded: they exist to accept the
legacy labels a model may still reach for.
"""

import shutil
import unittest
from pathlib import Path

from ruwritingstyles.config import load_manifest, load_passport_by_id
from ruwritingstyles.evals import _write_eval_result, load_eval_cases, run_eval_case

REPO_ROOT = Path(__file__).resolve().parents[1]

# case id -> the reviewing styles whose `checks` must cover its required types.
ADVERSARIAL_CASES = {
    "averintsev-adversarial": ("averintsev", "lit_historico_cultural"),
    "iesh-adversarial": ("ling_iesh",),
    "mts-adversarial": ("ling_mts",),
    "historico-cultural-adversarial": ("lit_historico_cultural",),
    "bakhtin-adversarial": ("lit_bakhtin",),
    "poststructural-adversarial": ("lit_poststructural",),
    "textology-adversarial": ("lit_textology",),
    # H1833 — the G-06 linguistic-cluster refusal set (adv_001–adv_005):
    # hedging, school terminology, unsourced dating, transliteration, quotes.
    "adv-001-hedging-adversarial": ("ling_tsh",),
    "adv-002-terminology-adversarial": ("ling_pfg",),
    "adv-003-unsourced-date-adversarial": ("ling_iesh",),
    "adv-004-transliteration-adversarial": ("indology",),
    "adv-005-quote-paraphrase-adversarial": ("ling_dss",),
}


class AdversarialRefusalCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = {case.case_id: case for case in load_eval_cases(REPO_ROOT)}
        cls.manifest = load_manifest(REPO_ROOT)

    def test_registry_covers_every_adversarial_case(self) -> None:
        """A new *-adversarial case must be registered here, not silently exempt."""
        in_manifest = {cid for cid in self.cases if cid.endswith("-adversarial")}
        self.assertEqual(
            in_manifest,
            set(ADVERSARIAL_CASES),
            "ADVERSARIAL_CASES is out of sync with evals/manifest.json — add the new "
            "case here (and give it grounded finding types + 0.0 diff bounds)",
        )

    def test_every_adversarial_case_forbids_any_edit(self) -> None:
        for case_id in ADVERSARIAL_CASES:
            with self.subTest(case=case_id):
                case = self.cases[case_id]
                self.assertTrue(
                    case.strict_fidelity,
                    f"{case_id} is an adversarial case but does not demand fidelity",
                )
                self.assertEqual(
                    case.max_changed_line_ratio,
                    0.0,
                    f"{case_id} would score a pass after changing lines",
                )
                self.assertEqual(
                    case.max_char_delta_ratio,
                    0.0,
                    f"{case_id} would score a pass after changing characters",
                )
                self.assertTrue(case.input_path.exists())

    def test_required_finding_types_exist_in_the_reviewing_styles_checks(self) -> None:
        for case_id, style_ids in ADVERSARIAL_CASES.items():
            with self.subTest(case=case_id):
                case = self.cases[case_id]
                self.assertEqual(case.default_styles, style_ids)
                checks: set[str] = set()
                for style_id in style_ids:
                    passport = load_passport_by_id(REPO_ROOT, style_id, self.manifest)
                    self.assertIsNotNone(passport, f"unknown style {style_id!r}")
                    checks.update(passport.get("checks") or [])
                self.assertTrue(case.required_finding_types)
                for required in case.required_finding_types:
                    self.assertIn(
                        required,
                        checks,
                        f"{case_id} requires {required!r}, which none of {list(style_ids)} "
                        f"can emit (their checks: {sorted(checks)})",
                    )

    def test_alias_keys_are_required_types(self) -> None:
        """An alias map keyed on a non-required type is dead config."""
        for case_id in ADVERSARIAL_CASES:
            with self.subTest(case=case_id):
                case = self.cases[case_id]
                for canonical in case.accepted_finding_aliases:
                    self.assertIn(canonical, case.required_finding_types)


class AdversarialEditFailsTheCaseTests(unittest.TestCase):
    """The fail direction, exercised at runtime (H1833).

    The static contract above pins the scoring *config*; this test pins the
    scoring *behaviour*: a provider that takes the temptation — here, stripping
    «По-видимому, » from adv-001's hedged generalization — must fail the case
    on the 0.0 diff bounds, not silently no-op. The mock provider plays the
    well-behaved lane (no edit); the adversarial lane is simulated by rewriting
    ``revised.md`` with the tempted edit and re-scoring the same run.
    """

    RUN_ID = "unittest-adv-001-refusal"

    def test_mock_run_scores_and_tempted_edit_fails(self) -> None:
        run_dir = REPO_ROOT / "runs" / self.RUN_ID
        shutil.rmtree(run_dir, ignore_errors=True)
        try:
            result = run_eval_case(
                repo_root=REPO_ROOT,
                case_id="adv-001-hedging-adversarial",
                provider_name="mock",
                run_id=self.RUN_ID,
            )
            import json

            honest = json.loads(result.result_path.read_text(encoding="utf-8"))
            # The well-behaved (mock, no-edit) lane surfaces a verdict…
            self.assertIsInstance(honest["scoring"]["passed"], bool)
            # …and makes no edit, so the diff bounds hold.
            self.assertTrue(honest["scoring"]["diff_within_limits"])

            # Adversarial lane: apply the temptation the case exists to resist.
            revised_path = run_dir / "revised.md"
            revised = revised_path.read_text(encoding="utf-8")
            self.assertIn("По-видимому, ", revised)
            revised_path.write_text(
                revised.replace("По-видимому, в языках", "В языках", 1),
                encoding="utf-8",
            )
            case = {c.case_id: c for c in load_eval_cases(REPO_ROOT)}[
                "adv-001-hedging-adversarial"
            ]
            rescored_path = _write_eval_result(
                repo_root=REPO_ROOT,
                run_dir=run_dir,
                case=case,
                provider_name="mock-adversarial",
                model="simulated-tempted-edit",
            )
            tempted = json.loads(rescored_path.read_text(encoding="utf-8"))
            self.assertFalse(tempted["scoring"]["diff_within_limits"])
            self.assertFalse(tempted["scoring"]["passed"])
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
