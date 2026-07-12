import json
import tempfile
import unittest
import unicodedata
from pathlib import Path

from ruwritingstyles.translit_lint import (
    lint_text,
    load_sanskrit_terms,
    run_translit_lint,
)

TERMS = [
    {"ru": "бхашья", "iast": "bhāṣya", "source": "Tubb Boose 2007"},
    {"ru": "самаса", "iast": "samāsa", "source": "Tubb Boose 2007"},
    {"ru": "татпуруша", "iast": "tatpuruṣa", "source": "Whitney 1889"},
    {"ru": "веда", "iast": "veda", "source": "Elizarenkova 1982"},
]


def types_of(result):
    return [f["type"] for f in result["findings"]]


class CleanTextTests(unittest.TestCase):
    def test_clean_text_has_no_findings(self) -> None:
        text = (
            "Термин «бхашья» (bhāṣya) обозначает развернутый комментарий.\n\n"
            "В бхашье комментатор разбирает сутру по словам. Ср. также\n"
            "татпуруша (tatpuruṣa) как тип сложного слова."
        )
        result = lint_text(text, TERMS)
        self.assertEqual(result["findings"], [], result["findings"])

    def test_russian_stress_marks_are_not_iast(self) -> None:
        text = "Ёлка и сло́во ѣсть. Обычная русская фраза без санскрита."
        result = lint_text(text, TERMS)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["summary"]["schemes_detected"], [])

    def test_code_blocks_are_skipped(self) -> None:
        text = "Обычный абзац.\n\n```\nbhAShya kRSNa смешанноеword\n```\n"
        result = lint_text(text, TERMS)
        self.assertEqual(result["findings"], [])


class FirstMentionTests(unittest.TestCase):
    def test_first_mention_without_iast_is_flagged(self) -> None:
        text = "Жанр бхашьи сложился рано.\n\nПозднее бхашья стала каноном."
        result = lint_text(text, TERMS)
        self.assertIn("missing_iast_on_first_mention", types_of(result))
        flagged = [f for f in result["findings"] if f["type"] == "missing_iast_on_first_mention"]
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["term"], "бхашья")
        self.assertEqual(flagged[0]["span_id"], "p001")

    def test_first_mention_with_iast_is_clean(self) -> None:
        text = "Жанр бхашьи (bhāṣya) сложился рано.\n\nПозднее бхашья стала каноном."
        result = lint_text(text, TERMS)
        self.assertNotIn("missing_iast_on_first_mention", types_of(result))

    def test_unrelated_russian_words_do_not_trigger_stem_match(self) -> None:
        # "ведет"/"ведущий" must not match the term "веда".
        text = "Дорога ведет в лес. Ведущий семинара ведет занятие."
        result = lint_text(text, TERMS)
        self.assertNotIn("missing_iast_on_first_mention", types_of(result))

    def test_heading_mention_with_glossed_prose_is_clean(self) -> None:
        # H588 N2 rater-B false positive: «# О слове мокша» consumed the
        # first-mention slot, so the properly glossed first prose mention
        # still produced a finding on the heading span.
        text = "# О слове бхашья\n\nЖанр бхашьи (bhāṣya) сложился рано."
        result = lint_text(text, TERMS)
        self.assertNotIn("missing_iast_on_first_mention", types_of(result))

    def test_heading_mention_does_not_relocate_prose_finding(self) -> None:
        # A heading never carries the gloss; an unglossed first PROSE mention
        # must still be flagged — on the prose span, not the heading.
        text = "# О слове бхашья\n\nЖанр бхашьи сложился рано."
        result = lint_text(text, TERMS)
        flagged = [f for f in result["findings"] if f["type"] == "missing_iast_on_first_mention"]
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["term"], "бхашья")
        self.assertTrue(flagged[0]["span_id"].startswith("p"), flagged[0]["span_id"])

    def test_heading_only_mention_is_clean(self) -> None:
        # A term that appears only in a heading has no prose mention to gloss.
        text = "# О слове бхашья\n\nЗдесь обсуждаются другие вопросы."
        result = lint_text(text, TERMS)
        self.assertNotIn("missing_iast_on_first_mention", types_of(result))


class SchemeMixTests(unittest.TestCase):
    def test_iast_plus_harvard_kyoto_is_flagged(self) -> None:
        text = (
            "Сложное слово tatpuruṣa описано у Панини.\n\n"
            "Далее автор пишет tatpuruSa в другой системе."
        )
        result = lint_text(text, TERMS)
        self.assertIn("mixed_transliteration_scheme", types_of(result))

    def test_pure_iast_is_not_flagged_as_mix(self) -> None:
        text = "Термины bhāṣya и tatpuruṣa и samāsa встречаются в IAST."
        result = lint_text(text, TERMS)
        self.assertNotIn("mixed_transliteration_scheme", types_of(result))
        self.assertEqual(result["summary"]["schemes_detected"], ["iast"])

    def test_english_words_with_capitals_are_not_hk(self) -> None:
        # "McDonald" has an internal capital but resolves to no Sanskrit term.
        text = "Ср. McDonald и WordNet — обычные латинские вкрапления с bhāṣya."
        result = lint_text(text, TERMS)
        self.assertNotIn("mixed_transliteration_scheme", types_of(result))


