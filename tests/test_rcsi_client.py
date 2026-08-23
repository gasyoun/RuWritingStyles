"""Offline tests for the RCSI platform client (S1.1) against frozen fixtures."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ruwritingstyles import rcsi  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "rcsi"


def _fixture(name: str) -> bytes:
    return (FIX / name).read_bytes()


class TestIdentifyParsingTests:
    def test_identify_parses_repository_name(self):
        with mock.patch.object(rcsi, "_throttled_get", return_value=_fixture("identify.xml")):
            info = rcsi.identify("2306-5737")
        assert info["repository_name"]
        assert info["earliest_datestamp"]

    def test_identify_raises_on_error_payload(self):
        payload = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">'
            b"<error code=\"badArgument\">Text</error></OAI-PMH>"
        )
        with mock.patch.object(rcsi, "_throttled_get", return_value=payload):
            try:
                rcsi.identify("0869-5873")
            except rcsi.RcsiError as exc:
                assert "badArgument" in str(exc)
            else:
                raise AssertionError("expected RcsiError")


class TestListRecordsTests:
    def test_records_yield_dc_fields_and_token_page(self):
        payload = _fixture("list_records.xml").decode("utf-8", errors="replace")
        # The real page carries a resumptionToken; the follow-up call must
        # return a token-less page or the walk never terminates.
        import re as _re

        final_payload = _re.sub(r"<resumptionToken[^>]*>.*?</resumptionToken>", "", payload, flags=_re.S)
        served: list[str] = []

        def fake_get(url, binary=False, use_cache=True):
            assert "verb=ListRecords" in url
            if "resumptionToken=" in url:
                return final_payload
            assert not served, "first call must be the token-less ListRecords request"
            served.append(url)
            return payload

        with mock.patch.object(rcsi, "_throttled_get", side_effect=fake_get):
            records = list(rcsi.list_records("0869-5873"))
        assert records, "fixture must contain at least one record"
        first = records[0]
        assert first["oai_identifier"].startswith("oai:")
        assert "title" in first or "description" in first or "creator" in first


class TestArticleMetaTests:
    def test_citation_meta_ru_en_stay_separate(self):
        html = _fixture("article_plungian.html").decode("utf-8", errors="replace")

        class _Resp:
            @staticmethod
            def read():
                return html.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        captured_url = {}

        def fake_urlopen(request, timeout):
            captured_url["url"] = request.full_url if hasattr(request, "full_url") else request
            return _Resp()

        cache_dir = FIX.parent / ".cache-tmp"
        with mock.patch.dict(
            rcsi.os.environ,
            {"RWS_RCSI_CACHE_DIR": str(cache_dir)},
        ), mock.patch.object(rcsi.urllib.request, "urlopen", fake_urlopen), \
                mock.patch.object(rcsi.time, "sleep"):
            meta = rcsi.article_meta("0869-5873", "268311")
        assert meta["journal_slug"] == "0869-5873"
        assert meta["article_id"] == "268311"
        assert meta["doi"] == "10.31857/S0869587324090018"
        assert "Плунгян" in "".join(meta["authors_ru"])
        assert meta["title_ru"], "ru title variant must be kept"
        assert meta["pdf_url"].endswith(".pdf") or "/download/" in meta["pdf_url"]

    def test_galley_pdf_url_verbatim(self):
        meta = {"pdf_url": "https://journals.rcsi.science/x/article/download/1/2"}
        assert rcsi.galley_pdf_url(meta).endswith("/2")
