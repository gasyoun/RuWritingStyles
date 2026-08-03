"""Philological CONFLICT_MATRIX coverage for roadmap L-08 (H1832).

Locks: every L-08 pair has a non-empty resolution hint under either key
ordering; the mock council cites that rule in ``reason`` when synthetic
conflicting findings are injected into a real council bundle.
"""

from __future__ import annotations

import json
import os
import shutil
import unittest
from pathlib import Path

os.environ.setdefault("RWS_OFFLINE", "1")

from ruwritingstyles.config import load_manifest, load_model_policy
from ruwritingstyles.council import (
    CONFLICT_MATRIX,
    create_council_bundle,
    lookup_conflict_hint,
)
from ruwritingstyles.execution import execute_council_artifact
from ruwritingstyles.providers import MockProvider, provider_from_name
from ruwritingstyles.runs import create_prepare_run
from ruwritingstyles.segment import normalize_document, segment_markdown

REPO_ROOT = Path(__file__).resolve().parents[1]

# roadmap_literary_clusters.md §L-08 — required pairs and a distinctive
# substring that must appear in each resolution hint (cite-able rule token).
L08_PAIRS: list[tuple[str, str, str]] = [
    ("lit_opoyaz", "lit_bakhtin", "escalate, author decides"),  # L1 ↔ L6
    ("lit_narratology", "lit_bakhtin", "Narratology vs Bakhtin: escalate"),  # L5 ↔ L6
    ("lit_textology", "ling_nss", "lit_textology_wins"),  # L3 ↔ NSS
    ("lit_poststructural", "ling_nss", "lit_poststructural_wins"),  # L9 ↔ NSS
    ("lit_poststructural", "lit_narratology", "Poststructural vs Narratology: escalate"),  # L9 ↔ L5
]

DOC = (
    "# Синтетический конфликт\n\n"
    "Текст, в котором сталкиваются две филологические школы.\n"
)


class ConflictMatrixLookupTests(unittest.TestCase):
    """Every L-08 pair resolves to a non-empty hint (both key orderings)."""

    def test_l08_pairs_nonempty_both_orderings(self) -> None:
        for a, b, token in L08_PAIRS:
            with self.subTest(pair=f"{a}↔{b}"):
                forward = lookup_conflict_hint(a, b)
                reverse = lookup_conflict_hint(b, a)
                self.assertIsNotNone(forward, f"missing matrix entry for ({a}, {b})")
                self.assertIsNotNone(reverse, f"reverse lookup failed for ({b}, {a})")
                self.assertTrue(str(forward).strip(), f"empty hint for ({a}, {b})")
                self.assertEqual(forward, reverse)
                self.assertIn(token, str(forward))

    def test_lookup_unknown_pair_returns_none(self) -> None:
        self.assertIsNone(lookup_conflict_hint("lit_opoyaz", "ling_mss"))
        self.assertIsNone(lookup_conflict_hint(None, "lit_bakhtin"))
        self.assertIsNone(lookup_conflict_hint("lit_bakhtin", "lit_bakhtin"))

    def test_matrix_keys_are_unique_up_to_order(self) -> None:
        seen: set[frozenset[str]] = set()
        for a, b in CONFLICT_MATRIX:
            key = frozenset((a, b))
            self.assertNotIn(key, seen, f"duplicate unordered pair {a}/{b}")
            seen.add(key)
            # One ordering only in the dict — reverse must not also be stored.
            self.assertNotIn((b, a), CONFLICT_MATRIX)


class ConflictMatrixPromptFidelityTests(unittest.TestCase):
    """The council prompt must not teach a rule the matrix contradicts (H2217).

    H1832 rewrote the L1 ↔ L6 entry to `escalate, author decides` but left the
    prompt's own CRITICAL worked example as `'Bakhtin > OPOYAZ'` — a school-wins
    verdict for the one pair the roadmap says must escalate. Since that example
    is the only citation pattern a live provider is shown, it biased the model
    against the shipped rule.
    """

    COUNCIL_SRC = (
        REPO_ROOT / "src" / "ruwritingstyles" / "council.py"
    ).read_text(encoding="utf-8")

    def test_prompt_has_no_school_wins_example_for_escalate_pairs(self) -> None:
        self.assertNotIn(
            "Bakhtin > OPOYAZ",
            self.COUNCIL_SRC,
            "council prompt asserts a winner for an `escalate` pair (L1 ↔ L6)",
        )

    def test_prompt_examples_are_backed_by_a_real_matrix_hint(self) -> None:
        """Every `'X > Y: token'` example in the prompt must exist in the matrix."""
        import re

        hints = " || ".join(CONFLICT_MATRIX.values())
        # Only the `Resolve Conflicts` instruction line — the one place the prompt
        # shows a provider what a citation should look like.
        instruction_lines = [
            line
            for line in self.COUNCIL_SRC.splitlines()
            if "**Resolve Conflicts**" in line
        ]
        self.assertTrue(instruction_lines, "Resolve Conflicts instruction not found")
        examples = [
            match
            for line in instruction_lines
            for match in re.findall(r"'([^'\n]{3,120})'", line)
            if ">" in match or " vs " in match
        ]
        self.assertTrue(examples, "no citation example found in the prompt")
        for example in examples:
            with self.subTest(example=example):
                self.assertIn(
                    example,
                    hints,
                    f"prompt cites '{example}', which no CONFLICT_MATRIX hint supports",
                )

    def test_escalate_pairs_never_name_a_winner_token(self) -> None:
        """An `escalate` hint must not also carry an `*_wins` resolution token."""
        for pair, hint in CONFLICT_MATRIX.items():
            if "Resolution: escalate" not in hint:
                continue
            with self.subTest(pair=pair):
                self.assertNotIn("_wins", hint, f"{pair} is both escalate and a win")