class MixedScriptAndDevanagariTests(unittest.TestCase):
    def test_cyrillic_latin_hybrid_word_is_flagged(self) -> None:
        text = "Появилось гибридное слово бхāшья в тексте."
        result = lint_text(text, TERMS)
        self.assertIn("iast_in_cyrillic_word", types_of(result))

    def test_latin_acronym_hyphen_cyrillic_is_not_flagged(self) -> None:
        # Real false positive found on a live article: "IAST-транслитерацией",
        # "TEI-схемы" are acronym+Cyrillic compounds, not fused transliteration.
        text = "Запись IAST-транслитерацией и работа с TEI-схемы и XML-разметкой."
        result = lint_text(text, TERMS)
        self.assertNotIn("iast_in_cyrillic_word", types_of(result))

    def test_cyrillic_term_hyphen_iast_gloss_is_not_flagged(self) -> None:
        text = "В сноски-bhāṣya автор выносит толкование."
        result = lint_text(text, TERMS)
        self.assertNotIn("iast_in_cyrillic_word", types_of(result))

    def test_devanagari_precomposed_nukta_is_flagged(self) -> None:
        # U+0958 (qa) is a composition exclusion: its NFC form is क + ◌़,
        # so a file containing the precomposed letter is NOT in NFC.
        text = "Деванагари: क़ौम в тексте."
        self.assertNotEqual(text, unicodedata.normalize("NFC", text))
        result = lint_text(text, TERMS)
        self.assertIn("devanagari_nfc_issue", types_of(result))

    def test_devanagari_nfc_is_clean(self) -> None:
        text = "Деванагари: धर्म в тексте. Термин самаса (samāsa) уже введен."
        result = lint_text(text, TERMS)
        self.assertNotIn("devanagari_nfc_issue", types_of(result))


class ProperNounTests(unittest.TestCase):
    TITLES = [{"ru": "махабхарата", "iast": "mahābhārata", "proper_noun": True}]

    def test_proper_noun_not_flagged_inconsistent(self) -> None:
        # Epic title legitimately appears as both «Махабхарата» and *mahābhārata*.
        text = (
            "Поэма Махабхарата огромна.\n\nВ Махабхарате много книг.\n\n"
            "Слово mahābhārata означает «великое сказание о бхаратах».\n\n"
            "Текст mahābhārata изучается давно."
        )
        result = lint_text(text, self.TITLES)
        self.assertNotIn("inconsistent_term_rendering", types_of(result))

    def test_proper_noun_not_flagged_missing_first_mention(self) -> None:
        result = lint_text("Поэма Махабхарата огромна.", self.TITLES)
        self.assertNotIn("missing_iast_on_first_mention", types_of(result))


class ConsistencyTests(unittest.TestCase):
    def test_free_variation_is_flagged(self) -> None:
        text = (
            "Первый абзац о самасе (samāsa) и ее типах.\n\n"
            "Дальше самаса обсуждается подробнее.\n\n"
            "Затем автор пишет про samāsa уже латиницей.\n\n"
            "И снова samāsa без кириллицы."
        )
        result = lint_text(text, TERMS)
        self.assertIn("inconsistent_term_rendering", types_of(result))


class RunArtifactTests(unittest.TestCase):
    def test_run_translit_lint_writes_artifact_and_merges_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "knowledge").mkdir()
            (root / "knowledge" / "sanskrit-terms.json").write_text(
                json.dumps(TERMS, ensure_ascii=False), encoding="utf-8"
            )
            run_dir = root / "runs" / "r1"
            run_dir.mkdir(parents=True)
            (run_dir / "normalized.md").write_text(
                "Жанр бхашьи сложился рано.", encoding="utf-8"
            )
            (run_dir / "verification.json").write_text(
                json.dumps({"run_id": "r1", "status": "prompt_ready", "warnings": []}),
                encoding="utf-8",
            )

            artifact = run_translit_lint(root, run_dir)

            doc = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertEqual(doc["status"], "completed")
            self.assertEqual(doc["source_file"], "normalized.md")
            self.assertEqual(
                doc["summary"]["finding_counts"]["missing_iast_on_first_mention"], 1
            )

            verification = json.loads(
                (run_dir / "verification.json").read_text(encoding="utf-8")
            )
            merged = [w for w in verification["warnings"] if w.get("source") == "translit_lint"]
            self.assertEqual(len(merged), 1)

            # Re-running must not duplicate warnings.
            run_translit_lint(root, run_dir)
            verification = json.loads(
                (run_dir / "verification.json").read_text(encoding="utf-8")
            )
            merged = [w for w in verification["warnings"] if w.get("source") == "translit_lint"]
            self.assertEqual(len(merged), 1)

    def test_load_terms_missing_file_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_sanskrit_terms(Path(tmp)), [])


if __name__ == "__main__":
    unittest.main()
