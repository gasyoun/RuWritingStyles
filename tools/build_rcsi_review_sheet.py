"""Render the W2.3 RCSI review-queue voting sheet from the committed catalogue.

Reads ``knowledge/rcsi/catalogue.json``, screens the roadmap-decided records,
shapes the uncertain tail into cards (``ruwritingstyles.rcsi_review``) and
renders parent + packs through the shared emitter (csl-pyutil >= 0.17
``render_review_sheet_packset``). Per-pack ``save_as`` destinations keep the
63 decisions exports from colliding in Downloads (H779 naming rule).

Output (gitignored ``review/``, mirroring the hub layout so the parent's
relative pack links work from disk too):
  rws_rcsi_uncertain_628.html            (parent / pack index)
  rws_rcsi_uncertain_628/pack-01.html … pack-63.html

Exports are named by the full convention (V8 banner per pack):
  RuWritingStyles/review/ruwritingstyles-rcsi-catalogue_uncertain-628_pack-NN_decisions.json

Usage:
    python tools/build_rcsi_review_sheet.py             # render into review/
    python tools/build_rcsi_review_sheet.py --out-dir /tmp/x
    python tools/build_rcsi_review_sheet.py --selftest  # offline synthetic packset
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ruwritingstyles.rcsi_review import (  # noqa: E402
    HUB_NAME,
    SHEET_ID,
    build_items,
    class_counts,
    load_catalogue,
    review_tail,
    screening_counts,
)

GENERATED = "03-09-2026"

FILTERS = [
    ("conflict", "Конфликт терминов"),
    ("noscope", "Нет Focus & Scope"),
    ("noterms", "Текст без терминов"),
]

_TITLE = "Хвост неопределённых журналов RCSI — очередь рассмотрения (W2.3)"
_SUBTITLE = (
    "Авто-классификатор (D04) не смог решить 629 из 992 журналов платформы RCSI по "
    "тексту области: 15 — конфликт терминов, 325 — без раздела Focus & Scope, "
    "288 — текст без терминов списка. Вестник РАН (0869-5873) на лист не попал — "
    "закреплён по имени (роадмап W2.1). Неопределённые статьи появятся после "
    "сбора W2.4 — для них будет отдельный лист."
)
_FOOTER = (
    "Одобрить — журнал включается в ограниченный сбор статей (W24-кандидат). "
    "Отклонить — журнал исключается из сбора. Отложить — пока вне сбора, до "
    "пересмотра. Поле заметки — для поправки названия/ISSN без смены вердикта. "
    "Знаменатели: 992 журнала обхода W2.1 → 629 неопределённых → 628 карточек. "
    "Голосуйте пакетами; прогресс сохраняется между открытиями страницы."
)


def render(out_dir: Path) -> list[Path]:
    try:
        from csl_pyutil import RU_UI_STRINGS, mark_cyrillic, render_review_sheet
        from csl_pyutil.evidence import EvidenceManifest, find_slp1
        from csl_pyutil.review_sheet import _render_pack_parent
    except ImportError as exc:  # pragma: no cover - environment guard
        raise SystemExit(
            "csl-pyutil >= 0.17 required for the V16 packset emitter: "
            'pip install "csl-pyutil @ git+https://github.com/sanskrit-lexicon/csl-pyutil@main"'
        ) from exc

    catalogue = load_catalogue(str(ROOT))
    tail = review_tail(catalogue)
    items = build_items(tail, highlight=mark_cyrillic)
    screening = screening_counts(catalogue) | {
        "evidence_path": "docs/SCREENING_EVIDENCE_rcsi-uncertain-review_03-09-2026.md",
        "rules": [
            "pinned-journals-stay-pinned (roadmap W2.1)",
            "hand-verified-profiles-all-include (none in tail)",
        ],
    }

    manifest = EvidenceManifest(SHEET_ID, [item["id"] for item in items], repo_root=str(ROOT))
    manifest.declare_joined(
        "knowledge/rcsi/catalogue.json",
        ["slug", "journal_name", "repository_name", "url", "scope_text_excerpt",
         "verdict", "matched_terms", "negative_terms"],
    )
    manifest.declare_omitted(
        "full #focusAndScope texts",
        "the W2.1 crawl stores 500-char excerpts only; the full scope text is "
        "one click away through the card's title link, so nothing is judged "
        "from a truncated witness",
    )
    for record in tail:
        fields = ["journal_name", "url"]
        if (record.get("scope_text_excerpt") or "").strip():
            fields.append("scope_text_excerpt")
        if record.get("matched_terms") or record.get("negative_terms"):
            fields.append("matched_terms")
        manifest.add_card(record["slug"], fields)

    # V13: the internal ids of this sheet are the catalogue slugs. Patterns
    # are the escaped slugs themselves (word-bounded), so a year range like
    # «1996-2012» inside a verbatim English excerpt is not an id; every slug
    # (own or foreign, when an excerpt quotes another journal's ISSN) must
    # appear with its journal name in the same question. The ident line on
    # every card satisfies the own-slug case.
    import html as _html
    import re as _re

    identity_gate = {
        "patterns": [r"\b%s\b" % _re.escape(r["slug"]) for r in catalogue],
        "labels": {
            r["slug"]: _html.escape(r.get("journal_name") or r["slug"])
            for r in catalogue
        },
    }

    # The scope excerpts are verbatim ENGLISH journal prose (U-language rule:
    # quoted source text stays as-is). The SLP1 heuristic flags ordinary
    # English words ("information", "conferences") in that prose; allow exactly
    # the tokens the cards themselves carry — anything genuinely SLP1 in a new
    # excerpt still blocks the build.
    card_text = " ".join(
        _re.sub(r"<[^>]+>", " ", item["question"] + " " + item["title"])
        for item in items
    )
    allow_slp1 = tuple(find_slp1(card_text))

    pack_size = 10
    slices = [items[i : i + pack_size] for i in range(0, len(items), pack_size)]
    config = {
        "sheet_id": SHEET_ID,
        "title": _TITLE,
        "subtitle": _SUBTITLE,
        "footer": _FOOTER,
        "approve_label": "Включить в сбор",
        "reject_label": "Исключить",
        "filters": FILTERS,
        "generated": GENERATED,
        "show_ids": True,
        "note_min_height_px": 88,
        "pack_size": pack_size,
        "packset_total": len(items),
        "ui_strings": RU_UI_STRINGS,
        "preflight": {"allow_slp1_tokens": allow_slp1},
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    # Mirror the hub layout (parent beside a <hub_name>/ pack dir) so the
    # parent's relative pack links work from disk, not only from the hub.
    pack_dir = out_dir / HUB_NAME
    pack_dir.mkdir(parents=True, exist_ok=True)
    for number, slice_items in enumerate(slices, 1):
        pack_config = dict(config)
        pack_config["pack"] = {"index": number, "total": len(slices)}
        save_name = f"{SHEET_ID}_pack-{number:02d}_decisions.json"
        pack_config["save_as"] = f"RuWritingStyles/review/{save_name}"
        pack_config["ui_strings"] = RU_UI_STRINGS | {
            "save_banner": (
                "Лист %s, пакет %d/%d. Кнопка экспорта сохраняет <code>%s</code> — "
                "положите файл в <code>RuWritingStyles/review/</code>."
                % (SHEET_ID, number, len(slices), save_name)
            )
        }
        pack_config["identity_gate"] = identity_gate
        html_text = render_review_sheet(
            slice_items,
            pack_config,
            extras=True,
            screening=screening,
            manifest=manifest,
        )
        path = pack_dir / f"pack-{number:02d}.html"
        path.write_text(html_text, encoding="utf-8")
        written.append(path)

    parent_config = dict(config)
    parent_config["save_as"] = f"RuWritingStyles/review/{SHEET_ID}_decisions.json"
    parent = _render_pack_parent(parent_config, slices, HUB_NAME)
    parent_path = out_dir / f"{HUB_NAME}.html"
    parent_path.write_text(parent, encoding="utf-8")
    written.append(parent_path)

    print(f"sheet_id {SHEET_ID}: {len(items)} cards -> {len(slices)} packs + parent in {out_dir}")
    print(f"screening: {screening}")
    return written


def selftest() -> int:
    """Offline: synthetic 12-record tail renders a 2-pack packset byte-shape."""
    records = []
    for index in range(12):
        records.append(
            {
                "slug": f"0000-{index:04d}",
                "journal_name": f"Тестовый журнал {index}",
                "repository_name": f"Test Journal {index}",
                "url": f"https://journals.rcsi.science/0000-{index:04d}",
                "scope_text_excerpt": "" if index % 3 == 0 else "Журнал по общей физике и технике.",
                "verdict": "uncertain",
                "matched_terms": ["морфология"] if index % 4 == 0 else [],
                "negative_terms": ["физик"] if index % 4 == 0 else [],
                "evidence_other": [],
                "checked_on": GENERATED,
            }
        )
    items = build_items(records)
    assert len(items) == 12
    assert all(item["id"] for item in items)
    assert len({item["id"] for item in items}) == 12
    assert {item["filt"] for item in items} <= set(FILTER_CODES)
    counts = class_counts(records)
    assert counts == {"conflict": 3, "noscope": 3, "noterms": 6}
    for item in items:
        entry = item["typology"][0]
        assert entry["n"] == counts[item["filt"]]
        assert 0.0 < entry["share"] <= 1.0
    try:
        from csl_pyutil import RU_UI_STRINGS, mark_cyrillic, render_review_sheet
        from csl_pyutil.review_sheet import _render_pack_parent
    except ImportError:
        print("selftest: item shaping OK; csl-pyutil absent, render part SKIPPED")
        return 0
    screening = {
        "deterministic": 1,
        "lookup": 0,
        "agent": 0,
        "human": len(items),
        "evidence_path": "selftest",
        "rules": ["selftest"],
    }
    pack_html = render_review_sheet(
        items[:10],
        {
            "sheet_id": "selftest-w23",
            "title": _TITLE,
            "subtitle": _SUBTITLE,
            "footer": _FOOTER,
            "approve_label": "Включить в сбор",
            "reject_label": "Исключить",
            "filters": FILTERS,
            "generated": GENERATED,
            "show_ids": True,
            "note_min_height_px": 88,
            "ui_strings": RU_UI_STRINGS,
        },
        extras=True,
        screening=screening,
    )
    assert "selftest-w23" in pack_html
    parent = _render_pack_parent(
        {"sheet_id": "selftest-w23", "title": _TITLE, "subtitle": _SUBTITLE,
         "footer": _FOOTER, "filters": FILTERS, "generated": GENERATED,
         "ui_strings": RU_UI_STRINGS},
        [items[:10], items[10:]],
        "selftest_w23",
    )
    assert "pack-01.html" in parent and "pack-02.html" in parent
    print("selftest OK: 12 synthetic cards -> 2-pack packset renders")
    return 0


FILTER_CODES = {"conflict", "noscope", "noterms"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=ROOT / "review")
    parser.add_argument("--selftest", action="store_true", help="offline synthetic render check")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    render(args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
