"""Unit tests for span-patch reconstruction (revision over-rewrite fix, H073)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ruwritingstyles.reconstruct import (
    govern_changes,
    reconstruct_revised,
    reconstruction_errors,
)
from ruwritingstyles.segment import normalize_document, segment_markdown


SAMPLE = (
    "# Заголовок\n"
    "\n"
    "Первый абзац с утверждением про этимологию слова.\n"
    "\n"
    "Второй абзац, который надо оставить нетронутым.\n"
    "\n"
    "Третий абзац с ещё одним тезисом.\n"
)


def _segments(text: str) -> list[dict]:
    return [seg.to_json() for seg in segment_markdown(text)]


class ReconstructRevisedTests(unittest.TestCase):
    def test_zero_change_reproduces_normalized_byte_identical(self) -> None:
        normalized = normalize_document(SAMPLE)
        segments = _segments(normalized)
        result = reconstruct_revised(normalized, segments, [])
        self.assertEqual(result, normalized)

    def test_zero_change_is_byte_identical_including_trailing_newline(self) -> None:
        normalized = normalize_document(SAMPLE)
        segments = _segments(normalized)
        result = reconstruct_revised(normalized, segments, [])
        self.assertTrue(result.endswith("\n"))
        self.assertEqual(result.encode("utf-8"), normalized.encode("utf-8"))

    def test_single_span_substitution_only_changes_that_span(self) -> None:
        normalized = normalize_document(SAMPLE)
        segments = _segments(normalized)
        # Pick the first paragraph span (the etymology claim).
        target = next(s for s in segments if s["type"] == "paragraph")
        replacement = "Первый абзац с утверждением про этимологию слова (спорно, требует источника)."
        result = reconstruct_revised(
            normalized,
            segments,
            [{"span_id": target["span_id"], "replacement_text": replacement}],
        )
        self.assertIn(replacement, result)
        # Untouched neighbours preserved verbatim.
        self.assertIn("Второй абзац, который надо оставить нетронутым.", result)
        self.assertIn("Третий абзац с ещё одним тезисом.", result)
        # Heading preserved and structure intact.
        self.assertTrue(result.startswith("# Заголовок\n\n"))
        self.assertTrue(result.endswith("\n"))

    def test_unknown_span_id_is_ignored_and_leaves_document_unchanged(self) -> None:
        normalized = normalize_document(SAMPLE)
        segments = _segments(normalized)
        result = reconstruct_revised(
            normalized,
            segments,
            [{"span_id": "does-not-exist", "replacement_text": "junk"}],
        )
        self.assertEqual(result, normalized)

    def test_change_without_replacement_text_is_ignored(self) -> None:
        normalized = normalize_document(SAMPLE)
        segments = _segments(normalized)
        target = next(s for s in segments if s["type"] == "paragraph")
        result = reconstruct_revised(
            normalized,
            segments,
            [{"span_id": target["span_id"], "explanation": "no text supplied"}],
        )
        self.assertEqual(result, normalized)

    def test_multiline_span_replacement(self) -> None:
        text = "Строка один.\nСтрока два.\n\nОтдельный абзац.\n"
        normalized = normalize_document(text)
        segments = _segments(normalized)
        target = segments[0]
        result = reconstruct_revised(
            normalized,
            segments,
            [{"span_id": target["span_id"], "replacement_text": "Новая строка."}],
        )
        self.assertIn("Новая строка.", result)
        self.assertIn("Отдельный абзац.", result)
        self.assertNotIn("Строка один.", result)


class ReconstructionErrorsTests(unittest.TestCase):
    def test_valid_reconstruction_has_no_errors(self) -> None:
        normalized = normalize_document(SAMPLE)
        segments = _segments(normalized)
        target = next(s for s in segments if s["type"] == "paragraph")
        changes = [{"span_id": target["span_id"], "replacement_text": "Короткая правка."}]
        revised = reconstruct_revised(normalized, segments, changes)
        self.assertEqual(reconstruction_errors(normalized, segments, changes, revised), [])

    def test_zero_change_valid_against_normalized(self) -> None:
        normalized = normalize_document(SAMPLE)
        segments = _segments(normalized)
        self.assertEqual(reconstruction_errors(normalized, segments, [], normalized), [])

    def test_tampered_revised_flags_error(self) -> None:
        normalized = normalize_document(SAMPLE)
        segments = _segments(normalized)
        tampered = normalized + "Незаявленная добавленная строка.\n"
        errors = reconstruction_errors(normalized, segments, [], tampered)
        self.assertTrue(any("faithful span-patch reconstruction" in e for e in errors))

    def test_unknown_span_and_missing_replacement_are_flagged(self) -> None:
        normalized = normalize_document(SAMPLE)
        segments = _segments(normalized)
        changes = [{"span_id": "nope"}]
        revised = reconstruct_revised(normalized, segments, changes)
        errors = reconstruction_errors(normalized, segments, changes, revised)
        self.assertTrue(any("unknown span_id" in e for e in errors))
        self.assertTrue(any("missing replacement_text" in e for e in errors))


class GovernChangesTests(unittest.TestCase):
    """Document-level growth budget (over-rewrite governor).

    Live models over-rewrite inside the span too (a 291-char paragraph came
    back as an 864-char essay in the karaka N=5 sweep), so the budget must be
    enforced by the engine, not the prompt."""

    def _setup(self):
        normalized = normalize_document(SAMPLE)
        segments = _segments(normalized)
        paragraphs = [s for s in segments if s["type"] == "paragraph"]
        return normalized, segments, paragraphs

    def test_surgical_patch_within_budget_is_accepted(self) -> None:
        normalized, segments, paragraphs = self._setup()
        change = {"span_id": paragraphs[0]["span_id"], "replacement_text": paragraphs[0]["text"] + " (спорно)."}
        accepted, rejected = govern_changes(normalized, segments, [change])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(rejected, [])

    def test_runaway_patch_is_rejected_with_reason(self) -> None:
        normalized, segments, paragraphs = self._setup()
        bloat = {"span_id": paragraphs[0]["span_id"], "replacement_text": "х" * (len(normalized) * 3)}
        accepted, rejected = govern_changes(normalized, segments, [bloat])
        self.assertEqual(accepted, [])
        self.assertEqual(len(rejected), 1)
        self.assertIn("fidelity budget", rejected[0]["rejection_reason"])

    def test_runaway_patch_does_not_evict_surgical_ones(self) -> None:
        normalized, segments, paragraphs = self._setup()
        surgical = {"span_id": paragraphs[0]["span_id"], "replacement_text": paragraphs[0]["text"] + " (см. MW)."}
        bloat = {"span_id": paragraphs[1]["span_id"], "replacement_text": "х" * (len(normalized) * 3)}
        accepted, rejected = govern_changes(normalized, segments, [bloat, surgical])
        self.assertEqual([c["span_id"] for c in accepted], [surgical["span_id"]])
        self.assertEqual([c["span_id"] for c in rejected], [bloat["span_id"]])

    def test_shrinking_patch_is_always_accepted(self) -> None:
        normalized, segments, paragraphs = self._setup()
        change = {"span_id": paragraphs[0]["span_id"], "replacement_text": "Коротко."}
        accepted, rejected = govern_changes(normalized, segments, [change])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(rejected, [])

    def test_governed_reconstruction_respects_char_budget(self) -> None:
        # End-to-end invariant: whatever the model sends, the reconstruction of
        # the governed change set never grows the document beyond the budget.
        normalized, segments, paragraphs = self._setup()
        changes = [
            {"span_id": p["span_id"], "replacement_text": p["text"] * 4} for p in paragraphs
        ]
        accepted, _rejected = govern_changes(normalized, segments, changes, growth_ratio=0.4)
        revised = reconstruct_revised(normalized, segments, accepted)
        self.assertLessEqual(len(revised) - len(normalized), int(0.4 * len(normalized)))

    def test_unknown_span_passes_through_untouched(self) -> None:
        normalized, segments, _ = self._setup()
        change = {"span_id": "nope", "replacement_text": "junk"}
        accepted, rejected = govern_changes(normalized, segments, [change])
        self.assertEqual(accepted, [change])
        self.assertEqual(rejected, [])


if __name__ == "__main__":
    unittest.main()
