"""HTTP client for journals.rcsi.science (RCSI/PKP-OJS platform).

Everything network lives here and nowhere else (`harvest.py` orchestrates but
never fetches; `journal_scope.py` never sees a URL). Three measured platform
facts shape this module (PLAN §platform-facts, H3153 bake-off):

1. The UA prescribed by the original plan draft is 403'd site-wide, while a
   common browser UA is served 200 on the same URLs in the same second. This
   module therefore sends a browser-shaped UA and keeps the polite 1 req/s
   throttle.
2. Site-wide OAI is broken (``/index/oai`` raises an SQL error); harvesting is
   per journal via ``{slug}/oai``.
3. The URL slug is not always the metadata ISSN (slug ``0869-5873`` carries
   ``citation_issn`` ``3034-5200``) — callers key on the slug.

The cache is on-disk, keyed by SHA-1 of the URL, under the scratch cache dir
(``RWS_RCSI_CACHE_DIR``, default a ``rcsi-cache/`` folder beside the system
temp dir) — never inside the public repo (D18).
"""

from __future__ import annotations

import hashlib
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterator
from xml.etree import ElementTree

__all__ = [
    "BASE",
    "USER_AGENT",
    "RcsiError",
    "RcsiRateLimited",
    "fetch",
    "identify",
    "list_records",
    "article_meta",
    "galley_pdf_url",
]

BASE = "https://journals.rcsi.science"

# Measured 19-08-2026: the plan's research-harvester UA is 403'd site-wide while
# a browser UA is served. Revisit only if the platform grants an allowance.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

_MIN_INTERVAL_SECONDS = 1.0
_LAST_REQUEST_MONOTON = [0.0]


class RcsiError(RuntimeError):
    """A fetch against the RCSI platform failed for a non-transient reason."""


class RcsiRateLimited(RcsiError):
    """HTTP 429 or 403 from the platform edge."""


def _cache_dir() -> Path:
    env = os.environ.get("RWS_RCSI_CACHE_DIR")
    if env:
        return Path(env)
    return Path(os.environ.get("TEMP", "/tmp")) / "opencode" / "rcsi-cache"


