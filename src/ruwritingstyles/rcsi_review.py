"""W2.3 review queue — shape the uncertain RCSI catalogue tail into cards.

Pure logic only: no ``csl_pyutil`` import, no network. The sheet generator
(``tools/build_rcsi_review_sheet.py``) consumes these functions, passes the
V7 ``mark_cyrillic`` highlighter in, and hands the items to the shared
review-sheet emitter.

The input is ``knowledge/rcsi/catalogue.json`` (W2.1 crawl, D05). Records with
``verdict == "uncertain"`` are the tail D04 refuses to drop silently; this
module splits it into three judgment classes, screens out what the roadmap
already decided, and emits emitter-shaped items with U7 typology chips
(count + share over the uncertain population, denominator stated in words).
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Callable

from .config import repo_root_from

__all__ = [
    "CATALOGUE_POPULATION",
    "CLASS_LABELS",
    "CLASS_FILTS",
    "SHEET_ID",
    "HUB_NAME",
    "SCREENED_PINNED_SLUGS",
    "card_class",
    "load_catalogue",
    "review_tail",
    "class_counts",
    "build_items",
    "screening_counts",
]

#: ``<repo-slug>-<topic>_<scope>`` — scope carries the tail size of the crawl
#: this sheet was cut from, so a future re-crawl yields a fresh sheet id.
SHEET_ID = "ruwritingstyles-rcsi-catalogue_uncertain-628"

#: Hub-local stem (short name convention of the vote hub).
HUB_NAME = "rws_rcsi_uncertain_628"

#: Roadmap W2.1: the five named journals stay pinned by name regardless of
#: verdict. Вестник РАН is the one pinned journal whose catalogue verdict is
#: ``uncertain`` — it never reaches the sheet.
SCREENED_PINNED_SLUGS = frozenset({"0869-5873"})

#: The catalogue record count this sheet's population denominators refer to.
CATALOGUE_POPULATION = 992

#: filt code -> human label (filter bar buttons); RU chrome per U6.
CLASS_FILTS: dict[str, str] = {
    "conflict": "Конфликт терминов",
    "noscope": "Нет Focus & Scope",
    "noterms": "Текст без терминов",
}

#: filt code -> full Russian class description used in panels.
CLASS_LABELS: dict[str, str] = {
    "conflict": "Конфликт терминов: найдены и тематические, и общенаучные",
    "noscope": "Раздел Focus & Scope на странице журнала отсутствует",
    "noterms": "Текст области получен, но терминов списка в нём нет",
}

_CONSEQUENCE_LINE = (
    "<p><b>Одобрить</b> — журнал включается (verdict → include), его статьи "
    "попадут в ограниченный сбор W2.4. <b>Отклонить</b> — журнал исключается "
    "(verdict → exclude), в сбор не попадёт. <b>Отложить</b> — останется в "
    "неопределённых и в сбор W2.4 не попадёт.</p>"
)


def load_catalogue(repo_root_str: str | None = None) -> list[dict[str, Any]]:
    root = Path(repo_root_str) if repo_root_str else repo_root_from()
    path = root / "knowledge" / "rcsi" / "catalogue.json"
    return json.loads(path.read_text(encoding="utf-8"))


def review_tail(catalogue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The uncertain records minus what the roadmap pre-decided (Phase 0-bis (a))."""
    return [
        record
        for record in catalogue
        if record.get("verdict") == "uncertain" and record.get("slug") not in SCREENED_PINNED_SLUGS
    ]


def card_class(record: dict[str, Any]) -> str:
    """Which of the three judgment classes the uncertain record falls into.

    - ``conflict`` — both a positive and a negative term matched (the
      classifier's designed conflicting-witness verdict, e.g. ``morphology``
      inside a paleontology scope);
    - ``noscope`` — no ``#focusAndScope`` text was captured at crawl time
      (Вестник РАН class: the page has no such section);
    - ``noterms`` — scope text exists but contains no term-list word.
    """
    if record.get("matched_terms"):
        return "conflict"
    if not (record.get("scope_text_excerpt") or "").strip():
        return "noscope"
    return "noterms"


def class_counts(tail: list[dict[str, Any]]) -> dict[str, int]:
    counts = {key: 0 for key in CLASS_FILTS}
    for record in tail:
        counts[card_class(record)] += 1
    return counts


def _term_chips(record: dict[str, Any]) -> list[str]:
    chips: list[str] = []
    for term in record.get("matched_terms") or []:
        chips.append(f"+{term}")
    for term in record.get("negative_terms") or []:
        chips.append(f"−{term}")
    return chips


