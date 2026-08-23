"""Offline tests for the sanity gate and the extraction chain (S0.4/S1.5)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ruwritingstyles.extract import (  # noqa: E402
    extract_best,
    extract_html,
    extract_pdf,
    sanity,
)

FIX = Path(__file__).resolve().parent / "fixtures" / "rcsi"


class TestSanityGateTests:
    def test_real_russian_passes(self):
        text = "Корпусная лингвистика изучает языкознание с помощью данных и методов анализа текстов. " * 40
        assert sanity(text)["verdict"] == "pass"

    def test_mojibake_fails(self):
        text = (FIX / "mojibake.txt").read_text(encoding="utf-8")
        assert sanity(text)["verdict"] == "fail"

    def test_empty_fails_without_raising(self):
        result = sanity(None)
        assert result["verdict"] == "fail"
        assert result["words"] == 0

    def test_english_text_passes_with_expect_cyrillic_false(self):
        text = "Corpus linguistics studies language data with quantitative methods and analysis. " * 40
        assert sanity(text, expect_cyrillic=False)["verdict"] == "pass"


class TestHtmlExtractionTests:
    def test_article_body_selector_yields_plungian_body(self):
        html = (FIX / "article_plungian.html").read_text(encoding="utf-8", errors="replace")
        text, prov = extract_html(html)
        assert text is not None
        assert prov["extractor"].startswith("bs4-")
        assert len(text.split()) > 3000

    def test_page_without_container_returns_none(self):
        text, prov = extract_html("<html><body><p>hi</p></body></html>")
        assert text is None
        assert prov["note"] == "no body container"


class TestPdfExtractionTests:
    def test_mini_english_pdf_passes(self):
        text, prov = extract_pdf(FIX / "mini_en.pdf")
        assert text is not None
        assert prov["extractor"].startswith("pymupdf")
        metrics = sanity(text, expect_cyrillic=False)
        assert metrics["verdict"] == "pass"


class TestExtractBestTests:
    def test_html_failure_falls_through_to_pdf(self):
        pdf_bytes = (FIX / "mini_en.pdf").read_bytes()
        text, provenance = extract_best(
            html="<html><body><p>short</p></body></html>",
            pdf_bytes=pdf_bytes,
            expect_cyrillic=False,
        )
        assert text is not None
        sources = [a.get("source") for a in provenance["attempts"]]
        assert "html" in sources and "pdf" in sources
        assert provenance["won"]["source"] == "pdf"

    def test_no_sources_returns_none_with_attempts(self):
        text, provenance = extract_best(html=None, pdf_bytes=None, expect_cyrillic=True)
        assert text is None
        assert provenance["won"] is None
