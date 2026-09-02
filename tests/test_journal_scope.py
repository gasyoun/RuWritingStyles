"""Offline tests for the subject classifier (S1.4, W2.2).

Two layers, mirroring D15:

* inline unit tests over synthetic records (class semantics);
* fixture-backed tests over ``tests/fixtures/rcsi/article_meta_samples.json`` —
  six real article metas frozen live 02-09-2026 through
  ``tools/export_rcsi_fixtures.py``, one per verdict class, including the
  OAI-dc:subject rescue path and an English-language article.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ruwritingstyles import harvest  # noqa: E402
from ruwritingstyles.journal_scope import classify_article, classify_journal  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "rcsi"


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


def _load_article_samples() -> list[dict]:
    path = FIXTURES / "article_meta_samples.json"
    samples = json.loads(path.read_text(encoding="utf-8"))
    assert samples, "frozen article-meta sample set must not be empty"
    return samples


class TestArticleClassificationFixtures:
    """W2.2: the classifier of D04 against live-frozen platform records."""

    def test_every_frozen_sample_classifies_to_its_expected_verdict(self):
        for sample in _load_article_samples():
            verdict = classify_article(
                sample["meta"],
                selection_record=sample["selection_record"] or None,
            )
            assert verdict["verdict"] == sample["expect"]["verdict"], (
                f"{sample['journal_slug']}/{sample['article_id']}:"
                f" got {verdict['verdict']}, expected {sample['expect']['verdict']}"
            )
            assert verdict["expect_cyrillic"] is sample["expect"]["expect_cyrillic"], (
                f"{sample['journal_slug']}/{sample['article_id']}: expect_cyrillic drifted"
            )

    def test_fixture_set_covers_all_verdict_classes(self):
        verdicts = {sample["expect"]["verdict"] for sample in _load_article_samples()}
        assert {"include", "exclude", "uncertain"} <= verdicts

    def test_fixture_set_covers_the_english_language_case(self):
        en_samples = [s for s in _load_article_samples() if not s["expect"]["expect_cyrillic"]]
        assert en_samples, "an English-language article (expect_cyrillic=False) must stay frozen"
        assert all(s["meta"].get("language", "").startswith("en") for s in en_samples)

    def test_oai_subject_rescues_a_title_only_uncertain_record(self):
        rescue = [
            s for s in _load_article_samples() if s["selection_record"].get("subject")
        ]
        assert rescue, "one frozen sample must carry the dc:subject rescue path"
        for sample in rescue:
            verdict = classify_article(sample["meta"], selection_record=sample["selection_record"])
            plain = classify_article(
                {k: v for k, v in sample["meta"].items() if k not in ("keywords_ru", "keywords_en")}
            )
            assert plain["verdict"] == "uncertain", "rescue sample must be uncertain without dc:subject"
            assert verdict["verdict"] == "include"


class TestHarvestSelectionWiring:
    """D04 filters over OAI Dublin Core subject plus title and keywords."""

    def test_harvest_journal_forwards_oai_subject_to_the_classifier(self, tmp_path, monkeypatch):
        record = {
            "oai_identifier": "oai:journals.rcsi.science:article/990001",
            "subject": ["фольклор; былины; метрика"],
        }
        meta = {
            "journal_slug": "2619-032X",
            "article_id": "990001",
            "url": "https://journals.rcsi.science/2619-032X/article/view/990001",
            "title_ru": "О стихотворном размере былин",
            "title_en": "On the verse metre of bylinas",
            "authors_ru": ["Иванов И. И."],
            "authors_en": ["Ivanov I. I."],
            "year": 2025,
            "volume": "1",
            "issue": "1",
            "firstpage": "1",
            "lastpage": "10",
            "language": "ru",
            "keywords_ru": [],
            "keywords_en": [],
        }
        monkeypatch.setattr(
            "ruwritingstyles.rcsi.list_records", lambda *a, **k: iter([record])
        )
        monkeypatch.setattr(
            "ruwritingstyles.rcsi.article_meta", lambda *a, **k: dict(meta)
        )
        monkeypatch.setattr(harvest, "_corpus_dir", lambda: (tmp_path, tmp_path / "quarantine"))

        summary = harvest.harvest_journal("2619-032X", dry_run=True)

        assert summary["written"], "the rescuable article must reach the written list"
        assert summary["written"][0]["verdict"] == "include"

    def test_harvest_journal_without_oai_subject_stays_uncertain(self, tmp_path, monkeypatch):
        record = {"oai_identifier": "oai:journals.rcsi.science:article/990002"}
        meta = {
            "journal_slug": "2619-032X",
            "article_id": "990002",
            "url": "https://journals.rcsi.science/2619-032X/article/view/990002",
            "title_ru": "Отчёт о работе отделения за год",
            "title_en": "Branch annual report",
            "authors_ru": [],
            "authors_en": [],
            "year": 2025,
            "volume": "1",
            "issue": "1",
            "firstpage": "1",
            "lastpage": "2",
            "language": "ru",
            "keywords_ru": [],
            "keywords_en": [],
        }
        monkeypatch.setattr(
            "ruwritingstyles.rcsi.list_records", lambda *a, **k: iter([record])
        )
        monkeypatch.setattr(
            "ruwritingstyles.rcsi.article_meta", lambda *a, **k: dict(meta)
        )
        monkeypatch.setattr(harvest, "_corpus_dir", lambda: (tmp_path, tmp_path / "quarantine"))

        summary = harvest.harvest_journal("2619-032X", dry_run=True)

        assert summary["written"][0]["verdict"] == "uncertain"
