"""Tests for the pinned manifest and the D13 corpus-verify guarantee (S1.8)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ruwritingstyles.harvest import build_stem, corpus_verify, load_pinned_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class TestManifestShapeTests:
    def test_five_unique_pinned_urls(self):
        pinned = load_pinned_manifest(ROOT)
        assert len(pinned) == 5
        urls = {entry["url"] for entry in pinned}
        assert len(urls) == 5
        for entry in pinned:
            assert entry["slug"] and str(entry["article_id"]).isdigit()

    def test_expected_stems_backfilled_after_harvest(self):
        pinned = load_pinned_manifest(ROOT)
        missing = [entry["url"] for entry in pinned if not entry.get("expected_stem")]
        assert not missing, f"expected_stem must be backfilled after the live harvest: {missing}"


class TestStemTests:
    def test_stem_follows_year_surname_title_rule(self):
        stem = build_stem({
            "year": 2024,
            "authors_ru": ["Плунгян Владимир Александрович"],
            "title_ru": "Корпусная лингвистика на современном этапе",
        })
        parts = stem.split("_")
        assert parts[0] == "2024"
        assert parts[1] == "Plungyan"
        assert "Korpusnaya" in stem and len(stem) <= 120

    def test_latin_authors_pass_through(self):
        stem = build_stem({
            "year": 2021,
            "authors_en": ["Chilingaryan K.P."],
            "title_en": "Corpus Linguistics: Theory Vs Methodilogy",
        })
        assert stem.startswith("2021_Chilingaryan_")


def _make_fake_repo(tmp: Path, *, with_bibliography_row: bool) -> tuple[Path, Path]:
    repo_root = tmp / "repo"
    (repo_root / "schemas").mkdir(parents=True)
    (repo_root / "knowledge").mkdir()
    for name in ("journal-profile.schema.json", "article-sidecar.schema.json"):
        (repo_root / "schemas" / name).write_text((ROOT / "schemas" / name).read_text(encoding="utf-8"), encoding="utf-8")
    pinned_dir = repo_root / "knowledge" / "rcsi"
    pinned_dir.mkdir(parents=True)

    sidecar = {
        "stem": "2024_Plungyan_test-entry",
        "journal_slug": "0869-5873",
        "article_id": "268311",
        "url": "https://journals.rcsi.science/0869-5873/article/view/268311",
        "doi": "10.31857/TEST",
        "title_ru": "Корпусная лингвистика на современном этапе",
        "authors_ru": ["Плунгян В. А."],
        "year": 2024,
        "extraction": {"source": "html", "extractor": "bs4-article", "verdict": "pass",
                        "sanity": {"cyrillic_ratio": 0.9, "replacement_ratio": 0.0,
                                    "word_hit_rate": 0.5, "words": 400},
                        "harvested_on": "23-08-2026"},
        "selection": {"verdict": "include", "matched_terms": ["лингвистика"]},
    }
    text = ("Корпусная лингвистика на современном этапе изучает данные языка. " * 10)
    corpus_dir = tmp / "corpus"
    corpus_dir.mkdir(parents=True)
    (corpus_dir / "2024_Plungyan_test-entry.txt").write_text(text, encoding="utf-8", newline="\n")
    (corpus_dir / "2024_Plungyan_test-entry.json").write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    bib_row = {
        "id": "Плунгян 2024", "author": "Плунгян В. А.", "year": 2024,
        "title": "Корпусная лингвистика на современном этапе", "kind": "article",
        "doi": "10.31857/TEST", "tags": [],
    } if with_bibliography_row else None
    bibliography = [row for row in [bib_row] if row]
    (repo_root / "knowledge" / "bibliography.json").write_text(
        json.dumps(bibliography, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (pinned_dir / "pinned_articles.json").write_text(json.dumps([{
        "url": sidecar["url"], "slug": "0869-5873", "article_id": "268311",
        "expected_stem": "2024_Plungyan_test-entry",
        "search_phrase": "лингвистика на современном",
    }], ensure_ascii=False), encoding="utf-8")
    return repo_root, corpus_dir


class TestCorpusVerifyTests:
    def test_all_checks_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_root, corpus_dir = _make_fake_repo(tmp_path, with_bibliography_row=True)
            results = corpus_verify(repo_root=repo_root, corpus_dir=corpus_dir)
            assert len(results) == 1
            assert results[0]["ok"] is True, results[0]["problems"]

    def test_missing_bibliography_row_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_root, corpus_dir = _make_fake_repo(tmp_path, with_bibliography_row=False)
            results = corpus_verify(repo_root=repo_root, corpus_dir=corpus_dir)
            assert results[0]["ok"] is False
            assert any("bibliography" in p for p in results[0]["problems"])

    def test_missing_text_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_root, corpus_dir = _make_fake_repo(tmp_path, with_bibliography_row=True)
            (corpus_dir / "2024_Plungyan_test-entry.txt").unlink()
            results = corpus_verify(repo_root=repo_root, corpus_dir=corpus_dir)
            assert results[0]["ok"] is False
            assert any("missing" in p or "empty" in p for p in results[0]["problems"])
