"""`rws run --journal <id>` flag + the journal-compliance presence check."""

import json
import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.cli import build_parser
from ruwritingstyles.report import _journal_section, journal_compliance

PROFILE = {
    "id": "test-journal",
    "name": "Test Journal",
    "max_chars": 40000,
    "citation_format": "GOST-R-7.0.100-2018",
    "transliteration_scheme": "IAST",
    "abstract_required": ["ru", "en"],
    "keywords_required": ["ru", "en"],
}


class JournalRunFlagTests(unittest.TestCase):
    def test_run_subcommand_accepts_journal(self) -> None:
        ns = build_parser().parse_args(["run", "doc.md", "--journal", "vestnik-spbu"])
        self.assertEqual(ns.journal, "vestnik-spbu")


class JournalComplianceSectionTests(unittest.TestCase):
    def _run_dir(self, doc: str) -> Path:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        (d / "project-context.json").write_text(
            json.dumps({"journal_profile": PROFILE}, ensure_ascii=False), encoding="utf-8"
        )
        (d / "normalized.md").write_text(doc, encoding="utf-8")
        return d

    def test_flags_missing_english_abstract_and_keywords(self) -> None:
        # Russian abstract + keywords present, English absent — the real gúṇa case.
        section = _journal_section(self._run_dir(
            "# Заголовок\n\n**Аннотация.** Текст.\n\n**Ключевые слова:** гуна, словарь.\n\nТекст."
        ))
        self.assertIn("Аннотация (ru, en): ru ✓, en ⚠ нет", section)
        self.assertIn("Ключевые слова (ru, en): ru ✓, en ⚠ нет", section)
        self.assertIn("/ 40000 знаков — OK", section)

    def test_both_languages_present_pass(self) -> None:
        section = _journal_section(self._run_dir(
            "# T\n\n**Аннотация.** Текст.\n\n## Abstract\n\nText.\n\n"
            "**Ключевые слова:** a.\n\n**Keywords:** b.\n"
        ))
        self.assertIn("ru ✓, en ✓", section)
        self.assertNotIn("⚠ нет", section)


class AbstractWordCountTests(unittest.TestCase):
    def test_counts_words_and_flags_over_limit(self) -> None:
        profile = {"name": "J", "abstract_required": ["ru"], "abstract_max_words": 5}
        comp = journal_compliance(
            "# T\n\n**Аннотация.** один два три четыре пять шесть.\n\nТекст.\n", profile
        )
        self.assertEqual(
            comp["abstract"][0],
            {"lang": "ru", "present": True, "words": 6, "max": 5, "over": 1},
        )

    def test_within_limit_reports_zero_over(self) -> None:
        profile = {"name": "J", "abstract_required": ["ru"], "abstract_max_words": 200}
        comp = journal_compliance("**Аннотация.** один два три.\n\nX.\n", profile)
        item = comp["abstract"][0]
        self.assertEqual(item["words"], 3)
        self.assertEqual(item["over"], 0)

    def test_no_word_fields_without_limit(self) -> None:
        # Profiles without abstract_max_words keep the original presence-only shape.
        comp = journal_compliance("**Аннотация.** один два.", {"name": "J", "abstract_required": ["ru"]})
        self.assertEqual(comp["abstract"][0], {"lang": "ru", "present": True})

    def test_keywords_word_limit_flags_over(self) -> None:
        # Восток (Oriens): keywords capped at 10 words (keywords_max_words).
        profile = {"name": "J", "keywords_required": ["ru"], "keywords_max_words": 3}
        comp = journal_compliance(
            "**Ключевые слова:** санскрит, лексикография, стиль, корпус.\n\nX.\n",
            profile,
        )
        self.assertEqual(
            comp["keywords"][0],
            {"lang": "ru", "present": True, "words": 4, "max": 3, "over": 1},
        )

    def test_keywords_without_limit_keep_presence_only_shape(self) -> None:
        profile = {"name": "J", "keywords_required": ["ru"]}
        comp = journal_compliance("**Ключевые слова:** санскрит.\n", profile)
        self.assertEqual(comp["keywords"][0], {"lang": "ru", "present": True})

    def test_absent_abstract_has_no_word_fields(self) -> None:
        profile = {"name": "J", "abstract_required": ["en"], "abstract_max_words": 200}
        comp = journal_compliance("**Аннотация.** только русская.\n\nX.\n", profile)
        self.assertEqual(comp["abstract"][0], {"lang": "en", "present": False})

    def test_section_renders_word_count(self) -> None:
        profile = {
            "id": "j", "name": "J", "max_chars": 40000,
            "abstract_required": ["ru"], "abstract_max_words": 5, "keywords_required": [],
        }
        d = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        (d / "project-context.json").write_text(
            json.dumps({"journal_profile": profile}, ensure_ascii=False), encoding="utf-8"
        )
        (d / "normalized.md").write_text(
            "# T\n\n**Аннотация.** один два три четыре пять шесть.\n", encoding="utf-8"
        )
        section = _journal_section(d)
        self.assertIn("6/5 слов", section)
        self.assertIn("+1 сверх лимита", section)


if __name__ == "__main__":
    unittest.main()
