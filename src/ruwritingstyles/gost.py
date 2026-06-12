"""GOST R 7.0.100-2018 bibliography formatting (краткая форма списка литературы).

Entries come from knowledge/bibliography.json. Supported kinds:
book (default), article, chapter, web. Missing optional fields are omitted
gracefully so legacy 5-field entries still render.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _is_cyrillic_entry(entry: dict[str, Any]) -> bool:
    head = str(entry.get("author") or entry.get("title") or "")
    for char in head:
        if char.isalpha():
            return "Ѐ" <= char <= "ӿ"
    return False


def sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Alphabetical, Cyrillic block before Latin (ВЯ/ППВ convention)."""
    return sorted(
        entries,
        key=lambda e: (
            0 if _is_cyrillic_entry(e) else 1,
            str(e.get("author") or e.get("title") or "").lower(),
            e.get("year") or 0,
        ),
    )


def _join_gost(parts: list[Any]) -> str:
    """Join areas with «. — », normalizing trailing periods to exactly one."""
    cleaned = [str(p).strip().rstrip(".") for p in parts if p and str(p).strip()]
    return ". — ".join(cleaned) + "."


def format_gost(entry: dict[str, Any]) -> str:
    """Render one bibliography entry in GOST R 7.0.100-2018 short form."""
    kind = entry.get("kind", "book")
    author = str(entry.get("author") or "").strip()
    title = str(entry.get("title") or "").strip().rstrip(".")
    year = entry.get("year")
    pages = entry.get("pages")

    head = f"{author} {title}".strip() if author else title

    if kind == "article":
        journal = str(entry.get("journal") or "").strip()
        parts: list[Any] = [f"{head} // {journal}"]
        volume = entry.get("volume")
        if year:
            parts.append(year)
        if volume:
            parts.append(f"Т. {volume}")
        number = entry.get("number")
        if number:
            parts.append(f"№ {number}")
        if pages:
            parts.append(f"С. {pages}")
        return _join_gost(parts)

    if kind == "chapter":
        container = str(entry.get("container") or "").strip()
        return _join_gost(
            [f"{head} // {container}", _imprint(entry), f"С. {pages}" if pages else ""]
        )

    if kind == "web":
        url = entry.get("url")
        return _join_gost([head, f"URL: {url}" if url else ""])

    # book (default)
    return _join_gost(
        [head, entry.get("edition"), _imprint(entry), f"{pages} с." if pages else ""]
    )


def _imprint(entry: dict[str, Any]) -> str:
    city = entry.get("city")
    publisher = entry.get("publisher")
    year = entry.get("year")
    place = " : ".join(str(p) for p in (city, publisher) if p)
    if place and year:
        return f"{place}, {year}"
    if place:
        return place
    if year:
        return str(year)
    return ""


def render_gost_list(entries: list[dict[str, Any]]) -> str:
    lines = ["# Литература", ""]
    for index, entry in enumerate(sort_entries(entries), start=1):
        lines.append(f"{index}. {format_gost(entry)}")
    lines.append("")
    return "\n".join(lines)


def write_gost_references(run_dir: Path, entries: list[dict[str, Any]]) -> Path:
    target = run_dir / "references-gost.md"
    target.write_text(render_gost_list(entries), encoding="utf-8")
    return target
