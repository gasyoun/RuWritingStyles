"""Offline tests for the wave-2 catalogue crawl (W2.1, D05).

Fixtures mirror the measured 30-08-2026 platform layout: paginated index over
``/index?searchInitial=&journalsPage=N`` with
``<h2 class="journalNameMobli"><a href="{BASE}/{slug}">{Name}</a></h2>``
entries, and the Aims & Scope paragraph under
``/about/editorialPolicies`` ``<div id="focusAndScope">``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ruwritingstyles import harvest, rcsi  # noqa: E402
from ruwritingstyles.journal_scope import classify_journal  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "rcsi"

BASE = rcsi.BASE


def _index_page(entries: list[tuple[str, str]], *, next_page: int | None) -> str:
    links = "".join(
        f'<h2 class="journalNameMobli"><a href="{BASE}/{slug}">{name}</a></h2>'
        for slug, name in entries
    )
    pager = (
        f'<a href="{BASE}/index?searchInitial=&amp;journalsPage={next_page}#journals">next</a>'
        if next_page
        else ""
    )
    return f"<html><body>{links}{pager}</body></html>"


def _policies_page(scope_text: str, *, with_anchor: bool = True) -> str:
    anchor = f'<div id="focusAndScope"><p>{scope_text}</p></div>' if with_anchor else ""
    return f"<html><body><div>{anchor}</div></body></html>"


def _identify_xml(name: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">'
        "<Identify><repositoryName>"
        f"{name}"
        "</repositoryName><earliestDatestamp>2000-01-01</earliestDatestamp>"
        "<adminEmail>a@b.c</adminEmail></Identify></OAI-PMH>"
    )


class TestIndexWalk:
    def test_walk_index_follows_pagination_and_dedupes(self):
        last_page = _index_page(
            [("2619-032X", "Культура: теория и практика")], next_page=None
        )
        pages = {
            BASE + "/index?searchInitial=&journalsPage=1": _index_page(
                [("0002-1881", "Agricultural Chemistry")], next_page=2
            ),
            BASE + "/index?searchInitial=&journalsPage=2": _index_page(
                [("2306-5737", "Acta Linguistica Petropolitana"), ("vramn", "Вестник РАН")], next_page=3
            ),
            # out-of-range page: the platform serves the final page forever
            BASE + "/index?searchInitial=&journalsPage=3": last_page,
            BASE + "/index?searchInitial=&journalsPage=4": last_page,
            BASE + "/index?searchInitial=&journalsPage=5": last_page,
        }

        def fake_get(url, binary=False, use_cache=True):
            if url not in pages:
                return "<html><body></body></html>"
            return pages[url]

        with mock.patch.object(rcsi, "_throttled_get", side_effect=fake_get):
            index = rcsi.walk_index()
        assert index == {
            "0002-1881": "Agricultural Chemistry",
            "2306-5737": "Acta Linguistica Petropolitana",
            "vramn": "Вестник РАН",
            "2619-032X": "Культура: теория и практика",
        }

    def test_walk_stops_on_repeated_tail_page(self):
        tail = _index_page([("2225-4293", "Физические основы приборостроения")], next_page=9)

        def fake_get(url, binary=False, use_cache=True):
            return tail  # every page identical — repeat-detection must stop at page 2

        with mock.patch.object(rcsi, "_throttled_get", side_effect=fake_get), \
                mock.patch.object(rcsi, "_MAX_INDEX_PAGES", 10):
            served = list(rcsi.index_pages())
        assert [page for page, _entries in served] == [1]

    def test_non_issn_slug_is_kept(self):
        html = _index_page([("vramn", "Вестник РАН")], next_page=None)
        with mock.patch.object(rcsi, "_throttled_get", return_value=html):
            index = rcsi.walk_index()
        assert "vramn" in index

    def test_walk_raises_when_layout_changes(self):
        with mock.patch.object(rcsi, "_throttled_get", return_value="<html><body>layout changed</body></html>"):
            try:
                rcsi.walk_index()
            except rcsi.RcsiError as exc:
                assert "no journals" in str(exc)
            else:
                raise AssertionError("expected RcsiError")


class TestScopeText:
    def test_scope_paragraph_extracted(self):
        with mock.patch.object(
            rcsi,
            "_throttled_get",
            return_value=_policies_page("The journal publishes papers in linguistics and philology."),
        ):
            text = rcsi.fetch_scope_text("2306-5737")
        assert "linguistics" in text

    def test_missing_anchor_returns_empty_string(self):
        with mock.patch.object(rcsi, "_throttled_get", return_value=_policies_page("", with_anchor=False)):
            assert rcsi.fetch_scope_text("0002-1881") == ""

    def test_http_error_returns_empty_string(self):
        with mock.patch.object(rcsi, "_throttled_get", side_effect=rcsi.RcsiError("404")):
            assert rcsi.fetch_scope_text("0002-1881") == ""


class TestClassifyJournalSmoke:
    def test_linguistics_scope_includes(self):
        verdict = classify_journal(
            "The key topics include theoretical linguistics, comparative linguistics and language typology."
        )
        assert verdict["verdict"] == "include"
        assert "linguistics" in verdict["positive"]

    def test_negative_only_scope_excludes(self):
        verdict = classify_journal("The journal covers physics, chemistry and biology of condensed matter.")
        assert verdict["verdict"] == "exclude"

    def test_empty_scope_is_uncertain(self):
        assert classify_journal("")["verdict"] == "uncertain"


class TestBuildCatalogue:
    def _setup(self, tmp_path: Path):
        pages = {
            BASE + "/index?searchInitial=&journalsPage=1": _index_page(
                [("2306-5737", "Acta Linguistica Petropolitana"), ("0002-1881", "Agricultural Chemistry")],
                next_page=None,
            ),
            BASE + "/index?searchInitial=&journalsPage=2": "<html><body></body></html>",
            BASE + "/2306-5737/about/editorialPolicies": _policies_page(
                "The journal publishes works in linguistics, language typology and philology."
            ),
            BASE + "/0002-1881/about/editorialPolicies": _policies_page(
                "Research in physics, chemistry and soil science of agricultural systems."
            ),
        }
        identifies = {
            "2306-5737": _identify_xml("Acta Linguistica Petropolitana"),
            "0002-1881": _identify_xml("Agricultural Chemistry"),
        }

        def fake_get(url, binary=False, use_cache=True):
            if url in pages:
                return pages[url]
            if "/oai?verb=Identify" in url:
                slug = url.split("/")[-2]
                return identifies[slug]
            raise AssertionError(f"unexpected URL {url}")

        return fake_get

    def test_catalogue_written_with_verdicts_and_evidence(self, tmp_path):
        fake_get = self._setup(tmp_path)
        with mock.patch.object(rcsi, "_throttled_get", side_effect=fake_get):
            catalogue = harvest.build_catalogue(tmp_path, checked_on="30-08-2026")
        by_slug = {record["slug"]: record for record in catalogue}
        assert set(by_slug) == {"2306-5737", "0002-1881"}
        assert by_slug["2306-5737"]["verdict"] == "include"
        assert by_slug["2306-5737"]["scope_text_excerpt"].startswith("The journal publishes")
        assert by_slug["2306-5737"]["repository_name"] == "Acta Linguistica Petropolitana"
        assert by_slug["0002-1881"]["verdict"] == "exclude"
        # every journal gets a record, exclusions included (D05)
        persisted = json.loads((tmp_path / "knowledge" / "rcsi" / "catalogue.json").read_text(encoding="utf-8"))
        assert {record["slug"] for record in persisted} == {"2306-5737", "0002-1881"}
        for record in persisted:
            assert record["checked_on"] == "30-08-2026"

    def test_identify_failure_degrades_to_uncertain(self, tmp_path):
        pages = {
            BASE + "/index?searchInitial=&journalsPage=1": _index_page(
                [("0320-9601", "Some Journal")], next_page=None
            ),
            BASE + "/index?searchInitial=&journalsPage=2": "<html><body></body></html>",
            BASE + "/0320-9601/about/editorialPolicies": _policies_page(
                "Studies in linguistics and ancient languages."
            ),
        }

        def fake_get(url, binary=False, use_cache=True):
            if url in pages:
                return pages[url]
            if "/oai?verb=Identify" in url:
                raise rcsi.RcsiError("HTTP 500")
            raise AssertionError(f"unexpected URL {url}")

        with mock.patch.object(rcsi, "_throttled_get", side_effect=fake_get):
            catalogue = harvest.build_catalogue(tmp_path, checked_on="30-08-2026")
        record = catalogue[0]
        assert record["slug"] == "0320-9601"
        assert record["verdict"] == "include"  # classifier still saw the scope text
        assert record["repository_name"] == ""
        assert any("identify failed" in entry for entry in record["evidence_other"])

    def test_output_schema_validity(self, tmp_path):
        fake_get = self._setup(tmp_path)
        schema = json.loads(
            (Path(__file__).resolve().parents[1] / "schemas" / "rcsi-catalogue.schema.json").read_text(encoding="utf-8")
        )
        from ruwritingstyles.schema_validation import validate_json_schema

        with mock.patch.object(rcsi, "_throttled_get", side_effect=fake_get):
            catalogue = harvest.build_catalogue(tmp_path, checked_on="30-08-2026")
        assert list(validate_json_schema(catalogue, schema)) == []


class TestFixturesMatchLiveLayout:
    """The frozen real pages must satisfy the crawl contract (S1.9 discipline)."""

    def test_catalogue_page_fixture_matches_journal_anchor(self):
        html = (FIXTURES / "catalogue_page1.html").read_text(encoding="utf-8")
        entries = [
            (slug, rcsi._anchor_text(name))
            for slug, name in rcsi._JOURNAL_ANCHOR_RE.findall(html)
        ]
        # 50 journal entries on the frozen page 1 (49 at the 19-08 probe; the
        # platform grows). 0869-5873 sits on a later page — the walk finds it.
        assert len(entries) >= 40, f"page 1 must carry the ~50 journal entries, got {len(entries)}"
        slugs = [slug for slug, _name in entries]
        assert "2306-5737" in slugs
        assert all("/" not in slug for slug in slugs), "slug is a URL path component, never keyed on ISSN"
        names = [name for _slug, name in entries]
        assert any("Acta" in name for name in names)
        # markup-only URLs (css/js/meta) never leak in as journals
        assert "index" not in slugs and "js" not in slugs and "lib" not in slugs

    def test_policy_page_fixture_has_scope_paragraph(self):
        html = (FIXTURES / "editorial_policies.html").read_text(encoding="utf-8")
        assert '<div id="focusAndScope"' in html
        with mock.patch.object(rcsi, "_throttled_get", return_value=html):
            text = rcsi.fetch_scope_text("2306-5737")
        assert len(text.split()) >= 20, "Aims & Scope paragraph must be substantive"

    def test_full_crawl_runs_offline_over_frozen_fixtures(self, tmp_path):
        page1 = (FIXTURES / "catalogue_page1.html").read_text(encoding="utf-8")
        policies = (FIXTURES / "editorial_policies.html").read_text(encoding="utf-8")

        def fake_get(url, binary=False, use_cache=True):
            if "journalsPage=1" in url:
                return page1
            if "editorialPolicies" in url:
                return policies
            if "journalsPage=" in url:
                return "<html><body></body></html>"  # past the end
            if "/oai?verb=Identify" in url:
                raise rcsi.RcsiError("offline fixture run: Identify not served")
            raise AssertionError(f"unexpected URL {url}")

        with mock.patch.object(rcsi, "_throttled_get", side_effect=fake_get):
            catalogue = harvest.build_catalogue(tmp_path, checked_on="30-08-2026")
        assert len(catalogue) >= 40
        by_slug = {record["slug"]: record for record in catalogue}
        # every real Identify fetch failed in this offline run, so records carry
        # the degradation evidence and the catalogue-page name stands in
        assert all("identify failed" in " ".join(record["evidence_other"]) for record in catalogue)
        acta = by_slug["2306-5737"]
        assert acta["journal_name"] == "Acta Linguistica Petropolitana. Transactions of the Institute for Linguistic Studies"
        assert acta["scope_text_excerpt"], "Acta scope paragraph must come from the frozen policy page"