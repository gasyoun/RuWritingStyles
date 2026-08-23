"""Offline tests for the subject classifier (S1.4)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ruwritingstyles.journal_scope import classify_article, classify_journal  # noqa: E402


class TestArticleClassificationTests:
    def test_linguistic_title_includes(self):
        verdict = classify_article({
            "title_ru": "Корпусная лингвистика на современном этапе",
            "keywords_ru": ["корпусная лингвистика"],
        })
        assert verdict["verdict"] == "include"
        assert verdict["expect_cyrillic"] is True

    def test_general_science_excludes(self):
        verdict = classify_article({
            "title_ru": "О применении нейронных сетей в клинической медицине",
            "keywords_ru": ["нейронные сети", "медицина"],
        })
        assert verdict["verdict"] == "exclude"

    def test_unmatched_is_uncertain(self):
        verdict = classify_article({"title_ru": "Годовой отчёт совета", "keywords_ru": []})
        assert verdict["verdict"] == "uncertain"

    def test_english_language_meta_sets_expect_cyrillic_false(self):
        verdict = classify_article({
            "title_en": "Greek in contact with Italo-Romance",
            "language": "en",
        })
        assert verdict["expect_cyrillic"] is False

    def test_ru_language_meta_keeps_cyrillic_expectation(self):
        verdict = classify_article({"title_en": "Corpus linguistics", "language": "ru"})
        assert verdict["expect_cyrillic"] is True

    def test_oai_subject_rescues_uncertain(self):
        verdict = classify_article(
            {"title_ru": "К проблеме классификации"},
            selection_record={"subject": ["языкознание", "филология"]},
        )
        assert verdict["verdict"] == "include"


class TestJournalClassificationTests:
    def test_scope_text_verdicts(self):
        include = classify_journal("Журнал публикует статьи по языкознанию и грамматике")
        exclude = classify_journal("Исследования по физике плазмы и биологии клетки")
        assert include["verdict"] == "include"
        assert exclude["verdict"] == "exclude"