def _throttled_get(url: str, *, binary: bool = False, use_cache: bool = True) -> bytes | str:
    cache_key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    cache_path = _cache_dir() / f"{cache_key}{'' if binary else '.txt'}"
    if use_cache and cache_path.exists():
        data = cache_path.read_bytes()
        return data if binary else data.decode("utf-8", errors="replace")

    wait = _MIN_INTERVAL_SECONDS - (time.monotonic() - _LAST_REQUEST_MONOTON[0])
    if wait > 0:
        time.sleep(wait)

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
            _LAST_REQUEST_MONOTON[0] = time.monotonic()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(raw)
            return raw if binary else raw.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:  # pragma: no cover - live-path
            _LAST_REQUEST_MONOTON[0] = time.monotonic()
            if exc.code in (429, 403):
                raise RcsiRateLimited(f"{exc.code} for {url}") from exc
            if 500 <= exc.code < 600:
                last_error = exc
                time.sleep(2.0 * (attempt + 1))
                continue
            raise RcsiError(f"HTTP {exc.code} for {url}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - live-path
            last_error = exc
            time.sleep(2.0 * (attempt + 1))
    raise RcsiError(f"GET failed after retries: {url}") from last_error


_OAI_NS = "{http://www.openarchives.org/OAI/2.0/}"
_DC_NS = "{http://purl.org/dc/elements/1.1/}"

# Measured 23-08-2026: the live Вестник РАН ListRecords payload carries a raw
# NUL byte inside an abstract — the platform's own XML is occasionally not
# well-formed. Strip C0 controls (except tab/LF/CR) before parsing instead of
# failing the whole walk over one bad abstract.
_XML_UNSAFE_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _parse_oai(text: str | bytes) -> "ElementTree.Element":
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    return ElementTree.fromstring(_XML_UNSAFE_CONTROLS.sub("", text))


def identify(slug: str) -> dict[str, Any]:
    """OAI Identify for one journal."""
    root = _parse_oai(_throttled_get(f"{BASE}/{slug}/oai?verb=Identify"))
    ident = root.find(f"{_OAI_NS}Identify")
    if ident is None:
        error = root.find(f"{_OAI_NS}error")
        if error is not None:
            raise RcsiError(f"Identify failed for {slug}: [{error.get('code', 'error')}] {(error.text or '').strip()}")
        raise RcsiError(f"Identify failed for {slug}: no Identify element")
    def _t(tag: str) -> str:
        node = ident.find(f"{_OAI_NS}{tag}")
        return (node.text or "").strip() if node is not None and node.text else ""
    base = ident.find(f"{_OAI_NS}baseURL")
    return {
        "repository_name": _t("repositoryName"),
        "earliest_datestamp": _t("earliestDatestamp"),
        "admin_email": _t("adminEmail"),
        "oai_base": (base.text or "").strip() if base is not None else "",
    }


def list_records(slug: str, *, since: str | None = None, max_records: int | None = None) -> Iterator[dict[str, Any]]:
    """Yield Dublin Core records via OAI ListRecords, following resumptionToken."""
    token: str | None = None
    yielded = 0
    while True:
        params = [f"verb=ListRecords&metadataPrefix=oai_dc"]
        if token:
            params = [f"verb=ListRecords&resumptionToken={token}"]
        elif since:
            params.append(f"from={since}")
        root = _parse_oai(_throttled_get(f"{BASE}/{slug}/oai?{'&'.join(params)}"))
        records = root.findall(f".//{_OAI_NS}record")
        for record in records:
            header = record.find(f"{_OAI_NS}header")
            if header is None or header.get("status") == "deleted":
                continue
            identifier_node = header.find(f"{_OAI_NS}identifier")
            datestamp_node = header.find(f"{_OAI_NS}datestamp")
            entry: dict[str, Any] = {
                "oai_identifier": (identifier_node.text or "").strip() if identifier_node is not None else "",
                "datestamp": (datestamp_node.text or "").strip() if datestamp_node is not None else "",
            }
            for element in record.findall(f".//{_DC_NS}*"):
                tag = element.tag.split("}", 1)[-1]
                value = (element.text or "").strip()
                if not value:
                    continue
                entry.setdefault(tag, [])
                existing = entry[tag]
                if isinstance(existing, list):
                    existing.append(value)
            yield entry
            yielded += 1
            if max_records is not None and yielded >= max_records:
                return
        token_node = root.find(f".//{_OAI_NS}resumptionToken")
        token = (token_node.text or "").strip() if token_node is not None and token_node.text else ""
        if not token:
            return


_CITATION_META_RE = re.compile(r"citation_(?P<key>[a-z_]+?)(?:_(?P<lang>ru|en|ru-RU|en-US))?$", re.IGNORECASE)


def article_meta(slug: str, article_id: str) -> dict[str, Any]:
    """Parse every citation_* meta tag off one article page.

    ru/en variants stay separate (``title_ru`` / ``title_en``); repeated tags
    without language variants (authors, keywords) accumulate into lists.
    Returns the sidecar-shaped dict plus the raw HTML for the extractor.
    """
    url = f"{BASE}/{slug}/article/view/{article_id}"
    html = _throttled_get(url)
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RcsiError(
            "bs4 is required to parse citation_* metadata — install the [harvest] extra"
        ) from exc
    soup = BeautifulSoup(html, "html.parser")
    flat_lists = {"author", "keywords", "affiliation"}
    fields: dict[str, Any] = {}
    lang_variants: dict[tuple[str, str], list[str]] = {}

    for meta in soup.find_all("meta"):
        name = meta.get("name") or ""
        if not name.lower().startswith("citation_"):
            continue
        content = (meta.get("content") or "").strip()
        if not content:
            continue
        match = _CITATION_META_RE.match(name.lower())
        if match is None:
            key = name.lower()[len("citation_"):]
            fields.setdefault(key, [])
            if isinstance(fields[key], list):
                fields[key].append(content)
            continue
        key = match.group("key")
        lang = (match.group("lang") or "").split("-")[0].lower()
        if lang in ("ru", "en"):
            lang_variants.setdefault((key, lang), []).append(content)
        elif key in flat_lists:
            fields.setdefault(key, []).append(content)
        else:
            fields[key] = content

    def _one(key: str, lang: str) -> str:
        values = lang_variants.get((key, lang))
        if values:
            return values[0]
        # Fall back to the unsuffixed tag: the platform emits plain
        # citation_title in the article's primary language plus *_en variants
        # when a translated title exists.
        value = fields.get(key)
        if isinstance(value, str) and value:
            return value
        return ""

    def _many(key: str, lang: str | None) -> list[str]:
        # The platform usually emits plain repeated citation_author /
        # citation_keywords without a language suffix; language-suffixed
        # variants win when present, the plain list is the fallback.
        if lang is not None:
            values = lang_variants.get((key, lang))
            if values:
                return values
        plain = fields.get(key, [])
        return plain if isinstance(plain, list) else ([plain] if plain else [])

    doi = str(fields.get("doi", "") or "")
    meta_out: dict[str, Any] = {
        "journal_slug": slug,
        "article_id": str(article_id),
        "url": url,
        "doi": doi,
        "edn": str(fields.get("edn", "") or ""),
        "title_ru": _one("title", "ru"),
        "title_en": _one("title", "en"),
        "authors_ru": _many("author", "ru"),
        "authors_en": _many("author", "en"),
        "year": int(str(fields.get("date", "") or "")[:4] or 0),
        "volume": str(fields.get("volume", "") or ""),
        "issue": str(fields.get("issue", "") or ""),
        "firstpage": str(fields.get("firstpage", "") or ""),
        "lastpage": str(fields.get("lastpage", "") or ""),
        "language": str(fields.get("language", "") or "").split("-")[0],
        "keywords_ru": _many("keywords", "ru"),
        "keywords_en": _many("keywords", "en"),
        "issn": str(fields.get("issn", "") or ""),
        "pdf_url": str(fields.get("pdf_url", "") or ""),
    }
    meta_out["html"] = html
    return meta_out


def galley_pdf_url(meta: dict[str, Any]) -> str:
    """Return citation_pdf_url verbatim; never reconstruct it."""
    url = str(meta.get("pdf_url", "") or "")
    if not url:
        raise RcsiError(f"article {meta.get('article_id')} exposes no citation_pdf_url")
    return url
