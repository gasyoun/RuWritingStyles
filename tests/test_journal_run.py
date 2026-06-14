"""`rws run --journal <id>` flag + the journal-compliance presence check."""

import json
import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.cli import build_parser
from ruwritingstyles.report import _journal_section

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


if __name__ == "__main__":
    unittest.main()
