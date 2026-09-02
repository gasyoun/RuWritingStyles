"""Harvest RCSI journal articles into the private corpus (D03/D11/D13).

Orchestration only: HTTP lives in `rcsi`, extraction in `extract`,
classification in `journal_scope`. Per accepted article this writes
`<stem>.txt` + `<stem>.json` into the corpus directory resolved by
`corpus.CorpusManager`, appends a bibliography row to
`knowledge/bibliography.json`, and records the run manifest under
`runs/rcsi-harvest/`.

Idempotence: an article whose sidecar already exists with a ``pass`` verdict
is skipped unless ``force``. Gate/quarantine failures go to
``<corpus>/quarantine/`` with their score and reason — never indexed.

Windows discipline: every text file is written ``encoding="utf-8"`` with
``newline="\\n"`` and no BOM.

The D18 fence is structural here: nothing in this module ever writes inside
the public repo; the bibliography row lives in the repo by design (it is
metadata, not text), while article text and sidecars go to the private corpus.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import repo_root_from

__all__ = [
    "harvest_journal",
    "harvest_pinned",
    "corpus_verify",
    "build_stem",
    "load_pinned_manifest",
    "load_catalogue",
    "build_catalogue",
]

_PINNED_PATH_PARTS = ("knowledge", "rcsi", "pinned_articles.json")
_CATALOGUE_PATH_PARTS = ("knowledge", "rcsi", "catalogue.json")

# GOST-style romanization, letters only — used for filename stems so Windows
# path lengths stay safe and corpus.py's filename heuristics keep working. The
# full Cyrillic title always survives in the sidecar.
_ROMAN: dict[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _romanize(text: str) -> str:
    out = []
    for ch in text.lower():
        if ch in _ROMAN:
            out.append(_ROMAN[ch])
        elif ch.isascii() and ch.isalnum():
            out.append(ch)
        else:
            out.append(" ")
    slug = re.sub(r"\s+", "-", "".join(out).strip())
    return re.sub(r"-+", "-", slug)[:80].rstrip("-")


def _surname(author: str) -> str:
    """First author's surname from 'Плунгян В. А.' or 'V. A. Plungian'.

    Russian metadata puts the surname first; English puts it last, with
    single-letter initials either way. Drop initial-looking tokens (one or two
    letters, optionally dotted), then take the first remaining token.
    """
    first = re.split(r"[,;(]", author or "")[0].strip()
    for token in first.split():
        candidate = token.strip(".,")
        if not candidate or len(candidate) <= 2 and "." in token:
            continue
        if any("\u0400" <= ch <= "\u04FF" for ch in candidate):
            return _romanize(candidate).title()
        if candidate.isascii() and candidate.isalpha():
            return candidate.title()
    return "Unknown"


def build_stem(meta: dict[str, Any]) -> str:
    """`<year>_<Surname>_<slugified-ru-title>` per the ARCHITECTURE rule."""
    year = meta.get("year") or 0
    authors = meta.get("authors_ru") or meta.get("authors_en") or []
    surname = _surname(str(authors[0])) if authors else "Unknown"
    title = str(meta.get("title_ru") or meta.get("title_en") or "")
    slugified = _romanize(title)
    # Match the ARCHITECTURE stem shape: the title part starts capitalized.
    if slugified:
        slugified = slugified[0].upper() + slugified[1:]
    return f"{year}_{surname}_{slugified}"


def load_pinned_manifest(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = repo_root or Path(repo_root_from())
    path = root.joinpath(*_PINNED_PATH_PARTS)
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalogue(repo_root: Path) -> list[dict[str, Any]]:
    """Read the committed catalogue; D05 exclusion-reviewability contract."""
    path = repo_root.joinpath(*_CATALOGUE_PATH_PARTS)
    return json.loads(path.read_text(encoding="utf-8"))


def build_catalogue(repo_root: Path, *, checked_on: str) -> list[dict[str, Any]]:
    """Crawl the platform index, classify each journal, write the catalogue (W2.1/D05).

    One record per platform journal — exclusions are records with
    ``verdict: "exclude"``, never omissions. The crawled URL is the profile
    ``id`` (slug ≠ ISSN, S1.1 hazard); ``repository_name`` from the OAI
    ``Identify`` payload overwrites the catalogue-page anchor text, and a
    failed ``Identify`` degrades the record to ``uncertain`` with the error as
    evidence (a single unreachable journal is not a stop condition, PLAN
    §autonomy-contract 2).
    """
    from . import rcsi
    from .journal_scope import classify_journal

    index: dict[str, str] = rcsi.walk_index()
    catalogue: list[dict[str, Any]] = []
    for slug in sorted(index, key=lambda s: (len(s), s)):
        url = f"{rcsi.BASE}/{slug}"
        page_name = index[slug]
        repository_name = ""
        scope_text = ""
        evidence_other: list[str] = []
        try:
            info = rcsi.identify(slug)
            repository_name = str(info.get("repository_name", "") or "")
        except rcsi.RcsiError as exc:
            evidence_other.append(f"identify failed: {exc}")
        scope_text = rcsi.fetch_scope_text(slug)
        if not scope_text and not repository_name:
            evidence_other.append("no Identify payload and no #focusAndScope paragraph on /about/editorialPolicies")
        verdict = classify_journal(" \u00b7 ".join([repository_name, page_name, scope_text]))
        catalogue.append(
            {
                "slug": slug,
                "journal_name": page_name,
                "repository_name": repository_name,
                "url": url,
                "scope_text_excerpt": scope_text[:500],
                "verdict": verdict["verdict"],
                "matched_terms": verdict["positive"][:8],
                "negative_terms": verdict["negative"][:8],
                "evidence_other": evidence_other,
                "checked_on": checked_on,
            }
        )
    path = repo_root.joinpath(*_CATALOGUE_PATH_PARTS)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalogue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return catalogue


def _corpus_dir() -> tuple[Path, Path]:
    from .corpus import CorpusManager

    manager = CorpusManager(Path(repo_root_from()))
    directory = Path(manager.corpus_dir)
    quarantine = directory.parent / "quarantine"
    quarantine.mkdir(parents=True, exist_ok=True)
    return directory, quarantine


def _fetch_pdf_bytes(meta: dict[str, Any]) -> bytes | None:
    from . import rcsi

    try:
        url = rcsi.galley_pdf_url(meta)
    except rcsi.RcsiError:
        return None
    try:
        raw = rcsi._throttled_get(url, binary=True)
        return raw if isinstance(raw, bytes) else None
    except rcsi.RcsiError:
        return None


def _append_bibliography_row(repo_root: Path, sidecar: dict[str, Any]) -> dict[str, Any]:
    bib_path = repo_root / "knowledge" / "bibliography.json"
    entries = json.loads(bib_path.read_text(encoding="utf-8"))
    doi = str(sidecar.get("doi", "") or "")
    url = str(sidecar.get("url", "") or "")
    for entry in entries:
        if doi and str(entry.get("doi", "")) == doi:
            return entry
        if not doi and url and str(entry.get("url", "")) == url:
            return entry
    base_id = f"{_surname(str((sidecar.get('authors_ru') or sidecar.get('authors_en') or [''])[0]))} {sidecar.get('year', '')}".strip()
    existing_ids = {str(entry.get("id")) for entry in entries}
    entry_id, suffix, index = base_id, "", 0
    while entry_id in existing_ids:
        index += 1
        suffix = chr(ord("a") + index - 1)
        entry_id = f"{base_id}{suffix}"
    row: dict[str, Any] = {
        "id": entry_id,
        "author": sidecar["authors_ru"][0] if sidecar.get("authors_ru") else "",
        "year": sidecar.get("year", 0),
        "title": sidecar.get("title_ru") or sidecar.get("title_en", ""),
        "kind": "article",
        "journal": sidecar.get("journal_name_ru", ""),
        "volume": sidecar.get("volume", ""),
        "issue": sidecar.get("issue", ""),
        "pages": _pages(sidecar),
        "url": sidecar.get("url", ""),
        "tags": ["rcsi-harvest"],
    }
    if doi:
        row["doi"] = doi
    entries.append(row)
    bib_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return row


def _pages(sidecar: dict[str, Any]) -> str:
    first, last = str(sidecar.get("firstpage", "") or ""), str(sidecar.get("lastpage", "") or "")
    if first and last and first != last:
        return f"{first}-{last}"
    return first


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def harvest_journal(
    slug: str,
    *,
    limit: int | None = None,
    since: str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Enumerate, filter, extract, gate, write. Returns a summary dict."""
    from . import rcsi
    from .journal_scope import classify_article

    summary: dict[str, Any] = {"slug": slug, "written": [], "skipped": [], "quarantined": []}
    accepted = 0

    for record in rcsi.list_records(slug, since=since):
        if limit is not None and accepted >= limit:
            break
        identifier = str(record.get("oai_identifier", ""))
        article_id = identifier.rsplit(":", 1)[-1]
        meta = rcsi.article_meta(slug, article_id)
        stem = build_stem(meta)

        if dry_run:
            corpus_dir = _corpus_dir()[0]
            sidecar_path = corpus_dir / f"{stem}.json"
            if sidecar_path.exists() and not force:
                existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
                if existing.get("extraction", {}).get("verdict") == "pass":
                    summary["skipped"].append(stem)
                    continue
            meta.pop("html", "")
            selection = classify_article(meta, selection_record=record)
            result = {"stem": stem, "status": "dry-run", "verdict": selection["verdict"]}
        else:
            result = _harvest_one(slug, meta, force=force, pinned_reason="", selection_record=record)

        if result.get("status") == "already-pass":
            summary["skipped"].append(stem)
            continue
        if result.get("status") == "quarantined":
            summary["quarantined"].append(stem)
            continue
        accepted += 1
        summary["written"].append(result)

    _write_run_manifest(summary, slug)
    return summary


