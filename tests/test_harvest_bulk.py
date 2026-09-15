"""Offline tests for the bulk 'include' harvest loop (D20/W2.4).

No network: ``rcsi.list_records``/``rcsi.article_meta`` are monkeypatched per
slug, mirroring the pattern in ``tests/test_journal_scope.py``'s
``TestHarvestSelectionWiring``. ``harvest.load_catalogue`` is monkeypatched to
a small synthetic catalogue so the loop's include/exclude filtering and its
per-journal failure isolation are both exercised without a live crawl.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ruwritingstyles import harvest  # noqa: E402

CATALOGUE = [
    {"slug": "AAA", "journal_name": "Journal A", "verdict": "include"},
    {"slug": "BBB", "journal_name": "Journal B", "verdict": "include"},
    {"slug": "CCC", "journal_name": "Journal C (excluded)", "verdict": "exclude"},
    {"slug": "DDD", "journal_name": "Journal D (uncertain)", "verdict": "uncertain"},
    {"slug": "EEE", "journal_name": "Journal E (unreachable)", "verdict": "include"},
]

_META_TEMPLATE = {
    "title_ru": "О лингвистических вопросах",
    "title_en": "On linguistic questions",
    "authors_ru": ["Иванов И. И."],
    "authors_en": ["Ivanov I. I."],
    "year": 2025,
    "volume": "1",
    "issue": "1",
    "firstpage": "1",
    "lastpage": "10",
    "language": "ru",
    "keywords_ru": ["лингвистика"],
    "keywords_en": ["linguistics"],
}


def _records_and_metas(slug: str, count: int) -> tuple[list[dict], dict[str, dict]]:
    records = []
    metas = {}
    for i in range(count):
        article_id = f"{slug}-{i}"
        records.append({"oai_identifier": f"oai:journals.rcsi.science:article/{article_id}"})
        meta = dict(_META_TEMPLATE)
        meta.update(
            {
                "journal_slug": slug,
                "article_id": article_id,
                "url": f"https://journals.rcsi.science/{slug}/article/view/{article_id}",
            }
        )
        metas[article_id] = meta
    return records, metas


class TestHarvestAllInclude:
    def test_loops_only_include_slugs_and_respects_the_cap(self, tmp_path, monkeypatch):
        monkeypatch.setattr(harvest, "load_catalogue", lambda root: CATALOGUE)
        monkeypatch.setattr(harvest, "_corpus_dir", lambda: (tmp_path, tmp_path / "quarantine"))

        per_slug_records = {
            "AAA": _records_and_metas("AAA", 3),
            "BBB": _records_and_metas("BBB", 1),
        }

        def fake_list_records(slug, since=None):
            if slug == "EEE":
                raise harvest.rcsi.RcsiError("simulated network failure")
            records, _ = per_slug_records[slug]
            return iter(records)

        def fake_article_meta(slug, article_id):
            _, metas = per_slug_records[slug]
            return dict(metas[article_id])

        monkeypatch.setattr("ruwritingstyles.rcsi.list_records", fake_list_records)
        monkeypatch.setattr("ruwritingstyles.rcsi.article_meta", fake_article_meta)

        overall = harvest.harvest_all_include(cap=2, dry_run=True, repo_root=tmp_path)

        assert overall["include_journals"] == 3  # AAA, BBB, EEE — CCC/DDD excluded
        assert overall["journals_harvested"] == 2  # AAA, BBB
        assert overall["journals_failed"] == 1
        assert overall["failed_journals"][0]["slug"] == "EEE"
        slugs_seen = {entry["slug"] for entry in overall["per_journal"]}
        assert slugs_seen == {"AAA", "BBB"}
        aaa_entry = next(e for e in overall["per_journal"] if e["slug"] == "AAA")
        assert aaa_entry["written"] == 2  # cap=2 even though 3 records exist

    def test_one_journal_failure_does_not_stop_the_run(self, tmp_path, monkeypatch):
        catalogue = [
            {"slug": "FAIL", "journal_name": "Fails", "verdict": "include"},
            {"slug": "OK", "journal_name": "Fine", "verdict": "include"},
        ]
        monkeypatch.setattr(harvest, "load_catalogue", lambda root: catalogue)
        monkeypatch.setattr(harvest, "_corpus_dir", lambda: (tmp_path, tmp_path / "quarantine"))

        records, metas = _records_and_metas("OK", 1)

        def fake_list_records(slug, since=None):
            if slug == "FAIL":
                raise harvest.rcsi.RcsiError("boom")
            return iter(records)

        def fake_article_meta(slug, article_id):
            return dict(metas[article_id])

        monkeypatch.setattr("ruwritingstyles.rcsi.list_records", fake_list_records)
        monkeypatch.setattr("ruwritingstyles.rcsi.article_meta", fake_article_meta)

        overall = harvest.harvest_all_include(cap=5, dry_run=True, repo_root=tmp_path)

        assert overall["journals_failed"] == 1
        assert overall["journals_harvested"] == 1
        assert overall["per_journal"][0]["slug"] == "OK"

    def test_writes_a_bulk_run_manifest(self, tmp_path, monkeypatch):
        monkeypatch.setattr(harvest, "load_catalogue", lambda root: [])
        monkeypatch.setattr(harvest, "_corpus_dir", lambda: (tmp_path, tmp_path / "quarantine"))
        monkeypatch.setattr(harvest, "repo_root_from", lambda: tmp_path)

        overall = harvest.harvest_all_include(cap=5, dry_run=True, repo_root=tmp_path)

        assert overall["include_journals"] == 0
        manifests = list((tmp_path / "runs" / "rcsi-harvest").glob("bulk-include-*.json"))
        assert manifests, "a bulk-include run manifest must be written"
