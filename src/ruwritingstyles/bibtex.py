"""BibTeX and GOST reference outputs for a run.

Entries are sourced from knowledge/bibliography.json via KnowledgeManager —
never hardcoded. Only citations actually found in the revised text are
emitted; with no text, the whole bibliography is rendered (legacy behaviour
kept for `rws report` on bare runs).
"""

from __future__ import annotations

import re
from pathlib import Path
from .io_utils import atomic_write_text
from typing import Any

from .citations import extract_citations
from .gost import sort_entries, write_gost_references
from .knowledge import KnowledgeManager

_KIND_TO_BIBTEX = {
    "book": "book",
    "article": "article",
    "chapter": "incollection",
    "web": "misc",
}


def bibtex_key(entry: dict[str, Any]) -> str:
    raw = str(entry.get("id") or entry.get("author") or "ref")
    key = re.sub(r"[^\w]", "", raw, flags=re.ASCII).lower()
    return key or "ref"


def entry_to_bibtex(entry: dict[str, Any]) -> str:
    kind = _KIND_TO_BIBTEX.get(entry.get("kind", "book"), "misc")
    fields: list[tuple[str, Any]] = [
        ("author", entry.get("author")),
        ("title", entry.get("title")),
        ("year", entry.get("year")),
        ("publisher", entry.get("publisher")),
        ("address", entry.get("city")),
        ("journal", entry.get("journal")),
        ("booktitle", entry.get("container")),
        ("volume", entry.get("volume")),
        ("number", entry.get("number")),
        ("pages", entry.get("pages")),
        ("edition", entry.get("edition")),
        ("url", entry.get("url")),
    ]
    body = ",\n".join(f"  {name} = {{{value}}}" for name, value in fields if value)
    return f"@{kind}{{{bibtex_key(entry)},\n{body}\n}}"


def matched_entries(repo_root: Path, revised_text: str = "") -> list[dict[str, Any]]:
    """Bibliography entries cited in the text (all entries when no text)."""
    km = KnowledgeManager(repo_root)
    bibliography = km._load_bibliography()
    if not revised_text:
        return sort_entries(list(bibliography))

    matched: dict[str, dict[str, Any]] = {}
    for citation in extract_citations(revised_text):
        entry = km.verify_citation(citation)
        # Collection-heading matches verify a citation but carry no
        # bibliographic fields — they cannot be rendered as references.
        if entry and entry.get("kind") != "collection" and (entry.get("title") or entry.get("author")):
            matched[str(entry.get("id"))] = entry
    return sort_entries(list(matched.values()))


def generate_bibtex(
    run_id: str, revised_text: str = "", repo_root: Path | None = None
) -> str:
    entries = matched_entries(repo_root, revised_text) if repo_root else []
    citations = extract_citations(revised_text) if revised_text else []

    header = f"% BibTeX for RuWritingStyles Run: {run_id}\n"
    header += "% Source: knowledge/bibliography.json\n"
    if citations:
        header += f"% Extracted Citations: {', '.join(citations)}\n"
    header += "\n"

    return header + "\n\n".join(entry_to_bibtex(e) for e in entries)


def write_bibtex(run_dir: Path, repo_root: Path | None = None) -> Path:
    """Write references.bib and references-gost.md for a run."""
    if repo_root is None:
        repo_root = run_dir.parent.parent  # runs/<run-id>/ layout
    run_id = run_dir.name
    revised_path = run_dir / "revised.md"
    revised_text = (
        revised_path.read_text(encoding="utf-8") if revised_path.exists() else ""
    )

    entries = matched_entries(repo_root, revised_text)
    bib_path = run_dir / "references.bib"
    atomic_write_text(bib_path, generate_bibtex(run_id, revised_text, repo_root))
    write_gost_references(run_dir, entries)
    return bib_path
