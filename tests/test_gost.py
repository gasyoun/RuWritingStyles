import json
import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.bibtex import (
    bibtex_key,
    entry_to_bibtex,
    generate_bibtex,
    matched_entries,
    write_bibtex,
)
from ruwritingstyles.gost import format_gost, render_gost_list, sort_entries


BOOK = {
    "id": "Zaliznyak 2004",
    "author": "Зализняк А. А.",
    "year": 2004,
    "title": "Древненовгородский диалект",
    "kind": "book",
    "edition": "2-е изд., перераб. с учетом материала находок 1995–2003 гг.",
    "city": "М.",
    "publisher": "Языки славянской культуры",
    "pages": "872",
}

ARTICLE = {
    "id": "Elizarenkova 1995",
    "author": "Елизаренкова Т. Я.",
    "year": 1995,
    "title": "О языке ведийской поэзии",
    "kind": "article",
    "journal": "Вопросы языкознания",
    "number": "3",
    "pages": "12–29",
}

LATIN_BOOK = {
    "id": "Whitney 1889",
    "author": "Whitney W. D.",
    "year": 1889,
    "title": "Sanskrit Grammar",
    "kind": "book",
    "edition": "2nd ed.",
    "city": "Cambridge (Mass.)",
    "publisher": "Harvard University Press",
    "pages": "552",
}

WEB = {
    "id": "NKRYA",
    "author": "НКРЯ",
    "year": 2024,
    "title": "Национальный корпус русского языка",
    "kind": "web",
    "url": "https://ruscorpora.ru",
}


class FormatGostTests(unittest.TestCase):
    def test_book_reference_format(self) -> None:
        self.assertEqual(
            format_gost(BOOK),
            "Зализняк А. А. Древненовгородский диалект. — "
            "2-е изд., перераб. с учетом материала находок 1995–2003 гг. — "
            "М. : Языки славянской культуры, 2004. — 872 с.",
        )

    def test_article_reference_format(self) -> None:
        self.assertEqual(
            format_gost(ARTICLE),
            "Елизаренкова Т. Я. О языке ведийской поэзии // Вопросы языкознания. — "
            "1995. — № 3. — С. 12–29.",
        )

    def test_latin_book_with_edition(self) -> None:
        # Latin-script entries take source-language designators (p., not с.).
        self.assertEqual(
            format_gost(LATIN_BOOK),
            "Whitney W. D. Sanskrit Grammar. — 2nd ed. — "
            "Cambridge (Mass.) : Harvard University Press, 1889. — 552 p.",
        )

    def test_latin_article_uses_latin_designators(self) -> None:
        entry = {
            "id": "Feinstein Cicchetti 1990",
            "author": "Feinstein A. R., Cicchetti D. V.",
            "year": 1990,
            "title": "High agreement but low kappa: I. The problems of two paradoxes",
            "kind": "article",
            "journal": "Journal of Clinical Epidemiology",
            "volume": "43",
            "number": "6",
            "pages": "543–549",
        }
        self.assertEqual(
            format_gost(entry),
            "Feinstein A. R., Cicchetti D. V. High agreement but low kappa: "
            "I. The problems of two paradoxes // Journal of Clinical Epidemiology. — "
            "1990. — Vol. 43. — No. 6. — P. 543–549.",
        )

    def test_web_resource(self) -> None:
        self.assertEqual(
            format_gost(WEB),
            "НКРЯ Национальный корпус русского языка. — URL: https://ruscorpora.ru.",
        )

    def test_minimal_legacy_entry_renders_without_crash(self) -> None:
        legacy = {"id": "X 2000", "author": "Автор А. А.", "year": 2000, "title": "Заглавие"}
        self.assertEqual(format_gost(legacy), "Автор А. А. Заглавие. — 2000.")


class SortAndRenderTests(unittest.TestCase):
    def test_cyrillic_sorts_before_latin(self) -> None:
        ordered = sort_entries([LATIN_BOOK, BOOK, ARTICLE])
        self.assertEqual(
            [e["id"] for e in ordered],
            ["Elizarenkova 1995", "Zaliznyak 2004", "Whitney 1889"],
        )

    def test_render_numbered_list(self) -> None:
        text = render_gost_list([LATIN_BOOK, BOOK])
        lines = text.splitlines()
        self.assertEqual(lines[0], "# Литература")
        self.assertTrue(lines[2].startswith("1. Зализняк А. А."))
        self.assertTrue(lines[3].startswith("2. Whitney W. D."))


class BibtexFromKnowledgeTests(unittest.TestCase):
    def _make_repo(self, tmp: str) -> Path:
        root = Path(tmp)
        knowledge = root / "knowledge"
        knowledge.mkdir(parents=True)
        (knowledge / "bibliography.json").write_text(
            json.dumps([BOOK, ARTICLE, LATIN_BOOK], ensure_ascii=False),
            encoding="utf-8",
        )
        return root

    def test_bibtex_key_is_ascii_lowercase(self) -> None:
        self.assertEqual(bibtex_key(BOOK), "zaliznyak2004")

    def test_entry_to_bibtex_book_fields(self) -> None:
        bib = entry_to_bibtex(BOOK)
        self.assertIn("@book{zaliznyak2004,", bib)
        self.assertIn("author = {Зализняк А. А.}", bib)
        self.assertIn("address = {М.}", bib)

    def test_matched_entries_only_cited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_repo(tmp)
            text = "Как показано в (Zaliznyak 2004), система диалекта устойчива."
            entries = matched_entries(root, text)
            self.assertEqual([e["id"] for e in entries], ["Zaliznyak 2004"])

    def test_write_bibtex_emits_bib_and_gost_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_repo(tmp)
            run_dir = root / "runs" / "r1"
            run_dir.mkdir(parents=True)
            (run_dir / "revised.md").write_text(
                "Ср. (Zaliznyak 2004) и (Whitney 1889).", encoding="utf-8"
            )
            write_bibtex(run_dir, root)
            bib = (run_dir / "references.bib").read_text(encoding="utf-8")
            gost = (run_dir / "references-gost.md").read_text(encoding="utf-8")
            self.assertIn("@book{zaliznyak2004,", bib)
            self.assertIn("@book{whitney1889,", bib)
            self.assertIn("1. Зализняк А. А.", gost)
            self.assertIn("2. Whitney W. D.", gost)

    def test_generate_bibtex_without_repo_root_keeps_header(self) -> None:
        header = generate_bibtex("run-x", "")
        self.assertIn("% BibTeX for RuWritingStyles Run: run-x", header)


if __name__ == "__main__":
    unittest.main()
