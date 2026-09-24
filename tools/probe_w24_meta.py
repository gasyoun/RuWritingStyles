"""One-off live probe: does article_meta still parse a known-good pinned article?"""
from __future__ import annotations

import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "src")

from ruwritingstyles import rcsi

meta = rcsi.article_meta("0373-658X", "261465")
for key in ("title_ru", "title_en", "year", "doi", "url", "authors_ru"):
    print(key, "=", repr(meta.get(key))[:120])
html = meta.get("html", "")
print("html length:", len(html))
print("citation_ occurrences in html:", html.count("citation_"))
print(html[:400])
