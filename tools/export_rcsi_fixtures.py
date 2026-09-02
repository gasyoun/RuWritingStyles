"""Freeze RCSI network fixtures for offline tests (S1.9).

Fetches each fixture exactly once through the production client's throttle/cache
and writes it under tests/fixtures/rcsi/. Tests never touch the network; this
script is re-run only when the platform contract demonstrably changes.

Fixtures written:
  identify.xml          - OAI Identify for slug 2306-5737
  list_records.xml      - one ListRecords page incl. a resumptionToken
  article_plungian.html - the Плунгян article page (citation_* metas + body)
  mini_en.pdf           - a tiny generated PDF with English text (PyMuPDF)
  mojibake.txt          - a synthetic mojibake sample (gate must fail it)
  catalogue_page1.html  - paginated platform index, journal entries + pager (W2.1)
  editorial_policies.html - Aims & Scope page with #focusAndScope anchor (W2.1)
  article_meta_samples.json - six live article metas + OAI subjects with the
      expected subject-filter verdict per class (W2.2, D04)

Usage:
    python tools/export_rcsi_fixtures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

FIX = ROOT / "tests" / "fixtures" / "rcsi"


def main() -> int:
    from ruwritingstyles import rcsi

    FIX.mkdir(parents=True, exist_ok=True)

    identify_xml = rcsi._throttled_get(f"{rcsi.BASE}/2306-5737/oai?verb=Identify")
    if isinstance(identify_xml, str):
        identify_xml = identify_xml.encode("utf-8")
    (FIX / "identify.xml").write_bytes(identify_xml)
    print(f"  identify.xml ({len(identify_xml)} bytes)")

    records_xml = rcsi._throttled_get(
        f"{rcsi.BASE}/0869-5873/oai?verb=ListRecords&metadataPrefix=oai_dc&from=2024-09-01"
    )
    if isinstance(records_xml, str):
        records_xml = records_xml.encode("utf-8")
    (FIX / "list_records.xml").write_bytes(records_xml)
    print(f"  list_records.xml ({len(records_xml)} bytes)")

    html = rcsi._throttled_get(f"{rcsi.BASE}/0869-5873/article/view/268311")
    if isinstance(html, str):
        html = html.encode("utf-8")
    (FIX / "article_plungian.html").write_bytes(html)
    print(f"  article_plungian.html ({len(html)} bytes)")

    try:
        import fitz
    except ImportError:
        # PyMuPDF is the W0.4 winner, installed via the [harvest] extra; the
        # fixture already exists and tests never regenerate it.
        if not (FIX / "mini_en.pdf").exists():
            raise
        print("  mini_en.pdf (kept; pymupdf not installed)")
    else:
        doc = fitz.open()
        page = doc.new_page()
        line = "Corpus linguistics studies language data with quantitative methods of analysis."
        for offset in range(24):
            page.insert_text((72, 72 + 16 * offset), line)
        doc.save(FIX / "mini_en.pdf")
        doc.close()
        print("  mini_en.pdf")

    mojibake = "\ufffd" * 120 + "\u0401\u0401\u0401 \u00a4\u00a4\u00a4 " * 60
    (FIX / "mojibake.txt").write_text(mojibake, encoding="utf-8", newline="\n")
    print("  mojibake.txt")

    page1 = rcsi._throttled_get(f"{rcsi.BASE}/index?searchInitial=&journalsPage=1")
    if isinstance(page1, str):
        page1 = page1.encode("utf-8")
    (FIX / "catalogue_page1.html").write_bytes(page1)
    print(f"  catalogue_page1.html ({len(page1)} bytes)")

    policies = rcsi._throttled_get(f"{rcsi.BASE}/2306-5737/about/editorialPolicies")
    if isinstance(policies, str):
        policies = policies.encode("utf-8")
    (FIX / "editorial_policies.html").write_bytes(policies)
    print(f"  editorial_policies.html ({len(policies)} bytes)")

    _freeze_article_meta_samples()
    return 0


# W2.2 samples: one real article per subject-filter verdict class, measured
# live 02-09-2026. ``selection_subject`` is the OAI Dublin Core dc:subject the
# article page itself lacks — sample 6 exercises the D04 rescue path (title
# alone classifies uncertain; the OAI subject decides include).
_ARTICLE_META_SAMPLES = [
    {
        "slug": "0373-658X",
        "article_id": "141140",
        "selection_subject": [],
        "expect": {"verdict": "include", "expect_cyrillic": True},
    },
    {
        "slug": "2306-5737",
        "article_id": "416857",
        "selection_subject": [],
        "expect": {"verdict": "include", "expect_cyrillic": False},
    },
    {
        "slug": "0869-5873",
        "article_id": "430087",
        "selection_subject": [],
        "expect": {"verdict": "exclude", "expect_cyrillic": True},
    },
    {
        "slug": "0869-5873",
        "article_id": "258762",
        "selection_subject": [],
        "expect": {"verdict": "exclude", "expect_cyrillic": True},
    },
    {
        "slug": "0869-5873",
        "article_id": "376609",
        "selection_subject": [],
        "expect": {"verdict": "uncertain", "expect_cyrillic": True},
    },
    {
        "slug": "0373-658X",
        "article_id": "141145",
        "selection_subject": [
            "Боас Ф.; история лингвистики; лингвистика в США; лингвистическая"
            " относительность; фонология; этнолингвистика",
            "Boas F.; ethnolinguistics; history of linguistics; linguistic"
            " relativity; linguistics in the USA; phonology",
        ],
        "expect": {"verdict": "include", "expect_cyrillic": True},
    },
]


def _freeze_article_meta_samples() -> None:
    from ruwritingstyles import rcsi
    from ruwritingstyles.journal_scope import classify_article

    samples = []
    for sample in _ARTICLE_META_SAMPLES:
        meta = rcsi.article_meta(sample["slug"], sample["article_id"])
        meta.pop("html", "")
        selection_record = {"subject": sample["selection_subject"]} if sample["selection_subject"] else {}
        verdict = classify_article(meta, selection_record=selection_record or None)
        expected = sample["expect"]
        if verdict["verdict"] != expected["verdict"] or verdict["expect_cyrillic"] != expected["expect_cyrillic"]:
            raise SystemExit(
                f"live verdict drifted for {sample['slug']}/{sample['article_id']}:"
                f" got {verdict['verdict']}/{verdict['expect_cyrillic']},"
                f" expected {expected['verdict']}/{expected['expect_cyrillic']} —"
                " the frozen expectation must be re-measured, not blind-written"
            )
        samples.append(
            {
                "journal_slug": sample["slug"],
                "article_id": sample["article_id"],
                "meta": meta,
                "selection_record": selection_record,
                "expect": expected,
            }
        )
        print(f"  article_meta_samples: {sample['slug']}/{sample['article_id']} -> {verdict['verdict']}")
    path = FIX / "article_meta_samples.json"
    path.write_text(json.dumps(samples, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"  article_meta_samples.json ({path.stat().st_size} bytes, {len(samples)} samples)")


if __name__ == "__main__":
    raise SystemExit(main())