class ConflictMatrixCouncilCitationTests(unittest.TestCase):
    """Deliberation-level: mock provider cites the matrix rule in reason."""

    def _prepare_run_with_conflict(
        self, run_id: str, cluster_a: str, cluster_b: str
    ) -> Path:
        run_dir = REPO_ROOT / "runs" / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
        self.addCleanup(lambda: shutil.rmtree(run_dir, ignore_errors=True))

        norm = normalize_document(DOC)
        segs = segment_markdown(norm)
        manifest = load_manifest(REPO_ROOT)
        model_policy = load_model_policy(REPO_ROOT)
        create_prepare_run(
            repo_root=REPO_ROOT,
            input_path=Path("conflict-note.md"),
            original_text=DOC,
            normalized_text=norm,
            segments=segs,
            manifest=manifest,
            model_policy=model_policy,
            run_id=run_id,
            provider="mock",
            profile="researcher",
        )

        span_id = segs[0].span_id if segs else "p001"
        reviews_dir = run_dir / "reviews"
        reviews_dir.mkdir(parents=True, exist_ok=True)
        for style_id in (cluster_a, cluster_b):
            review = {
                "run_id": run_id,
                "style_id": style_id,
                "status": "completed",
                "summary": f"Synthetic conflict review from {style_id}.",
                "findings": [
                    {
                        "id": f"finding-{style_id}",
                        "style_id": style_id,
                        "span_id": span_id,
                        "severity": "warning",
                        "type": "methodological_conflict",
                        "finding": (
                            f"Synthetic finding from {style_id} that conflicts "
                            f"with the peer school on the same span."
                        ),
                        "suggestion": f"Apply {style_id} methodology.",
                        "confidence": 0.9,
                    }
                ],
            }
            (reviews_dir / f"{style_id}.review.json").write_text(
                json.dumps(review, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return run_dir

    def test_mock_council_reason_cites_l08_rule(self) -> None:
        # L1 ↔ L6 is the paradigmatic pair named first in the L-08 table.
        cluster_a, cluster_b, token = L08_PAIRS[0]
        run_id = "unittest-h1832-conflict-cite"
        run_dir = self._prepare_run_with_conflict(run_id, cluster_a, cluster_b)
        manifest = load_manifest(REPO_ROOT)
        model_policy = load_model_policy(REPO_ROOT)

        bundle = create_council_bundle(
            repo_root=REPO_ROOT, run_dir=run_dir, manifest=manifest
        )
        prompt = bundle.prompt_md.read_text(encoding="utf-8")
        self.assertIn("Philological Conflict Matrix", prompt)
        # Matrix text and findings both name the pair.
        self.assertIn(cluster_a, prompt)
        self.assertIn(cluster_b, prompt)
        hint = lookup_conflict_hint(cluster_a, cluster_b)
        self.assertIsNotNone(hint)
        self.assertIn(token, str(hint))

        execute_council_artifact(
            repo_root=REPO_ROOT,
            council_path=bundle.council_json,
            provider=provider_from_name("mock"),
            model=model_policy.resolve_model("council", "mock"),
        )
        council = json.loads(bundle.council_json.read_text(encoding="utf-8"))
        self.assertEqual(council.get("status"), "completed")
        decisions = council.get("decisions") or []
        self.assertTrue(decisions, "expected at least one council decision")
        reasons = " ".join(str(d.get("reason") or "") for d in decisions)
        self.assertIn("Conflict matrix rule", reasons)
        self.assertIn(token, reasons)

    def test_mock_without_conflicting_styles_keeps_placeholder_reason(self) -> None:
        """Ordinary MVP findings must not falsely cite a literary matrix rule."""
        provider = MockProvider()
        from ruwritingstyles.providers import ProviderRequest

        # Prompt lists the matrix (as every council prompt does) but findings
        # only carry an MVP passport style_id that is not a matrix key.
        prompt = (
            "## Philological Conflict Matrix (Methodological Resolution):\n"
            '```json\n{"lit_opoyaz vs lit_bakhtin": "…escalate, author decides…"}\n```\n'
            'Findings: {"style_id": "zalizniak-method", "id": "finding-001"}\n'
        )
        out = provider.generate_json(
            ProviderRequest(
                task="council",
                prompt=prompt,
                schema={},
                metadata={"run_id": "unittest-no-conflict", "finding_ids": ["finding-001"]},
            )
        )
        reason = out["decisions"][0]["reason"]
        self.assertEqual(
            reason, "Mock council keeps placeholder findings informational."
        )


if __name__ == "__main__":
    unittest.main()