def _population_panel(
    cls: str, counts: dict[str, int], population: int, record: dict[str, Any]
) -> tuple[str, str]:
    """U7 panel: the class chip's count + share, with the denominator in words."""
    share = counts[cls] / population
    seen = (
        "название + имя репозитория OAI"
        if cls == "noscope"
        else "название + имя репозитория OAI + текст Focus & Scope"
    )
    body = (
        f"<p>Класс карточки: <b>{CLASS_LABELS[cls]}</b> — "
        f"{counts[cls]} из {population} карточек листа ({share:.0%}); знаменатель "
        f"доли — 629 неопределённых журналов хвоста из {CATALOGUE_POPULATION} журналов "
        f"обхода W2.1 (лист не включает Вестник РАН — он закреплён по имени).</p>"
        f"<p>Классификатор (D04) видел: {seen}. Текущий вердикт в каталоге: "
        f"<code>uncertain</code>.</p>"
    )
    if cls == "conflict" and record.get("negative_terms"):
        body += (
            "<p>Общенаучные термины, удерживающие вердикт в конфликте: "
            f"<code>{html.escape(', '.join(record['negative_terms']))}</code>.</p>"
        )
    return ("Класс и знаменатель", body)


def build_items(
    tail: list[dict[str, Any]],
    *,
    population: int | None = None,
    highlight: Callable[[str], str] | None = None,
) -> list[dict[str, Any]]:
    """Emitter-shaped items for the review tail (Phase 1 normalization).

    ``population`` is the denominator for U7 shares; it defaults to the
    uncertain tail **including** the screened pinned journals (629 for the
    W2.1 crawl) — the population the sheet draws from, stated in words on
    every card. ``highlight`` receives the already-escaped excerpt text; the
    generator passes ``csl_pyutil.mark_cyrillic`` (V7), tests pass nothing.
    """
    slugs = {record.get("slug") for record in tail}
    if population is None:
        # SCREENED_PINNED_SLUGS names exactly the pinned journals whose
        # catalogue verdict is uncertain, so the sheet's population is the
        # tail plus those screened cards (629 for the W2.1 crawl).
        population = len(tail) + len(SCREENED_PINNED_SLUGS - slugs)
    counts = class_counts(tail)
    mark = highlight or (lambda text: text)
    items: list[dict[str, Any]] = []
    for record in tail:
        cls = card_class(record)
        excerpt = (record.get("scope_text_excerpt") or "").strip()
        if excerpt:
            ellipsis = "…" if len(excerpt) >= 500 else ""
            scope_html = f'<p class="scope">«{mark(html.escape(excerpt))}{ellipsis}»</p>'
        else:
            scope_html = (
                '<p class="scope">Текст Focus & Scope не получен: на странице '
                "/about/editorialPolicies нет раздела #focusAndScope (класс "
                "Вестника РАН). Решайте по названию журнала и странице по "
                "ссылке в заголовке карточки.</p>"
            )
        title = record.get("journal_name") or record.get("repository_name") or record["slug"]
        identity_line = (
            f'<p class="ident">Журнал <b>{html.escape(title)}</b> · '
            f"id <code>{html.escape(str(record['slug']))}</code></p>"
        )
        items.append(
            {
                "id": record["slug"],
                "filt": cls,
                "title": title,
                "title_href": record.get("url"),
                "badges": _term_chips(record),
                "typology": [
                    {
                        "label": CLASS_FILTS[cls],
                        "n": counts[cls],
                        "share": counts[cls] / population,
                    }
                ],
                "question": identity_line + scope_html + _CONSEQUENCE_LINE,
                "panels": [_population_panel(cls, counts, population, record)],
                "note_placeholder": "Уточнение к журналу (необязательно): неверное название, другой ISSN…",
            }
        )
    return items


def screening_counts(catalogue: list[dict[str, Any]]) -> dict[str, int]:
    """Phase 0-bis mapping for the emitter's required ``screening=`` argument.

    (a) deterministic — the roadmap pre-decides pinned journals (Вестник РАН);
    (b) lookup — the five hand-verified profiles are all ``include`` already,
        none sits in the tail, so zero lookups fired;
    (c) agent — deliberately zero: D04 keeps the tail human-visible instead of
        re-adjudicating 628 scope texts with a model;
    (d) human — the rest.
    """
    uncertain = [r for r in catalogue if r.get("verdict") == "uncertain"]
    screened = sum(1 for r in uncertain if r.get("slug") in SCREENED_PINNED_SLUGS)
    human = len(uncertain) - screened
    return {"deterministic": screened, "lookup": 0, "agent": 0, "human": human}