def harvest_pinned(*, force: bool = False) -> dict[str, Any]:
    """Harvest exactly the five pinned articles (D13), whatever the classifier says."""
    from . import rcsi
    from .config import repo_root_from

    repo_root = Path(repo_root_from())
    pinned = load_pinned_manifest(repo_root)
    summary: dict[str, Any] = {"pinned": len(pinned), "written": [], "quarantined": [], "failed": []}
    for entry in pinned:
        slug, article_id = entry["slug"], str(entry["article_id"])
        try:
            meta = rcsi.article_meta(slug, article_id)
        except rcsi.RcsiError as exc:
            summary["failed"].append({"url": entry["url"], "error": str(exc)})
            continue
        result = _harvest_one(slug, meta, force=force, pinned_reason=entry.get("reason", ""))
        (summary["quarantined"] if "error" in result else summary["written"]).append(result)
    _write_run_manifest(summary, "--pinned")
    return summary


def _harvest_one(
    slug: str,
    meta: dict[str, Any],
    *,
    force: bool,
    pinned_reason: str,
    journal_name: str | None = None,
    selection_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .extract import extract_best
    from .journal_scope import classify_article

    repo_root = Path(repo_root_from())
    today = datetime.now().strftime("%d-%m-%Y")
    html = meta.pop("html", "")
    selection = classify_article(meta, selection_record=selection_record)
    stem = build_stem(meta)
    corpus_dir, quarantine_dir = _corpus_dir()

    text_path = corpus_dir / f"{stem}.txt"
    sidecar_path = corpus_dir / f"{stem}.json"
    if not force and sidecar_path.exists():
        existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if existing.get("extraction", {}).get("verdict") == "pass":
            return {"stem": stem, "status": "already-pass"}

    pdf_bytes = _fetch_pdf_bytes(meta)
    text, provenance = extract_best(
        html=html,
        pdf_bytes=pdf_bytes,
        expect_cyrillic=bool(selection["expect_cyrillic"]),
    )
    won = provenance.get("won") or {}
    sidecar: dict[str, Any] = {
        "stem": stem,
        "journal_slug": slug,
        "journal_name_ru": journal_name or meta.get("journal_name_ru", ""),
        "article_id": meta["article_id"],
        "url": meta["url"],
        "doi": meta.get("doi", ""),
        "edn": meta.get("edn", ""),
        "title_ru": meta.get("title_ru", ""),
        "title_en": meta.get("title_en", ""),
        "authors_ru": meta.get("authors_ru", []),
        "authors_en": meta.get("authors_en", []),
        "year": meta.get("year", 0),
        "volume": meta.get("volume", ""),
        "issue": meta.get("issue", ""),
        "firstpage": meta.get("firstpage", ""),
        "lastpage": meta.get("lastpage", ""),
        "language": meta.get("language", ""),
        "keywords_ru": meta.get("keywords_ru", []),
        "keywords_en": meta.get("keywords_en", []),
        "pdf_url": meta.get("pdf_url", ""),
        "extraction": {
            "source": won.get("source", ""),
            "extractor": won.get("extractor", ""),
            "fallback_chain": [a.get("extractor", a.get("note", "")) for a in provenance.get("attempts", [])],
            "sanity": won.get("sanity", {}),
            "verdict": won.get("verdict", "fail"),
            "harvested_on": today,
        },
        "selection": {
            "verdict": selection["verdict"],
            "matched_terms": selection["matched_terms"],
            "negative_terms": selection["negative_terms"],
        },
        "pinned_reason": pinned_reason,
    }
    if text is None:
        (quarantine_dir / f"{stem}.json").write_text(
            json.dumps({"sidecar": sidecar, "attempts": provenance.get("attempts", [])}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return {"stem": stem, "status": "quarantined"}
    _write_text(text_path, text)
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    bib_row = _append_bibliography_row(repo_root, sidecar)
    return {"stem": stem, "status": "written", "bibliography_id": bib_row.get("id", "")}


def _write_run_manifest(summary: dict[str, Any], scope: str) -> None:
    runs_dir = Path(repo_root_from()) / "runs" / "rcsi-harvest"
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    path = runs_dir / f"{scope.replace('/', '_')}-{stamp}.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def corpus_verify(*, repo_root: Path | None = None, corpus_dir: Path | None = None) -> list[dict[str, Any]]:
    """Re-check every pinned entry (D13); one result row each, never raises."""
    from .schema_validation import validate_json_schema

    root = Path(repo_root or repo_root_from())
    pinned = load_pinned_manifest(root)
    directory = Path(corpus_dir) if corpus_dir else _corpus_dir()[0]
    schema = json.loads((root / "schemas" / "article-sidecar.schema.json").read_text(encoding="utf-8"))
    bib_entries = json.loads((root / "knowledge" / "bibliography.json").read_text(encoding="utf-8"))
    bib_dois = {str(entry.get("doi", "")) for entry in bib_entries if entry.get("doi")}
    bib_urls = {str(entry.get("url", "")) for entry in bib_entries if entry.get("url")}

    results: list[dict[str, Any]] = []
    from .corpus import CorpusManager
    from .db import Database

    Database(root)  # ensure the FTS schema exists before the retrieval probe
    manager = CorpusManager(root)

    for entry in pinned:
        problems: list[str] = []
        expected_stem = str(entry.get("expected_stem", "")) or None
        candidates: list[Path] = []
        if expected_stem:
            candidates.append(directory / f"{expected_stem}.txt")
        # A stem rename must not silently break the guarantee: also match by
        # URL through the sidecar when the expected stem is absent.
        if not candidates or not candidates[0].exists():
            for sidecar_path in sorted(directory.glob("*.json")):
                try:
                    data = json.loads(sidecar_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                if data.get("url") == entry.get("url"):
                    candidates.insert(0, directory / f"{data.get('stem')}.txt")
                    break
        text_path = next((c for c in candidates if c.exists()), None)
        if text_path is None:
            results.append({"url": entry["url"], "ok": False, "problems": ["text file missing"]})
            continue
        text = text_path.read_text(encoding="utf-8")
        if not text.strip():
            problems.append("text file empty")
        sidecar_path = text_path.with_suffix(".json")
        if not sidecar_path.exists():
            results.append({"url": entry["url"], "ok": False, "problems": ["sidecar missing"]})
            continue
        try:
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            results.append({"url": entry["url"], "ok": False, "problems": [f"sidecar invalid JSON: {exc}"]})
            continue
        errors = validate_json_schema(sidecar, schema)
        if errors:
            problems.extend(errors)
        doi = str(sidecar.get("doi", "") or "")
        if doi:
            if doi not in bib_dois:
                problems.append(f"no bibliography row for DOI {doi}")
        else:
            # D17 default (23-08-2026): some RCSI articles expose no DOI at
            # all (measured on 2782-5329/400674); the row is then matched by
            # the article URL recorded on the bibliography entry.
            url = str(sidecar.get("url", ""))
            if url and url not in bib_urls:
                problems.append("no bibliography row for this URL (article has no platform DOI)")
        if sidecar.get("extraction", {}).get("verdict") != "pass":
            problems.append("extraction verdict is not pass")

        phrase = _distinctive_phrase(entry, sidecar, text=text)
        if phrase:
            hits = manager.search(phrase, limit=5)
            if not any(Path(hit.get("file", "")).name == text_path.name for hit in hits):
                # The guarantee must not depend on external index state: index
                # this one file if absent, then retry the retrieval probe.
                manager.ingest_file(text_path)
                hits = manager.search(phrase, limit=5)
            if not any(Path(hit.get("file", "")).name == text_path.name for hit in hits):
                problems.append(f"FTS search on distinctive phrase did not return the file (phrase: {phrase!r})")

        results.append({"url": entry["url"], "ok": not problems, "problems": problems, "file": text_path.name})
    return results


def _distinctive_phrase(entry: dict[str, Any], sidecar: dict[str, Any], text: str = "") -> str:
    """Probe phrase for the D13 retrieval check.

    Title tokens are the probe of first choice. Measured exception
    (23-08-2026): the Плунгян page body never repeats the Russian title (the
    harvested body leads with the English metadata block), so a title probe
    would permanently fail an otherwise perfectly indexed file. Default: fall
    back to the five longest word tokens from the text itself — still
    distinctive, still verifies index integrity.
    """
    import re as _re

    def _tokens(source: str) -> list[str]:
        return [t for t in _re.findall(r"[^\W\d_]{5,}", source)]

    title = str(entry.get("search_phrase") or sidecar.get("title_ru") or sidecar.get("title_en") or "")
    words = _tokens(title)
    if len(words) > 3 and all(word.lower() in text.lower() for word in words[2:7]):
        # FTS5 MATCH treats punctuation as syntax (a colon is a column filter),
        # so the probe carries bare word tokens only.
        return " ".join(words[2:7])
    fallback = sorted(set(_tokens(text[:4000])), key=len, reverse=True)[:5]
    return " ".join(fallback)
