"""The extraction sanity gate — docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md (H3153).

The gate exists to catch one specific failure: a PDF whose embedded font
encodings turn Cyrillic into blanks or mojibake, producing output that is
*shaped* like text. These tests pin the shape of that discrimination, not the
exact ratios — the ratios are calibrated data and live in `SANITY_THRESHOLDS`.
"""

import unittest

from ruwritingstyles.config import PDF_EXTRACTOR_CHAIN, SANITY_THRESHOLDS
from ruwritingstyles.extract import sanity

# ~260 tokens of ordinary Russian academic prose, above the min_words floor.
GOOD_RU = (
    "В настоящей статье рассматривается вопрос о том, как корпусная лингвистика "
    "изменила представления исследователей о структуре русского языка. Автор "
    "показывает, что данные национального корпуса позволяют проверять гипотезы, "
    "которые ранее оставались предметом умозрительных рассуждений. Особое внимание "
    "уделяется частотным характеристикам словоформ и их распределению по жанрам. "
) * 12

# What pdftotext returns from the two known-garbled corpus PDFs: Latin-range
# noise where Cyrillic should be, punctuation and spacing intact.
MOJIBAKE = (
    "Ffl kdsjhf ldsjf, hgfd sdfkjh; wqoeiu zxcvbn qwerty. Lkjhgf dsapoi uytrew "
    "mnbvcx zaqwsx edcrfv tgbyhn ujmikl opqazw sxedcr fvtgby hnujmi. "
) * 12


class SanityShapeTests(unittest.TestCase):
    def test_real_russian_passes(self) -> None:
        result = sanity(GOOD_RU)
        self.assertEqual(result["verdict"], "pass", result)
        self.assertGreater(result["cyrillic_ratio"], 0.9)

    def test_mojibake_fails(self) -> None:
        result = sanity(MOJIBAKE)
        self.assertEqual(result["verdict"], "fail", result)
        self.assertLess(result["cyrillic_ratio"], 0.1)

    def test_replacement_characters_fail(self) -> None:
        result = sanity(GOOD_RU[:400] + "�" * 400)
        self.assertEqual(result["verdict"], "fail", result)
        self.assertGreater(result["replacement_ratio"], 0.0)

    def test_empty_and_none_do_not_raise(self) -> None:
        for value in ("", None):
            result = sanity(value)
            self.assertEqual(result["verdict"], "fail")
            self.assertEqual(result["words"], 0)

    def test_returns_every_documented_key(self) -> None:
        keys = {"cyrillic_ratio", "replacement_ratio", "word_hit_rate", "words", "verdict"}
        self.assertEqual(set(sanity(GOOD_RU)), keys)

    def test_english_abstract_does_not_sink_a_russian_body(self) -> None:
        """word_hit_rate scores Cyrillic tokens only — RCSI galleys carry en abstracts."""
        english_tail = "This article examines corpus linguistics and its methods. " * 20
        self.assertEqual(sanity(GOOD_RU + english_tail)["verdict"], "pass")


class LanguageExpectationTests(unittest.TestCase):
    """RCSI publishes English articles too — `expect_cyrillic=False` (H3153, ALP 21.1)."""

    GOOD_EN = (
        "This article investigates verb borrowing and integration in the modern "
        "varieties that have been affected by contact with neighbouring languages. "
        "The analysis is based on data from published corpora and shows that the "
        "form of the integrated loan verbs varies from variety to variety. "
    ) * 12

    def test_clean_english_passes_when_not_expecting_cyrillic(self) -> None:
        self.assertEqual(sanity(self.GOOD_EN, expect_cyrillic=False)["verdict"], "pass")

    def test_clean_english_fails_the_russian_expectation(self) -> None:
        """The default must stay strict, or garbled Cyrillic slips through as 'English'."""
        self.assertEqual(sanity(self.GOOD_EN)["verdict"], "fail")

    def test_mojibake_still_fails_under_the_latin_expectation(self) -> None:
        """Mojibake is Latin-range too; waiving the script floor must not waive sense."""
        self.assertEqual(sanity(MOJIBAKE, expect_cyrillic=False)["verdict"], "fail")

    def test_russian_fails_the_latin_expectation(self) -> None:
        self.assertEqual(sanity(GOOD_RU, expect_cyrillic=False)["verdict"], "fail")


class PinnedVerdictTests(unittest.TestCase):
    """The bake-off verdict is config, and config must stay self-consistent."""

    def test_thresholds_are_shared_not_duplicated(self) -> None:
        from ruwritingstyles import extract

        self.assertIs(SANITY_THRESHOLDS, extract.SANITY_THRESHOLDS)

    def test_chain_is_ordered_and_non_empty(self) -> None:
        self.assertGreater(len(PDF_EXTRACTOR_CHAIN), 1)
        self.assertEqual(len(set(PDF_EXTRACTOR_CHAIN)), len(PDF_EXTRACTOR_CHAIN))

    def test_chain_ends_in_ocr(self) -> None:
        """The fallback order must terminate in an escalation that ignores the text layer."""
        self.assertIn("ocr", PDF_EXTRACTOR_CHAIN[-1].lower())

    def test_threshold_keys_are_the_documented_four(self) -> None:
        self.assertEqual(
            set(SANITY_THRESHOLDS),
            {"min_cyrillic_ratio", "max_replacement_ratio", "min_word_hit_rate", "min_words"},
        )


if __name__ == "__main__":
    unittest.main()
