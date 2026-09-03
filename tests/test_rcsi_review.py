"""Offline tests for the W2.3 review-queue sheet shaper (rcsi_review).

Derive-don't-store: the class split and screening counts are recomputed from
the committed W2.1 catalogue on every run, so a drifted catalogue fails here
instead of silently reshaping the voting sheet.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ruwritingstyles import rcsi_review  # noqa: E402
from ruwritingstyles.rcsi_review import (  # noqa: E402
    CATALOGUE_POPULATION,
    build_items,
    card_class,
    class_counts,
    load_catalogue,
    review_tail,
    screening_counts,
)


def _record(**overrides):
    base = {
        "slug": "0000-0001",
        "journal_name": "Тестовый журнал",
        "repository_name": "Test Journal",
        "url": "https://journals.rcsi.science/0000-0001",
        "scope_text_excerpt": "Журнал публикует работы по языкознанию.",
        "verdict": "uncertain",
        "matched_terms": [],
        "negative_terms": [],
        "evidence_other": [],
        "checked_on": "31-08-2026",
    }
    base.update(overrides)
    return base


def test_catalogue_counts_match_frozen_crawl():
    catalogue = load_catalogue()
    assert len(catalogue) == CATALOGUE_POPULATION == 992
    uncertain = [r for r in catalogue if r["verdict"] == "uncertain"]
    assert len(uncertain) == 629
    assert sum(r["verdict"] == "include" for r in catalogue) == 61
    assert sum(r["verdict"] == "exclude" for r in catalogue) == 302


def test_review_tail_screens_pinned_journal():
    catalogue = load_catalogue()
    tail = review_tail(catalogue)
    assert len(tail) == 628
    assert "0869-5873" not in {r["slug"] for r in tail}
    assert len({r["slug"] for r in tail}) == len(tail)


def test_card_class_split_matches_frozen_tail():
    tail = review_tail(load_catalogue())
    counts = class_counts(tail)
    assert counts == {"conflict": 15, "noscope": 325, "noterms": 288}


def test_card_class_rules():
    assert card_class(_record(matched_terms=["морфология"], negative_terms=["физик"])) == "conflict"
    assert card_class(_record(scope_text_excerpt="   ")) == "noscope"
    assert card_class(_record()) == "noterms"
    # a positive match wins the class even when the excerpt is absent
    assert card_class(_record(scope_text_excerpt="", matched_terms=["филолог"])) == "conflict"


def test_screening_counts():
    screening = screening_counts(load_catalogue())
    assert screening == {"deterministic": 1, "lookup": 0, "agent": 0, "human": 628}


def test_build_items_shape():
    tail = review_tail(load_catalogue())
    items = build_items(tail)
    assert len(items) == 628
    by_id = {item["id"]: item for item in items}
    assert set(by_id) == {r["slug"] for r in tail}

    # U1: stable natural keys; U4: per-item link; filt matches the class
    for record in tail:
        item = by_id[record["slug"]]
        assert item["filt"] == card_class(record)
        assert item["title_href"] == record["url"]

    # U7: every typology chip carries count + share over the 629 tail
    counts = class_counts(tail)
    for item in items:
        (chip,) = item["typology"]
        assert chip["n"] == counts[item["filt"]]
        assert abs(chip["share"] - counts[item["filt"]] / 629) < 1e-9

    # U3: consequence line names all three verbs' outcomes on every card
    for item in items:
        assert "Одобрить" in item["question"] and "include" in item["question"]
        assert "Отклонить" in item["question"] and "exclude" in item["question"]
        assert "Отложить" in item["question"]


def test_build_items_question_carries_evidence():
    tail = review_tail(load_catalogue())
    items = {item["id"]: item for item in build_items(tail)}

    # noscope card states the absence instead of quoting nothing
    noscope = next(item for item in items.values() if item["filt"] == "noscope")
    assert "focusAndScope" in noscope["question"]

    # conflict card carries the verbatim excerpt and +/- term chips
    conflict = next(item for item in items.values() if item["filt"] == "conflict")
    record = next(r for r in tail if r["slug"] == conflict["id"])
    assert record["scope_text_excerpt"].strip()[:40] in conflict["question"]
    assert "+morphology" in conflict["badges"]
    assert any(badge.startswith("−") for badge in conflict["badges"])

    # noterms card quotes the scope text verbatim
    noterms = next(item for item in items.values() if item["filt"] == "noterms")
    record = next(r for r in tail if r["slug"] == noterms["id"])
    assert record["scope_text_excerpt"].strip()[:40] in noterms["question"]


def test_highlight_is_passed_the_escaped_excerpt():
    calls = []

    def fake_mark(text: str) -> str:
        calls.append(text)
        return f"<mark>{text}</mark>"

    items = build_items([_record()], highlight=fake_mark)
    assert calls and calls[0].startswith("Журнал публикует")
    assert '<p class="scope">«<mark>Журнал' in items[0]["question"]
